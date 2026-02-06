#ifndef WEBSERVERMODULE_H
#define WEBSERVERMODULE_H

#include <Arduino.h>
#include <LittleFS.h>
#include <ESPAsyncWebServer.h>
#include <Update.h>

AsyncWebServer server(80);

class WebServerModule {
public:

    void begin() {
        Serial.println("Initializing Web Server...");
        
        if (!LittleFS.begin()) {
            Serial.println("ERROR: Failed to mount LittleFS");
            return;
        }
        
        Serial.println("LittleFS mounted successfully");

        // Сброс сессии при старте
        loggedIn = false;

        // Обработчик корневого пути
        server.on("/", HTTP_GET, [&](AsyncWebServerRequest *request){
            Serial.println("GET /");
            if (loggedIn) {
                request->redirect("/index.html");
            } else {
                request->send(LittleFS, "/login.html", "text/html");
            }
        });

        // Обработка формы входа
        server.on("/login", HTTP_POST, [&](AsyncWebServerRequest *request){
            Serial.println("POST /login");
            
            String user = "";
            String pass = "";
            
            if (request->hasParam("username", true)) {
                user = request->getParam("username", true)->value();
            }
            if (request->hasParam("password", true)) {
                pass = request->getParam("password", true)->value();
            }
            
            Serial.printf("Login attempt: user='%s', pass='%s'\n", user.c_str(), pass.c_str());

            // Сравниваем через .equals()
            if (user.equals(authUser) && pass.equals(authPass)) {
                loggedIn = true;
                Serial.println("Login successful");
                request->send(200, "text/plain", "OK");
            } else {
                loggedIn = false;
                Serial.println("Login failed");
                request->send(401, "text/plain", "Unauthorized");
            }
        });

        // Проверка аутентификации
        server.on("/check-auth", HTTP_GET, [&](AsyncWebServerRequest *request){
            if (loggedIn) {
                request->send(200, "text/plain", "OK");
            } else {
                request->send(401, "text/plain", "Unauthorized");
            }
        });

        // Выход из системы
        server.on("/logout", HTTP_GET, [&](AsyncWebServerRequest *request){
            loggedIn = false;
            request->send(200, "text/plain", "Logged out");
        });

        // OTA обновление
        server.on("/update", HTTP_POST, 
            [&](AsyncWebServerRequest *request) {
                Serial.println("POST /update");
                
                if (!loggedIn) {
                    request->send(401, "text/plain", "Unauthorized");
                    return;
                }
                
                bool success = !Update.hasError();
                AsyncWebServerResponse *response = request->beginResponse(200, "text/plain", 
                    success ? "OK" : "FAIL");
                response->addHeader("Connection", "close");
                request->send(response);
                
                if (success) {
                    Serial.println("Update successful, rebooting...");
                    delay(1000);
                    ESP.restart();
                }
            },
            [&](AsyncWebServerRequest *request, const String& filename, size_t index, uint8_t *data, size_t len, bool final) {
                if (!loggedIn) {
                    return;
                }
                
                if (!index) {
                    Serial.printf("OTA Update Start: %s\n", filename.c_str());
                    if (!Update.begin(UPDATE_SIZE_UNKNOWN, U_FLASH)) {
                        Update.printError(Serial);
                    }
                }
                
                if (Update.write(data, len) != len) {
                    Update.printError(Serial);
                }
                
                if (final) {
                    if (Update.end(true)) {
                        Serial.printf("Update Success: %u bytes written\n", index + len);
                    } else {
                        Update.printError(Serial);
                    }
                }
            }
        );

        // Обработчик для статических файлов
        server.onNotFound([&](AsyncWebServerRequest *request){
            Serial.printf("File request: %s\n", request->url().c_str());
            
            String path = request->url();
            if (path.endsWith("/")) {
                path += "index.html";
            }
            
            // Для защищенных страниц проверяем аутентификацию
            if (path != "/login.html") {
                if (!loggedIn) {
                    request->redirect("/");
                    return;
                }
            }
            
            if (LittleFS.exists(path)) {
                request->send(LittleFS, path, getContentType(path));
            } else {
                Serial.printf("File not found: %s\n", path.c_str());
                request->send(404, "text/plain", "File not found");
            }
        });

        server.begin();
        Serial.println("Async WebServer started on port 80");
    }

private:

    const String authUser = "admin";
    const String authPass = "admin";
    bool loggedIn = false;

    // Определение типа контента по расширению файла
    String getContentType(String filename) {
        if (filename.endsWith(".html")) return "text/html";
        else if (filename.endsWith(".css")) return "text/css";
        else if (filename.endsWith(".js")) return "application/javascript";
        else if (filename.endsWith(".png")) return "image/png";
        else if (filename.endsWith(".jpg") || filename.endsWith(".jpeg")) return "image/jpeg";
        else if (filename.endsWith(".gif")) return "image/gif";
        else if (filename.endsWith(".ico")) return "image/x-icon";
        else if (filename.endsWith(".txt")) return "text/plain";
        else if (filename.endsWith(".json")) return "application/json";
        return "text/plain";
    }
};

#endif
