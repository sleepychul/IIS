#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vive Tracker → Unity 브리지 (y-up RH → y-up LH 변환 포함)
· OpenVR deprecation warning 필터링
· UDP 90 Hz 송신
"""

import warnings
# pkg_resources deprecated warning만 무시
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*"
)

import triad_openvr
import time
import socket
import threading
import numpy as np
from scipy.spatial.transform import Rotation as R

# 들어오는 UDP (Vive Tracker → Python)
UDP_IP   = "127.0.0.1"
UDP_PORT = 10003

# 나가는 UDP (Python → Unity)
TARGET_IP   = "127.0.0.1"
TARGET_PORT = 10004

# UDP 소켓 설정
sock_in  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_in.bind((UDP_IP, UDP_PORT))
sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_to_unity(idx: int, pos: np.ndarray, quat: np.ndarray):
    """
    Unity에 보낼 메시지 형식:
    idx, x, y, z, qx, qy, qz, qw
    """
    msg = (
        f"{idx},"
        f"{pos[0]:.6f},{pos[1]:.6f},{pos[2]:.6f},"
        f"{quat[0]:.6f},{quat[1]:.6f},{quat[2]:.6f},{quat[3]:.6f}"
    )
    sock_out.sendto(msg.encode('utf-8'), (TARGET_IP, TARGET_PORT))

def vive_tracker_loop():
    try:
        vr = triad_openvr.triad_openvr()
    except Exception as e:
        print("OpenVR 초기화 실패:", e)
        return

    # 트래커 이름별로 Unity 인덱스 매핑
    indexs = {
        'tracker_1': 3,
        'tracker_2': 1,
        'tracker_3': 2,
        'tracker_4': 0
    }

    # RH → LH 전환을 위한 Z축 반전 매트릭스
    C = np.diag([1.0, 1.0, -1.0])


    while True:
        try:
            for name, dev in vr.devices.items():
                if 'tracker' not in name:
                    continue

                # ----- raw (SteamVR) -----
                x_v, y_v, z_v, qx_v, qy_v, qz_v, qw_v = dev.get_pose_quaternion()
                pos_raw  = np.array([x_v, y_v, z_v])
                quat_raw = np.array([qx_v, qy_v, qz_v, qw_v])

                # 1) 위치 변환: Z 반전 (RH → LH)
                pos_unity = pos_raw * np.array([1.0, 1.0, -1.0])

                # 2) 회전 변환: quat → rotation matrix → C·R·C → quat
                r_v = R.from_quat([qx_v, qy_v, qz_v, qw_v])
                R_v = r_v.as_matrix()
                R_u = C @ R_v @ C
                quat_unity = R.from_matrix(R_u).as_quat()  # [x, y, z, w]

                # Unity로 전송
                idx = indexs.get(name)
                if idx is not None:
                    print(idx, pos_unity, quat_unity)
                    send_to_unity(idx, pos_unity, quat_unity)

            # SteamVR 트래킹 ~90 Hz
            time.sleep(1.0/100.0)

        except Exception as e:
            # 네트워크이나 VR 루프 중 예외가 발생해도 재시도
            print("에러:", e)
            time.sleep(0.1)

def main():
    t = threading.Thread(target=vive_tracker_loop, daemon=True)
    t.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("종료")
    finally:
        sock_in.close()
        sock_out.close()

if __name__ == "__main__":
    main()
