import config as cfg
import time
import threading
import system.gpio_manager as gpio_manager

class TouchSensor:
    """Класс для работы с touch sensor TTP223"""
    
    def __init__(self, touch_pin, logger=None, gpio_manager=None):
        """
        Инициализация touch sensor с использованием единого GPIO менеджера
        """
        self.logger = logger
        self.touch_pin = touch_pin
        
        # Используем единый менеджер GPIO
        self.gpio_manager = gpio_manager
        self.GPIO = self.gpio_manager.GPIO
        
        self.is_touched = False
        self.last_touch_time = 0
        self.touch_callbacks = []
        self.long_press_callbacks = []
        self.double_tap_callbacks = []
        
        self.monitoring = False
        self.monitor_thread = None
        
        # Настройка параметров для обработки жестов
        self.long_press_duration = 1.0
        self.double_tap_interval = 0.5
        self.last_release_time = 0
        self.tap_count = 0
        
        # Настройка пина как входа с pull-down
        if self.GPIO:
            if self.gpio_manager.setup_input(touch_pin, "PUD_DOWN"):
                self.logger.info(f"Touch sensor initialized on pin: {touch_pin}")
            else:
                self.logger.error("Touch sensor pin setup error")
        else:
            self.logger.warning("GPIO not available, emulation mode used")

    
    def read_sensor(self):
        """
        Чтение состояния сенсора
        
        Returns:
            bool: True если касание detected, False если нет
        """
        if self.GPIO:
            try:
                return self.GPIO.input(self.touch_pin) == self.GPIO.HIGH
            except Exception as e:
                self.logger.error(f"Sensor reading error: {e}")
                return False
        else:
            # Эмуляция для тестирования
            return False
    
    def add_touch_callback(self, callback):
        """
        Добавление callback функции для обработки касаний
        
        Args:
            callback: Функция, которая будет вызвана при касании
        """
        self.touch_callbacks.append(callback)
        self.logger.debug("Added callback for touches")
    
    def add_long_press_callback(self, callback):
        """
        Добавление callback функции для обработки длительных нажатий
        
        Args:
            callback: Функция, которая будет вызвана при длительном нажатии
        """
        self.long_press_callbacks.append(callback)
        self.logger.debug("Added callback for long presses")
    
    def add_double_tap_callback(self, callback):
        """
        Добавление callback функции для обработки двойных нажатий
        
        Args:
            callback: Функция, которая будет вызвана при двойном нажатии
        """
        self.double_tap_callbacks.append(callback)
        self.logger.debug("Added callback for double clicks")
    
    def _execute_callbacks(self, callback_list, *args):
        """Выполнение всех callback функций в списке"""
        for callback in callback_list:
            try:
                callback(*args)
            except Exception as e:
                self.logger.error(f"Error in callback function: {e}")
    
    def start_monitoring(self):
        """
        Запуск мониторинга сенсора в фоновом режиме
        """
        if self.monitoring:
            self.logger.warning("Monitoring has already started")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Touch sensor monitoring started")
    
    def stop_monitoring(self):
        """
        Остановка мониторинга сенсора
        """
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        self.logger.info("Touch sensor monitoring stopped")
    
    def _monitor_loop(self):
        """
        Основной цикл мониторинга сенсора
        """
        touch_start_time = 0
        is_long_press_detected = False
        
        while self.monitoring:
            current_state = self.read_sensor()
            current_time = time.time()
            
            # Обнаружение начала касания
            if current_state and not self.is_touched:
                self.is_touched = True
                touch_start_time = current_time
                is_long_press_detected = False
                self.last_touch_time = current_time
                self.logger.debug("Touch detected")
                
                # Обработка двойного нажатия
                if current_time - self.last_release_time < self.double_tap_interval:
                    self.tap_count += 1
                    if self.tap_count == 2:
                        self.logger.debug("Double tap detected")
                        self._execute_callbacks(self.double_tap_callbacks)
                        self.tap_count = 0
                else:
                    self.tap_count = 1
            
            # Обнаружение окончания касания
            elif not current_state and self.is_touched:
                self.is_touched = False
                self.last_release_time = current_time
                touch_duration = current_time - touch_start_time
                self.logger.debug(f"Touch ended, duration: {touch_duration:.2f}s")
                
                # Вызов callback для обычного касания
                if not is_long_press_detected and touch_duration < self.long_press_duration:
                    self._execute_callbacks(self.touch_callbacks)
            
            # Проверка длительного нажатия
            if self.is_touched and not is_long_press_detected:
                if current_time - touch_start_time >= self.long_press_duration:
                    is_long_press_detected = True
                    self.logger.debug("Long press detected")
                    self._execute_callbacks(self.long_press_callbacks)
            
            time.sleep(0.01)  # 10ms polling interval
    
    def wait_for_touch(self, timeout=None):
        """
        Ожидание касания (блокирующий вызов)
        
        Args:
            timeout (float): Таймаут ожидания в секундах
            
        Returns:
            bool: True если касание detected, False если таймаут
        """
        start_time = time.time()
        self.logger.debug("Ожидание касания...")
        
        while timeout is None or (time.time() - start_time) < timeout:
            if self.read_sensor():
                self.logger.debug("Touch detected in wait_for_touch")
                return True
            time.sleep(0.01)
        
        self.logger.debug("Touch Wait Timeout")
        return False
    
    def get_touch_duration(self):
        """
        Получение длительности текущего касания
        
        Returns:
            float: Длительность касания в секундах, 0 если нет касания
        """
        if self.is_touched:
            return time.time() - self.last_touch_time
        return 0.0
    
    def get_status(self):
        """
        Получение текущего статуса сенсора
        
        Returns:
            dict: Информация о состоянии сенсора
        """
        return {
            'is_touched': self.is_touched,
            'touch_duration': self.get_touch_duration(),
            'monitoring': self.monitoring,
            'pin': self.touch_pin,
            'last_touch_time': self.last_touch_time
        }
    
    def set_long_press_duration(self, duration):
        """
        Установка длительности для определения длительного нажатия
        
        Args:
            duration (float): Длительность в секундах
        """
        self.long_press_duration = max(0.1, duration)
        self.logger.info(f"Long press duration is set: {duration}s")
    
    def set_double_tap_interval(self, interval):
        """
        Установка интервала для определения двойного нажатия
        
        Args:
            interval (float): Интервал в секундах
        """
        self.double_tap_interval = max(0.1, interval)
        self.logger.info(f"Double click interval is set: {interval}s")
    
    def cleanup(self):
        """
        Очистка ресурсов
        """
        self.stop_monitoring()
        
        if self.GPIO:
            try:
                self.GPIO.cleanup()
                self.logger.info("Touch sensor resources cleared")
            except Exception as e:
                self.logger.error(f"Error clearing resources: {e}")
    
    def __del__(self):
        """Автоматическая очистка при удалении объекта"""
        self.cleanup()
        self.logger.info("Touch sensor deinitialized")


# Как использовать 

# # Инициализация
# touch_sensor = TTP223_TouchSensor(
#     cfg.TOUCH_SENSOR_PIN, 
#     touch_logger
# )

# # Настройка параметров
# touch_sensor.set_long_press_duration(cfg.TOUCH_LONG_PRESS_DURATION)
# touch_sensor.set_double_tap_interval(cfg.TOUCH_DOUBLE_TAP_INTERVAL)

# # Callback функции
# def handle_touch():
#     logger.info("Короткое касание detected")
#     # Действие при коротком касании

# def handle_long_press():
#     logger.info("Длительное нажатие detected") 
#     # Действие при длительном нажатии

# def handle_double_tap():
#     logger.info("Двойное нажатие detected")
#     # Действие при двойном нажатии

# # Добавление callback
# touch_sensor.add_touch_callback(handle_touch)
# touch_sensor.add_long_press_callback(handle_long_press)
# touch_sensor.add_double_tap_callback(handle_double_tap)

# # Запуск мониторинга
# touch_sensor.start_monitoring()