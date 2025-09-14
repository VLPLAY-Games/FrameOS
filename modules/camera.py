import config as cfg
from picamera2 import Picamera2
import time
from datetime import datetime
import os

class Camera:
    def __init__(self, resolution=cfg.CAMERA_RESOLUTION, framerate=cfg.CAMERA_FPS, logger=None):
        """
        Инициализация камеры для picamera2
        
        Args:
            resolution (tuple): Разрешение камеры (ширина, высота)
            framerate (int): Частота кадров
            logger: Экземпляр логгера
        """
        self.camera = None
        self.resolution = resolution
        self.framerate = framerate
        self.is_camera_active = False
        self.logger = logger
        
    def __enter__(self):
        """Контекстный менеджер для with statement"""
        self.initialize_camera()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие камеры при выходе из with"""
        self.close_camera()
        
    def initialize_camera(self):
        """Инициализация камеры"""
        try:
            self.camera = Picamera2()
            
            # Создаем конфигурацию для фото
            config = self.camera.create_still_configuration(
                main={"size": self.resolution},
                buffer_count=2
            )
            
            # Настраиваем камеру
            self.camera.configure(config)
            self.camera.set_controls({"FrameRate": self.framerate})
            
            self.is_camera_active = True
            if self.logger:
                self.logger.info("Camera initialized (picamera2)")
            else:
                print("Camera initialized (picamera2)")
            
        except Exception as e:
            error_msg = f"Camera initialization error: {e}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(error_msg)
            self.is_camera_active = False
            
    def close_camera(self):
        """Закрытие камеры"""
        if self.camera:
            self.camera.close()
            self.is_camera_active = False
            if self.logger:
                self.logger.info("The camera is closed")
            else:
                print("The camera is closed")
            
    def start_camera(self):
        """Запуск камеры (необходимо перед захватом)"""
        if self.is_camera_active and not self.camera.started:
            self.camera.start()
            if self.logger:
                self.logger.info("The camera is running")
            else:
                print("The camera is running")
            
    def capture_photo(self, filename=None, warmup_time=2):
        """
        Захват фотографии
        
        Args:
            filename (str): Имя файла для сохранения
            warmup_time (int): Время прогрева камеры в секундах
            
        Returns:
            bool: Успешно ли выполнено сохранение
        """
        if not self.is_camera_active:
            error_msg = "Camera is not active!"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(error_msg)
            return False
            
        try:
            # Запускаем камеру если еще не запущена
            if not self.camera.started:
                self.start_camera()
            
            # Генерируем имя файла, если не указано
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{cfg.CAMERA_HOME_DIR}photo_{timestamp}.jpg"
            
            # Даем камере время для настройки
            warmup_msg = f"Warming up the camera {warmup_time} sec..."
            if self.logger:
                self.logger.info(warmup_msg)
            else:
                print(warmup_msg)
            time.sleep(warmup_time)
            
            # Захват фото
            self.camera.capture_file(filename)
            success_msg = f"Photo saved as '{filename}'"
            if self.logger:
                self.logger.info(success_msg)
            else:
                print(success_msg)
            return True
            
        except Exception as e:
            error_msg = f"Error capturing photo: {e}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(error_msg)
            return False
            
    def set_camera_settings(self, brightness=cfg.CAMERA_BRIGHTNESS, contrast=cfg.CAMERA_CONTRAST, rotation=cfg.CAMERA_ROTATION):
        """
        Настройка параметров камеры
        
        Args:
            brightness (int): Яркость (0-100)
            contrast (int): Контраст (0-100)
            rotation (int): Поворот (0, 90, 180, 270)
        """
        if self.is_camera_active:
            # Устанавливаем настройки через controls
            controls = {}
            
            if brightness is not None:
                controls["Brightness"] = brightness / 100.0  # picamera2 использует 0.0-1.0
            if contrast is not None:
                controls["Contrast"] = contrast / 100.0  # picamera2 использует 0.0-1.0
            
            # Применяем настройки
            if controls:
                self.camera.set_controls(controls)
            
            # Поворот обрабатывается отдельно
            if rotation is not None:
                transform = Picamera2.Transform()
                if rotation == 90:
                    transform = transform.vflip
                elif rotation == 180:
                    transform = transform.vflip.hflip
                elif rotation == 270:
                    transform = transform.hflip
                
                # Обновляем конфигурацию с поворотом
                config = self.camera.create_still_configuration(
                    main={"size": self.resolution},
                    transform=transform
                )
                self.camera.configure(config)
            
            settings_msg = f"Camera settings applied: brightness={brightness}, contrast={contrast}, rotation={rotation}"
            if self.logger:
                self.logger.info(settings_msg)
            else:
                print(settings_msg)