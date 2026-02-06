// MIT License
// Copyright (c) 2025 VL_PLAY (Vlad)
// See https://github.com/VLPLAY-Games/XenoOS/blob/main/LICENSE for details.


#ifndef TIMER_H
#define TIMER_H

class Timer {
  private:
    uint32_t start_time;  // Время старта программы в миллисекундах

  public:
    // Конструктор
    Timer() {
      start_time = millis();
    }

    // Метод для получения времени в секундах с момента старта программы
    float get_sec() {
      return (millis() - start_time) / 1000.0f; 
    }

    // Метод для получения времени в формате [0.000] (секунды и миллисекунды)
    const char* get_sec_str() {
      float seconds = (millis() - start_time) / 1000.0f;
      String time_str = "[" + String(seconds, 3) + "]";
      return time_str.c_str();
    }

    // Метод для получения времени в миллисекундах с момента старта программы
    uint32_t get_millis() {
      return millis() - start_time; 
    }

    // Метод для печати времени на экран в формате [0.000]
    void print_time() {
      Serial.print("[");
      Serial.print(get_sec());
      Serial.print("] ");
    }

    // Утилита для вывода лога с таймером и цветной обработкой
    void println_with_timer(const String& message) {
      print_time();
      Serial.println(message);
    }

    void print_with_timer(const String& message) {
      print_time();
      Serial.print(message);
    }
};

#endif