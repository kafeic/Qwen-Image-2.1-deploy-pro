# -*- coding: utf-8 -*-
"""
配置加载模块

从 ``core/config.yaml`` 读取配置，转成 dataclass 供上层使用。
可通过环境变量 ``QWEN_IMAGE_CONFIG`` 指定其它配置文件路径。

用法：
    from core.config import CONFIG
    CONFIG.api.base_url
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

# ============================================================
# 路径常量
# ============================================================
CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CORE_DIR.parent
DEFAULT_CONFIG_PATH = CORE_DIR / "config.yaml"
CONFIG_PATH = Path(os.environ.get("QWEN_IMAGE_CONFIG", DEFAULT_CONFIG_PATH))


# ============================================================
# 配置数据结构
# ============================================================
@dataclass
class APIConfig:
    """vLLM-Omni API 服务配置"""

    base_url: str = "http://localhost:8014"
    api_prefix: str = "/v1"
    model_name: str = "Qwen/Qwen-Image-2.1"
    api_style: str = "openai_images"   # openai_images | chat
    timeout: int = 600
    connect_timeout: int = 30
    max_retries: int = 2

    @property
    def generate_endpoint(self) -> str:
        """文生图端点（OpenAI 兼容）"""
        return f"{self.base_url}{self.api_prefix}/images/generations"

    @property
    def edit_endpoint(self) -> str:
        """图像编辑端点（OpenAI 兼容）"""
        return f"{self.base_url}{self.api_prefix}/images/edits"

    @property
    def chat_endpoint(self) -> str:
        """多模态对话端点"""
        return f"{self.base_url}{self.api_prefix}/chat/completions"

    @property
    def models_endpoint(self) -> str:
        """模型列表端点"""
        return f"{self.base_url}{self.api_prefix}/models"

    @property
    def health_endpoint(self) -> str:
        """健康检查端点（vLLM 根路径 /health）"""
        return f"{self.base_url}/health"


@dataclass
class GenerationConfig:
    """图像生成默认参数"""

    width: int = 1024
    height: int = 1024
    num_inference_steps: int = 40
    guidance_scale: float = 1.0
    seed: int = 42
    output_format: str = "png"

    @property
    def size(self) -> str:
        """OpenAI 风格的 "WxH" 尺寸字符串"""
        return f"{self.width}x{self.height}"


@dataclass
class PathsConfig:
    """项目路径配置（相对项目根目录）"""

    data_dir: str = "data"
    raw_dir: str = "data/raw"
    output_dir: str = "data/outputs"

    @property
    def data_path(self) -> Path:
        return PROJECT_ROOT / self.data_dir

    @property
    def raw_path(self) -> Path:
        return PROJECT_ROOT / self.raw_dir

    @property
    def output_path(self) -> Path:
        return PROJECT_ROOT / self.output_dir


@dataclass
class DebugConfig:
    """调试开关"""

    log_payload: bool = True
    save_metadata: bool = True


@dataclass
class Config:
    """聚合配置"""

    api: APIConfig = field(default_factory=APIConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)


# ============================================================
# 加载逻辑
# ============================================================
def _section(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
    """取配置段，缺省返回空字典"""
    value = raw.get(key) or {}
    if not isinstance(value, dict):
        raise ValueError(f"config.yaml 中 `{key}` 必须是映射（dict）")
    return value


def load_config(path: Path | str = CONFIG_PATH) -> Config:
    """从 YAML 加载配置；文件不存在时使用全默认值。"""
    path = Path(path)
    raw: Dict[str, Any] = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    return Config(
        api=APIConfig(**_section(raw, "api")),
        generation=GenerationConfig(**_section(raw, "generation")),
        paths=PathsConfig(**_section(raw, "paths")),
        debug=DebugConfig(**_section(raw, "debug")),
    )


def ensure_dirs(cfg: Config | None = None) -> None:
    """确保输出目录存在"""
    cfg = cfg or CONFIG
    for d in (cfg.paths.raw_path, cfg.paths.output_path):
        d.mkdir(parents=True, exist_ok=True)


# 全局单例
CONFIG = load_config()

# 兼容旧引用
API_CONFIG = CONFIG.api
GEN_CONFIG = CONFIG.generation


__all__ = [
    "CORE_DIR", "PROJECT_ROOT", "CONFIG_PATH",
    "APIConfig", "GenerationConfig", "PathsConfig", "DebugConfig", "Config",
    "load_config", "ensure_dirs",
    "CONFIG", "API_CONFIG", "GEN_CONFIG",
]
