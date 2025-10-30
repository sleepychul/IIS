# === receive_audio.py (라즈베리파이용) ===
import sys, os
import socket
import threading
import time
sys.path.append(os.path.expanduser("~/Desktop/package"))
import sounddevice as sd

import numpy as np



HOST = "0.0.0.0"
PORT = 50007
SAMPLE_RATE = 44100
CHUNK = 4096

# ====== TCP 서버 설정 ======
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)
print(f"[SBC] Waiting for Operator PC on port {PORT}...")
conn, addr = server.accept()
print(f"[SBC] Connected to {addr}")

# ====== 수신 → 스피커 출력 ======
def receive_audio():
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        while True:
            try:
                data = conn.recv(CHUNK * 2)
                if not data:
                    break
                audio_data = np.frombuffer(data, dtype=np.int16)
                stream.write(audio_data)
            except Exception as e:
                print("[ERROR recv]", e)
                break

# ====== 마이크 → 송신 ======
def send_audio():
    def callback(indata, frames, time_, status):
        if status:
            print("[WARN]", status)
        try:
            conn.sendall((indata * 32767).astype(np.int16).tobytes())
        except Exception as e:
            print("[ERROR send]", e)
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=CHUNK, latency="high", callback=callback):
        while True:
            time.sleep(0.01)

# ====== 두 스레드 병렬 실행 ======
threading.Thread(target=receive_audio, daemon=True).start()
threading.Thread(target=send_audio, daemon=True).start()

print("[SBC] Bi-directional audio active. Press Ctrl+C to exit.")
while True:
    time.sleep(1)
