# Qwen-Image-2.1-deploy-pro

> 在国产昇腾 910B3（单卡 64GB）上部署 Qwen-Image-2.1 图像生成模型的完整教程与工程化项目。
> 如果你更习惯 ComfyUI 的方式，很抱歉，目前没有弄。
> 补丁为 AtomGit 开源项目中获取，感谢补丁大神，原网址在下方致谢中。

---

## 📖 项目简介

本项目提供在**昇腾 910B3** 等国产 NPU 上，基于 **vLLM-Omni v0.28.0** 部署 **Qwen-Image-2.1** 的完整流程。包含：

- 外网拉取镜像、离线导出与内网加载
- 容器化启动、离线安装 diffusers 与 transformers
- 应用昇腾 NPU 兼容补丁（**已修复原补丁脚本的 bug，并支持幂等重跑**）
- 启动推理服务并验证
- 提供文生图、图像编辑、透明图生成等测试脚本
- **可调试的核心模块**：API 客户端、YAML 提示词库、示例工作流、Gradio 调试台
- 并发配置与调优建议

项目名称：`Qwen-Image-2.1-deploy-pro`
> 作者：kafeic

---

## 📁 项目结构

```
Qwen-Image-2.1-deploy-pro/
├── core/                       # 核心模块
│   ├── config.yaml             # 核心配置（API / 生成 / 路径 / 调试）
│   ├── config.py               # 配置加载器
│   ├── client.py               # API 客户端封装（OpenAI 兼容）
│   ├── prompts/                # 提示词库（YAML 单文件，可直接编辑）
│   │   ├── __init__.py         #   加载器（支持 Jinja2 变量渲染）
│   │   ├── characters.yaml     #   短剧角色库
│   │   ├── shots.yaml          #   分镜镜头模板
│   │   ├── styles.yaml         #   风格预设
│   │   ├── game.yaml           #   游戏角色 / 资产模板
│   │   └── negative.yaml       #   负向提示词
│   └── workflows/              # 工作流定义
│       ├── base.py             #   工作流基类
│       ├── storyboard.py       #   AI 短剧分镜工作流
│       └── game_character.py   #   游戏角色 / 资产工作流
├── data/                       # 参考图、输出图（data/outputs）
├── deploy/                     # 部署相关文件
│   ├── docker-compose.yml      # 容器编排文件
│   ├── patches/                # NPU 兼容补丁
│   │   ├── patch_rope.py
│   │   └── patch_rope3.py
│   ├── start_service.sh        # 推理服务启动脚本（含可调参数注释）
│   ├── vllm-omni.conf          # Nginx 反向代理配置
│   └── deploy.md               # 部署步骤说明
├── offline_whls/               # 外网 whls 依赖包下载目录
├── test/                       # 测试脚本
├── app.py                      # Gradio 调试台（文生图 / 短剧分镜 / 游戏角色）
├── main.py                     # 命令行入口（示例用法）
├── requirements.txt
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
  - `ASCEND_RT_VISIBLE_DEVICES=5`：只使用 5 号卡（按需修改）
  - `--port 8014`：容器内服务端口，与 compose 端口映射一致
  - `--diffusion-attention-backend TORCH_SDPA`：910B3 上推荐使用，稳定优先
  - 脚本内已用注释列出常用可调参数（并发、VAE 切片/平铺、显存、日志等），按需取消注释

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

### 7. 应用 NPU 补丁（按顺序执行）

```bash
python /workspace/deploy/patches/patch_rope.py
python /workspace/deploy/patches/patch_rope3.py
```

两个脚本均已**幂等**，可安全重复执行：

- **首次运行自动创建 `.bak` 备份**（先备份、后补丁），无需手动 `cp`。
  备份位于 `/vllm-workspace/diffusers-main.bak/...`，**不参与运行**，补丁会跳过它。
- 已打过的补丁自动跳过。
- 单条补丁 MISS 不会阻塞其余补丁的保存。

> **关于补丁的说明**：本补丁源自 Ascend-SACT/Qwen-Image-2.1 开源项目，本项目
> 对其做了**修改与 bug 修复**——原 `patch_rope3.py` 在 `sys.exit(1)` 前未保存文件，
> 导致 edit B 丢失、补丁数停在 4。若本脚本在你的 diffusers 版本上仍报 `[MISS]`，
> 说明版本不兼容，请参考原项目补丁自行核对目标代码。

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

| 脚本 | 说明 |
|------|------|
| `test_t2i_full.py` | 完整参数文生图 |
| `test_t2i_openai_sdk.py` | OpenAI SDK 调用 |
| `test_t2j_batch.py` | 批量并发生图（注意文件名为 t2j） |
| `test_t2i_2k.py` | 2K 分辨率生图 |
| `test_t2i_transparent.py` | 透明图生成 |

所有脚本默认请求 `http://localhost:8014`，与 `start_service.sh` 端口一致。

