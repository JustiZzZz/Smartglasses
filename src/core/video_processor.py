import cv2
import numpy as np
import logging
import time
import base64
from typing import List, Tuple, Optional

class VideoProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.camera = None
        self.initialize_camera()

    def initialize_camera(self) -> bool:
        try:
            if self.camera is not None:
                self.camera.release()
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise RuntimeError("Failed to open camera")
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['video']['frame_width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['video']['frame_height'])
            self.camera.set(cv2.CAP_PROP_FPS, self.config['video']['fps'])
            return True
        except Exception as e:
            logging.error(f"Camera initialization error: {e}")
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.camera or not self.camera.isOpened():
            if not self.initialize_camera():
                return False, None
        try:
            return self.camera.read()
        except Exception as e:
            logging.error(f"Frame reading error: {e}")
            return False, None

    async def capture_sequence(self, duration: float = 2.0) -> List[str]:
        frames = []
        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = self.read_frame()
            if not ret:
                continue
            try:
                _, buffer = cv2.imencode('.jpg', frame)
                frames.append(base64.b64encode(buffer).decode('utf-8'))
            except Exception as e:
                logging.error(f"Frame encoding error: {e}")
        return frames

    def release(self):
        if self.camera:
            self.camera.release()