import numpy as np
from dynamixel_sdk import *

def _saturate(x, lo, hi):
    return max(lo, min(hi, x))


class XM430():
    ADDR_TORQUE_ENABLE = 64
    ADDR_OPERATING_MODE = 11
    ADDR_RETURN_DTIME = 9
    TORQUE_ENABLE = 1
    OPERATING_MODE = 5

    DXL_MINIMUM_POSITION_VALUE = 0  # Refer to the Minimum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE = 4095  # Refer to the Maximum Position Limit of product eManual

    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132

    ADDR_GOAL_CURRENT = 102
    ADDR_PRESENT_CURRENT = 126

    IDR_ADDR_READ_START = 224
    IDR_ADDR_WRITE_START = 235

    position_ratio = 0.087891
    current_ratio = 2.69
    current_torque_ratio = 1.0 / 1000

    def __init__(self,id,portHandler,packetHandler,groupBulkRead,groupBulkWrite):
        self.id = id
        self.initialPosition = 0
        self.presentPosition = 0
        self.presentCurrent = 0
        self.goalPosition = 0
        self.goalCurrent = 0
        self.portHandler = portHandler
        self.packetHandler = packetHandler
        self.groupBulkRead = groupBulkRead
        self.groupBulkWrite = groupBulkWrite

        # NEW: 토크 소프트 제한(Nm). None이면 제한 없음
        self.max_torque_nm = None

        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 0)
        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_RETURN_DTIME, 0)
        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_OPERATING_MODE, 5)
        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 1)
        packetHandler.write2ByteTxRx(self.portHandler, id, self.ADDR_GOAL_CURRENT, 0) # Goal Current를 0으로 설정
        packetHandler.write2ByteTxRx(self.portHandler, id, 168, 126)
        packetHandler.write2ByteTxRx(self.portHandler, id, 170, 127)
        packetHandler.write2ByteTxRx(self.portHandler, id, 172, 132)
        packetHandler.write2ByteTxRx(self.portHandler, id, 174, 133)
        packetHandler.write2ByteTxRx(self.portHandler, id, 176, 134)
        packetHandler.write2ByteTxRx(self.portHandler, id, 178, 135)
        packetHandler.write2ByteTxRx(self.portHandler, id, 190, 102)
        packetHandler.write2ByteTxRx(self.portHandler, id, 192, 103)
        packetHandler.write2ByteTxRx(self.portHandler, id, 194, 116)
        packetHandler.write2ByteTxRx(self.portHandler, id, 196, 117)
        packetHandler.write2ByteTxRx(self.portHandler, id, 198, 118)
        packetHandler.write2ByteTxRx(self.portHandler, id, 200, 119)


        groupBulkRead.addParam(self.id, self.IDR_ADDR_READ_START, 6)
        self.getInitialState()

    # NEW: 외부에서 토크 제한(Nm) 설정
    def setTorqueLimitNm(self, limit_nm: float | None):
        self.max_torque_nm = limit_nm

    def getInitialState(self):
        self.groupBulkRead.txRxPacket()  # 보내기 받기 한번에
        self.initialPosition = np.array(self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)).astype(np.int32)
        #print(self.initialPosition)

    def receiveMotorData(self):
        present_current = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START, 2)
        present_position = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)
        self.presentCurrent = np.array(present_current).astype(np.int16)
        self.presentPosition = np.array(present_position).astype(np.int32) - self.initialPosition
        return (self.presentCurrent * self.current_ratio * self.current_torque_ratio , self.presentPosition * self.position_ratio)
        #print(f"Current : {self.presentCurrent * self.current_ratio} mA, Position : {self.presentPosition * self.position_ratio} degree")

    def updateGoalPosition(self,degree):
        try:
            self.goalPosition = int(float(degree) / self.position_ratio)
        except Exception as e:
            print(e)

    def updateGoalCurrent(self, current):
        try:
            self.goalCurrent = int(float(current) / self.current_ratio)
            #print(self.goalCurrent)
        except Exception as e:
            print(e)

    # NEW: 토크(Nm) → Goal Current(LSB) 변환 + 소프트 토크 제한
    def updateGoalTorque(self, torque_nm: float):
        try:
            t_cmd = float(torque_nm)
            if self.max_torque_nm is not None:
                t_cmd = _saturate(t_cmd, -self.max_torque_nm, self.max_torque_nm)
            # Nm → (mA) → (LSB)
            denom = (self.current_torque_ratio * self.current_ratio)  # (Nm/mA)*(mA/LSB) = Nm/LSB
            if denom == 0:
                return
            self.goalCurrent = int(t_cmd / denom)
        except Exception as e:
            print(e)
    

    def sendMotorData(self):
        #self.groupBulkWrite.clearParam()
        data_430 = [DXL_LOBYTE(self.goalCurrent), DXL_HIBYTE(self.goalCurrent), DXL_LOBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
                    DXL_HIBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
                    DXL_LOBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition)), DXL_HIBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition))]
        self.groupBulkWrite.addParam(self.id, self.IDR_ADDR_WRITE_START, 6, data_430)
        #self.groupBulkWrite.txPacket()

    def enableTorque(self, mode : int):
        #self.groupBulkWrite.clearParam()
        if(mode == 0):
            #print("torque off")
            self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 0)
        elif(mode == 1):
            #print("torque on")
            self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 1)
        #self.groupBulkWrite.txPacket()

    def changeOperatingMode(self, mode : int):
        #self.groupBulkWrite.clearParam()
        #print(f"Operate Mode Command Received : {mode}")
        self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_OPERATING_MODE, mode)
        #self.groupBulkWrite.txPacket()

    def report(self):
        return self.presentPosition * self.position_ratio

