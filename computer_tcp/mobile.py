import socket
import threading
import time

# TCP 클라이언트 설정 (PC → 라즈베리파이)
RASPBERRY_PI_IP = '192.168.137.122'  # 라즈베리파이 IP 주소로 변경 필요
RASPBERRY_PI_PORT = 8080

# LOOPBACK UDP 소켓 설정 (Unity와 통신)
loopback_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
loopback_sock.bind(("127.0.0.1", 10005))
unity_ip = "127.0.0.1"
unity_port = 10004

# 수신 버퍼
rx_buffer = b''

# FPS 카운터
fps_count = 0

# TCP 소켓 (전역 변수로 선언)
tcp_sock = None


# 라즈베리파이로부터 TCP 수신 → Unity로 UDP 전송
def receive_tcp():
    global rx_buffer, fps_count, tcp_sock
    while True:
        try:
            chunk = tcp_sock.recv(1024)
            if not chunk:
                print("연결이 종료되었습니다.")
                break

            # 수신 버퍼에 누적
            rx_buffer += chunk

            # 버퍼 내에서 '\n'이 존재하면 한 줄씩 분할
            while b'\n' in rx_buffer:
                line, rx_buffer = rx_buffer.split(b'\n', 1)
                decoded_line = line.decode('utf-8', 'ignore')

                # 수신 프레임(라인) 수 카운트
                fps_count += 1

                msgs = decoded_line.split(',')
                if msgs[0] == 't':
                    # 터치 데이터 처리
                    pass
                elif msgs[0] == 'r':
                    # 회전 데이터 처리
                    pass
                else:
                    pass

                # Unity로 UDP 전송
                loopback_sock.sendto(decoded_line.encode('utf-8'), (unity_ip, unity_port))

        except Exception as e:
            print(f"Receive Error: {e}")
            time.sleep(0.001)


# Unity로부터 UDP 수신 → 라즈베리파이로 TCP 전송
def receive_from_unity():
    global tcp_sock
    while True:
        try:
            message, addr = loopback_sock.recvfrom(1024)
            message += b'\n'
            tcp_sock.sendall(message)
        except Exception as e:
            # 에러 출력 최소화 (너무 많이 출력되는 것 방지)
            pass


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
        # TCP 소켓 생성 및 연결
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"라즈베리파이 연결 중... {RASPBERRY_PI_IP}:{RASPBERRY_PI_PORT}")
        tcp_sock.connect((RASPBERRY_PI_IP, RASPBERRY_PI_PORT))
        print("라즈베리파이 연결 완료!")

        # 스레드 시작
        receive_thread = threading.Thread(target=receive_tcp, daemon=True)
        receive_thread.start()

        send_thread = threading.Thread(target=receive_from_unity, daemon=True)
        send_thread.start()

        fps_thread = threading.Thread(target=fps_monitor, daemon=True)
        fps_thread.start()

        # 메인 루프
        print("프로그램 실행 중... (Ctrl+C로 종료)")
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n사용자 종료 요청")
    except ConnectionRefusedError:
        print(f"연결 실패: 라즈베리파이({RASPBERRY_PI_IP}:{RASPBERRY_PI_PORT})에 연결할 수 없습니다.")
        print("라즈베리파이에서 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        # 자원 정리
        if tcp_sock:
            tcp_sock.close()
        loopback_sock.close()
        print("Program terminated.")