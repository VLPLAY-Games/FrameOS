from os import makedirs

# Camera

CAMERA_HOME_DIR = "cam/"
CAMERA_RESOLUTION = (640, 480)
CAMERA_FPS = 15
CAMERA_BRIGHTNESS = 50
CAMERA_CONTRAST = 50
CAMERA_ROTATION = 0

# Log

LOG_DIR = "logs/"
makedirs(LOG_DIR, exist_ok=True)

# Recognition

MODELS_DIR = "models/"
MODEL_RU = "vosk-ru-small"
makedirs(MODELS_DIR, exist_ok=True)

# RGB

RGB_RED_PIN = 17
RGB_GREEN_PIN = 27
RGB_BLUE_PIN = 22

RGB_COLORS = {
    # Основные цвета
    'red': (100, 0, 0),           # Красный
    'green': (0, 100, 0),         # Зеленый
    'blue': (0, 0, 100),          # Синий
    'white': (100, 100, 100),     # Белый
    'black': (0, 0, 0),           # Черный (выключено)
    
    # Яркие цвета
    'yellow': (100, 100, 0),      # Желтый
    'cyan': (0, 100, 100),        # Голубой
    'magenta': (100, 0, 100),     # Пурпурный
    'orange': (100, 65, 0),       # Оранжевый
    'purple': (80, 0, 80),        # Фиолетовый
    'pink': (100, 20, 80),        # Розовый
    
    # Неоновые цвета
    'neon_green': (20, 100, 20),  # Неоновый зеленый
    'neon_blue': (30, 30, 100),   # Неоновый синий
    'neon_pink': (100, 10, 50),   # Неоновый розовый
    'neon_yellow': (80, 100, 0),  # Неоновый желтый
    
    # Эффектные цвета
    'hot_pink': (100, 10, 60),    # Ярко-розовый
    'lime': (50, 100, 0),         # Лаймовый
    'turquoise': (0, 80, 80),     # Бирюзовый
    
    # Настроенческие цвета
    'calm_blue': (20, 40, 80),    # Спокойный синий
    'energetic_red': (100, 20, 20),# Энергичный красный
    'relaxing_green': (20, 60, 20),# Расслабляющий зеленый
}