import cv2

class VideoStream:
    def __init__(self, source):
        self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read_frame(self):
        return self.cap.read()

    def release(self):
        self.cap.release()
