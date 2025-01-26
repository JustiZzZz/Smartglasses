import asyncio
import websockets
import json
import cv2
import base64
import logging

class StreamClient:
    def __init__(self, config):
        self.config = config
        self.connected = False
        self.max_retries = 5
        self.retry_delay = 2
        self.reconnect_attempts = 0

    async def connect(self):
        while self.reconnect_attempts < self.max_retries:
            try:
                uri = f"ws://{self.config['server']['host']}:{self.config['server']['port']}"
                self.websocket = await websockets.connect(uri)
                self.connected = True
                self.reconnect_attempts = 0
                logging.info("Connected to server successfully")
                return True
            except Exception as e:
                self.reconnect_attempts += 1
                logging.error(f"Connection attempt {self.reconnect_attempts}/{self.max_retries} failed: {e}")
                if self.reconnect_attempts < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
        return False

    async def send_frame(self, frame):
        if not self.connected:
            if not await self.connect():
                return None
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            await self.websocket.send(json.dumps({
                'type': 'video',
                'data': frame_data,
                'source': 'raspberrypi'
            }))
            return await self.receive()
        except Exception as e:
            self.connected = False
            logging.error(f"Error sending frame: {e}")
            return None

    async def send_audio(self, stream):
        if not self.connected:
            return
        try:
            while self.connected:
                data = stream.read(4096, exception_on_overflow=False)
                if not data:
                    break
                await self.websocket.send(json.dumps({
                    'type': 'audio',
                    'data': base64.b64encode(data).decode('utf-8')
                }))
        except Exception as e:
            logging.error(f"Error sending audio: {e}")
            self.connected = False
        finally:
            stream.stop_stream()
            stream.close()

    async def receive(self):
        if not self.connected:
            return None
        try:
            response = await self.websocket.recv()
            return json.loads(response)
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            logging.error("Connection closed by server")
            return None
        except Exception as e:
            logging.error(f"Error receiving data: {e}")
            return None

    async def close(self):
        if self.connected:
            await self.websocket.close()
            self.connected = False