# -*- coding: utf-8 -*-
"""
工作流基类

统一持有 client / 提示词库 / 输出目录，提供「出图 + 保存 + 元数据」的通用能力。
具体工作流（短剧分镜、游戏角色）继承本类。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image

from ..client import OmniClient
from ..config import CONFIG
from ..prompts import PROMPTS, PromptLibrary

# (图像, 保存路径)
Result = Tuple[Image.Image, Path]


class BaseWorkflow:
    """工作流基类"""

    def __init__(
        self,
        client: Optional[OmniClient] = None,
        prompts: Optional[PromptLibrary] = None,
        output_dir: Optional[Path] = None,
    ):
        self.client = client or OmniClient()
        self.prompts = prompts or PROMPTS
        self.output_dir = Path(output_dir) if output_dir else CONFIG.paths.output_path
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 通用出图
    # --------------------------------------------------------
    def render(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        seed: Optional[int] = None,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        name: str = "image",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result:
        """调用文生图并保存，返回 (PIL.Image, 保存路径)。"""
        image = self.client.generate(
            prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            steps=steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
        )
        meta: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "steps": steps,
            "guidance_scale": guidance_scale,
        }
        if metadata:
            meta.update(metadata)
        path = self.client.save(image, self.output_dir / f"{name}.png", meta)
        return image, path
