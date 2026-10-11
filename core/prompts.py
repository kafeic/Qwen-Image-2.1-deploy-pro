"""
氧气瓶数据增强提示词库
基于 Qwen-Image-2.1 的数据增强

所有提示词使用英文（Qwen-Image-2.1 对英文响应更精确），
并附上中文翻译便于维护和审核。

提示词按用途分类：
- EDIT_PROMPTS：图像编辑（参考图像 → 修改状态/背景）
- TEXT2IMG_PROMPTS：纯文生图（补充稀缺场景）
- NEGATIVE_PROMPTS：负向提示词
"""
from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================
# 提示词数据结构
# ============================================================
@dataclass
class EditPrompt:
    """图像编辑提示词"""
    name: str                       # 配置名（用于文件名）
    prompt: str                     # 英文提示词
    prompt_zh: str                  # 中文翻译
    category: str                   # 分类：state / background / appearance
    seed: int = 42
    steps: int = 30
    cfg_scale: float = 4.0
    negative_prompt: str = ""


@dataclass
class Text2ImgPrompt:
    """文生图提示词"""
    name: str
    prompt: str
    prompt_zh: str
    category: str
    seed: int = 42
    steps: int = 30
    cfg_scale: float = 4.0
    negative_prompt: str = ""


# ============================================================
# 通用约束片段（可复用）
# ============================================================
KEEP_CYLINDER = (
    "Keep the oxygen cylinder's color, shape, valve structure "
    "and visible labels unchanged."
)
KEEP_CYLINDER_ZH = (
    "保持氧气瓶的颜色、形状、阀门结构和可见标签不变。"
)

PHYSICAL_REALISM = (
    "Maintain realistic geometry, perspective, ground contact, "
    "lighting and shadows."
)
PHYSICAL_REALISM_ZH = (
    "保持真实的几何结构、透视关系、地面接触、光照和阴影。"
)

USE_REFERENCE = "Use the reference image as the original scene."
USE_REFERENCE_ZH = "以参考图像作为原始场景。"


def _compose(*parts: str) -> str:
    """拼接多个提示词片段为完整提示词"""
    return " ".join(parts)


# ============================================================
# 一、倒伏状态增强提示词
# ============================================================
STATE_EDIT_PROMPTS: List[EditPrompt] = [
    EditPrompt(
        name="slight_tilt",
        category="state",
        prompt=_compose(
            USE_REFERENCE,
            KEEP_CYLINDER,
            "Tilt the cylinder slightly away from vertical, about 25 degrees.",
            PHYSICAL_REALISM,
            "Preserve the original environment.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶颜色、形状、阀门结构和标签不变。"
            "将瓶体从竖直方向略微倾斜约 25 度。保持真实几何、透视、地面接触、"
            "光照和阴影。保留原始环境。"
        ),
        seed=100,
    ),
    EditPrompt(
        name="heavy_tilt",
        category="state",
        prompt=_compose(
            USE_REFERENCE,
            KEEP_CYLINDER,
            "Tilt the cylinder at about 45 degrees from vertical, "
            "leaning against a wall.",
            PHYSICAL_REALISM,
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶颜色、形状、阀门结构和标签不变。"
            "将瓶体从竖直方向倾斜约 45 度，倚靠在墙上。保持真实几何、透视、"
            "地面接触、光照和阴影。"
        ),
        seed=200,
    ),
    EditPrompt(
        name="fallen",
        category="state",
        prompt=_compose(
            USE_REFERENCE,
            KEEP_CYLINDER,
            "Change the cylinder's physical state from upright to "
            "lying horizontally on the floor.",
            PHYSICAL_REALISM,
            "Preserve the original environment.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶颜色、形状、阀门结构和标签不变。"
            "将瓶体从直立状态改为水平倒在地面上。保持真实几何、透视、地面接触、"
            "光照和阴影。保留原始环境。"
        ),
        seed=300,
    ),
    EditPrompt(
        name="fallen_partial_occlusion",
        category="state",
        prompt=_compose(
            USE_REFERENCE,
            KEEP_CYLINDER,
            "Change the cylinder to lying horizontally on the floor, "
            "with part of the cylinder body partially obscured by "
            "nearby equipment or an object.",
            PHYSICAL_REALISM,
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶颜色、形状、阀门结构和标签不变。"
            "将瓶体改为水平倒在地面上，瓶体部分被附近设备或物体遮挡。"
            "保持真实几何、透视、地面接触、光照和阴影。"
        ),
        seed=400,
    ),
    EditPrompt(
        name="fallen_multi",
        category="state",
        prompt=_compose(
            USE_REFERENCE,
            KEEP_CYLINDER,
            "Show two oxygen cylinders: one still upright and one "
            "fallen horizontally on the floor.",
            PHYSICAL_REALISM,
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶颜色、形状、阀门结构和标签不变。"
            "画面中显示两个氧气瓶：一个保持直立，另一个水平倒在地面上。"
            "保持真实几何、透视、地面接触、光照和阴影。"
        ),
        seed=500,
    ),
]


