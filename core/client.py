"""
vLLM-Omni API 客户端封装
统一处理请求、重试、响应解析，供上层流水线调用。
"""
import base64
import time
from pathlib import Path
from typing import Optional, List

import requests

from .config import API_CONFIG, GEN_CONFIG, APIConfig, GenerationConfig


class OmniClient:
    """vLLM-Omni API 客户端"""

    def __init__(
        self,
        api_config: Optional[APIConfig] = None,
        gen_config: Optional[GenerationConfig] = None,
    ):
        self.api = api_config or API_CONFIG
        self.gen = gen_config or GEN_CONFIG

    # --------------------------------------------------------
    # 健康检查
    # --------------------------------------------------------
    def health(self) -> bool:
        """检查服务是否就绪"""
        try:
            resp = requests.get(self.api.health_endpoint, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    # --------------------------------------------------------
    # 文生图
    # --------------------------------------------------------
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        height: Optional[int] = None,
        width: Optional[int] = None,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> bytes:
        """
        文生图，返回图像 bytes。

        参数：
            prompt:          正向提示词
            negative_prompt: 负向提示词
            height/width:    分辨率
            steps:           采样步数
            cfg_scale:       引导系数
            seed:            随机种子
        """
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "extra_body": {
                "height": height or self.gen.height,
                "width": width or self.gen.width,
                "num_inference_steps": steps or self.gen.num_inference_steps,
                "cfg_scale": cfg_scale if cfg_scale is not None else self.gen.cfg_scale,
                "seed": seed if seed is not None else self.gen.seed,
                "negative_prompt": negative_prompt,
            },
        }
        data = self._post_with_retry(self.api.generate_endpoint, json=payload)
        img_url = data["choices"][0]["message"]["content"][0]["image_url"]["url"]
        return base64.b64decode(img_url.split(",", 1)[1])

    # --------------------------------------------------------
    # 图像编辑
    # --------------------------------------------------------
    def edit(
        self,
        image_path: str,
        prompt: str,
        negative_prompt: str = "",
        height: Optional[int] = None,
        width: Optional[int] = None,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> bytes:
        """
        图像编辑，返回编辑后的图像 bytes。
        """
        with open(image_path, "rb") as f:
            files = {
                "image": (Path(image_path).name, f, "image/png"),
            }
            data = {
                "model": self.api.model_name,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "size": f"{width or self.gen.width}x{height or self.gen.height}",
                "num_inference_steps": str(steps or self.gen.num_inference_steps),
                "cfg_scale": str(cfg_scale if cfg_scale is not None else self.gen.cfg_scale),
                "seed": str(seed if seed is not None else self.gen.seed),
                "output_format": self.gen.output_format,
            }
            resp = self._post_with_retry(
                self.api.edit_endpoint, files=files, data=data
            )
        return base64.b64decode(resp["data"][0]["b64_json"])

    # --------------------------------------------------------
    # 内部：带重试的 POST 请求
    # --------------------------------------------------------
    def _post_with_retry(self, url, json=None, files=None, data=None):
        last_err = None
        for attempt in range(self.api.max_retries + 1):
            try:
                resp = requests.post(
                    url,
                    json=json,
                    files=files,
                    data=data,
                    timeout=(self.api.connect_timeout, self.api.timeout),
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                if attempt < self.api.max_retries:
                    wait = 2 ** attempt
                    print(f"  请求失败（{e}），{wait}s 后重试...")
                    time.sleep(wait)
        raise RuntimeError(f"请求最终失败：{last_err}")


__all__ = ["OmniClient"]
