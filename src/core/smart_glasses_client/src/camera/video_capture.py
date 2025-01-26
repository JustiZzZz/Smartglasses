import cv2
import numpy as np
import logging
import queue
from threading import Thread
import sys

class VideoCapture:
    def __init__(self, config):
        self.config = config
        self.camera = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = False

    def initialize_camera(self):
        try:
            self.camera = cv2.VideoCapture(0)  # или другой индекс камеры
            if not self.camera.isOpened():
                raise RuntimeError("Failed to open camera")
                
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config['camera']['width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config['camera']['height'])
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            self.running = True
            Thread(target=self._capture_frames, daemon=True).start()
            logging.info("Camera initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Error initializing camera: {e}")
            return False

    def _capture_frames(self):
        while self.running:
            try:
                ret, frame = self.camera.read()
                if ret:
                    if self.frame_queue.full():
                        self.frame_queue.get()
                    self.frame_queue.put(frame)
            except Exception as e:
                logging.error(f"Error capturing frame: {e}")

    def get_frame(self):
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def release(self):
        self.running = False
        if self.camera:
            self.camera.release()