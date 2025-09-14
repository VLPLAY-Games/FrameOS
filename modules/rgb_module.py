import time
import threading
import RPi.GPIO as GPIO

class KY016_RGB:
    """Класс для управления RGB светодиодом KY-016"""
    
    def __init__(self, red_pin, green_pin, blue_pin, logger=None):
        """
        Инициализация RGB модуля
        
        Args:
            red_pin (int): GPIO пин для красного цвета
            green_pin (int): GPIO пин для зеленого цвета
            blue_pin (int): GPIO пин для синего цвета
            logger: Экземпляр логгера
        """
        self.logger = logger
        self.red_pin = red_pin
        self.green_pin = green_pin
        self.blue_pin = blue_pin
        
        self.current_color = (0, 0, 0)
        self.is_breathing = False
        self.breathing_thread = None
        
        try:
            self.GPIO = GPIO
            self.GPIO.setmode(self.GPIO.BCM)
            self.GPIO.setwarnings(False)
            
            # Настройка пинов как выход
            self.GPIO.setup(self.red_pin, self.GPIO.OUT)
            self.GPIO.setup(self.green_pin, self.GPIO.OUT)
            self.GPIO.setup(self.blue_pin, self.GPIO.OUT)
            
            # Создание PWM объектов
            self.red_pwm = self.GPIO.PWM(self.red_pin, 100)  # 100 Hz
            self.green_pwm = self.GPIO.PWM(self.green_pin, 100)
            self.blue_pwm = self.GPIO.PWM(self.blue_pin, 100)
            
            # Запуск PWM
            self.red_pwm.start(0)
            self.green_pwm.start(0)
            self.blue_pwm.start(0)
            
            self.logger.info(f"RGB module initialized on pins: R{red_pin}, G{green_pin}, B{blue_pin}")

        except Exception as e:
            self.logger.error(f"RGB module initialization error: {e}")
    
    def set_color(self, red, green, blue):
        """
        Установка цвета RGB
        
        Args:
            red (int): Красный (0-100)
            green (int): Зеленый (0-100)
            blue (int): Синий (0-100)
        """
        # Ограничиваем значения
        red = max(0, min(100, red))
        green = max(0, min(100, green))
        blue = max(0, min(100, blue))
        
        self.current_color = (red, green, blue)
        
        if self.GPIO:
            try:
                self.red_pwm.ChangeDutyCycle(red)
                self.green_pwm.ChangeDutyCycle(green)
                self.blue_pwm.ChangeDutyCycle(blue)
            except Exception as e:
                self.logger.error(f"Color setting error: {e}")
        else:
            self.logger.info(f"The color is set: R{red} G{green} B{blue} (emulation)")
    
    def set_color_hex(self, hex_color):
        """
        Установка цвета из HEX формата (#RRGGBB)
        
        Args:
            hex_color (str): HEX цвет, например "#FF0000" для красного
        """
        try:
            # Убираем # если есть
            hex_color = hex_color.lstrip('#')
            
            # Конвертируем HEX в RGB
            red = int(hex_color[0:2], 16) / 255 * 100
            green = int(hex_color[2:4], 16) / 255 * 100
            blue = int(hex_color[4:6], 16) / 255 * 100
            
            self.set_color(red, green, blue)
            self.logger.info(f"Color set from HEX: {hex_color}")
            
        except Exception as e:
            self.logger.error(f"HEX color conversion error: {e}")
    
    def off(self):
        """Выключение светодиода"""
        self.set_color(0, 0, 0)
        self.logger.info("RGB LED is off")
    
    def breathing_effect(self, color=(100, 0, 0), speed=2, duration=None):
        """
        Эффект дыхания (плавное изменение яркости)
        
        Args:
            color (tuple): Цвет (R, G, B)
            speed (float): Скорость эффекта (1-10)
            duration (float): Длительность в секундах (None - бесконечно)
        """
        if self.is_breathing:
            self.stop_breathing()
        
        self.is_breathing = True
        self.breathing_thread = threading.Thread(
            target=self._breathing_loop,
            args=(color, speed, duration),
            daemon=True
        )
        self.breathing_thread.start()
        self.logger.info(f"Breathing effect launched: {color}, speed: {speed}")
    
    def _breathing_loop(self, color, speed, duration):
        """Внутренний цикл эффекта дыхания"""
        start_time = time.time()
        
        while self.is_breathing:
            if duration and (time.time() - start_time) > duration:
                break
            
            # Плавное увеличение яркости
            for brightness in range(0, 101, 2):
                if not self.is_breathing:
                    break
                r = color[0] * brightness / 100
                g = color[1] * brightness / 100
                b = color[2] * brightness / 100
                self.set_color(r, g, b)
                time.sleep(0.02 / speed)
            
            # Плавное уменьшение яркости
            for brightness in range(100, -1, -2):
                if not self.is_breathing:
                    break
                r = color[0] * brightness / 100
                g = color[1] * brightness / 100
                b = color[2] * brightness / 100
                self.set_color(r, g, b)
                time.sleep(0.02 / speed)
        
        self.is_breathing = False
    
    def stop_breathing(self):
        """Остановка эффекта дыхания"""
        if self.is_breathing:
            self.is_breathing = False
            if self.breathing_thread and self.breathing_thread.is_alive():
                self.breathing_thread.join(timeout=1.0)
            self.logger.info("Breathing effect stopped")
    
    def blink(self, color=(100, 0, 0), interval=0.5, count=5):
        """
        Мигание цветом
        
        Args:
            color (tuple): Цвет (R, G, B)
            interval (float): Интервал мигания в секундах
            count (int): Количество миганий
        """
        def blink_loop():
            for i in range(count):
                if not self.is_breathing:  # Используем флаг breathing для контроля
                    break
                self.set_color(*color)
                time.sleep(interval)
                self.off()
                time.sleep(interval)
        
        self.stop_breathing()
        self.is_breathing = True
        self.breathing_thread = threading.Thread(target=blink_loop, daemon=True)
        self.breathing_thread.start()
        self.logger.info(f"Flashing started: {color}, interval: {interval}s, quantity: {count}")
    
    def get_status(self):
        """Получение текущего статуса"""
        return {
            'current_color': self.current_color,
            'is_breathing': self.is_breathing,
            'pins': {
                'red': self.red_pin,
                'green': self.green_pin,
                'blue': self.blue_pin
            }
        }
    
    def cleanup(self):
        """Очистка ресурсов"""
        self.stop_breathing()
        self.off()
        
        if self.GPIO:
            try:
                self.red_pwm.stop()
                self.green_pwm.stop()
                self.blue_pwm.stop()
                self.GPIO.cleanup()
                self.logger.info("RGB module resources cleared")
            except Exception as e:
                self.logger.error(f"Error clearing resources: {e}")
    
    def __del__(self):
        """Автоматическая очистка при удалении объекта"""
        self.cleanup()
        self.logger.info("RGB module deinitialized")



# Как использовать

# # Основные операции
# rgb.set_color(*cfg.RGB_COLORS['blue'])          # Синий

# # Эффекты с разными цветами
# rgb.breathing_effect(cfg.RGB_COLORS['neon_blue'], speed=3)     # Неоновое синее дыхание
# rgb.blink(cfg.RGB_COLORS['yellow'], interval=0.2, count=5)     # Желтое мигание