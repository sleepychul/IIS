import socket

# SBC의 IP 주소와 포트
SBC_IP = "192.168.137.122"   # SBC의 IP로 수정
SBC_PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((SBC_IP, SBC_PORT))
print(f"[INFO] Connected to SBC {SBC_IP}:{SBC_PORT}")

try:
    while True:
        data = client.recv(1024).decode(errors="ignore").strip()
        if data:
            print(f"[GPS] {data}")
except KeyboardInterrupt:
    print("\n[INFO] Stopped by user")
finally:
    client.close()
