# -*- coding: utf-8 -*-
"""
vLLM-Omni / OpenAI 兼容 API 客户端封装

统一处理请求构造、重试、响应解析与调试日志，供工作流与 Gradio 页面调用。
默认走已验证的 OpenAI 兼容端点 ``/v1/images/generations``（见 test/ 脚本），
可通过 ``config.yaml`` 的 ``api.api_style`` 切换到 ``chat`` 多模态端点。

用法：
    from core.client import OmniClient
    client = OmniClient()
    img = client.generate("一只在雨中的猫")   # 返回 PIL.Image
    client.save(img, "data/outputs/cat.png")
"""
from __future__ import annotations

import base64
import io
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from PIL import Image

from .config import CONFIG, APIConfig, Config, GenerationConfig

ImageInput = Union[str, Path, bytes, Image.Image]


class OmniClientError(RuntimeError):
    """客户端统一异常"""


class OmniClient:
    """vLLM-Omni API 客户端"""

    def __init__(
        self,
        config: Optional[Config] = None,
        api_config: Optional[APIConfig] = None,
        gen_config: Optional[GenerationConfig] = None,
    ):
        self.config = config or CONFIG
        self.api = api_config or self.config.api
        self.gen = gen_config or self.config.generation
        self.debug = self.config.debug

    # ========================================================
    # 健康检查 / 模型列表
    # ========================================================
    def health(self) -> bool:
        """检查服务是否就绪（GET /health）"""
        try:
            resp = requests.get(self.api.health_endpoint, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """列出服务暴露的模型名（GET /v1/models）。

        注意：部分 vLLM-Omni 部署该接口返回空列表，属已知现象，不影响推理。
        """
        try:
            resp = requests.get(self.api.models_endpoint, timeout=10)
            resp.raise_for_status()
            return [m.get("id", "") for m in resp.json().get("data", [])]
        except Exception as e:
            self._log(f"list_models 失败：{e}")
            return []

    # ========================================================
    # 文生图
    # ========================================================
    def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: Optional[int] = None,
        n: int = 1,
    ) -> Image.Image:
        """文生图，返回 PIL.Image。

        参数：
            prompt:          正向提示词
            negative_prompt: 负向提示词
            width/height:    分辨率（默认取 config.yaml）
            steps:           采样步数
            guidance_scale:  引导系数（1.0 = 不启用 CFG）
            seed:            随机种子（固定可复现）
            n:               生成数量（多数部署仅支持 1）
        """
        w = width or self.gen.width
        h = height or self.gen.height
        params = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": f"{w}x{h}",
            "num_inference_steps": steps if steps is not None else self.gen.num_inference_steps,
            "guidance_scale": guidance_scale if guidance_scale is not None else self.gen.guidance_scale,
            "seed": seed if seed is not None else self.gen.seed,
            "n": n,
            "output_format": self.gen.output_format,
        }

        if self.api.api_style == "chat":
            data = self._post_with_retry(self.api.chat_endpoint, json=self._chat_payload(params))
        else:
            data = self._post_with_retry(self.api.generate_endpoint, json=self._images_payload(params))
        return self._parse_image(data)

    # ========================================================
    # 图像编辑（图生图）
    # ========================================================
    def edit(
        self,
        image: ImageInput,
        prompt: str,
        *,
        negative_prompt: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> Image.Image:
        """图像编辑，返回编辑后的 PIL.Image。

        image 支持：本地路径 / bytes / PIL.Image。
        """
        w = width or self.gen.width
        h = height or self.gen.height
        img_bytes, filename = self._as_png_bytes(image)
        files = {"image": (filename, img_bytes, "image/png")}
        form = {
            "model": self.api.model_name,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "size": f"{w}x{h}",
            "num_inference_steps": str(steps if steps is not None else self.gen.num_inference_steps),
            "guidance_scale": str(guidance_scale if guidance_scale is not None else self.gen.guidance_scale),
            "seed": str(seed if seed is not None else self.gen.seed),
            "response_format": "b64_json",
        }
        data = self._post_with_retry(self.api.edit_endpoint, files=files, data=form)
        return self._parse_image(data)

    # ========================================================
    # 保存与元数据
    # ========================================================
    def save(
        self,
        image: Image.Image,
        path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """保存图像；``debug.save_metadata`` 为真时同目录写入 .json 元数据。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        if metadata is not None and self.debug.save_metadata:
            meta_path = path.with_suffix(".json")
            meta = dict(metadata)
            meta["image"] = path.name
            meta["size"] = list(image.size)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        return path

    # ========================================================
    # 内部：请求体构造
    # ========================================================
    def _images_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI /v1/images/generations 请求体"""
        payload = {"model": self.api.model_name, "response_format": "b64_json"}
        payload.update(params)
        return payload

    def _chat_payload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """多模态 /v1/chat/completions 请求体（extra_body 传扩散参数）"""
        return {
            "model": self.api.model_name,
            "messages": [{"role": "user", "content": params["prompt"]}],
            "extra_body": {
                "height": params["size"].split("x")[1],
                "width": params["size"].split("x")[0],
                "num_inference_steps": params["num_inference_steps"],
                "guidance_scale": params["guidance_scale"],
                "seed": params["seed"],
                "negative_prompt": params["negative_prompt"],
            },
        }

    # ========================================================
    # 内部：带重试的 POST
    # ========================================================
    def _post_with_retry(self, url, **kwargs) -> Dict[str, Any]:
        last_err: Optional[Exception] = None
        for attempt in range(self.api.max_retries + 1):
            t0 = time.time()
            try:
                resp = requests.post(
                    url,
                    timeout=(self.api.connect_timeout, self.api.timeout),
                    **kwargs,
                )
                resp.raise_for_status()
                self._log(
                    f"POST {url} -> {resp.status_code} "
                    f"({time.time() - t0:.1f}s)"
                )
                if self.debug.log_payload:
                    self._log_payload(kwargs)
                return resp.json()
            except Exception as e:
                last_err = e
                body = ""
                if isinstance(e, requests.HTTPError) and e.response is not None:
                    body = f" body={e.response.text[:300]}"
                self._log(f"请求失败（{e}）{body}")
                if attempt < self.api.max_retries:
                    wait = 2 ** attempt
                    self._log(f"{wait}s 后重试...")
                    time.sleep(wait)
        raise OmniClientError(f"请求最终失败：{last_err}")

    # ========================================================
    # 内部：响应解析
    # ========================================================
    @staticmethod
    def _parse_image(data: Dict[str, Any]) -> Image.Image:
        """从响应中提取图像并解码为 PIL.Image。"""
        # 1) OpenAI images 格式：{"data":[{"b64_json": ...} | {"url": ...}]}
        items = data.get("data")
        if isinstance(items, list) and items:
            item = items[0]
            if item.get("b64_json"):
                return OmniClient._b64_to_image(item["b64_json"])
            if item.get("url"):
                return OmniClient._url_to_image(item["url"])
        # 2) chat 格式：{"choices":[{"message":{"content":[{"image_url":{"url":...}}]}}]}
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content")
            if isinstance(content, list):
                for part in content:
                    url = (part.get("image_url") or {}).get("url")
                    if url:
                        return OmniClient._url_to_image(url)
            elif isinstance(content, str) and content.startswith("data:image"):
                return OmniClient._b64_to_image(content)
        raise OmniClientError(f"无法从响应中解析图像：{str(data)[:300]}")

    @staticmethod
    def _b64_to_image(b64: str) -> Image.Image:
        if "," in b64[:64] and b64.strip().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        return Image.open(io.BytesIO(base64.b64decode(b64)))

    @staticmethod
    def _url_to_image(url: str) -> Image.Image:
        if url.startswith("data:image"):
            return OmniClient._b64_to_image(url)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content))

    # ========================================================
    # 内部：输入归一化 / 日志
    # ========================================================
    @staticmethod
    def _as_png_bytes(image: ImageInput) -> tuple[bytes, str]:
        """把任意图像输入统一成 PNG bytes + 文件名。"""
        if isinstance(image, Image.Image):
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return buf.getvalue(), "input.png"
        if isinstance(image, (bytes, bytearray)):
            return bytes(image), "input.png"
        path = Path(image)
        return path.read_bytes(), path.name

    def _log(self, msg: str) -> None:
        print(f"[OmniClient] {msg}")

    def _log_payload(self, kwargs: Dict[str, Any]) -> None:
        payload = kwargs.get("json")
        if payload is None and kwargs.get("data") is not None:
            payload = kwargs["data"]
        if payload is not None:
            self._log(f"payload = {json.dumps(payload, ensure_ascii=False)[:500]}")


__all__ = ["OmniClient", "OmniClientError", "ImageInput"]
