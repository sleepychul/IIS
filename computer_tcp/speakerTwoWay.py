# === pc_audio.py ===
import socket
import threading
import sounddevice as sd
import numpy as np
import time

SBC_IP = "192.168.137.122"  # 🔹 SBC IP 주소로 수정
PORT = 50007
SAMPLE_RATE = 44100
CHUNK = 4096

# ====== TCP 연결 ======
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SBC_IP, PORT))
print(f"[PC] Connected to SBC {SBC_IP}:{PORT}")

# ====== 수신 → 스피커 ======
def receive_audio():
    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        while True:
            try:
                data = sock.recv(CHUNK * 2)
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
        print(np.mean(indata))
        if status:
            print("[WARN]", status)
        try:
            sock.sendall((indata * 32767).astype(np.int16).tobytes())
        except Exception as e:
            print("[ERROR send]", e)
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=CHUNK, latency="high", callback=callback):
        while True:
            time.sleep(0.01)

# ====== 두 스레드 병렬 실행 ======
threading.Thread(target=receive_audio, daemon=True).start()
threading.Thread(target=send_audio, daemon=True).start()

print("[PC] Bi-directional audio active. Press Ctrl+C to exit.")
while True:
    time.sleep(1)