# ============================================================
# 二、背景环境增强提示词
# ============================================================
BACKGROUND_EDIT_PROMPTS: List[EditPrompt] = [
    EditPrompt(
        name="hospital",
        category="background",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the oxygen cylinder unchanged.",
            "Replace the background with a hospital ward or corridor, "
            "clean white walls, medical equipment in the distance.",
            "Maintain the cylinder's original lighting and shadows.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶不变。"
            "将背景替换为医院病房或走廊，干净的白色墙壁，远处有医疗设备。"
            "保持氧气瓶原有的光照和阴影。"
        ),
        seed=1001,
    ),
    EditPrompt(
        name="factory",
        category="background",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the oxygen cylinder unchanged.",
            "Replace the background with an industrial factory workshop, "
            "metal structures, machinery.",
            "Maintain the cylinder's original lighting and shadows.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶不变。"
            "将背景替换为工业工厂车间，金属结构，机械设备。"
            "保持氧气瓶原有的光照和阴影。"
        ),
        seed=1002,
    ),
    EditPrompt(
        name="warehouse",
        category="background",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the oxygen cylinder unchanged.",
            "Replace the background with a gas cylinder storage area in "
            "a warehouse, shelving and pallets in the background.",
            "Maintain the cylinder's original lighting and shadows.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶不变。"
            "将背景替换为仓库中的气瓶存放区，背景有货架和托盘。"
            "保持氧气瓶原有的光照和阴影。"
        ),
        seed=1003,
    ),
    EditPrompt(
        name="lab",
        category="background",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the oxygen cylinder unchanged.",
            "Replace the background with a laboratory environment, "
            "instruments and equipment.",
            "Maintain the cylinder's original lighting and shadows.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶不变。"
            "将背景替换为实验室环境，仪器设备。"
            "保持氧气瓶原有的光照和阴影。"
        ),
        seed=1004,
    ),
    EditPrompt(
        name="complex",
        category="background",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the oxygen cylinder unchanged.",
            "Replace the background with a complex environment: "
            "people passing by, equipment partially obscuring the view, "
            "other gas cylinders in the background.",
            "Maintain the cylinder's original lighting and shadows.",
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶不变。"
            "将背景替换为复杂环境：有人经过、设备部分遮挡视线、"
            "背景中有其他气瓶。保持氧气瓶原有的光照和阴影。"
        ),
        seed=1005,
    ),
]


