import asyncio
import logging
import cv2
import numpy as np
import json
import base64
import pygame
import pyaudio
import os
import yaml
import tempfile
from camera.video_capture import VideoCapture
from network.stream_client import StreamClient

logging.basicConfig(level=logging.INFO)

class SmartGlasses:
    def __init__(self):
        self.config = self._load_config()
        self.video_capture = VideoCapture(self.config)
        self.stream_client = StreamClient(self.config)
        self.running = False
        self.audio = pyaudio.PyAudio()
        pygame.mixer.init()

    def _load_config(self):
        with open('config/config.yml', 'r') as f:
            return yaml.safe_load(f)

    async def initialize(self):
        try:
            if not self.video_capture.initialize_camera():
                raise RuntimeError("Failed to initialize camera")
            if not await self.stream_client.connect():
                raise RuntimeError("Failed to connect to server")
            return True
        except Exception as e:
            logging.error(f"Initialization error: {e}")
            return False

    async def process_audio_response(self, audio_data):
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_file.write(audio_data)
            temp_file.close()
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Error playing audio: {e}")
        finally:
            pygame.mixer.music.unload()
            if temp_file:
                os.remove(temp_file.name)

    async def run(self):
        try:
            if not await self.initialize():
                return
            
            self.running = True
            print("System started. Streaming video...")
            
            while self.running:
                frame = self.video_capture.get_frame()
                if frame is None:
                    continue

                try:
                    response = await self.stream_client.send_frame(frame)
                    if isinstance(response, dict):
                        if response.get('type') == 'start_recording':
                            stream = self.audio.open(
                                format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                input=True,
                                frames_per_buffer=4096
                            )
                            await self.stream_client.send_audio(stream)
                        elif response.get('type') == 'audio_response':
                            await self.process_audio_response(response['data'])
                except Exception as e:
                    logging.error(f"Error processing response: {e}")

                await asyncio.sleep(0.01)
                
        except Exception as e:
            logging.error(f"Critical error: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        self.running = False
        self.video_capture.release()
        self.audio.terminate()
        pygame.mixer.quit()

if __name__ == "__main__":
    glasses = SmartGlasses()
    asyncio.run(glasses.run())