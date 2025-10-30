import socket
import threading
import time
import numpy as np
from dynamixel_sdk import *
from dynamixel_motors import *

# ===== 설정 =====
# TCP 서버
TCP_IP = "0.0.0.0"  # 모든 인터페이스
TCP_PORT = 8091

# Dynamixel
BAUDRATE = 1000000
DEVICENAME = '/dev/motor'  # ⭐ SBC의 실제 포트로 변경
                              # 리눅스: /dev/ttyUSB0, /dev/ttyACM0
                              # 윈도우: COM18

# 모터 설정
Actuators = {0: "XM430", 1: "XM430", 3: "XC330"}
TorqueLimitsNm = [0.3, 0.3, 0.3]
# ================

# 전역 변수
Motors = []
MotorsCurrentPositions = [0 for i in range(len(Actuators))]
MotorsPresentTorques = [0 for i in range(len(Actuators))]
MotorsGoalPositions = [0 for i in range(len(Actuators))]
MotorsGoalTorques = [100 for i in range(len(Actuators))]
GoalOperatingModes = [10 for i in range(len(Actuators))]
GoalTorqueModes = [10 for i in range(len(Actuators))]

# Dynamixel 초기화
portHandler = PortHandler(DEVICENAME)
packetHandler = PacketHandler(2.0)

if not portHandler.openPort():
    print("[오류] 포트 열기 실패")
    quit()

if not portHandler.setBaudRate(BAUDRATE):
    print("[오류] Baudrate 설정 실패")
    quit()

groupBulkWrite = GroupBulkWrite(portHandler, packetHandler)
groupBulkWrite.clearParam()
groupBulkRead = GroupBulkRead(portHandler, packetHandler)
groupBulkRead.clearParam()

def Initialize_Motors():
    """모터 초기화"""
    for id, type in Actuators.items():
        if type == "XM430":
            Motors.append(XM430(id, portHandler, packetHandler, groupBulkRead, groupBulkWrite))
        elif type == "XC330":
            Motors.append(XC330(id, portHandler, packetHandler, groupBulkRead, groupBulkWrite))
        else:
            print(f"[오류] 잘못된 모터 타입: {type}")
   
    for i, m in enumerate(Motors):
        lim = TorqueLimitsNm[i]
        m.setTorqueLimitNm(lim)
   
    print(f"[완료] {len(Motors)}개 모터 초기화")

def SendMotorData():
    """모터에 명령 전송"""
    groupBulkWrite.clearParam()
    CheckChangeModes()
    for i in range(len(Motors)):
        Motors[i].sendMotorData()
    groupBulkWrite.txPacket()

def CheckChangeModes():
    """모터 모드 변경"""
    for i in range(len(Motors)):
        if GoalTorqueModes[i] != 10:
            Motors[i].enableTorque(GoalTorqueModes[i])
            GoalTorqueModes[i] = 10
       
        if GoalOperatingModes[i] != 10:
            Motors[i].enableTorque(0)
            Motors[i].changeOperatingMode(GoalOperatingModes[i])
            Motors[i].enableTorque(1)
            GoalOperatingModes[i] = 10

def ReceiveMotorData():
    """모터 상태 수신"""
    groupBulkRead.txRxPacket()
    for i in range(len(Motors)):
        result = Motors[i].receiveMotorData()
        MotorsPresentTorques[i] = result[0]
        MotorsCurrentPositions[i] = result[1]

def ParsingCommand(message: str):
    """명령 파싱"""
    write_datas = message.strip().split(",")
   
    try:
        if write_datas[0] == 'p':
            i = int(write_datas[1])
            goal_position = float(write_datas[2])
            goal_torque = float(write_datas[3])
            Motors[i].updateGoalPosition(goal_position)
            Motors[i].updateGoalTorque(goal_torque)
           
        elif write_datas[0] == 'c':
            i = int(write_datas[1])
            goal_torque = float(write_datas[2])
            Motors[i].updateGoalTorque(goal_torque)
           
        elif write_datas[0] == 't':
            id = int(write_datas[1])
            mode = int(write_datas[2])
            GoalTorqueModes[id] = int(mode)
           
        elif write_datas[0] == 'co':
            id = int(write_datas[1])
            mode = int(write_datas[2])
            GoalOperatingModes[id] = int(mode)
           
    except Exception as e:
        print(f"[오류] 명령 파싱: {e} | 메시지: {message}")

