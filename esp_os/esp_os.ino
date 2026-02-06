#include <Arduino.h>

#include "core/filesys.h"
#include "core/timer.h"

#include "modules/wifi.h"
#include "modules/webserver.h"

#include "core/boot.h"

void setup() {
    BootLoader bl;
    if (!bl.boot()) {
      Serial.println("CRITICAL ERROR while booting");
      while (1);
    }
}

void loop() {

}