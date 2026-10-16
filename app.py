# -*- coding: utf-8 -*-
"""
Qwen-Image-2.1 调试 / 演示页面（Gradio）

启动：
    python app.py
    python app.py --host 0.0.0.0 --port 7860 --share

标签页：
    1. 文生图     自由提示词出图
    2. 短剧分镜   选角色 / 镜头 / 风格，逐镜生成（内置示例剧本）
    3. 游戏角色   三视图 / 概念图 / 头像 / 道具
    4. 服务状态   健康检查、模型列表、当前配置

每个标签页都带「调试信息」面板，显示实际组装的 prompt 与请求参数。
"""
from __future__ import annotations

import argparse
import json
from typing import List, Optional, Tuple

import gradio as gr

from core import CONFIG, PROMPTS, OmniClient
from core.workflows import GameCharacterWorkflow, Shot, StoryboardWorkflow

# ============================================================
# 延迟初始化（服务未启动时页面也能打开）
# ============================================================
_client: Optional[OmniClient] = None
_storyboard: Optional[StoryboardWorkflow] = None
_game: Optional[GameCharacterWorkflow] = None


def get_client() -> OmniClient:
    global _client
    if _client is None:
        _client = OmniClient()
    return _client


def get_storyboard() -> StoryboardWorkflow:
    global _storyboard
    if _storyboard is None:
        _storyboard = StoryboardWorkflow(client=get_client())
    return _storyboard


def get_game() -> GameCharacterWorkflow:
    global _game
    if _game is None:
        _game = GameCharacterWorkflow(client=get_client())
    return _game


SIZE_PRESETS = ["1024x1024", "1280x720", "720x1280", "1536x1024", "1024x1536", "2048x2048"]


def _parse_size(size: str) -> Tuple[int, int]:
    w, h = size.lower().split("x")
    return int(w), int(h)


def _debug(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ============================================================
# 1. 文生图
# ============================================================
def ui_generate(prompt, negative, size, steps, guidance, seed):
    if not prompt or not prompt.strip():
        return None, "⚠️ 请先填写提示词"
    w, h = _parse_size(size)
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "size": size,
        "num_inference_steps": int(steps),
        "guidance_scale": float(guidance),
        "seed": int(seed),
    }
    try:
        img = get_client().generate(
            prompt,
            negative_prompt=negative,
            width=w, height=h,
            steps=int(steps),
            guidance_scale=float(guidance),
            seed=int(seed),
        )
    except Exception as e:  # noqa: BLE001
        return None, f"❌ 生成失败：{e}\n\n请求参数：\n{_debug(payload)}"
    return img, _debug(payload)


# ============================================================
# 2. 短剧分镜
# ============================================================
def ui_shot(character, shot_type, style, scene, action, mood, seed):
    if not scene.strip() or not action.strip():
        return None, "⚠️ 请填写「场景」与「动作」"
    shot = Shot(
        shot_type=shot_type,
        character=character or "",
        action=action,
        scene=scene,
        mood=mood or "tense",
        style=style,
        seed=int(seed),
    )
    prompt, negative = get_storyboard().build_prompt(shot)
    try:
        img, path = get_storyboard().render_shot(shot, index=1, prefix="ui")
    except Exception as e:  # noqa: BLE001
        return None, f"❌ 生成失败：{e}\n\n组装提示词：\n{prompt}"
    return img, _debug({
        "shot_type": shot_type, "character": character or "（空镜）",
        "style": style, "scene": scene, "action": action, "mood": mood,
        "seed": int(seed), "saved": str(path),
        "prompt": prompt, "negative_prompt": negative,
    })


def ui_demo_script():
    shots = StoryboardWorkflow.demo_script()
    images: List = []
    logs: List[str] = []
    for i, shot in enumerate(shots, 1):
        prompt, _ = get_storyboard().build_prompt(shot)
        try:
            img, path = get_storyboard().render_shot(shot, index=i, prefix="demo")
            images.append(img)
            logs.append(f"[{i}] {shot.shot_type} / {shot.character or '空镜'}"
                        f"  → {path.name}\n    {prompt[:120]}...")
        except Exception as e:  # noqa: BLE001
            logs.append(f"[{i}] ❌ 失败：{e}")
    return images, "\n\n".join(logs) if logs else "（无输出）"


# ============================================================
# 3. 游戏角色
# ============================================================
def ui_game(asset_type, role, appearance, style, seed):
    if not appearance.strip():
        return None, "⚠️ 请填写角色外观描述"
    prompt, negative = get_game().build_prompt(asset_type, role, appearance, style)
    try:
        img, path = get_game().render_asset(
            asset_type, role, appearance, style, seed=int(seed),
        )
    except Exception as e:  # noqa: BLE001
        return None, f"❌ 生成失败：{e}\n\n组装提示词：\n{prompt}"
    return img, _debug({
        "asset_type": asset_type, "role": role, "style": style,
        "appearance": appearance, "seed": int(seed), "saved": str(path),
        "prompt": prompt, "negative_prompt": negative,
    })


# ============================================================
# 4. 服务状态
# ============================================================
def ui_status():
    client = get_client()
    ok = client.health()
    models = client.list_models()
    lines = [
        f"健康检查（{CONFIG.api.health_endpoint}）：{'✅ 就绪' if ok else '❌ 不可达'}",
        f"模型列表（{CONFIG.api.models_endpoint}）：{models or '（空，属已知现象）'}",
        "",
        "当前配置：",
        f"  base_url     = {CONFIG.api.base_url}",
        f"  model_name   = {CONFIG.api.model_name}",
        f"  api_style    = {CONFIG.api.api_style}",
        f"  默认分辨率   = {CONFIG.generation.width}x{CONFIG.generation.height}",
        f"  默认步数     = {CONFIG.generation.num_inference_steps}",
        f"  默认引导系数 = {CONFIG.generation.guidance_scale}",
        f"  输出目录     = {CONFIG.paths.output_path}",
    ]
    return "\n".join(lines)