class XC330():
    ADDR_TORQUE_ENABLE = 64
    ADDR_OPERATING_MODE = 11
    ADDR_RETURN_DTIME = 9

    TORQUE_ENABLE = 1
    OPERATING_MODE = 5

    DXL_MINIMUM_POSITION_VALUE = 0  # Refer to the Minimum Position Limit of product eManual
    DXL_MAXIMUM_POSITION_VALUE = 4095  # Refer to the Maximum Position Limit of product eManual

    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132

    ADDR_GOAL_CURRENT = 102
    ADDR_PRESENT_CURRENT = 126

    IDR_ADDR_READ_START = 208
    IDR_ADDR_WRITE_START = 219
    position_ratio = 0.087891
    current_ratio = 1
    current_torque_ratio = 0.63 / 740

    def __init__(self,id,portHandler,packetHandler,groupBulkRead,groupBulkWrite):
        self.id = id
        self.goalOperatingMode = 1
        self.goalTorqueEnable = 1
        self.initialPosition = 0
        self.presentPosition = 0
        self.presentCurrent = 0
        self.goalPosition = 0
        self.goalCurrent = 0
        self.portHandler = portHandler
        self.packetHandler = packetHandler
        self.groupBulkRead = groupBulkRead
        self.groupBulkWrite = groupBulkWrite

        # NEW: 토크 소프트 제한(Nm)
        self.max_torque_nm = None


        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 0)
        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_RETURN_DTIME, 0)
        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_OPERATING_MODE, 5)
        packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 1)
        packetHandler.write2ByteTxRx(self.portHandler, id, self.ADDR_GOAL_CURRENT, 0) # Goal Current를 0으로 설정
        packetHandler.write2ByteTxRx(self.portHandler, id, 168, 126)
        packetHandler.write2ByteTxRx(self.portHandler, id, 170, 127)
        packetHandler.write2ByteTxRx(self.portHandler, id, 172, 132)
        packetHandler.write2ByteTxRx(self.portHandler, id, 174, 133)
        packetHandler.write2ByteTxRx(self.portHandler, id, 176, 134)
        packetHandler.write2ByteTxRx(self.portHandler, id, 178, 135)
        packetHandler.write2ByteTxRx(self.portHandler, id, 190, 102)
        packetHandler.write2ByteTxRx(self.portHandler, id, 192, 103)
        packetHandler.write2ByteTxRx(self.portHandler, id, 194, 116)
        packetHandler.write2ByteTxRx(self.portHandler, id, 196, 117)
        packetHandler.write2ByteTxRx(self.portHandler, id, 198, 118)
        packetHandler.write2ByteTxRx(self.portHandler, id, 200, 119)
        groupBulkRead.addParam(self.id, self.IDR_ADDR_READ_START, 6)
        self.getInitialState()

    # NEW: 외부에서 토크 제한(Nm) 설정
    def setTorqueLimitNm(self, limit_nm: float | None):
        self.max_torque_nm = limit_nm


    def updateGoalPosition(self, degree):
        try:
            self.goalPosition = int(float(degree) / self.position_ratio)
        except Exception as e:
            print(e)

    def updateGoalCurrent(self, current):
        try:
            self.goalCurrent = int(float(current) / self.current_ratio)
        except Exception as e:
            print(e)

    def updateGoalTorque(self, torque):
        try:
            t_cmd = float(torque)
            if self.max_torque_nm is not None:
                t_cmd = _saturate(t_cmd, -self.max_torque_nm, self.max_torque_nm)
            denom = (self.current_torque_ratio * self.current_ratio)  # Nm/LSB
            if denom == 0:
                return
            self.goalCurrent = int(t_cmd / denom)
        except Exception as e:
            print(e)

    def getInitialState(self):
        self.groupBulkRead.txRxPacket()  # 보내기 받기 한번에
        self.initialPosition = np.array(self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)).astype(np.int32)
        #print(self.initialPosition)

    def receiveMotorData(self):
        present_current = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START, 2)
        present_position = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)
        self.presentCurrent = np.array(present_current).astype(np.int16) 
        self.presentPosition = np.array(present_position).astype(np.int32) - self.initialPosition
        return (self.presentCurrent * self.current_ratio * self.current_torque_ratio, self.presentPosition * self.position_ratio)
        #print(f"Current : {self.presentCurrent * self.current_ratio} mA, Position : {self.presentPosition * self.position_ratio} degree")

    def sendMotorData(self):
        #self.groupBulkWrite.clearParam()
        data_330 = [DXL_LOBYTE(self.goalCurrent), DXL_HIBYTE(self.goalCurrent), DXL_LOBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
                    DXL_HIBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
                    DXL_LOBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition)), DXL_HIBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition))]
        self.groupBulkWrite.addParam(self.id, self.IDR_ADDR_WRITE_START, 6, data_330)
        #self.groupBulkWrite.txPacket()

    def enableTorque(self, mode : int):
        #self.groupBulkWrite.clearParam()
        if (mode == 0):
            self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 0)
        elif (mode == 1):
            self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 1)

        #self.groupBulkWrite.txPacket()


    def changeOperatingMode(self, mode : int):
        #self.groupBulkWrite.clearParam()
        #print(f"Operate Mode Command Received : {mode}")
        self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_OPERATING_MODE, mode)
        #self.groupBulkWrite.txPacket()

    def report(self):
        return self.presentPosition * self.position_ratio



