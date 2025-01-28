import pyaudio
import pygame
import tempfile
import os
from pydub import AudioSegment
import logging
from threading import Thread
import asyncio


class AudioProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.pyaudio = pyaudio.PyAudio()
        pygame.mixer.init()
        self._current_stream = None
        self.bluetooth_handler = None

    def create_stream(self) -> pyaudio.Stream:
        try:
            if self._current_stream:
                self._current_stream.stop_stream()
                self._current_stream.close()

            stream = self.pyaudio.open(
                format=getattr(pyaudio, self.config['audio']['format']),
                channels=self.config['audio']['channels'],
                rate=self.config['audio']['rate'],
                input=True,
                input_device_index=self.config['audio']['device_id'],
                frames_per_buffer=self.config['audio']['chunk']
            )
            self._current_stream = stream
            return stream
        except Exception as e:
            logging.error(f"Error creating audio stream: {e}")
            raise

    async def play_audio(self, audio_segment: AudioSegment, use_bluetooth: bool = False):
        if use_bluetooth and self.config['bluetooth']['enabled']:
            await self._play_audio_bluetooth(audio_segment)
        else:
            await self._play_audio_default(audio_segment)

    async def _play_audio_bluetooth(self, audio_segment: AudioSegment):
        try:
            # я устала
            pass
        except Exception as e:
            logging.error(f"Bluetooth playback failed: {e}")
            await self._play_audio_default(audio_segment)

    async def _play_audio_default(self, audio_segment: AudioSegment):
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio_segment.export(temp_file.name, format='wav')
            temp_file.close()

            pygame.mixer.init()
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)

        except Exception as e:
            logging.error(f"Error playing audio: {e}")
        finally:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except Exception as e:
                    logging.warning(f"Failed to remove temporary file: {e}")

    def cleanup(self):
        if self._current_stream:
            self._current_stream.stop_stream()
            self._current_stream.close()
        self.pyaudio.terminate()
        pygame.mixer.quit()
