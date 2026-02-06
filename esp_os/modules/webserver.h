#ifndef WEBSERVERMODULE_H
#define WEBSERVERMODULE_H

#include <Arduino.h>
#include <LittleFS.h>
#include <ESPAsyncWebServer.h>
#include <Update.h>

class WebServerModule {
public:
    WebServerModule() : server(80) {}

    void begin() {
        if (!LittleFS.begin()) {
            Serial.println("Failed to mount LittleFS");
            return;
        }

        // Сброс сессии при старте
        loggedIn = false;

        // Страница логина
        server.on("/", HTTP_GET, [&](AsyncWebServerRequest *request){
            if (loggedIn) {
                request->redirect("/index.html");
            } else {
                request->send(LittleFS, "/login.html", "text/html");
            }
        });

        // Обработка формы входа
        server.on("/login", HTTP_POST, [&](AsyncWebServerRequest *request){
            String user = getParam(request, "username");
            String pass = getParam(request, "password");

            if (user == authUser && pass == authPass) {
                loggedIn = true;
                request->redirect("/index.html");
            } else {
                request->send(200, "text/html", "<h2>Login failed</h2><a href='/'>Try again</a>");
            }
        });

        // Страница index
        server.on("/index.html", HTTP_GET, [&](AsyncWebServerRequest *request){
            if (!loggedIn) { request->redirect("/"); return; }
            request->send(LittleFS, "/index.html", "text/html");
        });

        // Страница ESP32
        server.on("/esp32", HTTP_GET, [&](AsyncWebServerRequest *request){
            if (!loggedIn) { request->redirect("/"); return; }
            request->send(LittleFS, "/esp32.html", "text/html");
        });

        // OTA
        server.on("/update", HTTP_POST,
            [&](AsyncWebServerRequest *request){
                if (!loggedIn) { request->redirect("/"); return; }

                bool ok = !Update.hasError();
                request->send(200, "text/plain",
                              ok ? "Update OK. Rebooting..." : "Update Failed");

                delay(500);
                if (ok) ESP.restart();
            },
            [&](AsyncWebServerRequest *request, String filename, size_t index, uint8_t *data, size_t len, bool final){
                if (index == 0) {
                    Serial.printf("OTA start: %s\n", filename.c_str());
                    if (!Update.begin(UPDATE_SIZE_UNKNOWN)) Update.printError(Serial);
                }

                if (Update.write(data, len) != len) Update.printError(Serial);

                if (final) {
                    if (Update.end(true)) Serial.println("OTA success");
                    else Update.printError(Serial);
                }
            }
        );

        server.begin();
        Serial.println("Async WebServer started");
    }

private:
    AsyncWebServer server;

    const char* authUser = "admin";
    const char* authPass = "admin";
    bool loggedIn = false;

    String getParam(AsyncWebServerRequest *request, const char* name) {
        if (request->hasParam(name, true)) {
            return request->getParam(name, true)->value();
        }
        return "";
    }
};

#endif
