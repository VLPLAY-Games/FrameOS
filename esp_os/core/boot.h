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

        if (!fs.begin()) {
            return false;
        }
        fs.listDir(LittleFS, "/", 1);
        wifi.start_ap("FrameOS", "12345678");

        webser.begin();
        wifi.get_ip_address();
        return true;
    }
};

#endif