# === sound_client.py (PC 측 사운드 클라이언트) ===
import socket

SBC_IP = "192.168.137.122"  # SBC IP
PORT = 8002

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SBC_IP, PORT))
print(f"[PC] Connected to SBC sound server ({SBC_IP}:{PORT})")

while True:
    cmd = input("Sound command (alert / warning / success / exit): ").strip()
    if cmd == "exit":
        break
    sock.send(f"sound {cmd}".encode())

sock.close()
print("[PC] Disconnected.")
