from openai import OpenAI
import numpy as np
import cv2
import base64
import logging

class VisionService:
    def __init__(self, config: dict):
        self.client = OpenAI(api_key=config['api']['openai_key'])
        self.config = config

    async def analyze_frame(self, frame: np.ndarray) -> dict:
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')

            prompt_messages = [{
                "role": "user",
                "content": [
                    "Опиши, что происходит на изображении. КРАТКО!",
                    {"image": frame_base64, "resize": 768},
                ],
            }]

            params = {
                "model": self.config['models']['vision'],
                "messages": prompt_messages,
                "max_tokens": 200,
            }

            result = self.client.chat.completions.create(**params)
            response_text = result.choices[0].message.content
            logging.info(f"Vision API response: {response_text}")
            return {
                'type': 'analysis_result',
                'data': response_text
            }
        except Exception as e:
            logging.error(f"Error analyzing frame: {e}")
            return None
