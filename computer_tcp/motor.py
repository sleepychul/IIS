import socket
import threading
import time

# ===== 설정 =====
# Unity UDP 통신
UNITY_UDP_RECEIVE_PORT = 8090
UNITY_UDP_SEND_IP = "127.0.0.1"
UNITY_UDP_SEND_PORT = 9996

# SBC TCP 통신
SBC_TCP_IP = "192.168.137.138"  # ⭐ SBC의 실제 IP로 변경
SBC_TCP_PORT = 8091
# ================

class TcpBridge:
    def __init__(self):
        # UDP 소켓 (Unity와 통신)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(("127.0.0.1", UNITY_UDP_RECEIVE_PORT))
        
        # TCP 소켓 (SBC와 통신)
        self.tcp_socket = None
        self.connected = False
        self.running = True
        
    def connect_to_sbc(self):
        """SBC TCP 서버에 연결"""
        retry_count = 0
        while self.running and not self.connected:
            try:
                print(f"[연결] SBC({SBC_TCP_IP}:{SBC_TCP_PORT}) 연결 시도 중... ({retry_count + 1})")
                self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_socket.connect((SBC_TCP_IP, SBC_TCP_PORT))
                self.tcp_socket.settimeout(1.0)
                self.connected = True
                print(f"[성공] SBC 연결 완료!")
                break
            except Exception as e:
                retry_count += 1
                print(f"[실패] {e}")
                if self.tcp_socket:
                    self.tcp_socket.close()
                time.sleep(2)
                
    def unity_to_sbc(self):
        """Unity → SBC 중계 스레드"""
        print("[시작] Unity → SBC 중계 스레드")
        
        while self.running:
            try:
                # Unity로부터 UDP 수신
                data, addr = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                
                # SBC로 TCP 전송
                if self.connected:
                    self.tcp_socket.sendall((message + '\n').encode('utf-8'))
                    print(f"[Unity→SBC] {message}")
                else:
                    print("[경고] SBC 연결 끊김, 재연결 시도...")
                    self.connect_to_sbc()
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[오류] Unity→SBC: {e}")
                self.connected = False
                self.connect_to_sbc()
                
    def sbc_to_unity(self):
        """SBC → Unity 중계 스레드"""
        print("[시작] SBC → Unity 중계 스레드")
        buffer = ""
        
        while self.running:
            try:
                if not self.connected:
                    time.sleep(0.1)
                    continue
                
                # SBC로부터 TCP 수신
                data = self.tcp_socket.recv(1024)
                if not data:
                    print("[경고] SBC 연결 종료됨")
                    self.connected = False
                    self.connect_to_sbc()
                    continue
                
                buffer += data.decode('utf-8')
                
                # 줄바꿈으로 메시지 분리
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)
                    message = message.strip()
                    
                    if message:
                        # Unity로 UDP 전송
                        self.udp_socket.sendto(
                            message.encode('utf-8'),
                            (UNITY_UDP_SEND_IP, UNITY_UDP_SEND_PORT)
                        )
                        print(f"[SBC→Unity] {message}")
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[오류] SBC→Unity: {e}")
                self.connected = False
                buffer = ""
                self.connect_to_sbc()
    
    def run(self):
        """메인 실행"""
        print("=" * 60)
        print("TCP Bridge 시작")
        print("=" * 60)
        print(f"Unity UDP 수신: 127.0.0.1:{UNITY_UDP_RECEIVE_PORT}")
        print(f"Unity UDP 송신: 127.0.0.1:{UNITY_UDP_SEND_PORT}")
        print(f"SBC   TCP 연결: {SBC_TCP_IP}:{SBC_TCP_PORT}")
        print("=" * 60)
        
        # SBC 연결
        self.connect_to_sbc()
        
        # 중계 스레드 시작
        t1 = threading.Thread(target=self.unity_to_sbc, daemon=True)
        t2 = threading.Thread(target=self.sbc_to_unity, daemon=True)
        
        t1.start()
        t2.start()
        
        # 메인 루프
        try:
            print("\n[실행 중] Ctrl+C로 종료")
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n[종료] 프로그램 종료 중...")
            self.running = False
            
        # 정리
        if self.tcp_socket:
            self.tcp_socket.close()
        self.udp_socket.close()
        print("[완료] TCP Bridge 종료")

if __name__ == "__main__":
    bridge = TcpBridge()
    bridge.run()