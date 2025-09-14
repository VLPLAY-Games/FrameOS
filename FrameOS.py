import config as cfg
import modules.logger as logger
import modules.camera as cam
import modules.cv as cv
import modules.rgb_module as rgb
import modules.touch_sensor as ts
import modules.microphone as microphone

def main():
    cam_logger = logger.Logger("CameraSystem", "camera.log")
    rgb_logger = logger.Logger("RGBModule", "rgb_module.log")
    cv_logger = logger.Logger("CV", "cv.log")
    touch_logger = logger.Logger("TouchSensor", "touch_sensor.log")
    microphone_logger = logger.Logger("Microphone", "microphone.log")
    audio_logger = logger.Logger("AudioModule", "audio.log")
    power_logger = logger.Logger("PowerManagment", "power.log")
    # camera = cam.Camera(logger=cam_logger)
    # camera.initialize_camera()
    
    # if camera.is_camera_active:
    #     camera.capture_photo(warmup_time=1)
    #     camera.close_camera()

if __name__ == "__main__":
    main()