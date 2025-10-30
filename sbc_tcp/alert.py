# === sound_server.py (SBC 전용 사운드 서버) ===
import os, sys
import socket
import threading
sys.path.append(os.path.expanduser("~/Desktop/package"))
import sounddevice as sd
import numpy as np

HOST = "0.0.0.0"
PORT = 8002

def play_sound(mode="alert"):
    fs = 44100
    duration = 0.3
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    if mode == "alert":
        tone = 0.5 * np.sin(2 * np.pi * 880 * t)
    elif mode == "warning":
        tone = 0.5 * np.sin(2 * np.pi * 440 * t)
    elif mode == "success":
        tone = 0.5 * np.sin(2 * np.pi * 660 * t)
    else:
        tone = np.zeros_like(t)
    sd.play(tone, fs)
    sd.wait()

def handle_client(conn, addr):
    print(f"[SOUND] Connected from {addr}")
    while True:
        try:
            data = conn.recv(1024).decode().strip()
            if not data:
                break
            print(f"[SOUND CMD] {data}")
            parts = data.split()
            if parts[0] == "sound" and len(parts) == 2:
                play_sound(parts[1])
        except Exception as e:
            print(f"[ERROR] {e}")
            break
    conn.close()
    print(f"[SOUND] Disconnected {addr}")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)
    print(f"[SOUND] Waiting for Operator PC on port {PORT}...")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()
