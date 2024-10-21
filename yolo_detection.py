from ultralytics import YOLO

class YOLODetector:
    def __init__(self, model_path, confidence_threshold=0.3):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

    def detect_objects(self, frame):
        return self.model(frame)