# import numpy as np
# from dynamixel_sdk import *

# class XM430():
#     ADDR_TORQUE_ENABLE = 64
#     ADDR_OPERATING_MODE = 11
#     ADDR_RETURN_DTIME = 9
#     TORQUE_ENABLE = 1
#     OPERATING_MODE = 5

#     DXL_MINIMUM_POSITION_VALUE = 0  # Refer to the Minimum Position Limit of product eManual
#     DXL_MAXIMUM_POSITION_VALUE = 4095  # Refer to the Maximum Position Limit of product eManual

#     ADDR_GOAL_POSITION = 116
#     ADDR_PRESENT_POSITION = 132

#     ADDR_GOAL_CURRENT = 102
#     ADDR_PRESENT_CURRENT = 126

#     IDR_ADDR_READ_START = 224
#     IDR_ADDR_WRITE_START = 235

#     position_ratio = 0.087891
#     current_ratio = 2.69
#     current_torque_ratio = 1.0 / 1000

#     def __init__(self,id,portHandler,packetHandler,groupBulkRead,groupBulkWrite):
#         self.id = id
#         self.initialPosition = 0
#         self.presentPosition = 0
#         self.presentCurrent = 0
#         self.goalPosition = 0
#         self.goalCurrent = 0
#         self.portHandler = portHandler
#         self.packetHandler = packetHandler
#         self.groupBulkRead = groupBulkRead
#         self.groupBulkWrite = groupBulkWrite
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 0)
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_RETURN_DTIME, 0)
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_OPERATING_MODE, 5)
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 1)
#         packetHandler.write2ByteTxRx(self.portHandler, id, self.ADDR_GOAL_CURRENT, 0) # Goal Current를 0으로 설정
#         packetHandler.write2ByteTxRx(self.portHandler, id, 168, 126)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 170, 127)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 172, 132)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 174, 133)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 176, 134)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 178, 135)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 190, 102)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 192, 103)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 194, 116)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 196, 117)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 198, 118)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 200, 119)
#         groupBulkRead.addParam(self.id, self.IDR_ADDR_READ_START, 6)
#         self.getInitialState()

