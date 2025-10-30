# === operator_yolo_client.py ===
import cv2
import socket
import struct
import pickle
import threading
import numpy as np
from ultralytics import YOLO
import random
from collections import deque

# ========== TCP 통신 설정 ==========
SERVER_IP = "192.168.137.122"   # ✅ SBC의 실제 IP
PORT = 8000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SERVER_IP, PORT))
print(f"[Operator] Connected to SBC {SERVER_IP}:{PORT}")

# ========== YOLO 초기화 ==========
print("YOLO 모델 로드 중...")
model = YOLO("yolov8n.pt")
print("✅ YOLO 모델 로드 완료")

# ========== 색상 팔레트 및 기록 ==========
def generate_colors(num_colors):
    colors = []
    for i in range(num_colors):
        hue = int(360 * i / num_colors)
        color_hsv = np.array([[[hue, 255, 255]]], dtype=np.uint8)
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0, 0]
        colors.append(tuple(map(int, color_bgr)))
    return colors

def calculate_movement_vector(positions, min_frames=30):
    if len(positions) < min_frames:
        return None
    recent_positions = list(positions)[-min_frames:]
    if len(recent_positions) < 2:
        return None
    positions_array = np.array(recent_positions)
    x_coords = positions_array[:, 0]
    y_coords = positions_array[:, 1]
    time_steps = np.arange(len(recent_positions))
    if len(time_steps) > 1:
        x_slope = np.polyfit(time_steps, x_coords, 1)[0]
        y_slope = np.polyfit(time_steps, y_coords, 1)[0]
        mag = np.sqrt(x_slope**2 + y_slope**2)
        if mag > 0.1:
            scale = min(50, max(20, mag * 10))
            return (x_slope * scale / mag, y_slope * scale / mag)
    return None

def draw_person_tracking(frame, boxes, track_ids, confidences, color_map, history, frame_count):
    for box, tid, conf in zip(boxes, track_ids, confidences):
        x1, y1, x2, y2 = map(int, box)
        cx, cy = int((x1+x2)/2), int((y1+y2)/2)
        if tid not in history: history[tid] = deque(maxlen=50)
        history[tid].append((cx, cy))
        if tid not in color_map:
            color_map[tid] = (random.randint(50,255), random.randint(50,255), random.randint(50,255))
        color = color_map[tid]
        cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)

        mv = calculate_movement_vector(history[tid], min_frames=min(30, len(history[tid])))
        if mv is not None:
            dx, dy = mv
            cv2.arrowedLine(frame, (cx, cy), (int(cx+dx), int(cy+dy)), color, 2, tipLength=0.3)
        label = f"ID:{tid} {conf:.2f}"
        cv2.putText(frame, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

# ========== 명령 전송 쓰레드 ==========
def send_command():
    while True:
        cmd = input("Command to SBC (ex: res 640 480): ")
        client.send(cmd.encode())

# ========== 카메라 영상 수신 + YOLO 처리 ==========
def receive_video():
    data = b""
    payload_size = struct.calcsize(">L")
    cv2.namedWindow("YOLO Real-time Tracking", cv2.WINDOW_NORMAL)
    frame_count = 0
    color_map, history = {}, {}
    while True:
        # --- 데이터 수신 ---
        while len(data) < payload_size:
            packet = client.recv(4096)
            if not packet:
                print("[❌] 연결이 종료됨")
                return
            data += packet

        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack(">L", packed_msg_size)[0]

        while len(data) < msg_size:
            data += client.recv(4096)

        frame_data = data[:msg_size]
        data = data[msg_size:]

        frame = pickle.loads(frame_data)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
        frame_count += 1

        # --- YOLO 추적 수행 ---
        results = model.track(frame, verbose=False, persist=True)
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            mask = classes == 0
            if mask.any():
                frame = draw_person_tracking(
                    frame, boxes[mask], ids[mask], confidences[mask],
                    color_map, history, frame_count
                )

        cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.imshow("YOLO Real-time Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

# ========== 메인 ==========
threading.Thread(target=send_command, daemon=True).start()
receive_video()
