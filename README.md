# HTTP Garage Toggle (Home Assistant)

Home Assistant custom integration to control a garage door via **HTTP toggle**:
- `open/close` all send the same HTTP request (e.g. `GET /?switch=1`)
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

#define RelaisPin D1
#define ClosePin D3

const char* ssid = "xxxx"; // Your SSID
const char* password = "xxxxx"; // Your WiFi Password
const char* doorstatus = "";
int currentstate;
int timetoopen = 25; // Time in seconds after which the door is considered closed
unsigned long switchedtime;
unsigned long previousMillis = 0;
unsigned long pingInterval = 60000; // Ping test interval (60 seconds)
unsigned long restartInterval = 60000; // Restart check interval (60 seconds)
unsigned long lastPingTime = 0;
unsigned long lastRestartTime = 0;
const char* targetIP = "192.168.1.1"; // Pingable Device, for example your Router

ESP8266WebServer server(80);

void setup()
{
  pinMode(RelaisPin, OUTPUT);
  pinMode(ClosePin, INPUT_PULLUP);
  digitalWrite(RelaisPin, 1);

  Serial.begin(115200);
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }
  server.on("/", BuildIndex);
  server.onNotFound ( handleNotFound );
  InitialDoorStatus();
  server.begin();
}

void loop()
{
  unsigned long currentMillis = millis();

  // Überprüfen, ob das Zielgerät erreichbar ist
  if (currentMillis - lastPingTime >= pingInterval) {
    lastPingTime = currentMillis;
    if (!isTargetReachable(targetIP)) {
      // Führe einen Neustart durch
      Serial.println("Zielgerät nicht erreichbar! Führe einen Neustart durch...");
      ESP.restart();
    }
  }

  // Überprüfen, ob WiFi-Verbindung verloren ist und versuchen, sie wiederherzustellen
  if ((WiFi.status() != WL_CONNECTED) && (currentMillis - previousMillis >= pingInterval)) {
    Serial.println("Reconnecting to WiFi...");
    WiFi.disconnect();
    WiFi.reconnect();
    previousMillis = currentMillis;
  }

  server.handleClient();
  
  // Überprüfen, ob sich der Türstatus geändert hat
  int newState = digitalRead(ClosePin);
  if (newState != currentstate) {
    currentstate = newState;
    if (currentstate == LOW) { // Wenn der Türkontakt geschlossen ist (LOW)
      doorstatus = "CLOSED";
      switchedtime = currentMillis; // Aktualisiere die Zeit, zu der die Tür geschlossen wurde
    } else {
      doorstatus = "OPEN";
    }
  }

  // Überprüfen, ob die Zeit abgelaufen ist, um die Tür als geschlossen zu betrachten
  if (doorstatus == "CLOSED" && currentMillis - switchedtime >= timetoopen * 1000) {
    doorstatus = "CLOSED";
  }

  // Überprüfen, ob es Zeit ist, den Neustart-Test durchzuführen
  if (currentMillis - lastRestartTime >= restartInterval) {
    lastRestartTime = currentMillis;
    if (!isTargetReachable(targetIP)) {
      // Führe einen Neustart durch
      Serial.println("Zielgerät nicht erreichbar! Führe einen Neustart durch...");
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
    if (digitalRead(ClosePin) == HIGH) { // Wenn der Türkontakt geöffnet ist (HIGH)
      doorstatus = "CLOSING";
    }
    else if (digitalRead(ClosePin) == LOW) { // Wenn der Türkontakt geschlossen ist (LOW)
      doorstatus = "OPENING";
    }
    DoSwitch();
  }
  server.send(200, "text/html", doorstatus);
}

void InitialDoorStatus()
{
  currentstate = digitalRead(ClosePin);
  if (currentstate == LOW) { // Wenn der Türkontakt geschlossen ist (LOW)
    doorstatus = "CLOSED";
    switchedtime = millis(); // Aktualisiere die Zeit, zu der die Tür geschlossen wurde
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
## Hardware & Wiring (ESP8266)

> This wiring matches the included ESP8266 sketch (NodeMCU / Wemos D1 mini style pins).  
> Relay is triggered on **D1**, the reed/limit switch is read on **D3**.

### Bill of Materials
- ESP8266 board (e.g., Wemos D1 mini or NodeMCU)
- 1× relay module (3.3 V or 5 V, depending on your module and power)
- 1× reed switch (magnetic door contact) or a limit switch
- Wires, magnet for the reed contact, power supply

### Connections (ESP8266)
**Relay module**
- `IN` → **D1** (ESP8266)  
  (This pin is driven HIGH for ~300–1000 ms to simulate a button press.)
- `VCC` → **3.3 V** (or **5 V** if your relay module requires it)
- `GND` → **GND**

**Reed switch (door closed detection)**
- One side of the reed → **D3** (ESP8266)
- Other side of the reed → **GND**

> Your code configures `D3` with an internal pull-up (INPUT_PULLUP).  
> That means:
> - **Door fully closed** → reed **closed** → `D3` is **LOW** → status **CLOSED**  
> - **Door open** → reed **open** → `D3` is **HIGH** → status **OPEN**

**Garage opener terminals**
- Connect the relay’s **dry contacts** (COM/NO or the two screw terminals on your relay) **in parallel** to the two push-button terminals of your garage door opener.  
  The relay simply “presses” the existing button momentarily.

**Power**
- Power the ESP8266 via **USB** or a **5 V** supply (VIN).  
- Make sure **GND** is common between ESP8266, relay module, and reed switch.

### Mounting tips
- Fix the **reed switch** on the frame and the **magnet** on the door so that the contact **closes only when the door is fully shut**.
- Keep relay wiring short and away from noise sources. If your opener uses low-voltage button lines (typical), the relay’s dry contacts are safe to wire in parallel.

### How it works with this firmware
1. Home Assistant calls `GET http://<esp-ip>/?switch=1`.
2. The ESP8266 drives **D1 HIGH** briefly to toggle the door (like pressing the wall button).
3. The status page `GET /` returns text containing `Door Status: OPEN` or `Door Status: CLOSED`.
4. The integration polls that page and shows the correct cover state.

> **Note:** If you use a different ESP board or pins, adjust the defines in your sketch accordingly and re-check the wiring.

⸻
Credits / License

Inspired by / based on https://github.com/apexad/homebridge-garagedoor-command (MIT License).
MIT License – see LICENSE.
