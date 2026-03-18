import os
import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

import litellm
from ..config import config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMWrapper:
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
            # Clean up markdown code blocks if any
            import re

            match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", content, re.DOTALL)
            if match:
                content = match.group(1)
            else:
                # If no code block, just try to find the first { and last }
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    content = content[start : end + 1]

            return response_model.model_validate_json(content)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
