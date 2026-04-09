import json
from typing import Any

import httpx

from assistant.settings import get_settings


class OpenAIError(RuntimeError):
    """Raised when the OpenAI request fails."""


class OpenAIClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.openai_base_url.rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def generate_json(self, *, prompt: str, schema_hint: str) -> dict[str, Any]:
        if not self.is_configured():
            raise OpenAIError("OPENAI_API_KEY 未配置，无法调用 LLM。")

        payload = {
            "model": self.settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "你是一个结构化输出助手。"
                                "只返回合法 JSON，不要输出 markdown，不要补充解释。"
                                f"输出字段要求: {schema_hint}"
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.settings.openai_timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/responses",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise OpenAIError(
                f"OpenAI 调用失败: {response.status_code} {response.text}"
            )

        data = response.json()
        text = self._extract_text(data)
        if not text:
            raise OpenAIError("OpenAI 返回中没有可解析文本。")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenAIError(f"LLM 返回不是合法 JSON: {text}") from exc

    def _extract_text(self, response_data: dict[str, Any]) -> str:
        output = response_data.get("output", [])
        for item in output:
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return content.get("text", "").strip()
        return response_data.get("output_text", "").strip()
