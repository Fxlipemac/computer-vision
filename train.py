from ultralytics import YOLO

model = YOLO("yolo11n.pt")

model.train(
    data="construction-safety-2/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16
)