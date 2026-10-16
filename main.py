# -*- coding: utf-8 -*-
"""
命令行示例入口

演示 core 的用法：
    python main.py t2i "一只在雨中的猫"
    python main.py storyboard     # 运行内置示例剧本（4 镜）
    python main.py game           # 生成游戏角色三视图
    python main.py health         # 检查服务状态

也可以直接打开 Gradio 调试页面： python app.py
"""
import sys

from core import CONFIG, OmniClient, PROMPTS
from core.workflows import GameCharacterWorkflow, StoryboardWorkflow


def cmd_health():
    client = OmniClient()
    print(f"服务地址：{CONFIG.api.base_url}")
    print(f"健康检查：{'✅ 就绪' if client.health() else '❌ 不可达'}")
    print(f"模型列表：{client.list_models() or '（空，属已知现象）'}")


def cmd_t2i(prompt: str):
    client = OmniClient()
    img = client.generate(prompt, negative_prompt=PROMPTS.negative_for("default"))
    path = client.save(img, CONFIG.paths.output_path / "cli_t2i.png",
                       metadata={"prompt": prompt})
    print(f"已保存：{path}  尺寸：{img.size}")


def cmd_storyboard():
    wf = StoryboardWorkflow()
    results = wf.run(StoryboardWorkflow.demo_script(), prefix="demo")
    print(f"\n共生成 {len(results)} 个分镜：")
    for shot, (img, path) in results:
        print(f"  - {shot.shot_type:14s} -> {path.name}")


def cmd_game():
    wf = GameCharacterWorkflow()
    _, path = wf.render_asset(
        "character_sheet", "hero",
        "a young swordsman, silver hair, blue cloak, glowing rune sword",
        "game_concept", seed=2001,
    )
    print(f"已保存：{path}")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "health"
    if cmd == "health":
        cmd_health()
    elif cmd == "t2i":
        cmd_t2i(args[1] if len(args) > 1 else "a serene Japanese garden with cherry blossoms")
    elif cmd == "storyboard":
        cmd_storyboard()
    elif cmd == "game":
        cmd_game()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
