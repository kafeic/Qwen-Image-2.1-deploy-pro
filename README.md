# Qwen-Image-2.1-deploy-pro

> 在国产昇腾 910B3（单卡 64GB）上部署 Qwen-Image-2.1 图像生成模型的完整教程与工程化项目。
> 如果你更习惯 ComfyUI 的方式，很抱歉，目前没有弄。
> 补丁为 AtomGit 开源项目中获取，感谢补丁大神，原网址在下方致谢中。

---

## 📖 项目简介

本项目提供在**昇腾 910B3** 等国产 NPU 上，基于 **vLLM-Omni v0.28.0** 部署 **Qwen-Image-2.1** 的完整流程。包含：

- 外网拉取镜像、离线导出与内网加载
- 容器化启动、离线安装 diffusers 与 transformers
- 应用昇腾 NPU 兼容补丁
- 启动推理服务并验证
- 提供文生图、图像编辑、透明图生成等测试脚本
- 并发配置与调优建议

项目名称：`Qwen-Image-2.1-deploy-pro`
> 作者：kafeic
> **注意事项**：当前项目中 core 中的代码当前只是 AI 生成的示例，
> 且并未校验，未与项目结构中的对齐，当前项目只完成了部署的流程。
> 核心工作流的模块实现建议本地实践与开发，后续将会上传通用工作流。

---

## 📁 项目结构

```
Qwen-Image-2.1-deploy-pro/
├── core/                       # 自定义工作流、提示词、封装配置、client
│   ├── prompts/                # 提示词模板
│   ├── workflows/              # 工作流定义
│   ├── client.py               # API 客户端封装
│   └── config.yaml             # 核心配置
├── data/                       # 图生图待定文件夹（参考图、掩码等）
├── deploy/                     # 部署相关文件
│   ├── docker-compose.yml      # 容器编排文件
│   ├── patches/                # NPU 兼容补丁
│   │   ├── patch_rope.py
│   │   └── patch_rope3.py
│   ├── start_service.sh        # 推理服务启动脚本
│   ├── vllm-omni.conf          # Nginx 反向代理配置
│   └── deploy.md               # 部署步骤说明
├── offline_whls/               # 外网 whls 依赖包下载目录
├── test/                       # 测试脚本
│   ├── check_health.sh
│   ├── test_t2i_basic.sh
│   ├── test_t2i_full.py
│   ├── test_t2i_openai_sdk.py
│   ├── test_t2i_batch.py
│   ├── test_t2i_2k.py
│   └── test_t2i_transparent.py
├── .gitignore
├── requirements.txt
├── main.py                     # 主入口（可扩展）
└── README.md
```

---

## 🖥️ 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | aarch64 |
| NPU | 昇腾 910B3（单卡 64GB） |
| 模型权重 | Qwen-Image-2.1（约 30GB+） |

---

## 📦 准备阶段（外网机器）

### 1. 下载模型

- **魔搭（ModelScope）**：  
  https://modelscope.cn/models/Qwen/Qwen-Image-2.1  
  下载后放置到内网服务器 `/opt/data/models/Qwen-Image-2.1`

- **HuggingFace**：  
  https://huggingface.co/Qwen/Qwen-Image-2.1

### 2. 拉取 Docker 镜像（南大镜像源）约 30GB

```bash
docker pull quay.nju.edu.cn/ascend/vllm-omni:v0.28.0
```

### 3. 导出镜像为离线包

```bash
docker save quay.nju.edu.cn/ascend/vllm-omni:v0.28.0 -o vllm-omni-0.28.0.tar
gzip vllm-omni-0.28.0.tar
```

### 4. 下载 diffusers 源码与 transformers wheel

```bash
# diffusers main 源码
curl -L -o diffusers-main.tar.gz \
  https://codeload.github.com/huggingface/diffusers/tar.gz/refs/heads/main

# transformers 5.17.0 wheel
# 从 https://pypi.org/project/transformers/5.17.0/#files 下载 py3-none-any.whl
```

### 5. 克隆本项目并准备补丁

