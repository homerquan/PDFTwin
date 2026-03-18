import os
import json
import logging
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

import litellm
from ..config import config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMWrapper:
    @staticmethod
    def _looks_like_schema(candidate: Any) -> bool:
        return isinstance(candidate, dict) and "properties" in candidate and "type" in candidate

    @staticmethod
    def _unwrap_schema_like_candidate(candidate: Any, response_model: Type[T]) -> Any:
        if not isinstance(candidate, dict):
            return candidate

        properties = candidate.get("properties")
        model_fields = set(response_model.model_fields.keys())
        if isinstance(properties, dict) and model_fields.issubset(set(properties.keys())):
            return properties

        return candidate

    @staticmethod
    def _extract_json_candidates(content: str) -> list[Any]:
        candidates: list[Any] = []

        for match in re.finditer(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL):
            block = match.group(1).strip()
            if block:
                candidates.append(block)

        stripped = content.strip()
        if stripped:
            candidates.append(stripped)

        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(content):
            if content[idx] not in "[{":
                idx += 1
                continue

            try:
                obj, end = decoder.raw_decode(content[idx:])
                candidates.append(obj)
                idx += max(end, 1)
            except json.JSONDecodeError:
                idx += 1

        return candidates

    @staticmethod
    def call_structured(
        prompt: str,
        response_model: Type[T],
        image_base64: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> T:
        if not config.use_llm:
            raise RuntimeError("LLM calls are disabled via config.")

        messages = []
        if image_base64:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                        },
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": prompt})

        try:
            # Using litellm's structured output format if available or just raw json prompting
            # For simplicity across providers, we enforce JSON in the prompt
            json_prompt = f"{prompt}\n\nPlease respond strictly with a valid JSON instance matching this schema. Do NOT output the schema definition, but output the actual data in JSON format:\n{response_model.model_json_schema()}"
            if not image_base64:
                messages[0]["content"] = json_prompt
            else:
                messages[0]["content"][0]["text"] = json_prompt

            response = litellm.completion(
                model=config.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
                if "gemini" not in config.model.lower()
                else None,  # gemini json mode is handled via prompt or google specific options
            )

            content = response.choices[0].message.content.strip()
            validation_errors = []
            for candidate in reversed(LLMWrapper._extract_json_candidates(content)):
                try:
                    if isinstance(candidate, str):
                        parsed = json.loads(candidate)
                    else:
                        parsed = candidate

                    parsed = LLMWrapper._unwrap_schema_like_candidate(parsed, response_model)
                    if LLMWrapper._looks_like_schema(parsed):
                        continue

                    return response_model.model_validate(parsed)
                except Exception as e:
                    validation_errors.append(str(e))

            raise ValueError(
                "Unable to parse structured LLM response. "
                f"Validation attempts: {validation_errors[-3:]}. Raw response excerpt: {content[:500]}"
            )

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
