#!/usr/bin/env python3
# test_t2i_2k.py
# 2K 分辨率文生图

import requests
import base64

payload = {
    "model": "Qwen/Qwen-Image-2.1",
    "prompt": "An intricate steampunk clockwork heart, highly detailed, 8K",
    "size": "2048x2048",
    "num_inference_steps": 40,
    "seed": 777,
    "response_format": "b64_json",
}

resp = requests.post("http://localhost:8014/v1/images/generations", json=payload)
resp.raise_for_status()

with open("test_2k.png", "wb") as f:
    f.write(base64.b64decode(resp.json()["data"][0]["b64_json"]))

print("已保存: test_2k.png (2048x2048)")