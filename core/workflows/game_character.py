# -*- coding: utf-8 -*-
"""
游戏角色 / 资产工作流

给定角色定位、外观描述与风格，生成游戏概念资产（三视图 / 概念图 / 头像 / 道具）。

用法：
    from core.workflows import GameCharacterWorkflow
    wf = GameCharacterWorkflow()
    img, path = wf.render_asset("character_sheet", "hero",
                                "a young swordsman with silver hair and blue cloak",
                                "game_concept")
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .base import BaseWorkflow, Result


class GameCharacterWorkflow(BaseWorkflow):
    """游戏角色 / 资产工作流"""

    def build_prompt(
        self,
        asset_type: str,
        role: str,
        appearance: str,
        style: str,
    ) -> Tuple[str, str]:
        """组装 (正向提示词, 负向提示词)。"""
        role_desc = self.prompts.role(role)["prompt"]
        style_desc = self.prompts.style(style)["prompt"]
        prompt = self.prompts.render_asset(
            asset_type,
            role=role_desc,
            appearance=appearance,
            style=style_desc,
        )
        negative = " ".join(filter(None, [
            self.prompts.negative_for("default"),
            self.prompts.negative_for("game"),
        ]))
        return prompt, negative

    def render_asset(
        self,
        asset_type: str,
        role: str,
        appearance: str,
        style: str = "game_concept",
        seed: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Result:
        prompt, negative = self.build_prompt(asset_type, role, appearance, style)
        name = name or f"game_{asset_type}_{role}"
        return self.render(
            prompt,
            negative_prompt=negative,
            seed=seed,
            name=name,
            metadata={
                "kind": "game_asset",
                "asset_type": asset_type,
                "role": role,
                "appearance": appearance,
                "style": style,
            },
        )

    def run(
        self,
        asset_types: List[str],
        role: str,
        appearance: str,
        style: str = "game_concept",
        seed: Optional[int] = None,
    ) -> List[Tuple[str, Result]]:
        """批量生成多种资产，返回 [(资产类型, (图像, 路径)), ...]"""
        results: List[Tuple[str, Result]] = []
        for i, at in enumerate(asset_types, 1):
            print(f"[GameCharacter] {i}/{len(asset_types)} 资产：{at}")
            s = seed + i - 1 if seed is not None else None
            results.append((at, self.render_asset(at, role, appearance, style, seed=s)))
        return results
