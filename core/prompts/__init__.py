# -*- coding: utf-8 -*-
"""
提示词库（Prompt Library）

提示词全部以 YAML 单文件维护在本目录下，支持 Jinja2 变量渲染，
方便直接编辑、无需改动 Python 代码。

文件：
    characters.yaml  短剧角色库（外观描述，用于跨镜头一致性）
    shots.yaml       分镜镜头模板
    styles.yaml      风格预设
    game.yaml        游戏角色 / 资产模板
    negative.yaml    负向提示词

用法：
    from core.prompts import PROMPTS
    PROMPTS.character("lin_wan")["appearance"]
    PROMPTS.render_shot("closeup", character="...", action="...", scene="...",
                        mood="...", style="...")
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from jinja2 import Template

PROMPTS_DIR = Path(__file__).resolve().parent

# Gradio 下拉用的 (显示名, id) 形式
Choice = Tuple[str, str]


def _load(filename: str) -> Any:
    """加载单个 YAML 提示词文件"""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"提示词文件缺失：{path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _clean(text: str) -> str:
    """折叠多余空白，避免模板换行产生空格噪音"""
    return re.sub(r"\s+", " ", text).strip()


class PromptLibrary:
    """提示词库访问器"""

    def __init__(self, prompts_dir: Path = PROMPTS_DIR):
        self.dir = prompts_dir
        self.characters: List[Dict[str, Any]] = _load("characters.yaml").get("characters", [])
        self.shot_types: List[Dict[str, Any]] = _load("shots.yaml").get("shot_types", [])
        self.styles: List[Dict[str, Any]] = _load("styles.yaml").get("styles", [])
        self.game: Dict[str, Any] = _load("game.yaml")
        self.negative: Dict[str, str] = _load("negative.yaml").get("negative", {})

        self._char_map = {c["id"]: c for c in self.characters}
        self._shot_map = {s["id"]: s for s in self.shot_types}
        self._style_map = {s["id"]: s for s in self.styles}
        self._role_map = {r["id"]: r for r in self.game.get("roles", [])}
        self._asset_map = {a["id"]: a for a in self.game.get("asset_types", [])}

    # --------------------------------------------------------
    # 单项访问
    # --------------------------------------------------------
    def character(self, cid: str) -> Dict[str, Any]:
        if cid not in self._char_map:
            raise KeyError(f"未知角色 id：{cid}（可选：{list(self._char_map)}）")
        return self._char_map[cid]

    def shot(self, sid: str) -> Dict[str, Any]:
        if sid not in self._shot_map:
            raise KeyError(f"未知镜头 id：{sid}（可选：{list(self._shot_map)}）")
        return self._shot_map[sid]

    def style(self, sid: str) -> Dict[str, Any]:
        if sid not in self._style_map:
            raise KeyError(f"未知风格 id：{sid}（可选：{list(self._style_map)}）")
        return self._style_map[sid]

    def role(self, rid: str) -> Dict[str, Any]:
        return self._role_map[rid]

    def asset(self, aid: str) -> Dict[str, Any]:
        return self._asset_map[aid]

    def negative_for(self, key: str = "default") -> str:
        """取负向提示词；key 不存在时回退 default"""
        return self.negative.get(key) or self.negative.get("default", "")

    # --------------------------------------------------------
    # 渲染
    # --------------------------------------------------------
    @staticmethod
    def render(template: str, **variables: Any) -> str:
        """用 Jinja2 渲染模板并折叠空白"""
        return _clean(Template(template).render(**variables))

    def render_shot(self, shot_id: str, **variables: Any) -> str:
        return self.render(self.shot(shot_id)["template"], **variables)

    def render_asset(self, asset_id: str, **variables: Any) -> str:
        return self.render(self.asset(asset_id)["template"], **variables)

    # --------------------------------------------------------
    # 下拉选项
    # --------------------------------------------------------
    def character_choices(self) -> List[Choice]:
        return [(f"{c['name']}（{c['id']}）", c["id"]) for c in self.characters]

    def shot_choices(self) -> List[Choice]:
        return [(s["name"], s["id"]) for s in self.shot_types]

    def style_choices(self) -> List[Choice]:
        return [(s["name"], s["id"]) for s in self.styles]

    def role_choices(self) -> List[Choice]:
        return [(r["name"], r["id"]) for r in self.game.get("roles", [])]

    def asset_choices(self) -> List[Choice]:
        return [(a["name"], a["id"]) for a in self.game.get("asset_types", [])]


@lru_cache(maxsize=1)
def get_prompt_library() -> PromptLibrary:
    """获取提示词库单例（首次加载后缓存）"""
    return PromptLibrary()


PROMPTS = get_prompt_library()


__all__ = ["PromptLibrary", "PROMPTS", "get_prompt_library", "PROMPTS_DIR"]
