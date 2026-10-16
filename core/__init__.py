# -*- coding: utf-8 -*-
"""
Qwen-Image-2.1 核心模块

- 配置：    core.config        （读取 core/config.yaml）
- 客户端：  core.client        （OmniClient，OpenAI 兼容 API）
- 提示词库：core.prompts       （YAML + Jinja2，可外部编辑）
- 工作流：  core.workflows     （短剧分镜 / 游戏角色）
"""
from .config import CONFIG, Config, APIConfig, GenerationConfig, PathsConfig, ensure_dirs
from .client import OmniClient, OmniClientError
from .prompts import PROMPTS, PromptLibrary, get_prompt_library
from .workflows import (
    BaseWorkflow,
    Shot,
    StoryboardWorkflow,
    GameCharacterWorkflow,
)

__all__ = [
    # 配置
    "CONFIG", "Config", "APIConfig", "GenerationConfig", "PathsConfig", "ensure_dirs",
    # 客户端
    "OmniClient", "OmniClientError",
    # 提示词
    "PROMPTS", "PromptLibrary", "get_prompt_library",
    # 工作流
    "BaseWorkflow", "Shot", "StoryboardWorkflow", "GameCharacterWorkflow",
]
