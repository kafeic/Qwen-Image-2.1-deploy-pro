#!/usr/bin/env python3
# test_t2i_batch.py
# 批量并发生图

import concurrent.futures
import requests
import base64

SERVER = "http://localhost:8014/v1/images/generations"

prompts = [
    "A red apple on a white plate, studio lighting",
    "A blue sports car on a coastal highway at sunset",
    "A cozy cabin in a snowy forest, warm light from windows",
    "A futuristic city skyline with flying cars, neon lights",
]

def generate(args):
    idx, prompt = args
    payload = {
        "model": "Qwen/Qwen-Image-2.1",
        "prompt": prompt,
        "size": "1024x1024",
        "response_format": "b64_json",
        "seed": 100 + idx,
    }
    resp = requests.post(SERVER, json=payload)
    resp.raise_for_status()
    img_b64 = resp.json()["data"][0]["b64_json"]
    filename = f"batch_{idx}.png"
    with open(filename, "wb") as f:
        f.write(base64.b64decode(img_b64))
    return filename

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(generate, enumerate(prompts)))

for r in results:
    print(f"已保存: {r}")
