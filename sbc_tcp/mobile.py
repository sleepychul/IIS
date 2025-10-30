import socket
import serial
import threading
import time

# 시리얼 통신 설정 (라즈베리파이 ↔ ESP32)
SERIAL_PORT = '/dev/mobile' # USB 시리얼: /dev/ttyUSB0, GPIO 시리얼: /dev/ttyAMA0 또는 /dev/serial0
BAUD_RATE = 115200

# TCP 서버 설정 (라즈베리파이 ↔ PC)
TCP_HOST = '0.0.0.0'  # 모든 인터페이스에서 접속 허용
TCP_PORT = 8080

# 전역 변수
ser = None
server_sock = None
client_sock = None
rx_buffer = b''
fps_count = 0


# ESP32로부터 시리얼 수신 → PC로 TCP 전송
def serial_to_tcp():
    global rx_buffer, fps_count, client_sock, ser
    while True:
        try:
            if ser and ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
               
                # 수신 버퍼에 누적
                rx_buffer += chunk

                # 버퍼 내에서 '\n'이 존재하면 한 줄씩 분할
                while b'\n' in rx_buffer:
                    line, rx_buffer = rx_buffer.split(b'\n', 1)
                    decoded_line = line.decode('utf-8', 'ignore')

                    # 수신 프레임(라인) 수 카운트
                    fps_count += 1

                    # PC로 TCP 전송
                    if client_sock:
                        try:
                            client_sock.sendall(decoded_line.encode('utf-8') + b'\n')
                        except:
                            print("PC 연결 끊김")
                            break

            time.sleep(0.001)  # CPU 사용률 조절

        except Exception as e:
            print(f"Serial to TCP Error: {e}")
            time.sleep(0.01)


# PC로부터 TCP 수신 → ESP32로 시리얼 전송
def tcp_to_serial():
    global client_sock, ser
    tcp_buffer = b''
    while True:
        try:
            if client_sock:
                chunk = client_sock.recv(1024)
                if not chunk:
                    print("PC 연결이 종료되었습니다.")
                    break

                tcp_buffer += chunk

                # '\n' 기준으로 메시지 분할
                while b'\n' in tcp_buffer:
                    line, tcp_buffer = tcp_buffer.split(b'\n', 1)
                    # ESP32로 시리얼 전송
                    if ser:
                        ser.write(line + b'\n')

        except Exception as e:
            print(f"TCP to Serial Error: {e}")
            time.sleep(0.01)


# FPS 모니터링 함수
def fps_monitor():
    global fps_count
    while True:
        time.sleep(1.0)
        print(f"[FPS] {fps_count} lines/sec")
        fps_count = 0


# 메인 실행
if __name__ == "__main__":
    try:
        # 시리얼 포트 열기
        print(f"시리얼 포트 연결 중... {SERIAL_PORT}")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"시리얼 포트 연결 완료! ({SERIAL_PORT}, {BAUD_RATE} baud)")

        # TCP 서버 소켓 생성
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((TCP_HOST, TCP_PORT))
        server_sock.listen(1)
       
        print(f"TCP 서버 대기 중... {TCP_HOST}:{TCP_PORT}")
        print("PC에서 접속을 기다리고 있습니다...")
       
        client_sock, client_addr = server_sock.accept()
        print(f"PC 연결됨: {client_addr}")

        # 스레드 시작
        serial_to_tcp_thread = threading.Thread(target=serial_to_tcp, daemon=True)
        serial_to_tcp_thread.start()

        tcp_to_serial_thread = threading.Thread(target=tcp_to_serial, daemon=True)
        tcp_to_serial_thread.start()

        fps_thread = threading.Thread(target=fps_monitor, daemon=True)
        fps_thread.start()

        # 메인 루프
        print("프로그램 실행 중... (Ctrl+C로 종료)")
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n사용자 종료 요청")
    except serial.SerialException as e:
        print(f"시리얼 포트 오류: {e}")
        print(f"포트 확인: ls /dev/tty* | grep -E 'USB|AMA'")
        print(f"권한 부여: sudo chmod 666 {SERIAL_PORT}")
    except PermissionError:
        print(f"권한 오류: {SERIAL_PORT}에 접근할 수 없습니다.")
        print(f"해결 방법: sudo chmod 666 {SERIAL_PORT}")
        print(f"또는 사용자를 dialout 그룹에 추가: sudo usermod -a -G dialout $USER")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        # 자원 정리
        if ser:
            ser.close()
            print("시리얼 포트 닫힘")
        if client_sock:
            client_sock.close()
            print("클라이언트 연결 닫힘")
        if server_sock:
            server_sock.close()
            print("서버 소켓 닫힘")
        print("Program terminated.")
