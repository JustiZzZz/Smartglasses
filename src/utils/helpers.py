import subprocess
import yaml
from typing import Optional, Dict
import os
import json

def get_token():
    try:
        # Сначала пробуем получить токен через CLI
        result = subprocess.run(['yc', 'iam', 'create-token'],
                                capture_output=True,
                                text=True)
        if result.returncode == 0:
            return result.stdout.strip()

        # Если CLI недоступен, используем статический токен
        return "t1.9euelZqRmZOKno6SjpnGlZ6Lm4uLmO3rnpWanJLMnZeLjc-ekpaalorPx5fl9PdfXTJD-e9OVTWR3fT3HwwwQ_nvTlU1kc3n9euelZqJy4nPxpjKjJGUkMyZkpWdje_8xeuelZqJy4nPxpjKjJGUkMyZkpWdjQ.j3HmfQCxHwkuWytOhAWP_6ZRlVDtrAhvCueF1FXrSHHSBIX39Yhhpl3uv-747FABRZ7QYtFOcXzp0bw6ys1xDg"
    except Exception as e:
        print(f"Ошибка получения токена: {e}")
        # Возвращаем статический токен в случае ошибки
        return "t1.9euelZqRmZOKno6SjpnGlZ6Lm4uLmO3rnpWanJLMnZeLjc-ekpaalorPx5fl9PdfXTJD-e9OVTWR3fT3HwwwQ_nvTlU1kc3n9euelZqJy4nPxpjKjJGUkMyZkpWdje_8xeuelZqJy4nPxpjKjJGUkMyZkpWdjQ.j3HmfQCxHwkuWytOhAWP_6ZRlVDtrAhvCueF1FXrSHHSBIX39Yhhpl3uv-747FABRZ7QYtFOcXzp0bw6ys1xDg"

def load_config() -> Dict:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'config',
        'config.yml'
    )
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

