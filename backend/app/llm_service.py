import os
from openai import OpenAI
from app.config import settings

class QwenLLMService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.QWEN_API_KEY or os.getenv("QWEN_API_KEY"),
            base_url=os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        )
        self.model_name = os.getenv("QWEN_MODEL", "qwen-plus")

    def generate_chat_response(self, system_prompt: str, user_message: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception:
            # Never return an error string as if it were a reply — the caller falls back
            # to the deterministic composer instead of showing the user a 401.
            raise