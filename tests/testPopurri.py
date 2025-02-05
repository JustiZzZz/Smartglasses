import cv2
import pyaudio
import grpc
import torch
import torch.cuda
import mediapipe as mp
import time
import io
import pygame
import base64
from openai import OpenAI
import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc
import yandex.cloud.ai.tts.v3.tts_pb2 as tts_pb2
import yandex.cloud.ai.tts.v3.tts_service_pb2_grpc as tts_service_pb2_grpc
import pydub
import threading
import subprocess
import json

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 4096
DEVICE_ID = 1
FOLDER_ID = ""
OPENAI_API_KEY = ""

def get_yc_token():
    try:
        result = subprocess.run(['yc', 'iam', 'create-token'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            raise Exception(f"Failed to get token: {result.stderr}")
    except Exception as e:
        print(f"Error getting YC token: {e}")
        return None

class GestureDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils

    @torch.cuda.amp.autocast()
    def detect_l_gesture(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    thumb_tip = hand_landmarks.landmark[4]
                    index_tip = hand_landmarks.landmark[8]
                    middle_tip = hand_landmarks.landmark[12]
                    coords = torch.tensor([
                        [thumb_tip.y, middle_tip.y],
                        [thumb_tip.x, index_tip.x],
                        [index_tip.y, middle_tip.y]
                    ], device=device)
                    conditions = torch.tensor([
                        coords[0][0] < coords[0][1],
                        abs(coords[1][0] - coords[1][1]) > 0.1,
                        coords[2][0] < coords[2][1]
                    ], device=device)
                    if torch.all(conditions):
                        return True
            return False
        except Exception as e:
            print(f"Ошибка при определении жеста: {e}")
            return False

def process_frame_cuda(frame):
    frame_tensor = torch.from_numpy(frame).to(device)
    return frame_tensor

def process_speech(audio):
    try:
        token = get_yc_token()
        if not token:
            raise Exception("Не удалось получить токен")

        cred = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
        stub = stt_service_pb2_grpc.RecognizerStub(channel)
        recognize_options = stt_pb2.StreamingOptions(
            recognition_model=stt_pb2.RecognitionModelOptions(
                audio_format=stt_pb2.AudioFormatOptions(
                    raw_audio=stt_pb2.RawAudio(
                        audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                        sample_rate_hertz=RATE,
                        audio_channel_count=CHANNELS
                    )
                ),
                language_restriction=stt_pb2.LanguageRestrictionOptions(
                    restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                    language_code=['ru-RU']
                )
            )
        )
        metadata = (
            ('authorization', f'Bearer {token}'),
            ('x-folder-id', FOLDER_ID),
        )

        def gen():
            yield stt_pb2.StreamingRequest(session_options=recognize_options)
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=DEVICE_ID,
                frames_per_buffer=CHUNK
            )
            try:
                while True:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    if not data:
                        break
                    yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
            finally:
                stream.stop_stream()
                stream.close()

        responses = stub.RecognizeStreaming(gen(), metadata=metadata)
        for response in responses:
            if response.WhichOneof('Event') == 'partial' and response.partial.alternatives:
                text = response.partial.alternatives[0].text
                print(f"Распознано: {text}")
                if 'опиши' in text.lower():
                    return True
        return False
    finally:
        channel.close()

def synthesize(text):
    token = get_yc_token()
    if not token:
        raise Exception("Не удалось получить токен")

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
    cred = grpc.ssl_channel_credentials()
    channel = grpc.secure_channel('tts.api.cloud.yandex.net:443', cred)
    stub = tts_service_pb2_grpc.SynthesizerStub(channel)
    metadata = [
        ('authorization', f'Bearer {token}'),
        ('x-folder-id', FOLDER_ID)
    ]
    try:
        it = stub.UtteranceSynthesis(request, metadata=metadata)
        audio = io.BytesIO()
        for response in it:
            audio.write(response.audio_chunk.data)
        audio.seek(0)
        return pydub.AudioSegment.from_wav(audio)
    finally:
        channel.close()

# Остальные функции остаются без изменений
def capture_video(existing_cap=None):
    if existing_cap is not None and existing_cap.isOpened():
        cap = existing_cap
    else:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Не удалось открыть камеру")
    base64Frames = []
    start_time = time.time()
    try:
        while (time.time() - start_time) < 2:
            ret, frame = cap.read()
            if not ret:
                print("Ошибка чтения кадра при записи видео")
                break
            frame_tensor = process_frame_cuda(frame)
            frame_processed = frame_tensor.cpu().numpy()
            _, buffer = cv2.imencode(".jpg", frame_processed)
            base64Frames.append(base64.b64encode(buffer).decode("utf-8"))
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f"Ошибка при захвате видео: {e}")
    return base64Frames

def analyze_with_gpt(frames):
    client = OpenAI(api_key=OPENAI_API_KEY)
    PROMPT_MESSAGES = [
        {
            "role": "user",
            "content": [
                "Ты - голосовой помощник в очках с компьютерным зрением. Это кадры из камеры очков. Создай убедительное описание того, что происходит в видео. КРАТКО",
                *map(lambda x: {"image": x, "resize": 768}, frames[0::50]),
            ],
        },
    ]
    params = {
        "model": "gpt-4o",
        "messages": PROMPT_MESSAGES,
        "max_tokens": 200,
    }
    result = client.chat.completions.create(**params)
    return result.choices[0].message.content

def play_audio(audio_segment):
    output_file = '../../output.wav'
    audio_segment.export(output_file, format='wav')
    pygame.mixer.init()
    pygame.mixer.music.load(output_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()

def process_audio_in_thread(audio_segment):
    thread = threading.Thread(target=play_audio, args=(audio_segment,))
    thread.start()
    return thread

def main():
    try:
        torch.cuda.init()
        gesture_detector = GestureDetector()
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Ошибка: не удалось открыть камеру")
            return
        audio = pyaudio.PyAudio()
        print(f"Using device: {device}")
        print("Покажите перевернутую 'Г' пальцами для начала распознавания речи")
        audio_thread = None

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Ошибка получения кадра, пробую переподключиться...")
                cap.release()
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    print("Не удалось переподключиться к камере")
                    break
                continue

            frame_tensor = process_frame_cuda(frame)
            processed_frame = frame_tensor.cpu().numpy()
            cv2.imshow('Frame', processed_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            if gesture_detector.detect_l_gesture(processed_frame):
                print("Жест распознан! Говорите команду с словом 'Опиши'...")
                if process_speech(audio):
                    print("Команда распознана! Записываю 2 секунды видео...")
                    base64Frames = capture_video(cap)
                    if base64Frames:
                        print("Анализирую видео...")
                        description = analyze_with_gpt(base64Frames)
                        print("Синтезирую речь...")
                        audio_segment = synthesize(description)
                        print("Воспроизвожу ответ...")
                        if audio_thread and audio_thread.is_alive():
                            audio_thread.join()
                        audio_thread = process_audio_in_thread(audio_segment)
                        print("Готов к следующему распознаванию. Покажите жест...")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        if 'audio' in locals():
            audio.terminate()
        cv2.destroyAllWindows()
        torch.cuda.empty_cache()

if __name__ == "__main__":
    main()
