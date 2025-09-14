import config as cfg
import modules.logger as logger
import modules.camera as cam
import modules.power as power
import modules.rgb_module as rgb
import modules.touch_sensor as ts
import modules.commandProcessor as cmdProcessor
import modules.cv as cv
import modules.microphone as microphone
import modules.recognition as recognition
import system.ts_funcs as ts_funcs
import system.gpio_manager as gpio_manager

def main():
    """ Инициализация логеров """
    rgb_logger = logger.Logger("RGBModule", "rgb_module.log")
    cam_logger = logger.Logger("CameraSystem", "camera.log")
    cv_logger = logger.Logger("CompVision", "cv.log")
    touch_logger = logger.Logger("TouchSensor", "touch_sensor.log")
    microphone_logger = logger.Logger("Microphone", "microphone.log")
    audio_logger = logger.Logger("AudioModule", "audio.log")
    power_logger = logger.Logger("PowerManagment", "power.log")
    recognition_logger = logger.Logger("RecognitionSystem", "recognition.log")
    cmd_logger = logger.Logger("CommandProcessor", "cmdProcessor_.log")

    """ Инициализация модулей """

    gpio_manager_main = gpio_manager.GPIOManager()

    rgb_module = rgb.KY016_RGB(
        cfg.RGB_RED_PIN, 
        cfg.RGB_GREEN_PIN, 
        cfg.RGB_BLUE_PIN, 
        rgb_logger,
        gpio_manager_main
    )
    rgb_module.breathing_effect(cfg.RGB_COLORS['calm_blue'], speed=3)

    camera = cam.Camera(logger=cam_logger)
    camera.initialize_camera()

    touch_sensor = ts.TouchSensor(
        cfg.TOUCH_SENSOR_PIN, 
        touch_logger,
        gpio_manager_main
    )
    touch_sensor.add_touch_callback(ts_funcs.ts_handle_touch)
    touch_sensor.add_long_press_callback(ts_funcs.ts_handle_long_press)
    touch_sensor.add_double_tap_callback(ts_funcs.ts_handle_double_tap)
    touch_sensor.set_long_press_duration(cfg.TOUCH_LONG_PRESS_DURATION)
    touch_sensor.set_double_tap_interval(cfg.TOUCH_DOUBLE_TAP_INTERVAL)
    touch_sensor.start_monitoring()

    power_mgmt = power.PowerManagement(i2c_bus=1, logger=power_logger)
    power_mgmt.battery_capacity = cfg.BATTERY_CAPACITY
    power_mgmt.nominal_voltage = cfg.BATTERY_NOMINAL_VOLTAGE
    power_mgmt.max_voltage = cfg.BATTERY_MAX_VOLTAGE
    power_mgmt.min_voltage = cfg.BATTERY_MIN_VOLTAGE
    power_mgmt.shutdown_voltage = cfg.BATTERY_SHUTDOWN_VOLTAGE
    power_mgmt.initialize_with_autodetect()
    power_mgmt.start_monitoring(cfg.POWER_MONITOR_INTERVAL)

    cmd_processor = cmdProcessor.CommandProcessor(logger=cmd_logger)

    recognizer = recognition.SpeechRecognition(logger=recognition_logger)
    recognizer.load_model()

    """ Завершение инициализации """
    rgb_module.stop_breathing()
    rgb_module.set_color(*cfg.RGB_COLORS['relaxing_green'])


if __name__ == "__main__":
    main()