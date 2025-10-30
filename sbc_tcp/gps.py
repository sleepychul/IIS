import serial
import socket
import threading

# ==== CONFIG ====
SERIAL_PORT = "/dev/ttyACM0"   # ESP32가 연결된 포트 (예: /dev/ttyACM0 또는 /dev/ttyUSB0)
BAUD_RATE = 115200

TCP_HOST = "0.0.0.0"   # SBC가 서버로 동작
TCP_PORT = 5000

# ==== Serial 초기화 ====
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

# ==== TCP 서버 설정 ====
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((TCP_HOST, TCP_PORT))
server.listen(1)

print(f"[INFO] Waiting for Operator PC to connect on port {TCP_PORT}...")
conn, addr = server.accept()
print(f"[INFO] Operator PC connected from {addr}")

# ==== Serial → TCP 송신 스레드 ====
def serial_to_tcp():
    while True:
        try:
            if ser.in_waiting > 0:
                data = ser.readline().decode(errors="ignore").strip()
                if data:
                    conn.sendall((data + "\n").encode())
                    print(f"[TX] {data}")
        except Exception as e:
            print("[ERROR serial_to_tcp]", e)
            break

# ==== TCP → Serial 수신 (선택 사항) ====
def tcp_to_serial():
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            ser.write(data)
        except Exception as e:
            print("[ERROR tcp_to_serial]", e)
            break

# ==== Thread 시작 ====
t1 = threading.Thread(target=serial_to_tcp)
t2 = threading.Thread(target=tcp_to_serial)
t1.start()
t2.start()

t1.join()
t2.join()
