# gpio_manager.py
import logging
import RPi.GPIO as GPIO

class GPIOManager:
    """Единый менеджер для управления GPIO"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPIOManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.GPIO = None
            self._initialized = True
            self._initialize_gpio()
    
    def _initialize_gpio(self):
        """Инициализация GPIO"""
        try:
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BOARD)
            self.GPIO.setwarnings(False)
            logging.info("GPIO manager initialized in BCM mode")
        except ImportError:
            logging.warning("RPi.GPIO not available, using emulation mode")
            self.GPIO = None
        except Exception as e:
            logging.error(f"GPIO initialization error: {e}")
            self.GPIO = None
    
    def setup_output(self, pin):
        """Настройка пина как выхода"""
        if self.GPIO:
            try:
                self.GPIO.setup(pin, self.GPIO.OUT)
                return True
            except Exception as e:
                logging.error(f"Pin setting error {pin} as a way out: {e}")
        return False
    
    def setup_input(self, pin, pull_up_down=None):
        """Настройка пина как входа"""
        if self.GPIO:
            try:
                if pull_up_down == "PUD_UP":
                    self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)
                elif pull_up_down == "PUD_DOWN":
                    self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=self.GPIO.PUD_DOWN)
                else:
                    self.GPIO.setup(pin, self.GPIO.IN)
                return True
            except Exception as e:
                logging.error(f"Pin setting error {pin} as an entrance: {e}")
        return False
    
    def cleanup(self):
        """Очистка всех ресурсов GPIO"""
        if self.GPIO:
            try:
                self.GPIO.cleanup()
                logging.info("GPIO resources cleared")
            except Exception as e:
                logging.error(f"GPIO Clear Error: {e}")
    
    def __del__(self):
        """Автоматическая очистка при завершении"""
        self.cleanup()
    