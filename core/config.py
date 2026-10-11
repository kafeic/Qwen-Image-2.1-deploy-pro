"""
模型调用配置
所有与 vLLM-Omni 服务通信相关的配置集中在此，便于统一修改。
"""
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================
# 项目路径配置
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
AUGMENTED_DIR = DATA_DIR / "augmented"


# ============================================================
# API 服务配置
# ============================================================
@dataclass
class APIConfig:
    """vLLM-Omni API 服务配置"""

    # 服务地址（通过 Nginx 代理后的地址）
    # 内网服务器 IP + Nginx 对外端口 + location 前缀
    base_url: str = "http://123.123.xx.xx:8443/qwen-images-2.1"

    # API 版本前缀（与 vLLM-Omni 一致）
    api_prefix: str = "/v1"

    # 模型名称（用于请求体中的 model 字段）
    model_name: str = "Qwen-Image-2.1"

    # 请求超时（秒），图像生成耗时长，设置较大
    timeout: int = 600

    # 连接超时（秒）
    connect_timeout: int = 30

    # 失败重试次数
    max_retries: int = 2

    @property
    def generate_endpoint(self) -> str:
        """文生图端点"""
        return f"{self.base_url}{self.api_prefix}/chat/completions"

    @property
    def edit_endpoint(self) -> str:
        """图像编辑端点"""
        return f"{self.base_url}{self.api_prefix}/images/edits"

    @property
    def health_endpoint(self) -> str:
        """健康检查端点"""
        return f"{self.base_url}/health"


# ============================================================
# 图像生成默认参数
# ============================================================
@dataclass
class GenerationConfig:
    """图像生成的默认参数"""

    # 分辨率
    height: int = 1024
    width: int = 1024

    # 采样步数（30 步为质量与速度的平衡点）
    num_inference_steps: int = 30

    # 无分类器引导系数
    # = 1.0 时关闭 CFG；> 1.0 时启用，增强提示词控制力
    cfg_scale: float = 4.0

    # 随机种子（固定可复现）
    seed: int = 42

    # 每次请求生成的图像数量
    n: int = 1

    # 输出格式
    output_format: str = "png"


# ============================================================
# 全局配置实例
# ============================================================
API_CONFIG = APIConfig()
GEN_CONFIG = GenerationConfig()


# ============================================================
# 目录初始化
# ============================================================
def ensure_dirs():
    """确保所有必要目录存在"""
    for d in [RAW_DIR, AUGMENTED_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    for sub in ["fallen_states", "backgrounds", "brands", "text2img"]:
        (AUGMENTED_DIR / sub).mkdir(parents=True, exist_ok=True)


__all__ = [
    "PROJECT_ROOT", "DATA_DIR", "RAW_DIR", "AUGMENTED_DIR",
    "APIConfig", "GenerationConfig",
    "API_CONFIG", "GEN_CONFIG",
    "ensure_dirs",
]