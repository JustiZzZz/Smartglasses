import cv2
import mediapipe as mp
import numpy as np
from typing import Optional


class GestureDetector:
    def __init__(self, config: dict):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config['gesture']['max_hands'],
            min_detection_confidence=config['gesture']['min_detection_confidence'],
            model_complexity=0
        )

    def detect_thumbs_up(self, frame: np.ndarray) -> bool:
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False
            results = self.hands.process(frame_rgb)

            if not results.multi_hand_landmarks:
                return False

            for hand_landmarks in results.multi_hand_landmarks:
                thumb_tip = hand_landmarks.landmark[4]
                thumb_ip = hand_landmarks.landmark[3]
                thumb_mcp = hand_landmarks.landmark[2]

                index_tip = hand_landmarks.landmark[8]
                middle_tip = hand_landmarks.landmark[12]
                ring_tip = hand_landmarks.landmark[16]
                pinky_tip = hand_landmarks.landmark[20]

                thumb_up = thumb_tip.y < thumb_ip.y < thumb_mcp.y

                other_fingers_down = all([
                    index_tip.y > thumb_mcp.y,
                    middle_tip.y > thumb_mcp.y,
                    ring_tip.y > thumb_mcp.y,
                    pinky_tip.y > thumb_mcp.y
                ])

                if thumb_up and other_fingers_down:
                    return True

            return False

        except Exception as e:
            print(f"Ошибка при определении жеста: {e}")
            return False
