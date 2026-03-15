#!/usr/bin/env python3
"""
闲鱼项目统一 LLM 适配层。

优先走本机 OpenClaw CLI（复用 openai-codex/gpt-5.4 OAuth 链路），
只有显式配置 API_KEY / OPENAI_API_KEY 时才回退到 OpenAI SDK。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional


Message = Dict[str, str]


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("模型返回为空")

    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _build_openclaw_prompt(messages: List[Message], json_mode: bool) -> str:
    lines = [
        "你正在为一个本地 Python 自动化脚本提供模型输出。",
        "不要调用工具，不要修改文件，不要解释推理过程。",
    ]
    if json_mode:
        lines.append("输出要求：只输出一个合法 JSON 对象，不要加代码块，不要加额外说明。")
    else:
        lines.append("输出要求：只输出最终回答正文，不要加额外说明。")
    lines.append("下面是消息链：")

    for message in messages:
        role = message.get("role", "user").upper()
        content = (message.get("content") or "").strip()
        lines.append(f"[{role}]")
        lines.append(content)

    lines.append("现在输出 ASSISTANT 的最终内容。")
    return "\n".join(lines)


class XianyuLLM:
    def __init__(self):
        self.backend = self._resolve_backend()
        self.client = self._build_sdk_client() if self.backend == "sdk" else None
        self.model = os.getenv("MODEL_NAME") or "openai-codex/gpt-5.4"

    def _resolve_backend(self) -> str:
        preferred = os.getenv("XIANYU_LLM_BACKEND", "auto").strip().lower()
        has_sdk_key = bool(os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY"))
        has_openclaw = shutil.which("openclaw") is not None

        if preferred == "sdk":
            return "sdk"
        if preferred == "openclaw":
            return "openclaw"
        if has_sdk_key:
            return "sdk"
        if has_openclaw:
            return "openclaw"
        raise RuntimeError("未检测到可用 LLM 后端：既没有 API key，也找不到 openclaw 命令")

    def _build_sdk_client(self):
        from openai import OpenAI

        api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("MODEL_BASE_URL")
        kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAI(**kwargs)

    def complete_text(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 500,
        top_p: Optional[float] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> str:
        if self.backend == "sdk":
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if top_p is not None:
                kwargs["top_p"] = top_p
            if extra_body:
                kwargs["extra_body"] = extra_body

            response = self.client.chat.completions.create(**kwargs)
            return (response.choices[0].message.content or "").strip()

        prompt = _build_openclaw_prompt(messages, json_mode=False)
        return self._run_openclaw(prompt)

    def complete_json(
        self,
        messages: List[Message],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: Optional[float] = None,
    ) -> Dict[str, Any]:
        if self.backend == "sdk":
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if top_p is not None:
                kwargs["top_p"] = top_p
            response = self.client.chat.completions.create(**kwargs)
            return _extract_json_object(response.choices[0].message.content or "")

        prompt = _build_openclaw_prompt(messages, json_mode=True)
        return _extract_json_object(self._run_openclaw(prompt))

    def _run_openclaw(self, prompt: str) -> str:
        cmd = [
            "openclaw",
            "agent",
            "--agent",
            "main",
            "--message",
            prompt,
            "--json",
            "--thinking",
            "minimal",
            "--timeout",
            os.getenv("XIANYU_OPENCLAW_TIMEOUT", "180"),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"OpenClaw 调用失败: {detail}")

        payload = json.loads(result.stdout)
        body = payload.get("result") if isinstance(payload.get("result"), dict) else payload
        payloads = body.get("payloads") or []
        if not payloads or not payloads[0].get("text"):
            raise RuntimeError("OpenClaw 返回为空")
        return payloads[0]["text"].strip()