# ============================================================
# 三、品牌与瓶体外观增强提示词
# ============================================================
APPEARANCE_EDIT_PROMPTS: List[EditPrompt] = [
    EditPrompt(
        name="color_variant",
        category="appearance",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the cylinder's shape, valve structure and labels unchanged.",
            "Change the cylinder's body color to a different common "
            "oxygen cylinder color.",
            PHYSICAL_REALISM,
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶形状、阀门结构和标签不变。"
            "将瓶体颜色改为另一种常见的氧气瓶颜色。"
            "保持真实几何、透视、地面接触、光照和阴影。"
        ),
        seed=2001,
    ),
    EditPrompt(
        name="wear_and_tear",
        category="appearance",
        prompt=_compose(
            USE_REFERENCE,
            "Keep the cylinder's shape, color, valve structure and "
            "labels unchanged.",
            "Add realistic wear, stains and reflective variation to "
            "the cylinder surface.",
            PHYSICAL_REALISM,
        ),
        prompt_zh=(
            "以参考图像为原始场景。保持氧气瓶形状、颜色、阀门结构和标签不变。"
            "在瓶体表面增加真实的磨损、污渍和反光变化。"
            "保持真实几何、透视、地面接触、光照和阴影。"
        ),
        seed=2002,
    ),
]


# ============================================================
# 四、文生图补充提示词（补充稀缺场景）
# ============================================================
TEXT2IMG_PROMPTS: List[Text2ImgPrompt] = [
    Text2ImgPrompt(
        name="t2i_fallen_hospital",
        category="text2img",
        prompt=(
            "A blue medical oxygen cylinder lying horizontally on a "
            "hospital floor, photorealistic, clear lighting, visible "
            "valve and label, natural shadows."
        ),
        prompt_zh=(
            "一个蓝色医用氧气瓶水平倒在医院地板上，照片级真实，"
            "光照清晰，可见阀门和标签，自然阴影。"
        ),
        seed=3001,
    ),
    Text2ImgPrompt(
        name="t2i_fallen_warehouse",
        category="text2img",
        prompt=(
            "An industrial oxygen gas cylinder fallen on the ground in "
            "a warehouse, metal floor, realistic shadows, photorealistic."
        ),
        prompt_zh=(
            "一个工业氧气瓶倒在仓库地面上，金属地板，真实阴影，照片级真实。"
        ),
        seed=3002,
    ),
    Text2ImgPrompt(
        name="t2i_fallen_factory",
        category="text2img",
        prompt=(
            "A green oxygen cylinder lying on a factory floor, "
            "industrial environment, machinery in the background, "
            "photorealistic, natural lighting."
        ),
        prompt_zh=(
            "一个绿色氧气瓶倒在工厂地面上，工业环境，背景有机械设备，"
            "照片级真实，自然光照。"
        ),
        seed=3003,
    ),
]


# ============================================================
# 五、负向提示词（通用）
# ============================================================
DEFAULT_NEGATIVE_PROMPT = (
    "floating object, deformed valve, distorted shape, "
    "incorrect shadow, blurry, low quality, watermark, text artifacts"
)
DEFAULT_NEGATIVE_PROMPT_ZH = (
    "悬浮物体、变形阀门、扭曲形状、错误阴影、模糊、低质量、水印、文字伪影"
)


# ============================================================
# 汇总（便于批量调用）
# ============================================================
ALL_EDIT_PROMPTS: List[EditPrompt] = (
    STATE_EDIT_PROMPTS
    + BACKGROUND_EDIT_PROMPTS
    + APPEARANCE_EDIT_PROMPTS
)


def get_prompts_by_category(category: str) -> List[EditPrompt]:
    """按分类筛选编辑提示词"""
    return [p for p in ALL_EDIT_PROMPTS if p.category == category]


__all__ = [
    "EditPrompt", "Text2ImgPrompt",
    "STATE_EDIT_PROMPTS", "BACKGROUND_EDIT_PROMPTS",
    "APPEARANCE_EDIT_PROMPTS", "TEXT2IMG_PROMPTS",
    "ALL_EDIT_PROMPTS", "get_prompts_by_category",
    "DEFAULT_NEGATIVE_PROMPT", "DEFAULT_NEGATIVE_PROMPT_ZH",
]