import logging
import config as cfg
from datetime import datetime
import os

class Logger:
    """Универсальный класс для логирования в файл и консоль с цветным выводом уровня"""
    
    # Цвета для уровней логирования
    LEVEL_COLORS = {
        'DEBUG': '\033[94m',     # Синий
        'INFO': '\033[92m',      # Зеленый
        'WARNING': '\033[93m',   # Желтый
        'ERROR': '\033[91m',     # Красный
        'CRITICAL': '\033[95m',  # Бордовый/Пурпурный
        'RESET': '\033[0m',      # Сброс цвета
    }
    
    def __init__(self, name="Logger", log_file="FrameOS.log", level=logging.INFO):
        """
        Инициализация логгера
        
        Args:
            name (str): Имя логгера
            log_file (str): Имя файла для логов
            level: Уровень логирования
        """
        self.name = name
        self.log_file = cfg.LOG_DIR + log_file
        
        # Создаем логгер
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Убираем существующие обработчики чтобы избежать дублирования
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Создаем форматтер для файла (без цветов)
        file_formatter = logging.Formatter('[%(asctime)s]  [%(levelname)s]  [%(name)s] - %(message)s')
        
        # Создаем форматтер для консоли (с цветами только для уровня)
        console_formatter = ColoredFormatter('[%(asctime)s] [%(levelname)s]  [%(name)s] - %(message)s')
        
        # Файловый обработчик
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        
        # Добавляем обработчики
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.info(f"Logger '{name}' initialized, file: {log_file}")

    def __del__(self):
        """Деинициализация логгера"""
        self.info(f"Logger '{self.name}' deinitialized")

    def debug(self, message):
        """Логирование отладочного сообщения"""
        self.logger.debug(message)

    def info(self, message):
        """Логирование информационного сообщения"""
        self.logger.info(message)

    def warning(self, message):
        """Логирование предупреждения"""
        self.logger.warning(message)

    def error(self, message):
        """Логирование ошибки"""
        self.logger.error(message)

    def critical(self, message):
        """Логирование критической ошибки"""
        self.logger.critical(message)

    def log_event(self, event_type, details=""):
        """
        Логирование события с типом
        
        Args:
            event_type (str): Тип события
            details (str): Дополнительная информация
        """
        message = f"[{event_type.upper()}] {details}"
        self.info(message)

    def clear_log_file(self):
        """Очистка файла логов"""
        try:
            with open(self.log_file, 'w', encoding='utf-8'):
                pass
            self.info("Log file cleared")
        except Exception as e:
            self.error(f"Error clearing log file: {e}")

  
class ColoredFormatter(logging.Formatter):
    """Кастомный форматтер для цветного вывода только уровня логирования"""
    
    def format(self, record):
        # Получаем стандартное форматированное сообщение
        message = super().format(record)
        
        # Ищем уровень логирования в формате [LEVELNAME]
        level_pattern = f"[{record.levelname}]"
        if level_pattern in message:
            level_name = record.levelname
            if level_name in Logger.LEVEL_COLORS:
                color = Logger.LEVEL_COLORS[level_name]
                reset = Logger.LEVEL_COLORS['RESET']
                # Заменяем только уровень на цветной
                message = message.replace(
                    level_pattern, 
                    f"{color}{level_pattern}{reset}"
                )
        
        return message
