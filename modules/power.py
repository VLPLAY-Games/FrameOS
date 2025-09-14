import config as cfg
import time
import threading
import smbus
import os
import RPi.GPIO as GPIO
from ina219 import INA219
from ina219 import DeviceRangeError
import system.gpio_manager as gpio_manager


class PowerManagement:
    """Класс для управления питанием и мониторинга батареи 18650 с INA219"""
    
    def __init__(self, i2c_bus=1, logger=None):
        """
        Инициализация power management с использованием единого GPIO менеджера
        """
        self.logger = logger
        self.i2c_bus = i2c_bus
        
        # Используем единый менеджер GPIO
        self.gpio_manager = gpio_manager.GPIOManager()
        self.GPIO = self.gpio_manager.GPIO
        
        self.ina219 = None
        self.monitoring = False
        self.monitor_thread = None
        
        # Параметры батареи 18650 3400mAh
        self.battery_capacity = 3400
        self.nominal_voltage = 3.7
        self.max_voltage = 4.2
        self.min_voltage = 3.0
        self.shutdown_voltage = 3.2
        
        # Текущие показания
        self.voltage = 0.0
        self.current = 0.0
        self.power = 0.0
        self.capacity_remaining = 0.0
        self.percentage = 0.0
        self.charging = False
        
        # Статистика
        self.start_time = time.time()
        self.energy_consumed = 0.0
        self.uptime = 0.0
        
        self.logger.info(f"Power management initialized, I2C bus: {i2c_bus}")

    
    def initialize_ina219(self):
        """
        Инициализация датчика INA219 с явным указанием I2C шины
        
        Returns:
            bool: Успешно ли инициализирован датчик
        """
        try:
            
            # Явно указываем I2C шину
            self.ina219 = INA219(
                shunt_ohms=0.1,
                max_expected_amps=2.0,
                address=0x40,
                busnum=self.i2c_bus  # Явно указываем номер шины
            )
            
            self.ina219.configure(
                voltage_range=self.ina219.RANGE_32V,
                gain=self.ina219.GAIN_AUTO,
                bus_adc=self.ina219.ADC_128SAMP,
                shunt_adc=self.ina219.ADC_128SAMP
            )
            
            # Тестовое чтение для проверки подключения
            test_voltage = self.ina219.voltage()
            self.logger.info(f"INA219 initialized successfully, voltage: {test_voltage}V")
            return True
            
        except ImportError:
            self.logger.warning("INA219 library not available, using emulation mode")
            return False
        except Exception as e:
            self.logger.error(f"INA219 initialization error: {e}")
            return False
    
    def detect_i2c_bus(self):
        """
        Автоматическое определение доступной I2C шины
        
        Returns:
            int: Номер I2C шины или None если не найдена
        """
        try:
            # Проверяем существующие I2C шины
            for bus in [1, 0, 2, 3, 4, 5, 6, 7]:
                if os.path.exists(f'/dev/i2c-{bus}'):
                    self.logger.info(f"I2C bus detected: {bus}")
                    return bus
            return None
        except Exception as e:
            self.logger.error(f"I2C bus detection error: {e}")
            return None
    
    def initialize_with_autodetect(self):
        """
        Инициализация с автоматическим определением I2C шины
        
        Returns:
            bool: Успешно ли инициализирован датчик
        """
        detected_bus = self.detect_i2c_bus()
        if detected_bus is not None:
            self.i2c_bus = detected_bus
            return self.initialize_ina219()
        else:
            self.logger.error("I2C шины не обнаружены")
            return False
    
    def read_sensors(self):
        """
        Чтение показаний с датчиков
        
        Returns:
            bool: Успешно ли прочитаны данные
        """
        try:
            if self.ina219:
                # Чтение напряжений и токов
                self.voltage = self.ina219.voltage()
                self.current = self.ina219.current() / 1000.0  # mA to A
                self.power = self.ina219.power() / 1000.0     # mW to W
                
                # Определение статуса зарядки
                self.charging = self.current > 0.01  # Ток > 10mA считается зарядкой
                
                # Расчет оставшейся емкости (упрощенный)
                self._calculate_capacity()
                
                return True
            else:
                # Эмуляция для тестирования
                self.voltage = 3.8 + (time.time() % 10) * 0.02
                self.current = 0.15 if time.time() % 20 > 10 else -0.3
                self.power = self.voltage * abs(self.current)
                self.charging = self.current > 0
                self._calculate_capacity()
                return True
                
        except Exception as e:
            self.logger.error(f"Sensor reading error: {e}")
            return False
    
    def _calculate_capacity(self):
        """Расчет оставшейся емкости и процента заряда"""
        # Процент заряда на основе напряжения (линейная аппроксимация)
        voltage_range = self.max_voltage - self.min_voltage
        voltage_percentage = (self.voltage - self.min_voltage) / voltage_range
        self.percentage = max(0, min(100, voltage_percentage * 100))
        
        # Оставшаяся емкость
        self.capacity_remaining = (self.percentage / 100) * self.battery_capacity
    
    def get_battery_status(self):
        """
        Получение статуса батареи
        
        Returns:
            dict: Информация о состоянии батареи
        """
        return {
            'voltage': round(self.voltage, 2),
            'current': round(self.current, 3),
            'power': round(self.power, 2),
            'percentage': round(self.percentage, 1),
            'capacity_remaining': round(self.capacity_remaining, 0),
            'charging': self.charging,
            'uptime': round(time.time() - self.start_time, 0)
        }
    
    def start_monitoring(self, interval=5.0):
        """
        Запуск мониторинга питания в фоновом режиме
        
        Args:
            interval (float): Интервал мониторинга в секундах
        """
        if self.monitoring:
            self.logger.warning("Monitoring has already started")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        self.logger.info(f"Power monitoring started at interval {interval}s")
    
    def stop_monitoring(self):
        """
        Остановка мониторинга питания
        """
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        self.logger.info("Power monitoring stopped")
    
    def _monitor_loop(self, interval):
        """
        Цикл мониторинга питания
        """
        last_update = time.time()
        
        while self.monitoring:
            try:
                if self.read_sensors():
                    # Обновление статистики энергопотребления
                    current_time = time.time()
                    time_diff = current_time - last_update
                    self.energy_consumed += (self.power * time_diff) / 3600  # Wh
                    last_update = current_time
                    self.uptime = current_time - self.start_time
                    
                    # Проверка критического уровня заряда
                    if self.voltage <= self.shutdown_voltage and not self.charging:
                        self.logger.warning(f"Critical battery level: {self.voltage}V")
                        self._handle_low_battery()
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
                time.sleep(interval)
    
    def _handle_low_battery(self):
        """
        Обработка низкого уровня заряда батареи
        """
        # Здесь можно добавить логику безопасного выключения
        self.logger.critical("LOW BATTERY! Power off recommended.")
        
        # Пример: отправка уведомления или запуск процедуры выключения
        # self.initiate_shutdown()
    
    def initiate_shutdown(self, delay=30):
        """
        Инициация безопасного выключения системы
        
        Args:
            delay (int): Задержка перед выключением в секундах
        """
        self.logger.warning(f"Shutdown initiated via {delay} sec")
        
        # Здесь можно добавить код для безопасного выключения
        # Например: сохранение состояния, закрытие соединений и т.д.
        
        def shutdown():
            time.sleep(delay)
            self.logger.critical("SYSTEM SHUTDOWN")
            # os.system("sudo shutdown -h now")
        
        shutdown_thread = threading.Thread(target=shutdown, daemon=True)
        shutdown_thread.start()
    
    def get_power_consumption_stats(self):
        """
        Получение статистики энергопотребления
        
        Returns:
            dict: Статистика энергопотребления
        """
        return {
            'energy_consumed_wh': round(self.energy_consumed, 2),
            'uptime_hours': round(self.uptime / 3600, 1),
            'average_power_w': round(self.energy_consumed * 3600 / self.uptime, 2) if self.uptime > 0 else 0,
            'estimated_remaining_hours': round((self.capacity_remaining / 1000 * self.nominal_voltage) / 
                                            (self.energy_consumed * 3600 / self.uptime), 1) if self.uptime > 0 and self.energy_consumed > 0 else 0
        }
    
    def estimate_remaining_time(self):
        """
        Оценка оставшегося времени работы
        
        Returns:
            float: Оставшееся время в часах
        """
        if not self.charging and self.current > 0:
            # Расчет на основе текущего потребления
            current_consumption_a = abs(self.current)
            if current_consumption_a > 0:
                remaining_hours = (self.capacity_remaining / 1000) / current_consumption_a
                return max(0, round(remaining_hours, 1))
        return 0.0
    
    def is_charging(self):
        """
        Проверка статуса зарядки
        
        Returns:
            bool: True если заряжается, False если разряжается
        """
        return self.charging
    
    def is_battery_low(self):
        """
        Проверка низкого уровня заряда
        
        Returns:
            bool: True если уровень заряда низкий
        """
        return self.voltage <= self.shutdown_voltage and not self.charging
    
    def cleanup(self):
        """
        Очистка ресурсов
        """
        self.stop_monitoring()
        self.logger.info("Power management resources cleared")
    
    def __del__(self):
        """Автоматическая очистка при удалении объекта"""
        self.cleanup()
        self.logger.info("Power management deinitialized")