# ============================================================
# 页面
# ============================================================
def build_ui() -> gr.Blocks:
    char_choices = [("（空镜 / 无角色）", "")] + PROMPTS.character_choices()
    shot_choices = PROMPTS.shot_choices()
    style_choices = PROMPTS.style_choices()
    role_choices = PROMPTS.role_choices()
    asset_choices = PROMPTS.asset_choices()

    with gr.Blocks(title="Qwen-Image-2.1 调试台") as demo:
        gr.Markdown("# 🎬 Qwen-Image-2.1 调试台\n"
                    "文生图 / AI 短剧分镜 / 游戏角色 —— 提示词与工作流示例")

        # ---------- Tab 1：文生图 ----------
        with gr.Tab("文生图"):
            with gr.Row():
                with gr.Column():
                    t1_prompt = gr.Textbox(label="提示词 Prompt", lines=4,
                                           placeholder="A majestic dragon flying over misty mountains at sunrise")
                    t1_negative = gr.Textbox(label="负向提示词 Negative", lines=2,
                                             value=PROMPTS.negative_for("default"))
                    with gr.Row():
                        t1_size = gr.Dropdown(SIZE_PRESETS, value="1024x1024", label="分辨率")
                        t1_seed = gr.Number(value=42, label="随机种子", precision=0)
                    with gr.Row():
                        t1_steps = gr.Slider(10, 60, value=CONFIG.generation.num_inference_steps,
                                             step=1, label="采样步数")
                        t1_guidance = gr.Slider(1.0, 10.0, value=CONFIG.generation.guidance_scale,
                                                step=0.5, label="引导系数 CFG")
                    t1_btn = gr.Button("生成", variant="primary")
                with gr.Column():
                    t1_image = gr.Image(label="结果", type="pil")
                    t1_debug = gr.Code(label="调试信息（实际请求）", language="json")
            t1_btn.click(ui_generate,
                         inputs=[t1_prompt, t1_negative, t1_size, t1_steps, t1_guidance, t1_seed],
                         outputs=[t1_image, t1_debug])

        # ---------- Tab 2：短剧分镜 ----------
        with gr.Tab("短剧分镜"):
            with gr.Row():
                with gr.Column():
                    s_shot = gr.Dropdown(shot_choices, value=shot_choices[0][1], label="镜头类型")
                    s_char = gr.Dropdown(char_choices, value=char_choices[1][1], label="角色")
                    s_style = gr.Dropdown(style_choices, value=style_choices[0][1], label="风格")
                    s_scene = gr.Textbox(label="场景 Scene", value="a neon-lit city street in the rain")
                    s_action = gr.Textbox(label="动作 Action", value="walking quickly while holding an umbrella")
                    s_mood = gr.Textbox(label="情绪氛围 Mood", value="tense, uneasy")
                    s_seed = gr.Number(value=1002, label="随机种子", precision=0)
                    with gr.Row():
                        s_btn = gr.Button("生成该分镜", variant="primary")
                        s_demo = gr.Button("运行示例剧本（4 镜）")
                with gr.Column():
                    s_image = gr.Image(label="单镜结果", type="pil")
                    s_gallery = gr.Gallery(label="示例剧本分镜", columns=2)
                    s_debug = gr.Code(label="调试信息", language="json")
            s_btn.click(ui_shot,
                        inputs=[s_char, s_shot, s_style, s_scene, s_action, s_mood, s_seed],
                        outputs=[s_image, s_debug])
            s_demo.click(ui_demo_script, inputs=[], outputs=[s_gallery, s_debug])

        # ---------- Tab 3：游戏角色 ----------
        with gr.Tab("游戏角色"):
            with gr.Row():
                with gr.Column():
                    g_asset = gr.Dropdown(asset_choices, value=asset_choices[0][1], label="资产类型")
                    g_role = gr.Dropdown(role_choices, value=role_choices[0][1], label="角色定位")
                    g_style = gr.Dropdown(style_choices, value="game_concept", label="风格")
                    g_appearance = gr.Textbox(label="外观描述 Appearance", lines=3,
                                              value="a young swordsman, silver hair, blue cloak, glowing rune sword")
                    g_seed = gr.Number(value=2001, label="随机种子", precision=0)
                    g_btn = gr.Button("生成", variant="primary")
                with gr.Column():
                    g_image = gr.Image(label="结果", type="pil")
                    g_debug = gr.Code(label="调试信息", language="json")
            g_btn.click(ui_game,
                        inputs=[g_asset, g_role, g_appearance, g_style, g_seed],
                        outputs=[g_image, g_debug])

        # ---------- Tab 4：服务状态 ----------
        with gr.Tab("服务状态"):
            st_btn = gr.Button("检查服务", variant="primary")
            st_out = gr.Textbox(label="状态", lines=14)
            st_btn.click(ui_status, inputs=[], outputs=[st_out])

    return demo


def main():
    parser = argparse.ArgumentParser(description="Qwen-Image-2.1 Gradio 调试台")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（内网访问用 0.0.0.0）")
    parser.add_argument("--port", type=int, default=7860, help="端口")
    parser.add_argument("--share", action="store_true", help="生成公网分享链接")
    args = parser.parse_args()

    demo = build_ui()
    # 出图较慢，串行执行，避免压垮单卡服务
    demo.queue(default_concurrency_limit=1)
    demo.launch(server_name=args.host, server_port=args.port, share=args.share)


if __name__ == "__main__":
    main()