class MotorTcpServer:
    def __init__(self):
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.running = True
        self.connected = False
       
    def start_server(self):
        """TCP 서버 시작"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((TCP_IP, TCP_PORT))
        self.server_socket.listen(1)
        print(f"[시작] TCP 서버: {TCP_IP}:{TCP_PORT}")
       
    def wait_for_client(self):
        """클라이언트 연결 대기"""
        print("[대기] 클라이언트 연결 대기 중...")
        self.server_socket.settimeout(1.0)
       
        while self.running and not self.connected:
            try:
                self.client_socket, self.client_address = self.server_socket.accept()
                self.client_socket.settimeout(1.0)
                self.connected = True
                print(f"[연결] 클라이언트: {self.client_address}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[오류] 연결 대기: {e}")
                time.sleep(1)
   
    def receive_commands(self):
        """명령 수신 스레드"""
        print("[시작] 명령 수신 스레드")
        buffer = ""
       
        while self.running:
            try:
                if not self.connected:
                    time.sleep(0.1)
                    continue
               
                data = self.client_socket.recv(1024)
                if not data:
                    print("[종료] 클라이언트 연결 끊김")
                    self.connected = False
                    if self.client_socket:
                        self.client_socket.close()
                    self.wait_for_client()
                    buffer = ""
                    continue
               
                buffer += data.decode('utf-8')
               
                # 줄바꿈으로 명령 분리
                while '\n' in buffer:
                    command, buffer = buffer.split('\n', 1)
                    command = command.strip()
                    if command:
                        ParsingCommand(command)
                        print(f"[수신] {command}")
                       
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[오류] 명령 수신: {e}")
                self.connected = False
                buffer = ""
                if self.client_socket:
                    self.client_socket.close()
                self.wait_for_client()
   
    def update_motor_status(self):
        """모터 상태 업데이트 및 전송"""
        print("[시작] 모터 상태 업데이트 스레드")
       
        while self.running:
            try:
                # 모터 명령 전송
                SendMotorData()
               
                # 모터 상태 수신
                ReceiveMotorData()
               
                # 클라이언트에게 상태 전송
                if self.connected:
                    for i in range(len(Motors)):
                        msg = f"{i},{MotorsCurrentPositions[i]},{MotorsPresentTorques[i]}\n"
                        try:
                            self.client_socket.sendall(msg.encode('utf-8'))
                        except:
                            self.connected = False
                            break
               
                time.sleep(0.01)  # 100Hz
               
            except Exception as e:
                print(f"[오류] 모터 상태: {e}")
                time.sleep(0.1)
   
    def run(self):
        """메인 실행"""
        print("=" * 60)
        print("Motor TCP Server 시작")
        print("=" * 60)
        print(f"장치: {DEVICENAME}")
        print(f"모터: {len(Actuators)}개")
        print(f"포트: {TCP_PORT}")
        print("=" * 60)
       
        # 모터 초기화
        Initialize_Motors()
       
        # TCP 서버 시작
        self.start_server()
       
        # 클라이언트 대기
        self.wait_for_client()
       
        # 스레드 시작
        t1 = threading.Thread(target=self.receive_commands, daemon=True)
        t2 = threading.Thread(target=self.update_motor_status, daemon=True)
       
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
        print("[정리] 모터 토크 해제 중...")
        for i in range(len(Motors)):
            Motors[i].updateGoalTorque(0)
        SendMotorData()
       
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()
        portHandler.closePort()
        print("[완료] Motor TCP Server 종료")

if __name__ == "__main__":
    server = MotorTcpServer()
    server.run()