# Использование

# # Инициализация
# power_mgmt = PowerManagement(power_logger)

# # Настройка параметров батареи
# power_mgmt.battery_capacity = cfg.BATTERY_CAPACITY
# power_mgmt.nominal_voltage = cfg.BATTERY_NOMINAL_VOLTAGE
# power_mgmt.max_voltage = cfg.BATTERY_MAX_VOLTAGE
# power_mgmt.min_voltage = cfg.BATTERY_MIN_VOLTAGE
# power_mgmt.shutdown_voltage = cfg.BATTERY_SHUTDOWN_VOLTAGE

# # Инициализация INA219
# if power_mgmt.initialize_ina219():
#     logger.info("INA219 инициализирован")
# else:
#     logger.warning("INA219 в режиме эмуляции")

# # Запуск мониторинга
# power_mgmt.start_monitoring(cfg.POWER_MONITOR_INTERVAL)

# # Получение статуса в любом месте программы
# status = power_mgmt.get_battery_status()
# logger.info(f"Заряд батареи: {status['percentage']}%")

# # Проверка необходимости выключения
# if power_mgmt.is_battery_low():
#     logger.warning("Низкий уровень заряда!")
#     power_mgmt.initiate_shutdown(60)  # Выключение через 60 секунд





# # Пример использования
# if __name__ == "__main__":
    
#     # Попытка инициализации с автоопределением
#     if power_mgmt.initialize_with_autodetect():
#         print("✅ INA219 инициализирован успешно")
#     else:
#         print("⚠️  INA219 в режиме эмуляции")
    
#     try:
#         print("Демонстрация power management")
#         status = power_mgmt.get_battery_status()
#         print(f"Напряжение: {status['voltage']}V")
#         print(f"Заряд: {status['percentage']}%")
#         print(f"Ток: {status['current']}A")
        
#         # Запуск мониторинга
#         power_mgmt.start_monitoring(interval=2.0)
#         time.sleep(5)
        
#     except KeyboardInterrupt:
#         print("\nПрервано пользователем")
    
#     finally:
#         power_mgmt.cleanup()