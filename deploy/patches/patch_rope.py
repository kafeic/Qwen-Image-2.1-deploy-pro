#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPU 兼容补丁（第 1 轮）—— QwenImage21 ROPE 浮点化
================================================================

⚠️ 相对原参考项目的修改说明
----------------------------------------------------------------
本补丁来自 Ascend-SACT/Qwen-Image-2.1 开源项目（地址见 README 致谢），
本项目在其基础上做了「修改 + bug 修复」，主要差异：

  1. 原脚本 targets 同时包含「已安装文件」与 `.bak` 备份，且未创建 `.bak`；
     文件不存在时 `open()` 会直接抛 FileNotFoundError 崩溃。
     → 本版本只修补「已安装文件」，`.bak` 保持原始、不参与运行，
       并在首次运行时自动创建备份。
  2. 原脚本不幂等：重复执行会命中 [MISS] 后 `sys.exit(1)`。
     → 本版本重复执行安全，已打过的补丁自动跳过。
  3. 原脚本单条 MISS 即中断，可能导致其余补丁未保存。
     → 本版本单条 MISS 仅告警，不阻塞其余条目的保存。

如果本补丁脚本在你的 diffusers 版本上仍报 [MISS]，说明版本不兼容，
请参考原项目补丁自行核对目标代码。

================================================================
本脚本只修补「已安装」的 diffusers 文件（INSTALLED），并把原始文件
备份到 BACKUP（.bak）。备份保持原始版本、不参与运行，仅用于恢复对照。

用法：
    python /workspace/deploy/patches/patch_rope.py

前提：
    pip install /vllm-workspace/diffusers-main/
"""
import os
import shutil
import sys

# 已安装的 diffusers 文件（运行时实际加载的路径）
INSTALLED = "/usr/local/python3.12.13/lib/python3.12/site-packages/diffusers/models/transformers/transformer_qwenimage21.py"

# 原始文件备份（保持干净，不参与运行）
BACKUP = "/vllm-workspace/diffusers-main.bak/src/diffusers/models/transformers/transformer_qwenimage21.py"

# (旧代码片段, 新代码片段) 列表
EDITS = [
    # 1) rope_params: 去掉 torch.polar，保留纯浮点角度
    (
        "        freqs = torch.outer(index, 1.0 / torch.pow(theta, torch.arange(0, dim, 2).to(torch.float32).div(dim)))\n"
        "        return torch.polar(torch.ones_like(freqs), freqs)",
        "        freqs = torch.outer(index, 1.0 / torch.pow(theta, torch.arange(0, dim, 2).to(torch.float32).div(dim)))\n"
        "        return freqs  # npu patch: real angles instead of torch.polar complex",
    ),
    # 2) rope forward: 返回 (cos, sin) 浮点元组，替代复数拼接
    (
        "        return torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)",
        "        angles = torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)\n"
        "        return (torch.cos(angles), torch.sin(angles))  # npu patch",
    ),
    # 3) decode 时对 tuple 形式的 rotary_emb 切片
    (
        "            rotary_emb = rotary_emb[prefix_len:]",
        "            rotary_emb = (rotary_emb[0][prefix_len:], rotary_emb[1][prefix_len:])  # npu patch",
    ),
    # 4) apply_rotary: 复数路径 -> 浮点 rotate-half（数值等价），910B 上避免复数算子
    (
        "        query = apply_rotary_emb_qwen(query, rotary_emb, use_real=False)\n"
        "        key = apply_rotary_emb_qwen(key, rotary_emb, use_real=False)",
        "        query = apply_rotary_emb_qwen(query, rotary_emb, use_real=True)\n"
        "        key = apply_rotary_emb_qwen(key, rotary_emb, use_real=True)  # npu patch",
    ),
]


def ensure_backup(target: str, backup: str) -> bool:
    """确保 .bak 备份存在（先备份、后补丁，幂等）。"""
    if os.path.exists(backup):
        return True
    if not os.path.exists(target):
        print(f"[MISS] 找不到已安装的 diffusers 文件：\n    {target}")
        print("       请先执行：pip install /vllm-workspace/diffusers-main/")
        return False
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    shutil.copyfile(target, backup)
    print(f"[BAK] 已创建备份：{backup}")
    return True


def apply_edits(target: str) -> bool:
    """逐个应用补丁，幂等；单条失败不阻塞其余条目的保存。"""
    with open(target, encoding="utf-8") as f:
        src = f.read()
    changed: list[int] = []
    all_ok = True
    for i, (old, new) in enumerate(EDITS, 1):
        if new in src:
            print(f"[SKIP] edit {i} 已打过补丁")
            continue
        if old in src:
            src = src.replace(old, new, 1)
            changed.append(i)
            print(f"[OK]   edit {i} 应用成功")
        else:
            all_ok = False
            print(f"[MISS] edit {i} 找不到目标代码（版本不一致或已被修改）：\n    {old[:70]!r}")
    if changed:
        with open(target, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"[SAVE] 已写入：{target}")
    else:
        print("[SAVE] 无改动，文件未写入")
    return all_ok


def main():
    if not os.path.exists(INSTALLED):
        print(f"[MISS] 找不到已安装的 diffusers 文件：\n    {INSTALLED}")
        print("       请先执行：pip install /vllm-workspace/diffusers-main/")
        sys.exit(2)
    if not ensure_backup(INSTALLED, BACKUP):
        sys.exit(2)

    all_ok = apply_edits(INSTALLED)

    with open(INSTALLED, encoding="utf-8") as f:
        src = f.read()
    count = sum(1 for _, new in EDITS if new in src)
    print(f"[DONE] 第 1 轮补丁已应用 {count}/{len(EDITS)} 条")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
