import grpc
import io
import pydub
import logging
import numpy as np
import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc
import yandex.cloud.ai.tts.v3.tts_pb2 as tts_pb2
import yandex.cloud.ai.tts.v3.tts_service_pb2_grpc as tts_service_pb2_grpc
from src.utils.helpers import get_token


class SpeechService:
    def __init__(self, config):
        self.config = config
        self.token = get_token()
        if not self.token:
            raise Exception("Не удалось получить IAM токен")

    async def process_bluetooth_audio(self, audio_data):
        """Обработка аудио с Bluetooth-микрофона"""
        try:
            channel = grpc.secure_channel(
                'stt.api.cloud.yandex.net:443',
                grpc.ssl_channel_credentials()
            )
            stub = stt_service_pb2_grpc.RecognizerStub(channel)

            # Настройка распознавания
            recognize_options = stt_pb2.StreamingOptions(
                recognition_model=stt_pb2.RecognitionModelOptions(
                    audio_format=stt_pb2.AudioFormatOptions(
                        raw_audio=stt_pb2.RawAudio(
                            audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                            sample_rate_hertz=self.config['audio']['rate'],
                            audio_channel_count=self.config['audio']['channels']
                        )
                    ),
                    language_restriction=stt_pb2.LanguageRestrictionOptions(
                        restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                        language_code=['ru-RU']
                    )
                )
            )

            metadata = (
                ('authorization', f'Bearer {self.token}'),
                ('x-folder-id', self.config['yandex']['folder_id'])
            )

            # Отправка аудиоданных
            responses = stub.RecognizeStreaming(
                self._audio_stream_generator(audio_data, recognize_options),
                metadata=metadata
            )

            for response in responses:
                if response.WhichOneof('Event') == 'partial':
                    text = response.partial.alternatives[0].text
                    if 'опиши' in text.lower():
                        return True
            return False

        except Exception as e:
            logging.error(f"Ошибка распознавания речи: {e}")
            return False
        finally:
            if 'channel' in locals():
                channel.close()

    def _audio_stream_generator(self, audio_data, recognize_options):
        try:
            # Отправляем настройки
            yield stt_pb2.StreamingRequest(
                session_options=recognize_options
            )

            # Отправляем аудиоданные
            for chunk in audio_data:
                if chunk:
                    yield stt_pb2.StreamingRequest(
                        chunk=stt_pb2.AudioChunk(data=chunk)
                    )

        except Exception as e:
            logging.error(f"Ошибка в генераторе аудио: {e}")
            raise

    async def synthesize(self, text):
        """Синтез речи"""
        try:
            request = tts_pb2.UtteranceSynthesisRequest(
                text=text,
                output_audio_spec=tts_pb2.AudioFormatOptions(
                    container_audio=tts_pb2.ContainerAudio(
                        container_audio_type=tts_pb2.ContainerAudio.WAV
                    )
                ),
                hints=[
                    tts_pb2.Hints(voice='kirill'),
                    tts_pb2.Hints(role='good'),
                    tts_pb2.Hints(speed=1.5),
                ]
            )

            channel = grpc.secure_channel(
                'tts.api.cloud.yandex.net:443',
                grpc.ssl_channel_credentials()
            )
            stub = tts_service_pb2_grpc.SynthesizerStub(channel)

            metadata = [
                ('authorization', f'Bearer {self.token}'),
                ('x-folder-id', self.config['yandex']['folder_id'])
            ]

            audio = io.BytesIO()
            async for response in stub.UtteranceSynthesis(request, metadata=metadata):
                audio.write(response.audio_chunk.data)

            audio.seek(0)
            return pydub.AudioSegment.from_wav(audio)

        except Exception as e:
            logging.error(f"Ошибка синтеза речи: {e}")
            raise
        finally:
            if 'channel' in locals():
                channel.close()