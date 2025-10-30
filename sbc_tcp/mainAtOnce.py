import subprocess
import os
import time

# === SBC에서 실행할 Python 파일 목록 ===
scripts = [
    "speakerTwoWay.py",
    "motor_3.py",
    "mobile.py",
    "gps.py",
    "camera.py",
    "allert.py"
]

# === 현재 파일의 경로 기준으로 설정 ===
base_dir = os.path.dirname(os.path.abspath(__file__))

# === 각 스크립트를 병렬로 실행 ===
processes = []
for script in scripts:
    script_path = os.path.join(base_dir, script)
    if os.path.exists(script_path):
        print(f"▶ {script} 실행 중...")
        # SBC에서도 동일 터미널 내에서 병렬 실행
        p = subprocess.Popen(["python3", script_path])
        processes.append(p)
        time.sleep(0.3)
    else:
        print(f"⚠ 파일 없음: {script_path}")

print("\n✅ 모든 스크립트가 SBC 터미널에서 병렬로 실행 중입니다.")
print("🛑 중지하려면 Ctrl + C 를 눌러 모든 프로세스를 종료하세요.\n")

# === 메인 프로세스가 종료되지 않도록 유지 ===
try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n⏹ 사용자 종료 요청: 모든 프로세스 종료 중...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    print("모든 프로세스가 정상적으로 종료되었습니다.")
