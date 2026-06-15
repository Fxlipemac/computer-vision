import cv2
import os
import time
from flask import Flask, Response
from dotenv import load_dotenv

load_dotenv() # load variables .env

def scan_port(max_ports=5): # Scan for available ports
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

def take_snapshots(active_ports): # take snapshots of available ports
    output_dir = "snapshots"
    os.makedirs(output_dir, exist_ok=True)
    for port in active_ports:
        cap = cv2.VideoCapture(port)
        success, frame = cap.read()
        if success:
            cv2.imwrite(os.path.join(output_dir, f"camera_port_{port}.jpg"), frame)
        cap.release()

def generate_frames(port): # web stream generator - serve video streams to the browser
    cap = cv2.VideoCapture(port)

    while True:
        success, frame = cap.read()
        if success:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else: break

def start_server(active_ports): # web server controller
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

if __name__ == "__main__": # execute code
    active = scan_port()

    if active:
        print("Taking snapshots and starting server...")
        take_snapshots(active)
        start_server(active)
    else:
        print("No cameras found.")
