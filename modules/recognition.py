import os
import json
import threading
import queue
from vosk import Model, KaldiRecognizer
import pyaudio
import config as cfg

class SpeechRecognition:
    """Класс для распознавания речи с использованием Vosk"""
    
    def __init__(self, model_path=None, logger=None):
        """
        Инициализация распознавания речи
        
        Args:
            model_path (str): Путь к модели Vosk
            logger: Экземпляр логгера
        """
        self.logger = logger
        self.model_path = model_path or os.path.join(cfg.MODELS_DIR, cfg.MODEL_RU)
        
        self.model = None
        self.recognizer = None
        self.audio = None
        self.stream = None
        self.is_loaded = False
        self.is_listening = False
        self.recognition_thread = None
        self.recognition_queue = queue.Queue()
        
        self.logger.info(f"Speech recognition initialized, model path: {self.model_path}")
        
    def load_model(self):
        """
        Загрузка модели Vosk
        
        Returns:
            bool: Успешно ли загружена модель
        """
        try:
            if not os.path.exists(self.model_path):
                self.logger.error(f"Model path does not exist: {self.model_path}")
                return False
            
            self.logger.info("Loading Vosk model...")
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, 16000)
            
            # Инициализация аудио
            self.audio = pyaudio.PyAudio()
            
            self.is_loaded = True
            self.logger.info("Vosk model successfully loaded")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading Vosk model: {e}")
            self.is_loaded = False
            return False
    
    def unload_model(self):
        """
        Выгрузка модели и освобождение ресурсов
        """
        try:
            self.stop_listening()
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                
            if self.audio:
                self.audio.terminate()
                
            self.model = None
            self.recognizer = None
            self.audio = None
            self.stream = None
            self.is_loaded = False
            
            self.logger.info("Vosk model unloaded and resources freed")
            
        except Exception as e:
            self.logger.error(f"Error unloading Vosk model: {e}")
    
    def __del__(self):
        """Автоматическая выгрузка при удалении объекта"""
        self.unload_model()
        self.logger.info("Speech recognition deinitialized")
    
    def start_listening(self, callback=None):
        """
        Начало прослушивания аудио
        
        Args:
            callback: Функция обратного вызова для распознанного текста
        
        Returns:
            bool: Успешно ли начато прослушивание
        """
        if not self.is_loaded:
            self.logger.warning("Cannot start listening: model not loaded")
            return False
            
        if self.is_listening:
            self.logger.warning("Already listening")
            return False
            
        try:
            # Создаем аудиопоток
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000,
                stream_callback=self._audio_callback if callback else None
            )
            
            self.is_listening = True
            
            if callback:
                # Запускаем поток для обработки аудио с callback
                self.recognition_thread = threading.Thread(
                    target=self._recognition_loop,
                    args=(callback,),
                    daemon=True
                )
                self.recognition_thread.start()
            else:
                # Запускаем поток для добавления в очередь
                self.recognition_thread = threading.Thread(
                    target=self._audio_processing_loop,
                    daemon=True
                )
                self.recognition_thread.start()
            
            self.logger.info("Started listening to audio")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting audio listening: {e}")
            return False
    
    def stop_listening(self):
        """
        Остановка прослушивания аудио
        """
        if not self.is_listening:
            return
            
        self.is_listening = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                self.logger.error(f"Error stopping audio stream: {e}")
        
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=1.0)
        
        self.logger.info("Stopped listening to audio")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback для обработки аудиоданных
        """
        if self.recognizer.AcceptWaveform(in_data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '').strip()
            if text:
                self.recognition_queue.put(text)
        return (in_data, pyaudio.paContinue)
    
    def _recognition_loop(self, callback):
        """
        Цикл обработки распознанного текста с callback
        """
        while self.is_listening:
            try:
                text = self.recognition_queue.get(timeout=0.1)
                if text and callback:
                    callback(text)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in recognition loop: {e}")
    
    def _audio_processing_loop(self):
        """
        Цикл обработки аудио без callback (данные доступны через get_text())
        """
        while self.is_listening:
            try:
                data = self.stream.read(4000, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text:
                        self.recognition_queue.put(text)
            except Exception as e:
                self.logger.error(f"Error in audio processing loop: {e}")
                break
    
    def get_text(self, timeout=0.1):
        """
        Получение распознанного текста из очереди
        
        Args:
            timeout (float): Таймаут ожидания текста
            
        Returns:
            str: Распознанный текст или None
        """
        try:
            return self.recognition_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_queue(self):
        """
        Очистка очереди распознанного текста
        """
        while not self.recognition_queue.empty():
            try:
                self.recognition_queue.get_nowait()
            except queue.Empty:
                break
    
    def get_available_microphones(self):
        """
        Получение списка доступных микрофонов
        
        Returns:
            list: Список доступных аудиоустройств
        """
        try:
            audio = pyaudio.PyAudio()
            info = audio.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            
            microphones = []
            for i in range(num_devices):
                device_info = audio.get_device_info_by_host_api_device_index(0, i)
                if device_info.get('maxInputChannels') > 0:
                    microphones.append({
                        'index': i,
                        'name': device_info.get('name'),
                        'channels': device_info.get('maxInputChannels'),
                        'rate': device_info.get('defaultSampleRate')
                    })
            
            audio.terminate()
            return microphones
            
        except Exception as e:
            self.logger.error(f"Error getting microphone list: {e}")
            return []
