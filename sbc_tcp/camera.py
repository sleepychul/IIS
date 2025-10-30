# === camera_server.py (SBC) ===
import cv2, socket, struct, pickle, threading

HOST = "0.0.0.0"   # SBC 자신의 IP (모든 인터페이스에서 수신)
PORT = 8000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)
print(f"[SBC] Waiting for Operator PC on port {PORT} ...")
conn, addr = server.accept()
print(f"[SBC] Connected from {addr}")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

def receive_command():
    global cap
    while True:
        cmd = conn.recv(1024).decode().strip()
        if not cmd:
            break
        print("[CMD]", cmd)
        parts = cmd.split()
        if parts[0] == "res" and len(parts) == 3:
            w, h = int(parts[1]), int(parts[2])
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            print(f"[SBC] Resolution changed to {w}x{h}")

def send_video():
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        encoded, buffer = cv2.imencode('.jpg', frame)
        data = pickle.dumps(buffer)
        msg = struct.pack(">L", len(data)) + data
        conn.sendall(msg)

threading.Thread(target=receive_command, daemon=True).start()
send_video()