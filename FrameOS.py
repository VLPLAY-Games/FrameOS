import config as cfg
import modules.logger as logger
import modules.camera as cam
import modules.cv as cv
import modules.rgb_module as rgb
import modules.touch_sensor as ts
import modules.microphone as microphone
import modules.recognition as recognition

def main():
    rgb_logger = logger.Logger("RGBModule", "rgb_module.log")
    cam_logger = logger.Logger("CameraSystem", "camera.log")
    cv_logger = logger.Logger("CompVision", "cv.log")
    touch_logger = logger.Logger("TouchSensor", "touch_sensor.log")
    microphone_logger = logger.Logger("Microphone", "microphone.log")
    audio_logger = logger.Logger("AudioModule", "audio.log")
    power_logger = logger.Logger("PowerManagment", "power.log")
    recognition_logger = logger.Logger("RecognitionSystem", "recognition.log")

    rgb_module = rgb.KY016_RGB(
        cfg.RGB_RED_PIN, 
        cfg.RGB_GREEN_PIN, 
        cfg.RGB_BLUE_PIN, 
        rgb_logger
    )
    rgb_module.breathing_effect(cfg.RGB_COLORS['calm_blue'], speed=3)

    camera = cam.Camera(logger=cam_logger)
    camera.initialize_camera()

    recognizer = recognition.SpeechRecognition(logger=recognition_logger)
    recognizer.load_model()

    rgb_module.stop_breathing()

if __name__ == "__main__":
    main()