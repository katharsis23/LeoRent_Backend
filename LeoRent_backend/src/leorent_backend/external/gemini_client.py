from src.leorent_backend.config.gemini import GEMINI_SETTINGS
import google.generativeai as genai
from loguru import logger
from typing import Dict, Any


class GeminiClient:
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=GEMINI_SETTINGS.model_name,
            **GEMINI_SETTINGS.ai_model_config
        )
        self.api_key = genai.configure(
            api_key=GEMINI_SETTINGS.api_key.get_secret_value()
        )
        self.default_prompt = GEMINI_SETTINGS.default_prompt

    async def generate_json(self, user_prompt: str) -> Dict[str, Any]:
        try:
            prompt = f"{self.default_prompt} User query: {user_prompt}"

            # Ensure you are AWAITING the async call
            response = await self.model.generate_content_async(
                prompt,
                # This forces the model to return valid JSON
                generation_config={"response_mime_type": "application/json"}
            )
            logger.debug(f"Gemini response: {response.text}")

            # Use response.text to get the string, then parse it
            import json
            return json.loads(response.text)

        except Exception as gemini_error:
            logger.error(f"Gemini error: {gemini_error}")
            raise gemini_error
