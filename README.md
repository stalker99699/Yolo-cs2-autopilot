# Yolo-cs2-autopilot
🤖 Этот проект на 100% сгенерирован с помощью ИИ. Простите меня.

Автопилот для CS2 на базе YOLO (ONNX) под Linux. Состоит из двух модулей: сервер детекции (YOLO + FastAPI) и триггербот.

## Архитектура

    cs.py (YOLO-детектор)  →  HTTP API (localhost:8000)  →  triger.py (триггербот)
       │                           │
       ├── /detections (JSON)      │
       ├── /stream (MJPEG)         │
       └── /demo (веб-страница)    │
                                   └── pynput (эмуляция мыши)

## Возможности

- **Детекция** — YOLOv8 (ONNX) + `mss` захват экрана, инференс на CPU
- **Стриминг** — MJPEG поток с оверлеем (боксы, овалы, диагонали, лейблы)
- **Триггербот** — авто-выстрел при наведении на цель, с фильтрацией по confidence, размеру и ориентации
- **Человекоподобие** — рандомизация задержек (jitter), раздельная реакция на первый выстрел и скорострельность
- **Горячие клавиши** — настройка на лету без перезапуска

## Зависимости

    pip install ultralytics mss fastapi uvicorn pynput opencv-python numpy
    или
    pip install ultralytics mss fastapi uvicorn pynput opencv-python numpy --break-system-packages

Дополнительно для звука: `paplay` (PulseAudio) — обычно уже есть в Linux.

## Установка

    git clone https://github.com/stalker99699/Yolo-cs2-autopilot.git
    cd Yolo-cs2-autopilot
    # Положи свою .onnx модель (или используй yolo-1417-cs-player.onnx)

## Настройка

### cs.py — пути и параметры

    MODEL_PATH = "/путь/к/yolo-1417-cs-player.onnx"   # ← укажи путь к модели
    CONF_THRESHOLD = 0.50               # порог уверенности
    IMG_SIZE = 640                       # размер входа YOLO
    TARGET_FPS = 30                      # целевой FPS захвата
    SKIP_FRAMES = 2                      # инференс каждого N-го кадра

Режимы отрисовки:

    DRAW_RECTANGLE = True    # рамка bbox
    DRAW_OVAL = True         # вписанный овал
    DRAW_DIAGONALS = True    # диагонали
    SHOW_LABELS = True       # класс + confidence
    CALC_OVAL_AREA = True    # площадь овала в лейбле

### triger.py — параметры триггера

    API_URL = "http://127.0.0.1:8000/detections"
    CENTER_X, CENTER_Y = 640, 512    # центр экрана (прицел)
    CONF_MIN = 0.5                    # мин. confidence для выстрела
    VERT_RATIO_MAX = 1.6              # макс. соотношение w/h (фильтр "вертикальных" целей)
    ONLY_VERT = True                  # стрелять только по вертикальным целям

    REACTION_DELAY = 0.12             # задержка первого выстрела (сек)
    FIRE_RATE = 0.045                 # интервал между выстрелами (сек)
    CLICK_BASE = 0.018                # длительность клика (сек)
    CLICK_JITTER = 0.005              # ± рандом клика
    JITTER = 0.008                    # ± рандом интервалов

    SOUND_PATH = "/путь/к/ding.mp3"   # звук активации

## Запуск

**Терминал 1** — детектор:

    python cs.py

Стрим: `http://<ip>:8000/stream` | Демо: `http://<ip>:8000/demo`

**Терминал 2** — триггербот:

    python triger.py

## Горячие клавиши (triger.py)

| Клавиша | Действие |
|---------|----------|
| `Tab` | Вкл/выкл триггер |
| `t` | Вкл/выкл звук |
| `-` / `=` | Уменьшить / увеличить задержку реакции (шаг 10мс) |
| `_` / `+` (Shift) | Уменьшить / увеличить интервал скорострельности |

## API (cs.py)

| Эндпоинт | Описание |
|----------|----------|
| `GET /detections` | JSON с детекциями (bbox, confidence, center, orientation, oval_area) |
| `GET /stream` | MJPEG поток с оверлеем |
| `GET /demo` | HTML-страница с превью |

## Структура проекта

    ├── cs.py                      # YOLO-детектор + FastAPI сервер
    ├── triger.py                  # Триггербот (клиент API)
    ├── yolo-1417-cs-player.onnx   # ONNX модель (https://github.com/stalker99699/Yolo-cs-player.git)
    ├── detections.json            # автогенерируемый JSON детекций
    ├── LICENSE                    # GPL-3.0
    └── README.md

## Лицензия

GPL-3.0