---

## 🎨 模型功能说明

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

## 🧩 核心模块与工作流

### 配置

所有可调项集中在 `core/config.yaml`，改完无需动代码：

```yaml
api:
  base_url: "http://localhost:8014"   # 直连容器映射端口
  model_name: "Qwen/Qwen-Image-2.1"
  api_style: "openai_images"          # openai_images | chat
generation:
  width: 1024
  height: 1024
  num_inference_steps: 40
  guidance_scale: 1.0                 # 1.0 = 不启用 CFG
  seed: 42
debug:
  log_payload: true                   # 打印请求 payload，便于调试
  save_metadata: true                 # 出图时同目录写 .json 元数据
```

### 客户端

```python
from core import OmniClient

client = OmniClient()
print(client.health())                 # 健康检查
img = client.generate("一只在雨中的猫")  # 返回 PIL.Image
client.save(img, "data/outputs/cat.png", metadata={"prompt": "..."})
```

### 提示词库（可直接编辑）

提示词全部放在 `core/prompts/*.yaml`，支持 Jinja2 变量，改文件即生效：

```yaml
# core/prompts/shots.yaml
- id: closeup
  name: 特写
  template: >-
    cinematic close-up shot, {{character}} {{action}}, {{mood}},
    {{style}}, detailed face, dramatic lighting, film still
```

```python
from core import PROMPTS
PROMPTS.character("lin_wan")["appearance"]     # 取角色外观
PROMPTS.render_shot("closeup", character="...", action="...",
                    scene="...", mood="...", style="...")
```

### 工作流示例

**① AI 短剧分镜**（`core/workflows/storyboard.py`）

```python
from core.workflows import StoryboardWorkflow

wf = StoryboardWorkflow()
results = wf.run(StoryboardWorkflow.demo_script())   # 内置 4 镜示例剧本
for shot, (img, path) in results:
    print(shot.shot_type, "->", path)
```

**② 游戏角色 / 资产**（`core/workflows/game_character.py`）

```python
from core.workflows import GameCharacterWorkflow

wf = GameCharacterWorkflow()
img, path = wf.render_asset(
    "character_sheet", "hero",
    "a young swordsman, silver hair, blue cloak, glowing rune sword",
    "game_concept",
)
```

### 命令行入口

```bash
python main.py health                 # 检查服务状态
python main.py t2i "一只在雨中的猫"    # 文生图
python main.py storyboard             # 运行示例剧本（4 镜）
python main.py game                   # 生成游戏角色三视图
```

---

## 🖥️ Gradio 调试台

```bash
pip install -r requirements.txt
python app.py                         # 默认 http://127.0.0.1:7860
python app.py --host 0.0.0.0 --port 7860   # 内网访问
```

页面标签：

1. **文生图** —— 自由提示词出图，可调分辨率 / 步数 / 引导系数 / 种子
2. **短剧分镜** —— 选角色 / 镜头 / 风格，逐镜生成；一键运行示例剧本（4 镜）
3. **游戏角色** —— 三视图 / 概念图 / 头像 / 道具
4. **服务状态** —— 健康检查、模型列表、当前配置

每个标签页都带「调试信息」面板，显示**实际组装的 prompt 与请求参数**，方便排查。

---

## ⚡ 并发配置

`start_service.sh` 默认**未设置 `--max-num-seqs`**，即串行执行（并发数=1）。

如需开启并发，在 `start_service.sh` 的 `vllm serve` 命令中增加（脚本内已有注释示例）：

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
A：确认 diffusers 源码已成功安装，且补丁脚本在安装之后执行。本项目的补丁脚本已
修复「`sys.exit(1)` 导致补丁数停在 4」的 bug，可重复执行；若仍报 `[MISS]`，说明
diffusers 版本与补丁不兼容，请参考原项目补丁核对目标代码。

**Q：补丁脚本报 `.bak` 相关错误？**  
A：本项目的补丁脚本会**自动创建** `.bak` 备份，无需手动准备。`.bak` 不参与运行。

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

- [补丁来源](https://ai.gitcode.com/Ascend-SACT/Qwen-Image-2.1)（本项目对其补丁做了修改与 bug 修复）
- [vLLM-Omni](https://github.com/vllm-project/vllm-omni)
- [Qwen-Image-2.1](https://modelscope.cn/models/Qwen/Qwen-Image-2.1)
- [Ascend-SACT/Qwen-Image-2.1](https://ai.gitcode.com/Ascend-SACT/Qwen-Image-2.1)
- 南京大学开源镜像站

---
