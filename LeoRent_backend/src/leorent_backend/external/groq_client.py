from groq import AsyncGroq
from src.leorent_backend.config.groq import GROQ_SETTINGS
from loguru import logger
import json
from typing import Dict, Any
from fastapi import HTTPException, status



class GroqClient:
    def __init__(self):
        self.client = AsyncGroq(
            api_key=GROQ_SETTINGS.api_key.get_secret_value()
        )
        self.model_name = GROQ_SETTINGS.model_name
        self.default_prompt = GROQ_SETTINGS.default_prompt

    async def generate_json(self, user_prompt: str) -> Dict[str, Any]:
        try:
            # Groq works best with a System/User message split
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": self.default_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                model=self.model_name,
                # Enforces JSON output
                response_format={"type": "json_object"},
                temperature=0.1, # Keep it deterministic for extraction
            )
            
            content = chat_completion.choices[0].message.content
            logger.debug(f"Groq response: {content}")
            if content:
                return json.loads(content)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Groq response was empty"
                )
        except Exception as groq_error:
            logger.error(f"Groq error: {groq_error}")
            raise groq_error