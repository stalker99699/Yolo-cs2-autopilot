import urllib.request
import json
import time
import sys
import random
import subprocess
try:
    from pynput.keyboard import Listener, Key
    from pynput.mouse import Controller, Button
except ImportError:
    print("❌ pip install pynput"); sys.exit(1)

# ================= НАСТРОЙКИ =================
API_URL = "http://127.0.0.1:8000/detections"
CENTER_X, CENTER_Y = 640, 512
CHECK_HZ = 30
CONF_MIN = 0.5
VERT_RATIO_MAX, LAND_RATIO_MAX = 1.6, 1.6
ONLY_VERT = True

REACTION_DELAY = 0.12   # Задержка первого выстрела
FIRE_RATE = 0.045       # Интервал между выстрелами
STEP = 0.01             # Шаг настройки
CLICK_BASE = 0.018      # Длительность нажатия ЛКМ
CLICK_JITTER = 0.005    # ±5мс рандом нажатия
JITTER = 0.008          # ±8мс рандом интервалов

SOUND_PATH = "/home/stalker99699/CD/ADMIN/sound/activation/ding.mp3" # ← Путь к файлу
SOUND_ENABLED = True
# =============================================

enabled = True
mouse = Controller()
last_fire = 0
check_dt = 1.0 / CHECK_HZ

def in_ellipse(px, py, cx, cy, rx, ry):
    return ((px - cx)**2 / rx**2) + ((py - cy)**2 / ry**2) <= 1.0

def play_sound():
    if SOUND_ENABLED:
        # Linux (paplay) / macOS (afplay) / Win (powershell)
        cmd = f"paplay '{SOUND_PATH}' 2>/dev/null || afplay '{SOUND_PATH}' 2>/dev/null || powershell -c (New-Object Media.SoundPlayer '{SOUND_PATH}').PlaySync()"
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def on_press(key):
    global enabled, REACTION_DELAY, FIRE_RATE, SOUND_ENABLED
    try:
        if key == Key.tab:
            enabled = not enabled
            print(f"🎯 Trigger: {'✅ ВКЛ' if enabled else '⛔ ВЫКЛ'}")
        elif key.char == 't':
            SOUND_ENABLED = not SOUND_ENABLED
            print(f"🔊 Звук: {'✅ ВКЛ' if SOUND_ENABLED else '⛔ ВЫКЛ'}")
        elif key.char == '-':
            REACTION_DELAY = max(0.01, REACTION_DELAY - STEP)
            print(f"⚡ Реакция: {REACTION_DELAY*1000:.1f}мс ↓")
        elif key.char == '=':
            REACTION_DELAY = min(1.0, REACTION_DELAY + STEP)
            print(f"⚡ Реакция: {REACTION_DELAY*1000:.1f}мс ↑")
        elif key.char == '_':
            FIRE_RATE = max(0.01, FIRE_RATE - STEP)
            print(f"🔫 Скорость: {FIRE_RATE*1000:.1f}мс ↑")
        elif key.char == '+':
            FIRE_RATE = min(1.0, FIRE_RATE + STEP)
            print(f"🔫 Скорость: {FIRE_RATE*1000:.1f}мс ↓")
    except AttributeError:
        pass

listener = Listener(on_press=on_press)
listener.start()
print("🚀 Запущено. [TAB] триггер, [t] звук, [-/=] реакция, [_/+(Shift)] скорострельность.")

try:
    while True:
        t0 = time.perf_counter()
        if not enabled:
            time.sleep(0.1)
            continue

        try:
            with urllib.request.urlopen(API_URL, timeout=0.5) as r:
                data = json.loads(r.read().decode())
        except Exception:
            data = {"detections": []}

        for det in data.get("detections", []):
            if det["confidence"] < CONF_MIN: continue
            b = det["bbox"]
            bw, bh = b.get("width", b["x2"]-b["x1"]), b.get("height", b["y2"]-b["y1"])
            if bw < 5 or bh < 5: continue

            is_vert = (bw / bh) <= VERT_RATIO_MAX
            if ONLY_VERT and not is_vert: continue

            cx, cy = (b["x1"] + b["x2"]) / 2, (b["y1"] + b["y2"]) / 2
            if in_ellipse(CENTER_X, CENTER_Y, cx, cy, bw/2, bh/2):
                now = time.time()
                # Если >0.35с не стреляли → применяем реакцию, иначе скорострельность
                base_delay = REACTION_DELAY if (now - last_fire > 0.35) else FIRE_RATE
                eff_delay = base_delay + random.uniform(-JITTER, JITTER)

                if now - last_fire > eff_delay:
                    mouse.press(Button.left)
                    time.sleep(CLICK_BASE + random.uniform(-CLICK_JITTER, CLICK_JITTER))
                    mouse.release(Button.left)
                    last_fire = time.time()
                    play_sound()
                break  # Одна цель за кадр

        sl = check_dt - (time.perf_counter() - t0)
        if sl > 0: time.sleep(sl)
except KeyboardInterrupt:
    print("\n🛑 Остановлено.")
    listener.stop()
except Exception as e:
    print(f"⚠️ {e}")
    listener.stop()
