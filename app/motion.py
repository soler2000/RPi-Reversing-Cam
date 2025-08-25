import cv2, numpy as np, time
from . import settings

class MotionDetector:
    def __init__(self):
        self.prev = None

    def tick(self, frame_bgr):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9,9), 0)
        if self.prev is None:
            self.prev = gray
            return 0.0
        diff = cv2.absdiff(self.prev, gray)
        self.prev = gray
        score = float(np.mean(diff))
        return score
