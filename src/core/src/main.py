import asyncio
import cv2
import numpy as np
import logging
import json
import base64
import websockets
from core.gesture_detector import GestureDetector
from services.vision_service import VisionService
from services.speech_service import SpeechService
from utils.helpers import load_config

logging.basicConfig(level=logging.INFO)


class Server:
    def __init__(self):
        self.config = load_config()
        self.clients = set()
        self.gesture_detector = GestureDetector(self.config)
        self.vision_service = VisionService(self.config)
        self.speech_service = SpeechService(self.config)
        self.recording_clients = set()

    async def handle_client(self, websocket, path):
        client_ip = websocket.remote_address[0]
        logging.info(f"New connection from {client_ip}")
        self.clients.add(websocket)

        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)

                if data['type'] == 'video':
                    # Декодируем видеокадр
                    frame_data = base64.b64decode(data['data'])
                    nparr = np.frombuffer(frame_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Отображаем кадр
                    if frame is not None:
                        cv2.imshow('Video Stream', frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            break

                    # Проверяем жест
                    if self.gesture_detector.detect_thumbs_up(frame):
                        await websocket.send(json.dumps({
                            'type': 'start_recording'
                        }))
                        self.recording_clients.add(websocket)

                elif data['type'] == 'audio' and websocket in self.recording_clients:
                    audio_data = base64.b64decode(data['data'])
                    if await self.speech_service.detect_command(audio_data, "опиши"):
                        frames = await self.vision_service.analyze_frames(frame)
                        description = frames['description']
                        audio_response = await self.speech_service.synthesize(description)
                        await websocket.send(json.dumps({
                            'type': 'audio_response',
                            'data': base64.b64encode(audio_response).decode('utf-8')
                        }))
                        self.recording_clients.remove(websocket)

        except websockets.exceptions.ConnectionClosed:
            logging.info(f"Client disconnected: {client_ip}")
        finally:
            self.clients.remove(websocket)
            self.recording_clients.discard(websocket)
            cv2.destroyAllWindows()

    async def start(self):
        server = await websockets.serve(
            self.handle_client,
            self.config['server']['host'],
            self.config['server']['port']
        )
        logging.info(f"Server started on ws://{self.config['server']['host']}:{self.config['server']['port']}")
        await server.wait_closed()


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start())