#     def getInitialState(self):
#         self.groupBulkRead.txRxPacket()  # 보내기 받기 한번에
#         self.initialPosition = np.array(self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)).astype(np.int32)
#         #print(self.initialPosition)

#     def receiveMotorData(self):
#         present_current = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START, 2)
#         present_position = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)
#         self.presentCurrent = np.array(present_current).astype(np.int16)
#         self.presentPosition = np.array(present_position).astype(np.int32) - self.initialPosition
#         return (self.presentCurrent * self.current_ratio * self.current_torque_ratio , self.presentPosition * self.position_ratio)
#         #print(f"Current : {self.presentCurrent * self.current_ratio} mA, Position : {self.presentPosition * self.position_ratio} degree")

#     def updateGoalPosition(self,degree):
#         try:
#             self.goalPosition = int(float(degree) / self.position_ratio)
#         except Exception as e:
#             print(e)

#     def updateGoalCurrent(self, current):
#         try:
#             self.goalCurrent = int(float(current) / self.current_ratio)
#             #print(self.goalCurrent)
#         except Exception as e:
#             print(e)

#     def updateGoalTorque(self, torque):
#         try:
#             #print(int(float(torque) / (self.current_torque_ratio * self.current_ratio)))
#             self.goalCurrent = int(float(torque) / (self.current_torque_ratio * self.current_ratio))
#         except Exception as e:
#             print(e)

#     def sendMotorData(self):
#         #self.groupBulkWrite.clearParam()
#         data_430 = [DXL_LOBYTE(self.goalCurrent), DXL_HIBYTE(self.goalCurrent), DXL_LOBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
#                     DXL_HIBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
#                     DXL_LOBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition)), DXL_HIBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition))]
#         self.groupBulkWrite.addParam(self.id, self.IDR_ADDR_WRITE_START, 6, data_430)
#         #self.groupBulkWrite.txPacket()

#     def enableTorque(self, mode : int):
#         #self.groupBulkWrite.clearParam()
#         if(mode == 0):
#             #print("torque off")
#             self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 0)
#         elif(mode == 1):
#             #print("torque on")
#             self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 1)
#         #self.groupBulkWrite.txPacket()

#     def changeOperatingMode(self, mode : int):
#         #self.groupBulkWrite.clearParam()
#         #print(f"Operate Mode Command Received : {mode}")
#         self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_OPERATING_MODE, mode)
#         #self.groupBulkWrite.txPacket()

#     def report(self):
#         return self.presentPosition * self.position_ratio

# class XC330():
#     ADDR_TORQUE_ENABLE = 64
#     ADDR_OPERATING_MODE = 11
#     ADDR_RETURN_DTIME = 9

#     TORQUE_ENABLE = 1
#     OPERATING_MODE = 5

#     DXL_MINIMUM_POSITION_VALUE = 0  # Refer to the Minimum Position Limit of product eManual
#     DXL_MAXIMUM_POSITION_VALUE = 4095  # Refer to the Maximum Position Limit of product eManual

#     ADDR_GOAL_POSITION = 116
#     ADDR_PRESENT_POSITION = 132

#     ADDR_GOAL_CURRENT = 102
#     ADDR_PRESENT_CURRENT = 126

#     IDR_ADDR_READ_START = 208
#     IDR_ADDR_WRITE_START = 219
#     position_ratio = 0.087891
#     current_ratio = 1
#     current_torque_ratio = 0.63 / 740

