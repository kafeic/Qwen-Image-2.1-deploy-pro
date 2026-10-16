#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPU 兼容补丁（第 2 轮）—— apply_rotary_emb_qwen 多头安全 float 分支
================================================================

⚠️ 相对原参考项目的修改说明
----------------------------------------------------------------
本补丁来自 Ascend-SACT/Qwen-Image-2.1 开源项目（地址见 README 致谢）。
原脚本存在一个会导致「补丁数停在 4」的 bug，本版本已修复：

  原代码：
      if ok != 3:
          sys.exit(1)          # ← 先退出
      open(f, "w").write(src)  # ← 这行永远没执行，edit B 被丢弃

  由于第 1 轮 patch_rope.py 已把 rope forward 改成 (cos, sin)，
  本脚本的 edit A 必然 MISS（ok 只到 2），于是原脚本直接退出、
  edit B 的替换结果未写盘 —— 这就是补丁数停在 4 的原因。

  本版本：先保存、后退出；edit A 若已等效则跳过；单条 MISS 不阻塞保存；
  并自动创建 `.bak` 备份（若缺失）。

如果本补丁脚本在你的 diffusers 版本上仍报 [MISS] edit B，说明版本不兼容，
请参考原项目补丁自行核对目标代码。

================================================================
依赖：请先执行第 1 轮 patch_rope.py，再执行本脚本。

用法：
    python /workspace/deploy/patches/patch_rope3.py
"""
import os
import shutil
import sys

# 已安装的 diffusers 文件（运行时实际加载的路径）
INSTALLED = "/usr/local/python3.12.13/lib/python3.12/site-packages/diffusers/models/transformers/transformer_qwenimage21.py"

# 原始文件备份（保持干净，不参与运行）
BACKUP = "/vllm-workspace/diffusers-main.bak/src/diffusers/models/transformers/transformer_qwenimage21.py"

# --- edit A: rope forward -> 统一的 (cos, sin) [S, D_pair] ---
# 注意：patch_rope.py 的 edit 2 已把该处改成 (cos, sin)，此处仅负责把
# repeat_interleave 的旧写法修正为一致的写法；若已等效则直接跳过。
old_rope = """        angles = torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)
        return (
            torch.cos(angles).repeat_interleave(2, dim=-1),  # [S, dim]; matches rotate-half pair layout
            torch.sin(angles).repeat_interleave(2, dim=-1),
        )  # npu patch"""
new_rope = """        angles = torch.cat([self.freqs[0][frame_index], self.freqs[1][height_index], self.freqs[2][width_index]], dim=-1)
        return (torch.cos(angles), torch.sin(angles))  # npu patch: (cos, sin) each [S, D_pair]"""

# --- edit B: apply_rotary_emb_qwen -> float multi-head branch (complex-path equivalent) ---
old_fn = """    if use_real:
        cos, sin = freqs_cis  # [S, D]
        cos = cos[None, None]
        sin = sin[None, None]
        cos, sin = cos.to(x.device), sin.to(x.device)

        if use_real_unbind_dim == -1:"""
new_fn = """    if use_real:
        cos, sin = freqs_cis  # [S, D_pair]
        cos, sin = cos.to(x.device), sin.to(x.device)

        if isinstance(freqs_cis, tuple) and use_real_unbind_dim == -1:
            # npu patch: float-only equivalent of the complex path (multi-head safe).
            #   complex path: x_rot = view_as_complex(x.reshape(..., -1, 2))
            #                x_out = view_as_real(x_rot * freqs_cis.unsqueeze(1)).flatten(3)
            #   broadcast [S,1,D_pair] aligns with [B,S,H,D_pair] (H vs 1), so this
            #   works for QwenImage21's 32 heads, unlike the single-head real path.
            cos = cos.unsqueeze(1)  # [S, 1, D_pair]
            sin = sin.unsqueeze(1)
            x_real, x_imag = x.reshape(*x.shape[:-1], -1, 2).unbind(-1)  # [B, S, H, D_pair]
            x_real, x_imag = x_real.float(), x_imag.float()
            real = x_real * cos - x_imag * sin
            imag = x_imag * cos + x_real * sin
            return torch.stack([real, imag], dim=-1).flatten(-2).to(x.dtype)

        cos = cos[None, None]
        sin = sin[None, None]

        if use_real_unbind_dim == -1:"""


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


def apply(target: str) -> bool:
    with open(target, encoding="utf-8") as f:
        src = f.read()
    changed = False
    all_ok = True

    # ---- edit A：可能已被 patch_rope.py 等效处理 ----
    if new_rope in src:
        print("[SKIP] edit A 已存在（patch_rope.py 已处理）")
    elif old_rope in src:
        src = src.replace(old_rope, new_rope, 1)
        changed = True
        print("[OK]   edit A 应用成功")
    elif "torch.cos(angles), torch.sin(angles)" in src:
        # 功能上已等效（可能是 patch_rope.py 的简短注释版本），无需再改
        print("[SKIP] edit A 已等效（已存在 (cos, sin) 元组返回）")
    else:
        print("[MISS] edit A 找不到目标代码，跳过（不影响 edit B）")

    # ---- edit B：多头安全 float 分支（关键补丁，补到第 5 处） ----
    if new_fn in src:
        print("[SKIP] edit B 已存在")
    elif old_fn in src:
        src = src.replace(old_fn, new_fn, 1)
        changed = True
        print("[OK]   edit B 应用成功")
    else:
        all_ok = False
        print("[MISS] edit B 找不到目标代码，请检查 diffusers 版本是否与补丁兼容")

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
        print("       请先执行：pip install /vllm-workspace/diffusers-main/ 与 patch_rope.py")
        sys.exit(2)
    if not ensure_backup(INSTALLED, BACKUP):
        sys.exit(2)

    all_ok = apply(INSTALLED)

    with open(INSTALLED, encoding="utf-8") as f:
        src = f.read()
    count = src.count("npu patch")
    print(f"[DONE] 文件内 'npu patch' 累计数 = {count}（期望 5）")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
