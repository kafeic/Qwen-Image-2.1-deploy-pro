# -*- coding: utf-8 -*-
"""
工作流定义

- BaseWorkflow          工作流基类
- StoryboardWorkflow    AI 短剧分镜工作流
- GameCharacterWorkflow 游戏角色 / 资产工作流
"""
from .base import BaseWorkflow, Result
from .storyboard import Shot, StoryboardWorkflow
from .game_character import GameCharacterWorkflow

__all__ = [
    "BaseWorkflow", "Result",
    "Shot", "StoryboardWorkflow",
    "GameCharacterWorkflow",
]
