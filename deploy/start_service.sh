#!/bin/bash
# ============================================================
# Qwen-Image-2.1 推理服务启动脚本（昇腾 910B3 单卡）
# 网络模式：bridge + 端口映射（宿主机 8014 -> 容器 8014）
# ============================================================

# 清除容器级设备可见性变量，避免与进程级冲突
unset ASCEND_VISIBLE_DEVICES

# 只使用 5 号物理卡（64G，未被占用）
# 修改：按实际空闲卡号调整，例如 ASCEND_RT_VISIBLE_DEVICES=0
export ASCEND_RT_VISIBLE_DEVICES=5

# vLLM 平台与多进程方式
export VLLM_PLATFORM=ascend
export VLLM_WORKER_MULTIPROC_METHOD=spawn

# ============================================================
# 可选环境变量（按需取消注释）
# ============================================================
# 日志级别：INFO / DEBUG / ERROR，排查问题时建议 DEBUG
# export VLLM_LOG_LEVEL=INFO

# 是否从 ModelScope 拉取模型：0 = 不使用（使用本地权重）
# export VLLM_USE_MODELSCOPE=0

# 显存分配策略，减少碎片；910B 上推荐 expandable_segments
# export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True

# ============================================================
# 启动 vLLM 服务
# ============================================================
# --host 0.0.0.0  容器内监听所有接口，接受 Docker 网桥转发
# --port 8014     容器内端口，与 docker-compose ports 的容器端口一致
# --trust-remote-code  允许加载自定义模型代码
# --diffusion-load-format diffusers  指定扩散模型加载格式
# --diffusion-attention-backend TORCH_SDPA  910B 上必须显式指定，否则无日志挂死
# --tensor-parallel-size 1  单卡推理；多卡改为对应卡数
# --gpu-memory-utilization 0.9  显存利用率上限，OOM 时调低到 0.8

# ------------------------------------------------------------
# 可选参数（按需取消注释，追加到下方 vllm serve 命令末尾）
# ------------------------------------------------------------
# --max-num-seqs 2                 # 并发序列数：默认 1（串行）。910B 单卡建议从 2 起步，
#                                  # 2K 分辨率下容易 OOM，请配合 slicing/tiling 使用
# --request-batch-max-wait-ms 0    # 等待组批时间：0=延迟优先；20=吞吐优先
# --vae-use-slicing                # VAE 切片，降低单帧显存峰值（长序列/大图推荐）
# --vae-use-tiling                 # VAE 平铺，进一步降低显存峰值（2K 大图推荐）
# --max-model-len 32768            # 最大序列长度（含图像 token），显存不足时调低
# --block-size 128                 # KV cache 块大小，默认 128
# --enforce-eager                  # 关闭图模式，显存更省但速度略慢（排查/调试用）
# --dtype bfloat16                 # 模型精度，默认 bfloat16
# --seed 42                        # 全局随机种子，可复现
# --disable-log-requests           # 关闭逐请求日志，减少 IO 噪音
# --log-level info                 # vLLM 日志级别：debug/info/warning/error
# --num-scheduler-steps 1          # 每步调度的 batch 数，默认 1

exec vllm serve /opt/data/models/Qwen-Image-2.1 \
  --omni \
  --host 0.0.0.0 \
  --port 8014 \
  --trust-remote-code \
  --diffusion-load-format diffusers \
  --diffusion-attention-backend TORCH_SDPA \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9
