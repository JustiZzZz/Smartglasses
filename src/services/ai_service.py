from .speech_service import SpeechService
from .vision_service import VisionService
from typing import List


class AIService:
    def __init__(self, config: dict):
        self.speech_service = SpeechService(config)
        self.vision_service = VisionService(config)

    def process_voice_command(self, audio_stream) -> bool:
        """Process voice commands and detect trigger phrases"""
        return self.speech_service.process_speech(audio_stream)

    def analyze_scene(self, frames: List[str]) -> str:
        """Analyze captured video frames and generate description"""
        return self.vision_service.analyze_frames(frames)

    def synthesize_response(self, text: str):
        """Convert text response to speech"""
        return self.speech_service.synthesize(text)