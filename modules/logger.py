import logging
import config as cfg
from datetime import datetime
import os

class Logger:
    """Универсальный класс для логирования в файл и консоль"""
    
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
        
        # Создаем форматтер
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Файловый обработчик
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
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