```bash
git clone <本项目仓库地址> Qwen-Image-2.1-deploy-pro
cd Qwen-Image-2.1-deploy-pro
# 补丁已包含在 deploy/patches/ 中
```

### 6. 整理物料并拷贝到移动硬盘

将以下文件放入移动硬盘，准备带入内网：

- `vllm-omni-0.28.0.tar.gz`
- `diffusers-main.tar.gz`
- `transformers-5.17.0-py3-none-any.whl`
- `Qwen-Image-2.1-deploy-pro/` 整个项目目录

---

## 🚀 内网部署

### 1. 上传物料并加载镜像

```bash
# 将移动硬盘中的文件拷贝到内网服务器
cp /media/external/vllm-omni-0.28.0.tar.gz /home/deploy/
gunzip /home/deploy/vllm-omni-0.28.0.tar.gz
docker load -i /home/deploy/vllm-omni-0.28.0.tar

# 确认镜像已加载
docker images | grep vllm-omni
```

### 2. 准备项目目录

```bash
# 假设项目已拷贝到 /home/deploy/Qwen-Image-2.1-deploy-pro
cd /home/deploy/Qwen-Image-2.1-deploy-pro/deploy
```

确保目录结构如下：

```
Qwen-Image-2.1-deploy-pro/
└── deploy/
    ├── docker-compose.yml
    ├── patches/
    │   ├── patch_rope.py
    │   └── patch_rope3.py
    ├── start_service.sh
    ├── vllm-omni.conf
    ├── diffusers-main.tar.gz
    └── transformers-5.17.0-py3-none-any.whl
```

### 3. 根据需要修改配置文件

- **`docker-compose.yml`**：
  - `ASCEND_RT_VISIBLE_DEVICES=5`：指定使用的 NPU 卡号（根据实际情况修改）
  - 挂载路径：`/opt/data/models:/opt/data/models` 确认模型权重路径
  - 项目目录挂载：`.:/workspace/deploy`，容器内通过 `/workspace/deploy/` 访问部署文件

- **`start_service.sh`**：
  - `--port 8014`：容器内服务端口，与 compose 端口映射一致
  - `--diffusion-attention-backend TORCH_SDPA`：910B3 上推荐使用，稳定优先

### 4. 启动容器

```bash
cd /home/deploy/Qwen-Image-2.1-deploy-pro/deploy
docker-compose up -d
```

### 5. 进入容器

```bash
docker-compose exec vllm-omni-qwen bash
```

### 6. 离线安装 diffusers 源码与 transformers

**⚠️ 顺序很重要：必须先安装 diffusers 源码，再打补丁。**

```bash
# 解压 diffusers 源码（容器内路径为 /workspace/deploy/）
tar xf /workspace/deploy/diffusers-main.tar.gz -C /vllm-workspace/

# 安装 diffusers main 源码
pip install /vllm-workspace/diffusers-main/

# 离线安装 transformers 5.17.0
pip install /workspace/deploy/transformers-5.17.0-py3-none-any.whl
```

### 7. 应用 NPU 补丁

```bash
python /workspace/deploy/patches/patch_rope.py
python /workspace/deploy/patches/patch_rope3.py
```

### 8. 验证补丁是否生效（期望输出 5）

```bash
bash -c 'P=$(python3 -c "import diffusers,os;print(os.path.join(os.path.dirname(diffusers.__file__),\"models/transformers/transformer_qwenimage21.py\"))"); grep -c "npu patch" "$P"'
```

如果输出不是 `5`，请检查 diffusers 是否安装成功，以及补丁脚本是否与当前 diffusers main 兼容。

### 9. 启动推理服务（后台）

```bash
nohup bash /workspace/deploy/start_service.sh > /tmp/qwen_image_2_1_vllm.log 2>&1 &
```

### 10. 等待约 1 分钟后检查日志

```bash
grep "Application startup complete" /tmp/qwen_image_2_1_vllm.log
```

看到该字样即表示服务启动成功。

---

## 🧪 测试与验证

