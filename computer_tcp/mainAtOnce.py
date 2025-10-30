import subprocess
import os
import time

# === 실행할 파일 목록 ===
scripts = [
    "speakerTwoWay.py",
    "motor.py",
    "mobile.py",
    "gps.py",
    "recieveyolo.py",
    "alert.py"
    
]

# === 현재 경로 기준으로 스크립트 실행 ===
base_dir = os.path.dirname(os.path.abspath(__file__))

processes = []
for script in scripts:
    script_path = os.path.join(base_dir, script)
    if os.path.exists(script_path):
        print(f"▶ {script} 실행 중...")
        # VSCode의 동일한 터미널 내에서 병렬 실행
        p = subprocess.Popen(["python", script_path])
        processes.append(p)
        time.sleep(0.3)
    else:
        print(f"⚠ 파일 없음: {script_path}")

print("\n✅ 모든 스크립트가 백그라운드에서 실행 중입니다.")
print("🛑 중지하려면 Ctrl + C 를 눌러 모든 프로세스를 종료하세요.\n")

# === 메인 스크립트가 종료되지 않도록 유지 ===
try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n⏹ 사용자 종료 요청: 모든 프로세스 종료 중...")
    for p in processes:
        p.terminate()
    print("모든 프로세스가 정상적으로 종료되었습니다.")
