#!/bin/bash
# ============================================================
# Qwen-Image-2.1 推理服务启动脚本（昇腾 910B3 单卡）
# 网络模式：bridge + 端口映射（宿主机 8014 -> 容器 8014）
# ============================================================

# 清除容器级设备可见性变量，避免与进程级冲突
unset ASCEND_VISIBLE_DEVICES

# 只使用 5 号物理卡（64G，未被占用）
export ASCEND_RT_VISIBLE_DEVICES=5

# vLLM 平台与多进程方式
export VLLM_PLATFORM=ascend
export VLLM_WORKER_MULTIPROC_METHOD=spawn

# 启动 vLLM 服务
# --host 0.0.0.0  容器内监听所有接口，接受 Docker 网桥转发
# --port 8014     容器内端口，与 docker-compose ports 的容器端口一致
# --trust-remote-code  允许加载自定义模型代码
# --diffusion-load-format diffusers  指定扩散模型加载格式
# --diffusion-attention-backend TORCH_SDPA  910B 上必须显式指定
# --tensor-parallel-size 1  单卡推理
# --gpu-memory-utilization 0.9  显存利用率
exec vllm serve /opt/data/models/Qwen-Image-2.1 \
  --omni \
  --host 0.0.0.0 \
  --port 8014 \
  --trust-remote-code \
  --diffusion-load-format diffusers \
  --diffusion-attention-backend TORCH_SDPA \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9