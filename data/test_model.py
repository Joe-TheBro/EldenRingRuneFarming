from ultralytics import YOLO
from PIL import ImageGrab
screenshot = ImageGrab.grab()
model = YOLO("../eldenring-detect.pt")
res = model.predict(screenshot, save=True)