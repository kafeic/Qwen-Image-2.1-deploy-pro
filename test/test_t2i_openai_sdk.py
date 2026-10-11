#!/usr/bin/env python3
# test_t2i_openai_sdk.py
# 使用 OpenAI SDK 调用 vLLM-Omni

from openai import OpenAI
import base64

client = OpenAI(
    base_url="http://localhost:8014/v1",
    api_key="none",  # vLLM 不校验 key
)

response = client.images.generate(
    model="Qwen/Qwen-Image-2.1",
    prompt="A serene Japanese garden with cherry blossoms and a koi pond",
    n=1,
    size="1024x1024",
    response_format="b64_json",
)

img_b64 = response.data[0].b64_json
with open("test_sdk.png", "wb") as f:
    f.write(base64.b64decode(img_b64))

print("已保存: test_sdk.png")