#     def __init__(self,id,portHandler,packetHandler,groupBulkRead,groupBulkWrite):
#         self.id = id
#         self.goalOperatingMode = 1
#         self.goalTorqueEnable = 1
#         self.initialPosition = 0
#         self.presentPosition = 0
#         self.presentCurrent = 0
#         self.goalPosition = 0
#         self.goalCurrent = 0
#         self.portHandler = portHandler
#         self.packetHandler = packetHandler
#         self.groupBulkRead = groupBulkRead
#         self.groupBulkWrite = groupBulkWrite
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 0)
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_RETURN_DTIME, 0)
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_OPERATING_MODE, 5)
#         packetHandler.write1ByteTxRx(self.portHandler, id, self.ADDR_TORQUE_ENABLE, 1)
#         packetHandler.write2ByteTxRx(self.portHandler, id, self.ADDR_GOAL_CURRENT, 0) # Goal Current를 0으로 설정
#         packetHandler.write2ByteTxRx(self.portHandler, id, 168, 126)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 170, 127)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 172, 132)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 174, 133)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 176, 134)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 178, 135)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 190, 102)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 192, 103)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 194, 116)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 196, 117)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 198, 118)
#         packetHandler.write2ByteTxRx(self.portHandler, id, 200, 119)
#         groupBulkRead.addParam(self.id, self.IDR_ADDR_READ_START, 6)
#         self.getInitialState()

#     def updateGoalPosition(self, degree):
#         try:
#             self.goalPosition = int(float(degree) / self.position_ratio)
#         except Exception as e:
#             print(e)

#     def updateGoalCurrent(self, current):
#         try:
#             self.goalCurrent = int(float(current) / self.current_ratio)
#         except Exception as e:
#             print(e)

#     def updateGoalTorque(self, torque):
#         try:
#             #print(int(float(torque) / (self.current_torque_ratio * self.current_ratio)))
#             self.goalCurrent = int(float(torque) / (self.current_torque_ratio * self.current_ratio))
#         except Exception as e:
#             print(e)

#     def getInitialState(self):
#         self.groupBulkRead.txRxPacket()  # 보내기 받기 한번에
#         self.initialPosition = np.array(self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)).astype(np.int32)
#         #print(self.initialPosition)

#     def receiveMotorData(self):
#         present_current = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START, 2)
#         present_position = self.groupBulkRead.getData(self.id, self.IDR_ADDR_READ_START + 2, 4)
#         self.presentCurrent = np.array(present_current).astype(np.int16) 
#         self.presentPosition = np.array(present_position).astype(np.int32) - self.initialPosition
#         return (self.presentCurrent * self.current_ratio * self.current_torque_ratio, self.presentPosition * self.position_ratio)
#         #print(f"Current : {self.presentCurrent * self.current_ratio} mA, Position : {self.presentPosition * self.position_ratio} degree")

#     def sendMotorData(self):
#         #self.groupBulkWrite.clearParam()
#         data_330 = [DXL_LOBYTE(self.goalCurrent), DXL_HIBYTE(self.goalCurrent), DXL_LOBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
#                     DXL_HIBYTE(DXL_LOWORD(self.goalPosition +self.initialPosition)),
#                     DXL_LOBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition)), DXL_HIBYTE(DXL_HIWORD(self.goalPosition+self.initialPosition))]
#         self.groupBulkWrite.addParam(self.id, self.IDR_ADDR_WRITE_START, 6, data_330)
#         #self.groupBulkWrite.txPacket()

#     def enableTorque(self, mode : int):
#         #self.groupBulkWrite.clearParam()
#         if (mode == 0):
#             self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 0)
#         elif (mode == 1):
#             self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_TORQUE_ENABLE, 1)

#         #self.groupBulkWrite.txPacket()


#     def changeOperatingMode(self, mode : int):
#         #self.groupBulkWrite.clearParam()
#         #print(f"Operate Mode Command Received : {mode}")
#         self.packetHandler.write1ByteTxRx(self.portHandler, self.id, self.ADDR_OPERATING_MODE, mode)
#         #self.groupBulkWrite.txPacket()

#     def report(self):
#         return self.presentPosition * self.position_ratio

