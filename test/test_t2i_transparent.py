#!/usr/bin/env python3
# test_t2i_transparent.py
# 生成带透明通道的 PNG

import requests
import base64
from PIL import Image
import io

payload = {
    "model": "Qwen/Qwen-Image-2.1",
    "prompt": "A floating translucent crystal orb, transparent background, RGBA",
    "size": "1024x1024",
    "seed": 888,
    "response_format": "b64_json",
}

resp = requests.post("http://localhost:8014/v1/images/generations", json=payload)
resp.raise_for_status()

img_bytes = base64.b64decode(resp.json()["data"][0]["b64_json"])
img = Image.open(io.BytesIO(img_bytes))
img.save("test_transparent.png")

# 检查是否有 alpha 通道
if img.mode == "RGBA":
    print(f"✅ 透明图生成成功: test_transparent.png (mode={img.mode})")
else:
    print(f"⚠️ 输出模式为 {img.mode}，可能未启用透明通道")
