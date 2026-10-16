# -*- coding: utf-8 -*-
"""
AI 短剧分镜工作流

给定一组「分镜」（镜头类型 + 角色 + 动作 + 场景 + 情绪 + 风格），
逐镜生成画面，用于 AI 短剧 / 漫画的分镜草图。

用法：
    from core.workflows import StoryboardWorkflow, Shot
    wf = StoryboardWorkflow()
    shots = StoryboardWorkflow.demo_script()      # 内置示例剧本
    results = wf.run(shots)                       # -> [(Shot, 路径), ...]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .base import BaseWorkflow, Result


@dataclass
class Shot:
    """单个分镜"""

    shot_type: str            # shots.yaml 的镜头 id，如 closeup
    character: str            # characters.yaml 的角色 id；空镜可留空
    action: str               # 角色动作 / 事件
    scene: str                # 场景 / 环境
    mood: str = "tense"       # 情绪氛围 / 光影
    style: str = "cinematic_real"  # styles.yaml 的风格 id
    dialogue: str = ""        # 台词 / 字幕（仅记录，不注入画面）
    seed: Optional[int] = None


class StoryboardWorkflow(BaseWorkflow):
    """短剧分镜工作流"""

    # --------------------------------------------------------
    # 提示词组装
    # --------------------------------------------------------
    def build_prompt(self, shot: Shot) -> Tuple[str, str]:
        """把分镜组装为 (正向提示词, 负向提示词)。"""
        char = ""
        char_neg = ""
        if shot.character:
            c = self.prompts.character(shot.character)
            char = c["appearance"]
            char_neg = c.get("negative", "")

        style = self.prompts.style(shot.style)["prompt"]
        prompt = self.prompts.render_shot(
            shot.shot_type,
            character=char,
            action=shot.action,
            scene=shot.scene,
            mood=shot.mood,
            style=style,
        )
        negative = " ".join(filter(None, [
            self.prompts.negative_for("default"),
            self.prompts.negative_for("storyboard"),
            char_neg,
        ]))
        return prompt, negative

    # --------------------------------------------------------
    # 单镜 / 批量
    # --------------------------------------------------------
    def render_shot(self, shot: Shot, index: int = 1, prefix: str = "shot") -> Result:
        prompt, negative = self.build_prompt(shot)
        name = f"{prefix}_{index:02d}_{shot.shot_type}"
        return self.render(
            prompt,
            negative_prompt=negative,
            seed=shot.seed,
            name=name,
            metadata={"kind": "storyboard", "shot": shot.__dict__},
        )

    def run(self, shots: List[Shot], prefix: str = "shot") -> List[Tuple[Shot, Result]]:
        """按顺序生成全部分镜，返回 [(Shot, (图像, 路径)), ...]"""
        results: List[Tuple[Shot, Result]] = []
        for i, shot in enumerate(shots, 1):
            print(f"[Storyboard] {i}/{len(shots)} 镜头：{shot.shot_type} / {shot.character or '空镜'}")
            results.append((shot, self.render_shot(shot, index=i, prefix=prefix)))
        return results

    # --------------------------------------------------------
    # 示例剧本
    # --------------------------------------------------------
    @staticmethod
    def demo_script() -> List[Shot]:
        """内置示例：一场雨夜悬疑短剧（4 镜）。"""
        return [
            Shot(
                shot_type="establishing",
                character="",
                action="rain pouring over the city skyline at night",
                scene="a neon-lit city street in the rain",
                mood="cold, ominous",
                style="cyberpunk",
                seed=1001,
            ),
            Shot(
                shot_type="medium",
                character="lin_wan",
                action="walking quickly while holding a black umbrella, looking back",
                scene="a wet alley with flickering signs",
                mood="tense, uneasy",
                style="cyberpunk",
                dialogue="（旁白）她总觉得有人在跟着她。",
                seed=1002,
            ),
            Shot(
                shot_type="closeup",
                character="chen_mo",
                action="staring intently from the shadows",
                scene="a dark doorway",
                mood="suspenseful",
                style="cinematic_real",
                seed=1003,
            ),
            Shot(
                shot_type="over_shoulder",
                character="lin_wan",
                action="facing a tall man who blocks the alley exit",
                scene="the end of the alley, lit by a single street lamp",
                mood="confrontational, high tension",
                style="cinematic_real",
                dialogue="齐总：这么晚，一个人？",
                seed=1004,
            ),
        ]
