import os
import time
from mistralai import Mistral
import logging
import re

logger = logging.getLogger(__name__)

class MistralAPIClient:
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY не установлен в .env")
        self.client = Mistral(api_key=api_key)
        self.model = os.getenv("MISTRAL_MODEL")

    def chat_with_history(self, messages: list, temperature: float = 0.1) -> str:
        last_error = None

        for attempt in range(1, 4):  
            try:
                response = self.client.chat.complete(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=500
                )
                content = response.choices[0].message.content.strip()

                content = content.replace('\ufeff', '').replace('\u200b', '').replace('\u200c', '')
                content = content.replace('\u2028', '\n').replace('\u2029', '\n')

                content = content.replace('«', '"').replace('»', '"').replace('“', '"').replace('”', '"')

                content = re.sub(r'[^\w\sА-Яа-яЁё.,;:!?(){}\[\]"\'=<>+-/*&|]', ' ', content)
                content = re.sub(r'\s+', ' ', content).strip()

                if "ВЫБРАТЬ" in content:
                    content = content[content.index("ВЫБРАТЬ"):]
                    if "КОНЕЦ" in content.upper():
                        content = content[:content.upper().index("КОНЕЦ") + 5]
                    elif ";" in content:
                        content = content[:content.rindex(";") + 1]

                logger.info(f"LLM ответ получен ({len(content)} символов)")
                return content

            except Exception as e:
                last_error = e
                if attempt < 3:
                    delay = 2 * attempt  
                    logger.warning(f"LLM ошибка (попытка {attempt}/3): {str(e)[:80]}. Retry через {delay}с...")
                    time.sleep(delay)
                else:
                    logger.error(f"LLM ошибка после 3 попыток: {str(e)}")

        raise last_error
