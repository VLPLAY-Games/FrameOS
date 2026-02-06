#ifndef BOOT_H
#define BOOT_H

#include "filesys.h"
#include "../modules/wifi.h"
#include "../modules/webserver.h"

class BootLoader{
private:
    FileSystem fs;
    Wifi wifi;
    WebServerModule webser;

public:
    bool boot() {
        Serial.begin(115200);
        delay(100);
        
        Serial.println("\n=== FrameOS Booting ===");

        if (!fs.begin()) {
            Serial.println("CRITICAL: Filesystem mount failed!");
            return false;
        }
        
        Serial.println("Filesystem mounted");
        fs.listDir(LittleFS, "/", 1);
        
        Serial.println("Starting WiFi AP...");
        wifi.start_ap("FrameOS", "12345678");
        
        // Ждем инициализации WiFi
        delay(2000);
        
        Serial.println("Starting Web Server...");
        webser.begin();
        
        Serial.println("=== Boot completed ===");
        return true;
    }
};

#endif