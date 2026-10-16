# Qwen-Image-2.1 昇腾 910B 内网离线部署指南

## 前提条件
- 内网服务器已安装 Docker 与 docker-compose。
- 已通过 `docker load` 加载镜像 `quay.nju.edu.cn/ascend/vllm-omni:v0.28.0`。
- 已将以下文件放入宿主机 `/xxx/Qwen-Image-2.1-deploy-pro/deploy/` 目录：
  - `diffusers-main.tar.gz`（从 GitHub main 分支下载）
  - `transformers-5.17.0-py3-none-any.whl`（从 PyPI 下载）
  - `docker-compose.yml`
  - `vllm-omni.conf`
  - `deploy/patches/patch_rope.py`
  - `deploy/patches/patch_rope3.py`
  - `deploy/start_service.sh`
- 模型权重已放在宿主机 `/opt/data/models/Qwen-Image-2.1`。

## 目录结构
```
Qwen-Image-2.1-deploy-pro/
└── deploy/
    ├── docker-compose.yml
    ├── patches/
    │   ├── patch_rope.py
    │   └── patch_rope3.py
    ├── start_service.sh
    ├── diffusers-main.tar.gz
    └── transformers-5.17.0-py3-none-any.whl
```

## 部署步骤

### 1. 启动容器
```bash
cd /xxx/Qwen-Image-2.1-deploy-pro/deploy
docker-compose up -d
```

### 2. 进入容器
```bash
docker-compose exec vllm-omni-qwen bash
```

### 3. 离线安装 diffusers 源码与 transformers
**注意：必须先安装 diffusers 源码，再打补丁，否则补丁会打在旧版 diffusers 上并被覆盖。**
```bash
# 解压 diffusers 源码到 /vllm-workspace/
tar xf /workspace/deploy/diffusers-main.tar.gz -C /vllm-workspace/

# 安装 diffusers main 源码
pip install /vllm-workspace/diffusers-main/

# 离线安装 transformers 5.17.0
pip install /workspace/deploy/transformers-5.17.0-py3-none-any.whl
```

### 4.（可选）备份 diffusers 源码
补丁脚本会**自动**把被打补丁的文件备份到
`/vllm-workspace/diffusers-main.bak/...`，此步可跳过。
如需保留整份源码的干净备份，可执行：
```bash
cp -r /vllm-workspace/diffusers-main /vllm-workspace/diffusers-main.bak
```
`.bak` 仅用于恢复与对照，**不参与运行**，补丁脚本会跳过它。

### 5. 应用 NPU 补丁（按顺序执行）
```bash
python /workspace/deploy/patches/patch_rope.py
python /workspace/deploy/patches/patch_rope3.py
```
两个脚本均已**幂等**（重复执行安全）：
- 首次运行自动创建 `.bak` 备份（先备份、后补丁）。
- 已打过的补丁自动跳过。
- 单条补丁 MISS 不会阻塞其余补丁的保存。

> 本补丁来自 Ascend-SACT/Qwen-Image-2.1 开源项目，本项目对其做了修改与
> bug 修复（原 `patch_rope3.py` 在 `sys.exit(1)` 前未保存文件，导致补丁数
> 停在 4）。若本脚本仍报 [MISS]，说明 diffusers 版本不兼容，请参考原项目。

### 6. 验证补丁是否生效（期望输出 5）
```bash
bash -c 'P=$(python3 -c "import diffusers,os;print(os.path.join(os.path.dirname(diffusers.__file__),\"models/transformers/transformer_qwenimage21.py\"))"); grep -c "npu patch" "$P"'
```
如果输出不是 5，请检查 diffusers 是否安装成功，以及补丁脚本是否与当前 diffusers main 兼容。

### 7. 启动推理服务（后台）
```bash
nohup bash /workspace/deploy/start_service.sh > /tmp/qwen_image_2_1_vllm.log 2>&1 &
```

### 8. 等待约 1 分钟后检查日志
```bash
grep "Application startup complete" /tmp/qwen_image_2_1_vllm.log
```
