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
        self.websocket = None

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
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = base64.b64encode(buffer).decode('utf-8')
            await self.websocket.send(json.dumps({
                'type': 'video',
                'data': frame_data,
                'timestamp': str(asyncio.get_event_loop().time())
            }))
            return await self.receive()
        except Exception as e:
            self.connected = False
            logging.error(f"Error sending frame: {e}")
            return None