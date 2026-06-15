import cv2
import os
import time
from ultralytics import YOLO
from flask import Flask, Response
from dotenv import load_dotenv

# Load model trained
model = YOLO("runs/detect/train/weights/best.pt")

# Load variables .env
load_dotenv()

# Create directory to save snapshots with evidences
os.makedirs("evidence", exist_ok=True)

# Scan for available ports
def scan_port(max_ports=5):
    active_ports = []

    for port in range(max_ports):
        cap = cv2.VideoCapture(port)

        if cap.isOpened():
            success, frame = cap.read()
            if success:
                active_ports.append(port)
                print(f"Port {port} OK! ✅")
        cap.release()
    return active_ports

# Web Stream Generator - Serve video streams to the browser
def generate_frames(port):
    cap = cv2.VideoCapture(port)

    last_save_time = 0
    cooldown_seconds = 10

    while True:
        success, frame = cap.read()
        if success:
            results = model(frame, verbose=False, conf=0.50, classes=[0, 1, 3])

            persons = []
            equipments = []

            # Separation: List who is a person and who is an PPE in this exact frame
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = model.names[class_id]
                print(f"Detection: {class_name} | Confidence: {confidence:.2f}")

                # Get coordinates x1 (left), y1 (top), x2 (right), y2 (bottom)
                coords = box.xyxy[0].tolist() 

                if class_name == "person":
                    persons.append(coords)
                elif class_name in ["helmet", "no-helmet"]:
                    equipments.append((coords, class_name))
            annotated_frame = results[0].plot()
            
            # Business Logic: Mathematical crossover
            for i, p_coords in enumerate(persons):
                px1, py1, px2, py2 = p_coords

                has_helmet = False
                explicit_infraction = False

                for e_coords, e_name in equipments:
                    ex1, ey1, ex2, ey2 = e_coords

                    # Calculates the geometric center of the PPE
                    center_x = (ex1 + ex2) / 2 
                    center_y = (ey1 + ey2) / 2

                    # Checks whether the center of the PPE is within the person's area
                    if px1 <= center_x <= px2 and py1 <= center_y <= py2:
                        if e_name == "helmet":
                            has_helmet = True
                        elif e_name in ["no-helmet"]:
                            explicit_infraction = True

                # The result (Action)
                if explicit_infraction or not (has_helmet):
                    print(f"Worker {i+1}: INFRACTION - Missing or invalid PPE ❌")
                    cv2.rectangle(annotated_frame, (int(px1), int(py1)), (int(px2), int(py2)), (0, 0, 255), 3) # Red

                    current_time = time.time()
                    if current_time - last_save_time >= cooldown_seconds:
                        cv2.imwrite(f"evidence/infraction_{int(time.time())}.jpg", annotated_frame)
                        last_save_time = current_time
                else:
                    print(f"Worker {i+1}: OK ✅")
                    cv2.rectangle(annotated_frame, (int(px1), int(py1)), (int(px2), int(py2)), (0, 255, 0), 3) # Green

            # Returns the annotated image to the browser
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else: 
            cap.release()
            break

# web server controller
def start_server(active_ports):
    app = Flask(__name__)
    @app.route('/video/<int:port>')
    def video_feed(port):
        return Response(generate_frames(port), mimetype='multipart/x-mixed-replace;boundary=frame')
    @app.route('/')
    def index():
        html = "<h1>Active Cameras</h1>"
        for port in active_ports:
            html += f"<div><h3>Port {port}</h3><img src='/video/{port}' width='640'></div>"
        return html
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)

# execute code
if __name__ == "__main__":
    active = scan_port()

    if active:
        start_server(active)
    else:
        print("No cameras found.")
