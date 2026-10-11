#!/usr/bin/env python3
# test_t2i_full.py
# 完整参数文生图测试

# 参数说明：
#
# negative_prompt：描述图像中应避免的内容
#
# num_inference_steps：扩散步数，Qwen-Image-2.1 建议 40 步
#
# guidance_scale：分类器引导比例，Qwen-Image-2.1 默认 1.0（不启用 CFG）

import requests
import base64
import io
from PIL import Image

SERVER = "http://localhost:8014"

payload = {
    "model": "Qwen/Qwen-Image-2.1",
    "prompt": "A majestic dragon flying over misty mountains at sunrise, epic fantasy art",
    "negative_prompt": "blurry, low quality, distorted, ugly",
    "size": "1024x1024",
    "num_inference_steps": 40,
    "guidance_scale": 1.0,
    "seed": 12345,
    "response_format": "b64_json",
}

resp = requests.post(f"{SERVER}/v1/images/generations", json=payload)
resp.raise_for_status()

data = resp.json()
img_b64 = data["data"][0]["b64_json"]
img_bytes = base64.b64decode(img_b64)
img = Image.open(io.BytesIO(img_bytes))
img.save("test_full.png")
print("已保存: test_full.png")
print(f"图片尺寸: {img.size}")
