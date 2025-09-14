import re
import system.commandsDB as commandsDB
import system.commandsFunctions as cmdFuncs
from difflib import SequenceMatcher

class CommandProcessor:
    """Класс для обработки распознанных голосовых команд с нечетким сравнением"""
    
    def __init__(self, logger=None):
        """
        Инициализация процессора команд
        
        Args:
            logger: Экземпляр логгера
        """
        self.logger = logger
        # Регистрация обработчиков команд
        self.handlers = {
            'internet_status': cmdFuncs._handle_internet_status,
            'program_status': cmdFuncs._handle_program_status,
            'battery_status': cmdFuncs._handle_battery_status,
            'make_photo': cmdFuncs._handle_make_photo,
            'record_video': cmdFuncs._handle_record_video,
            'stop_video': cmdFuncs._handle_stop_video,
            'system_time': cmdFuncs._handle_system_time,
            'system_restart': cmdFuncs._handle_system_restart,
            'system_shutdown': cmdFuncs._handle_system_shutdown
        }
        
        # База команд с синонимами и ключевыми словами
        self.commands = commandsDB.commands
        
        self.logger.info("Command processor initialized")
    
    def similarity_ratio(self, text1, text2):
        """
        Расчет коэффициента схожести двух текстов
        
        Args:
            text1 (str): Первый текст
            text2 (str): Второй текст
            
        Returns:
            float: Коэффициент схожести (0.0-1.0)
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def contains_keywords(self, text, keywords, threshold=0.7):
        """
        Проверка содержания ключевых слов в тексте
        
        Args:
            text (str): Текст для проверки
            keywords (list): Список ключевых слов
            threshold (float): Порог схожести
            
        Returns:
            bool: True если содержит ключевые слова
        """
        text_words = text.lower().split()
        
        for keyword in keywords:
            for word in text_words:
                if self.similarity_ratio(keyword, word) >= threshold:
                    return True
        return False
    
    def matches_pattern(self, text, patterns):
        """
        Проверка соответствия текста регулярным выражениям
        
        Args:
            text (str): Текст для проверки
            patterns (list): Список регулярных выражений
            
        Returns:
            bool: True если соответствует хотя бы одному паттерну
        """
        text_lower = text.lower()
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def process_command(self, text, confidence_threshold=0.65):
        """
        Обработка распознанной команды
        
        Args:
            text (str): Распознанный текст
            confidence_threshold (float): Порог уверенности
            
        Returns:
            tuple: (command_name, confidence, original_text) или (None, 0, text)
        """
        if not text or len(text.strip()) < 2:
            return None, 0, text
        
        text_lower = text.lower().strip()
        self.logger.info(f"Command processing: '{text}'")
        
        best_match = None
        best_confidence = 0
        
        # Проверяем все команды
        for command_name, command_data in self.commands.items():
            confidence = 0
            
            # Проверка по ключевым словам
            if self.contains_keywords(text_lower, command_data['keywords']):
                confidence += 0.3
            
            # Проверка по регулярным выражениям
            if self.matches_pattern(text_lower, command_data['patterns']):
                confidence += 0.4
            
            # Дополнительная проверка на точное совпадение с общими фразами
            common_phrases = self._get_common_phrases(command_name)
            for phrase in common_phrases:
                ratio = self.similarity_ratio(text_lower, phrase)
                if ratio > confidence:
                    confidence = ratio
            
            # Если уверенность выше порога и это лучший результат
            if confidence >= confidence_threshold and confidence > best_confidence:
                best_match = command_name
                best_confidence = confidence
        
        if best_match:
            self.logger.info(f"Command recognized: {best_match} (confidence: {best_confidence:.2f})")
            return best_match, best_confidence, text
        else:
            self.logger.info(f"Command not recognized: '{text}'")
            return None, 0, text
    
    def _get_common_phrases(self, command_name):
        """
        Получение общих фраз для команды
        
        Args:
            command_name (str): Имя команды
            
        Returns:
            list: Список общих фраз
        """
        return commandsDB.phrases.get(command_name, [])
    
    def get_command_description(self, command_name):
        """
        Получение описания команды
        
        Args:
            command_name (str): Имя команды
            
        Returns:
            str: Описание команды или None
        """
        command = self.commands.get(command_name)
        return command['description'] if command else None
    
    def list_commands(self):
        """
        Получение списка всех доступных команд
        
        Returns:
            dict: Словарь с командами и их описаниями
        """
        return {name: data['description'] for name, data in self.commands.items()}
    
    def handle_voice_command(self, text):
        """
        Обработка голосовой команды
        
        Args:
            text (str): Распознанный текст
        """
        command, confidence, original = self.process_command(text)
        
        if command and command in self.handlers:
            try:
                self.handlers[command]()
                self.logger.info(f"Command executed: {command}")
            except Exception as e:
                self.logger.error(f"Command execution error {command}: {e}")
        else:
            self.logger.warning(f"Command not recognized: '{text}'")


# # Пример использования
# if __name__ == "__main__":
#     # Создание процессора команд
#     processor = CommandProcessor()
    
#     # Тестовые фразы для распознавания
#     test_phrases = [
#         "проверь интернет подключение",
#         "как работает программа",
#         "сколько заряда батареи",
#         "сделай фотографию пожалуйста",
#         "запиши видео сейчас",
#         "останови запись видео",
#         "который сейчас час",
#         "перезагрузи систему",
#         "выключи программу",
#         "непонятная команда"
#     ]
    
#     print("Тестирование обработки команд:")
#     print("=" * 50)
    
#     for phrase in test_phrases:
#         command, confidence, original = processor.process_command(phrase)
        
#         if command:
#             description = processor.get_command_description(command)
#             print(f"✅ '{phrase}' -> {command} ({confidence:.2f}) - {description}")
#         else:
#             print(f"❌ '{phrase}' -> Не распознано")
        
#         print("-" * 50)