以下脚本位于宿主机项目的 `test/` 目录下，直接在宿主机执行即可。

```bash
cd /home/deploy/Qwen-Image-2.1-deploy-pro/test
```

### 完整参数 Python 测试

```bash
python test_t2i_full.py
```

### OpenAI SDK 调用测试

```bash
python test_t2i_openai_sdk.py
```

### 批量并发生图

```bash
python test_t2i_batch.py
```

### 2K 分辨率生图

```bash
python test_t2i_2k.py
```

### 透明图生成

```bash
python test_t2i_transparent.py
```

所有脚本默认请求 `http://localhost:8014`，与 `start_service.sh` 端口一致。

> `check_health.sh` 与 `test_t2i_basic.sh` 暂未提供，后续补充。

---

## 🎨 功能说明

Qwen-Image-2.1 是一个统一的图像生成与编辑模型，主要能力包括：

| 功能 | 说明 | 是否需要特殊配置 |
|------|------|------------------|
| **文生图** | 根据文本生成图像，原生支持 2K 分辨率 | 无需额外配置 |
| **透明图生成** | 原生 RGBA 四通道输出，透明信息在 latent 空间生成 | 提示词中描述透明需求 |
| **图像编辑** | 支持圈选、涂抹、Mask 等方式局部编辑 | 需传递参考图与标注信息 |
| **多参考图** | 最多支持 10 张参考图输入，用于合成、试穿、室内设计等 | 需传递参考图列表 |
| **主体提取** | 从照片中提取主体并输出透明图层 | 需传递参考图 |
| **高清放大** | 2× / 3× / 4× 超分辨率放大 | 指定输出尺寸 |
| **快捷创作** | 换装、人物替换、全景摄影、三视图等 | 使用预设工作流 |

---

## ⚡ 并发配置

当前 `start_service.sh` **未设置 `--max-num-seqs`**，默认串行执行（并发数=1）。

如需开启并发，在 `start_service.sh` 的 `vllm serve` 命令中增加：

```bash
--max-num-seqs 4
```

**建议：**

- 910B3 单卡 64GB，建议从 `--max-num-seqs 2` 开始测试
- 观察显存占用与吞吐量，逐步调整到 `4`
- 2K 分辨率下并发容易 OOM，可配合 `--vae-use-slicing --vae-use-tiling` 降低显存峰值
- 延迟敏感场景保持 `--request-batch-max-wait-ms 0`；吞吐优先可设为 `20` 左右

---

## ❓ 常见问题

**Q：补丁验证输出不是 5？**  
A：确认 diffusers 源码已成功安装，且补丁脚本在安装之后执行。检查 `transformer_qwenimage21.py` 路径是否正确。

**Q：服务启动后无日志或挂死？**  
A：确认 `--diffusion-attention-backend TORCH_SDPA` 已设置。910B3 上使用 `FLASH_ATTN` 可能导致无日志挂死。

**Q：`/v1/models` 返回空列表？**  
A：已知现象，不影响实际推理调用。

**Q：2K 生图 OOM？**  
A：降低并发数，或启用 `--vae-use-slicing --vae-use-tiling`。

**Q：内网无法联网安装 pip 包？**  
A：使用外网下载好的 `diffusers-main.tar.gz` 和 `transformers-5.17.0-py3-none-any.whl` 离线安装。容器内路径为 `/workspace/deploy/`。

---

## 📄 许可证

本项目仅用于技术学习与部署参考，模型版权归 Qwen 团队所有。
(Qwen-Image-2.1 模型在官方中明确不可商用，请勿直接使用模型进行商用)

---

## 🙏 致谢

- [补丁来源](https://ai.gitcode.com/Ascend-SACT/Qwen-Image-2.1)
- [vLLM-Omni](https://github.com/vllm-project/vllm-omni)
- [Qwen-Image-2.1](https://modelscope.cn/models/Qwen/Qwen-Image-2.1)
- [Ascend-SACT/Qwen-Image-2.1](https://ai.gitcode.com/Ascend-SACT/Qwen-Image-2.1)
- 南京大学开源镜像站

---
