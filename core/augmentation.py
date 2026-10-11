"""
氧气瓶数据增强流水线

用法：
    from core.augmentation import AugmentationPipeline
    pipeline = AugmentationPipeline()
    pipeline.run_all()
"""
from pathlib import Path
from typing import List, Optional

from .config import (
    RAW_DIR, AUGMENTED_DIR, ensure_dirs,
)
from .client import OmniClient
from .prompts import (
    STATE_EDIT_PROMPTS,
    BACKGROUND_EDIT_PROMPTS,
    APPEARANCE_EDIT_PROMPTS,
    TEXT2IMG_PROMPTS,
    DEFAULT_NEGATIVE_PROMPT,
    EditPrompt,
    Text2ImgPrompt,
)


class AugmentationPipeline:
    """数据增强流水线"""

    def __init__(self, client: Optional[OmniClient] = None):
        self.client = client or OmniClient()
        ensure_dirs()

    # --------------------------------------------------------
    # 通用：批量图像编辑
    # --------------------------------------------------------
    def run_edit_batch(
        self,
        input_dir: Path,
        output_subdir: str,
        edit_prompts: List[EditPrompt],
        skip_existing: bool = True,
    ) -> List[str]:
        """
        对 input_dir 中的所有图像，按 edit_prompts 批量编辑。

        参数：
            input_dir:       源图像目录
            output_subdir:   输出子目录名（位于 data/augmented/ 下）
            edit_prompts:    编辑提示词列表
            skip_existing:   跳过已存在的输出，便于断点续跑
        """
        out_dir = AUGMENTED_DIR / output_subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        sources = sorted([
            f for f in input_dir.iterdir()
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        ])
        if not sources:
            print(f"  [警告] {input_dir} 中没有图像")
            return []

        print(f"  源图像：{len(sources)} 张，编辑配置：{len(edit_prompts)} 种")
        results = []

        for cfg in edit_prompts:
            print(f"  → 应用配置：{cfg.name}（{cfg.category}）")
            for src in sources:
                out_path = out_dir / f"{src.stem}_{cfg.name}.png"
                if skip_existing and out_path.exists():
                    print(f"     跳过（已存在）：{out_path.name}")
                    continue
                try:
                    img_bytes = self.client.edit(
                        str(src),
                        cfg.prompt,
                        negative_prompt=cfg.negative_prompt or DEFAULT_NEGATIVE_PROMPT,
                        seed=cfg.seed,
                        steps=cfg.steps,
                        cfg_scale=cfg.cfg_scale,
                    )
                    out_path.write_bytes(img_bytes)
                    results.append(str(out_path))
                    print(f"     已生成：{out_path.name}")
                except Exception as e:
                    print(f"     失败：{src.name} x {cfg.name}: {e}")
        return results

    # --------------------------------------------------------
    # 通用：批量文生图
    # --------------------------------------------------------
    def run_text2img_batch(
        self,
        output_subdir: str,
        prompts: List[Text2ImgPrompt],
        skip_existing: bool = True,
    ) -> List[str]:
        """按 prompts 批量文生图"""
        out_dir = AUGMENTED_DIR / output_subdir
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"  文生图配置：{len(prompts)} 种")
        results = []

        for cfg in prompts:
            out_path = out_dir / f"{cfg.name}.png"
            if skip_existing and out_path.exists():
                print(f"     跳过（已存在）：{out_path.name}")
                continue
            try:
                img_bytes = self.client.generate(
                    cfg.prompt,
                    negative_prompt=cfg.negative_prompt or DEFAULT_NEGATIVE_PROMPT,
                    seed=cfg.seed,
                    steps=cfg.steps,
                    cfg_scale=cfg.cfg_scale,
                )
                out_path.write_bytes(img_bytes)
                results.append(str(out_path))
                print(f"     已生成：{out_path.name}")
            except Exception as e:
                print(f"     失败：{cfg.name}: {e}")
        return results

    # --------------------------------------------------------
    # 完整流水线
    # --------------------------------------------------------
    def run_all(self, skip_existing: bool = True):
        """依次执行全部数据增强任务"""
        print("=" * 60)
        print("氧气瓶数据增强流水线")
        print("=" * 60)

        # Step 1: 倒伏状态增强
        print("\n[Step 1] 倒伏状态增强")
        self.run_edit_batch(
            RAW_DIR, "fallen_states",
            STATE_EDIT_PROMPTS, skip_existing,
        )

        # Step 2: 背景环境增强
        print("\n[Step 2] 背景环境增强")
        self.run_edit_batch(
            RAW_DIR, "backgrounds",
            BACKGROUND_EDIT_PROMPTS, skip_existing,
        )

        # Step 3: 外观增强
        print("\n[Step 3] 品牌与外观增强")
        self.run_edit_batch(
            RAW_DIR, "brands",
            APPEARANCE_EDIT_PROMPTS, skip_existing,
        )

        # Step 4: 文生图补充
        print("\n[Step 4] 文生图补充稀缺场景")
        self.run_text2img_batch(
            "text2img", TEXT2IMG_PROMPTS, skip_existing,
        )

        self._print_summary()

    # --------------------------------------------------------
    # 结果统计
    # --------------------------------------------------------
    def _print_summary(self):
        print("\n" + "=" * 60)
        print("增强结果统计")
        print("=" * 60)
        for sub in ["fallen_states", "backgrounds", "brands", "text2img"]:
            d = AUGMENTED_DIR / sub
            if d.exists():
                count = len(list(d.glob("*.png")))
                print(f"  {sub:20s}: {count:5d} 张")
        print("=" * 60)


__all__ = ["AugmentationPipeline"]