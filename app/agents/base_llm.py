import json
import time
from typing import Any, Dict, Iterable

import config


class LLMError(RuntimeError):
    pass


def _looks_like_unsupported_response_format(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "response_format" in message
        and (
            "unsupported" in message
            or "does not support parameters" in message
            or "unsupportedparamserror" in message
        )
    )


def _strip_markdown_fence(content: str) -> str:
    text = content.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].startswith(fence):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_json_content(content: str) -> Dict[str, Any]:
    text = _strip_markdown_fence(content)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _validate_expected_keys(data: Dict[str, Any], expected_keys: Iterable[str] | None) -> None:
    if not expected_keys:
        return

    missing = [key for key in expected_keys if key not in data]
    if missing:
        raise LLMError(f"模型返回JSON缺少必要字段：{missing}；实际字段：{list(data.keys())}")

    if set(data.keys()).issubset({"parse_error", "invalid_json_text"}):
        raise LLMError("模型返回了JSON修复请求包装对象，而不是目标业务JSON。")


class OpenAIJsonClient:
    def __init__(self, model: str | None = None):
        if not config.OPENAI_API_KEY:
            raise LLMError("OPENAI_API_KEY 为空。请在 .env 中配置，或使用 --provider mock。")

        from openai import OpenAI

        client_kwargs = {"api_key": config.OPENAI_API_KEY}
        if config.OPENAI_BASE_URL:
            client_kwargs["base_url"] = config.OPENAI_BASE_URL
        client_kwargs["timeout"] = config.OPENAI_TIMEOUT

        self.client = OpenAI(**client_kwargs)
        self.model = model or config.OPENAI_MODEL

    def _completion_content(self, messages: list[Dict[str, str]], use_response_format: bool) -> str:
        request_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if use_response_format:
            request_kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**request_kwargs)
        content = response.choices[0].message.content
        if not content:
            raise LLMError("模型返回内容为空")
        return content

    def _repair_json_content(
        self,
        invalid_content: str,
        parse_error: Exception,
        expected_keys: Iterable[str] | None,
        use_response_format: bool,
    ) -> Dict[str, Any]:
        keys_text = ", ".join(expected_keys or [])
        messages = [
            {
                "role": "system",
                "content": (
                    "你是严格的JSON修复器。只输出一个合法JSON对象，不要输出解释、Markdown或代码块。"
                    "你的任务是修复用户提供的坏JSON文本本身，不要把parse_error或invalid_json_text当作输出字段。"
                    "必须保留原始业务语义和字段结构，只修复语法问题，例如缺少逗号、非法引号、尾随逗号。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"解析错误：{parse_error}\n"
                    f"修复后的JSON对象必须包含这些顶层字段：{keys_text}\n"
                    "下面是需要修复的坏JSON文本，只输出修复后的JSON对象：\n"
                    + invalid_content
                ),
            },
        ]
        repaired = self._completion_content(messages, use_response_format=use_response_format)
        data = _parse_json_content(repaired)
        _validate_expected_keys(data, expected_keys)
        return data

    def chat_json(
        self,
        system_prompt: str,
        user_payload: Dict[str, Any],
        expected_keys: Iterable[str] | None = None,
    ) -> Dict[str, Any]:
        last_error: Exception | None = None
        use_response_format = True

        for attempt in range(3):
            try:
                keys_text = ", ".join(expected_keys or [])
                messages = [
                    {
                        "role": "system",
                        "content": (
                            system_prompt
                            + "\n\n重要：最终回复必须是一个可被 json.loads 直接解析的合法JSON对象。"
                            + "不要输出Markdown代码块，不要输出解释。字符串内部如需使用英文双引号，必须转义。"
                            + (f"顶层必须包含这些字段：{keys_text}。" if keys_text else "")
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                    },
                ]

                content = self._completion_content(messages, use_response_format=use_response_format)
                try:
                    data = _parse_json_content(content)
                    _validate_expected_keys(data, expected_keys)
                    return data
                except json.JSONDecodeError as exc:
                    last_error = LLMError(f"模型返回不是合法 JSON：{exc}")
                    try:
                        return self._repair_json_content(
                            content,
                            exc,
                            expected_keys=expected_keys,
                            use_response_format=use_response_format,
                        )
                    except Exception as repair_exc:
                        last_error = LLMError(f"模型返回不是合法 JSON，自动修复也失败：{repair_exc}")
                        time.sleep(1 + attempt * 2)
                except LLMError as exc:
                    last_error = exc
                    time.sleep(1 + attempt * 2)
            except Exception as exc:
                last_error = exc
                if use_response_format and _looks_like_unsupported_response_format(exc):
                    use_response_format = False
                    continue
                time.sleep(1 + attempt * 2)

        raise LLMError(f"LLM 调用失败：{last_error}")
