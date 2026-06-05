import mss
import cv2
import numpy as np
import threading
import time
import socket
import sys
import json
import os
import math
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from ultralytics import YOLO
import uvicorn

# ================= НАСТРОЙКИ =================
MODEL_PATH = ".onnx"
CONF_THRESHOLD = 0.50
IMG_SIZE = 640
TARGET_FPS = 30
SKIP_FRAMES = 2  # Инференс каждого N-го кадра

# 🎨 Режимы отрисовки (True/False)
DRAW_RECTANGLE = True
DRAW_OVAL = True
DRAW_DIAGONALS = True
SHOW_LABELS = True
CALC_OVAL_AREA = True

# 📂 Пути и Demo
JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "detections.json")
ENABLE_DEMO_STREAM = True  # Включить синхронную демо-страницу
# =============================================

app = FastAPI()
frame_lock = threading.Lock()
json_lock = threading.Lock()
latest_frame_bytes = None
current_detections = {"timestamp": 0, "count": 0, "detections": []}

def log(msg): print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

log("Загрузка ONNX-модели...")
try:
    model = YOLO(MODEL_PATH, task="detect")
    log("✅ Модель загружена.")
except Exception as e:
    log(f"❌ Ошибка модели: {e}"); sys.exit(1)

def calc_oval_area(w, h):
    return round(math.pi * (w / 2) * (h / 2), 2)

def process_detections(res, img_shape):
    h, w = img_shape[:2]
    detections = []
    if res.boxes is not None and len(res.boxes) > 0:
        for box, cls, conf in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.cpu().numpy(), res.boxes.conf.cpu().numpy()):
            x1, y1, x2, y2 = map(int, box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            bw, bh = x2 - x1, y2 - y1
            
            det = {
                "class": res.names[int(cls)],
                "class_id": int(cls),
                "confidence": round(float(conf), 3),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "width": bw, "height": bh},
                "center": {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2},
                "orientation": "land" if bw > bh else "vert"
            }
            if CALC_OVAL_AREA:
                det["oval_area"] = calc_oval_area(bw, bh)
            if DRAW_DIAGONALS:
                det["diagonals"] = {
                    "d1": {"start": [x1, y1], "end": [x2, y2]},
                    "d2": {"start": [x1, y2], "end": [x2, y1]}
                }
            detections.append(det)
    return detections

def draw_overlay(frame, dets):
    for det in dets:
        b = det["bbox"]
        x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
        w, h = x2 - x1, y2 - y1
        if w < 5 or h < 5: continue
        
        if DRAW_RECTANGLE:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if DRAW_DIAGONALS:
            cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 1)
            cv2.line(frame, (x1, y2), (x2, y1), (255, 0, 0), 1)
        if DRAW_OVAL:
            cv2.ellipse(frame, ((x1+x2)//2, (y1+y2)//2), (w//2, h//2), 0, 0, 360, (0, 255, 255), 2)
        if SHOW_LABELS:
            area = f"{det['oval_area']}px " if CALC_OVAL_AREA else ""
            label = f"{det['class']}({det['confidence']:.2f}) {det['orientation']} {area}"
            cv2.putText(frame, label, (x1, max(y1-10, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return frame

def capture_loop():
    global latest_frame_bytes
    log("🚀 Запуск цикла захвата...")
    
    # Пустой JSON при старте
    with open(JSON_PATH, 'w') as f: json.dump({"timestamp": time.time(), "count": 0, "detections": []}, f)

    with mss.MSS() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        log(f"🖥 Монитор: {monitor['width']}x{monitor['height']}")
        target_dt = 1.0 / TARGET_FPS
        frame_count = 0
        
        while True:
            t0 = time.perf_counter()
            frame_count += 1
            try:
                img = np.array(sct.grab(monitor))[:, :, :3]
                
                if frame_count % SKIP_FRAMES == 0:
                    res = model(img, conf=CONF_THRESHOLD, device="cpu", imgsz=IMG_SIZE, verbose=False, half=False)[0]
                    dets = process_detections(res, img.shape)
                    
                    with json_lock:
                        current_detections.update({"timestamp": time.time(), "count": len(dets), "detections": dets})
                        with open(JSON_PATH, 'w') as f: json.dump(current_detections.copy(), f, indent=2)
                    
                    demo = img.copy()
                    with frame_lock:
                        latest_frame_bytes = cv2.imencode('.jpg', draw_overlay(demo, dets), [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
            except Exception as e:
                log(f"⚠️ {e}")
            
            sl = target_dt - (time.perf_counter() - t0)
            if sl > 0: time.sleep(sl)

threading.Thread(target=capture_loop, daemon=True).start()

@app.get("/detections")
async def get_detections():
    with json_lock: return current_detections.copy()

@app.get("/stream")
async def stream():
    def gen():
        while True:
            with frame_lock: frame = latest_frame_bytes
            if frame: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.01)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

if ENABLE_DEMO_STREAM:
    @app.get("/demo", response_class=HTMLResponse)
    async def demo():
        return """<html><body style="background:#111;color:#0f0;font-family:monospace;margin:0;padding:10px;">
        <h3>🎯 YOLO Sync Demo</h3><div style="display:flex;gap:10px;">
        <img src="/stream" style="max-width:60vw;border:2px solid #0f0;">
        <pre id="j" style="flex:1;background:#222;padding:10px;overflow:auto;height:80vh;">Loading...</pre></div>
        <script>setInterval(async()=>{document.getElementById('j').textContent=JSON.stringify(await(await fetch('/detections')).json(),null,2)},100)</script></body></html>"""

if __name__ == "__main__":
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(("8.8.8.8",80));ip=s.getsockname()[0];s.close()
    except: ip="127.0.0.1"
    log(f"🌐 Stream: http://{ip}:8000/stream")
    if ENABLE_DEMO_STREAM: log(f"🎬 Demo: http://{ip}:8000/demo")
    uvicorn.run(app, host="0.0.0.0", port=8000)
