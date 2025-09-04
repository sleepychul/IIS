import socket
import threading
import time

# 블루투스 설정
pc_bt_address = 'D4:D8:53:37:7F:E3'  # PC 블루투스 주소
pc_bt_port = 12                     # PC 블루투스 포트

# ESP32 블루투스 주소

#target_addr = '94:54:c5:97:08:9e'   # ESP32 블루투스 주소
target_addr = '94:54:c5:90:0e:3a'
target_port = 1            # ESP32 블루투스 포트

# 블루투스 소켓 생성 및 연결
bt = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
bt.bind((pc_bt_address, pc_bt_port))
bt.connect((target_addr, target_port))

# 논블로킹 모드 설정
#bt.setblocking(False)

# LOOPBACK UDP 소켓 설정
loopback_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
loopback_sock.bind(("127.0.0.1", 10001))
unity_ip = "127.0.0.1"
unity_port = 10002

# 수신 버퍼
rx_buffer = b''

# 초당 프레임(라인) 수를 측정하기 위한 전역 변수
fps_count = 0


# 블루투스 수신 함수
def receive_bt():
    global rx_buffer
    global fps_count
    while True:
        try:
            chunk = bt.recv(128)
            # 데이터가 없으면 연결이 끊긴 것으로 판단
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
                    # 터치 데이터 (msgs[1], msgs[2]) 처리
                    pass
                elif msgs[0] == 'r':
                    pass
                    # 회전 데이터 (msgs[1], msgs[2], msgs[3], msgs[4]) 처리
                    #print(f"회전 : {msgs[1]},{msgs[2]},{msgs[3]},{msgs[4]}")
                else:
                    pass
                    #print(decoded_line)
                # 필요 시 Loopback 사용 예시
                loopback_sock.sendto(decoded_line.encode('utf-8'), (unity_ip, unity_port))

        except BlockingIOError:
            # 논블로킹에서 수신할 데이터가 없으면 예외 발생
            pass
        except Exception as e:
            # 루프가 너무 빨리 돌지 않도록 잠시 대기
            time.sleep(0.001)
            print(f"Receive Error: {e}")
            pass



def receiveFromUnity():
    while(True):
        try:
            message, addr = loopback_sock.recvfrom(1024)
            message += bytes('\n', 'utf-8')
            bt.send(message)
        except Exception as e:
            #print(f"Send Error: {e}")
            pass

# 블루투스 전송 함수
def send_bt():
    while True:
        try:
            MESSAGE = input(">>> ")
            # '\n'을 붙여 보내면, 수신 쪽에서도 '\n' 기준 파싱 용이
            bt.send(bytes(MESSAGE + '\n', 'utf-8'))
        except Exception as e:
            print(f"Send Error: {e}")
            break


# FPS(프레임 수) 모니터링 함수
def fps_monitor():
    global fps_count
    while True:
        # 1초 대기 후 fps_count를 출력하고 0으로 리셋
        time.sleep(1.0)
        print(f"[FPS] {fps_count} lines/sec")
        fps_count = 0


# 블루투스 수신 스레드 시작
receive_thread = threading.Thread(target=receive_bt, daemon=True)
receive_thread.start()

# 블루투스 전송 스레드 시작
send_thread = threading.Thread(target=receiveFromUnity, daemon=True)
send_thread.start()

# FPS 모니터 스레드 시작
fps_thread = threading.Thread(target=fps_monitor, daemon=True)
fps_thread.start()

# 메인 루프
running = True
try:
    while running:
        # 필요한 메인 스레드 작업(키 입력, pygame 이벤트 등)이 있다면 이곳에 배치
        time.sleep(0.1)
except KeyboardInterrupt:
    print("사용자 종료 요청")
    running = False

# 블루투스/소켓 자원 정리
bt.close()
loopback_sock.close()
print("Program terminated.")