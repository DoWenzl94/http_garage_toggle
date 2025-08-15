# HTTP Garage Toggle (Home Assistant)

Home Assistant custom integration to control a garage door via **HTTP toggle**:
- `open/close/stop` all send the same HTTP request (e.g. `GET /?switch=1`)
- Status is polled from a page containing `Door Status: OPEN|CLOSED`
- `device_class: garage`, works with HomeKit Bridge

---

## Installation via HACS

1. **Open HACS** → *Integrations* → Top right three dots → **Custom repositories**
2. Add your repository URL: https://github.com/DoWenzl94/http_garage_toggle  
   Category: `Integration`
3. Install the integration → Restart Home Assistant
4. Go to **Settings → Devices & Services → Add integration** → Search for `HTTP Garage Toggle`
5. Configure:
   - **Base URL**: e.g. `http://192.168.1.100`
   - **Toggle Path**: `/?switch=1`
   - **Status Path**: `/`
   - **Scan interval**: e.g. `35`

---

## ESP8266 Firmware Example (Arduino)

The integration expects:
- **Toggle**: `GET http://<ESP_IP>/?switch=1` → triggers the relay like a push button
- **Status**: `GET http://<ESP_IP>/` → returns text containing `Door Status: OPEN` or `Door Status: CLOSED`

> **Note:** Pin assignment may differ depending on your ESP board – please verify and adjust if necessary.  
> See wiring guide: [ESP32/ESP8266 Pinout & Wiring](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/)

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include "secrets.h" // Contains WIFI_SSID, WIFI_PASS, TARGET_IP (see below)

#define RelaisPin D1
#define ClosePin D3

const char* doorstatus = "";
int currentstate;
int timetoopen = 25; // Time in seconds after which the door is considered closed
unsigned long switchedtime;
unsigned long previousMillis = 0;
unsigned long pingInterval = 60000; // Ping test interval (60 seconds)
unsigned long restartInterval = 60000; // Restart check interval (60 seconds)
unsigned long lastPingTime = 0;
unsigned long lastRestartTime = 0;

ESP8266WebServer server(80);

void setup()
{
  pinMode(RelaisPin, OUTPUT);
  pinMode(ClosePin, INPUT_PULLUP);
  digitalWrite(RelaisPin, 1);

  Serial.begin(115200);
  
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }
  server.on("/", BuildIndex);
  server.onNotFound(handleNotFound);
  InitialDoorStatus();
  server.begin();
}

void loop()
{
  unsigned long currentMillis = millis();

  // Ping target device
  if (currentMillis - lastPingTime >= pingInterval) {
    lastPingTime = currentMillis;
    if (!isTargetReachable(TARGET_IP)) {
      Serial.println("Target not reachable! Restarting...");
      ESP.restart();
    }
  }

  // Reconnect WiFi if disconnected
  if ((WiFi.status() != WL_CONNECTED) && (currentMillis - previousMillis >= pingInterval)) {
    Serial.println("Reconnecting to WiFi...");
    WiFi.disconnect();
    WiFi.reconnect();
    previousMillis = currentMillis;
  }

  server.handleClient();
  
  // Check door status change
  int newState = digitalRead(ClosePin);
  if (newState != currentstate) {
    currentstate = newState;
    if (currentstate == LOW) {
      doorstatus = "CLOSED";
      switchedtime = currentMillis;
    } else {
      doorstatus = "OPEN";
    }
  }

  // Auto-close timeout logic
  if (doorstatus == "CLOSED" && currentMillis - switchedtime >= timetoopen * 1000) {
    doorstatus = "CLOSED";
  }

  // Restart check
  if (currentMillis - lastRestartTime >= restartInterval) {
    lastRestartTime = currentMillis;
    if (!isTargetReachable(TARGET_IP)) {
      Serial.println("Target not reachable! Restarting...");
      ESP.restart();
    }
  }
}

void DoSwitch() {
  digitalWrite(RelaisPin, 1 ^ 1);
  delay(1000);
  digitalWrite(RelaisPin, 1 ^ 0);
  switchedtime = millis();
}

void BuildIndex()
{
  server.sendHeader("Cache-Control", "no-cache");
  if (server.arg("switch") == "1")
  {
    if (digitalRead(ClosePin) == HIGH) {
      doorstatus = "CLOSING";
    }
    else if (digitalRead(ClosePin) == LOW) {
      doorstatus = "OPENING";
    }
    DoSwitch();
  }
  server.send(200, "text/html", doorstatus);
}

void InitialDoorStatus()
{
  currentstate = digitalRead(ClosePin);
  if (currentstate == LOW) {
    doorstatus = "CLOSED";
    switchedtime = millis();
  } else {
    doorstatus = "OPEN";
  }
}

void handleNotFound()
{
  server.send(404, "text/plain", "404: Not found");
}

bool isTargetReachable(const char* ip) {
  WiFiClient client;
  
  if (!client.connect(ip, 80)) {
    return false;
  }

  client.stop();
  return true;
}
```
Wiring
	•	Relay output → connect to the two push-button terminals of your garage door opener
	•	Reed switch (magnetic sensor) → mounted so it closes when the door is fully closed
	•	Common GND between ESP, relay module, and reed switch
	•	Power supply: USB or separate 5V power supply

More info on ESP32 pinout and GPIO specifics: [https://randomnerdtutorials.com/esp32-pinout-reference-gpios/](https://samela.io/blog/2022-01-02.esp32-garage-door-opener.html)

⸻
Credits / License

Inspired by / based on https://github.com/apexad/homebridge-garagedoor-command (MIT License).
MIT License – see LICENSE.
