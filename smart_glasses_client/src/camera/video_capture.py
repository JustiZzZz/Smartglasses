import sys
sys.path.append('/usr/lib/python3/dist-packages')
from picamera2 import Picamera2
import numpy as np
import logging
from threading import Thread
import queue
import cv2

class VideoCapture:
    def __init__(self, config):
        self.config = config
        self.camera = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = False

    def initialize_camera(self):
        try:
            self.start()
            return True
        except Exception as e:
            logging.error(f"Error initializing camera: {e}")
            return False

    def start(self):
        try:
            self.camera = Picamera2()
            config = self.camera.create_preview_configuration(
                main={"size": (self.config['camera']['width'],
                              self.config['camera']['height'])},
                controls={"FrameDurationLimits": (33333, 33333)}
            )
            self.camera.configure(config)
            self.camera.start()
            self.running = True
            Thread(target=self._capture_frames, daemon=True).start()
            logging.info("Video capture started")
        except Exception as e:
            logging.error(f"Error starting video capture: {e}")
            raise

    def _capture_frames(self):
        while self.running:
            try:
                frame = self.camera.capture_array()
                if self.frame_queue.full():
                    self.frame_queue.get()
                self.frame_queue.put(frame)
            except Exception as e:
                logging.error(f"Error capturing frame: {e}")

    def get_frame(self):
        try:
            if self.frame_queue.empty():
                return None
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def release(self):
        self.running = False
        if self.camera:
            self.camera.stop()
            self.camera.close()