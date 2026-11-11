#include <Arduino.h>
#include <WiFi.h>
#include <WiFiAP.h>
#include <WiFiUdp.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <WebSerial.h>
#include <SCServo.h>
#include <cstring>

SCSCL sc;

AsyncWebServer server(80);
const uint16_t HAND_TCP_PORT = 8765;
WiFiServer handServer(HAND_TCP_PORT);
WiFiClient handClient;
String jointCommandBuffer;   // network (TCP) joint-command stream
String consoleCommandBuffer; // Serial / WebSerial console (gestures + manual lines)
// UDP command path (:8766). Same ASCII lines as TCP, one line per datagram, no connection.
// Why it exists: measured on the robot WiFi, the hand link loses 12-25% of packets with 1.5 s holes.
// Over TCP every lost setpoint is RETRANSMITTED (rto backed off to 680 ms, cwnd 2) and delivered
// seconds late, so the fingers freeze and then jump to a stale target. A setpoint stream wants the
// opposite: lose it, forget it, act on the next one. UDP gives exactly that — a hole costs the
// steps inside it and nothing more. TCP on :8765 is kept for old hosts and for `nc` debugging.
// "Q" in a datagram gets "K:<uptime ms>" back to the sender, so a host can prove the firmware is
// listening before it trusts fire-and-forget (UDP would otherwise fail silently).
const uint16_t HAND_UDP_PORT = 8766;
WiFiUDP handUdp;
String udpCommandBuffer;
const size_t COMMAND_BUFFER_LIMIT = 160;
const int STREAM_DEFAULT_SPEED = 900;

// WiFi credentials. Put the real ones in secrets.h beside this sketch (not tracked by git):
//   #define WIFI_SSID "..."
//   #define WIFI_PASSWORD "..."
//   #define AP_PASSWORD "..."      // optional: the fallback access point's
#if __has_include("secrets.h")
#include "secrets.h"
#endif
#ifndef WIFI_SSID
#define WIFI_SSID "YOUR_WIFI_SSID"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#endif
#ifndef AP_PASSWORD
#define AP_PASSWORD "CHANGE_ME_8CHARS"
#endif
const char* ssid = WIFI_SSID;                   // the network the hand joins
const char* password = WIFI_PASSWORD;
const char* apSsid = "HANDY";                   // its own access point when that network is absent
const char* apPassword = AP_PASSWORD;

unsigned long last_print_time = millis();

// the uart used to control servos.
// GPIO 18 - S_RXD, GPIO 19 - S_TXD, as default.
#define S_RXD 18
#define S_TXD 19

// the IIC used to control OLED screen.
// GPIO 21 - S_SDA, GPIO 22 - S_SCL, as default.
#define S_SCL 22
#define S_SDA 21

// the GPIO used to control RGB LEDs.
// GPIO 23, as default.
#define RGB_LED 23
#define NUMPIXELS 2

// Side
int Side = 1;  // replace "1" by "2" for left hand

//Speed
int MaxSpeed = 1000;
int CloseSpeed = 750;

//Fingers middle poses
int MiddlePos[8] = { 520, 511, 500, 490, 515, 520, 480, 511 };  // replace values by your calibration results

//Servo control
float Step = 0.293;  // 300°/1024

bool APMode = false;

#include "RGB_CTRL.h"
#include "SCREEN_CTRL.h"
#include "HAND_CTRL.h"

void handleIncomingByte(char c, String& buffer);
void processCommandBuffer(const String& line);
bool parseJointCommand(const String& payload);
void applyJointTargets(const float* offsets, size_t count, int speed);
bool isGestureCommand(char c);

void setup() {
  Wire.begin(S_SDA, S_SCL);
  InitScreen();
  screenUpdate("Screen: OK!", 2);

  InitRGB();
  RGBcolor(100, 0, 100);
  screenUpdate("RGB: OK!", 2);

  Serial.begin(115200);
  screenUpdate("Serial: OK!", 2);

  Serial1.begin(1000000, SERIAL_8N1, S_RXD, S_TXD);
  sc.pSerial = &Serial1;
  screenUpdate("Servos: OK!", 2);

  // Connect to Wifi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  // Start an AP if the connection failed
  if (WiFi.waitForConnectResult() != WL_CONNECTED) {
    APMode = true;
    screenUpdate("WiFi Failed!\n", 2);
    WiFi.softAP(apSsid, apPassword);
  }

  // Display the IP on the screen
  if (APMode) {
    screenUpdate("WIFI UP!", 2);
    screenUpdate(WiFi.softAPIP().toString(), 1);
  } else {
    // Once connected, print IP
    screenUpdate("WIFI UP!", 2);
    screenUpdate(WiFi.localIP().toString(), 1);
  }

  server.on("/", HTTP_GET, [](AsyncWebServerRequest* request) {
    request->send(200, "text/plain", "Hi! This is WebSerial demo. You can access webserial interface at http://" + WiFi.localIP().toString() + "/webserial");
  });

  // WebSerial is accessible at "<IP Address>/webserial" in browser
  WebSerial.begin(&server);

  /* Attach Message Callback */
  WebSerial.onMessage([&](uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; i++) {
      handleIncomingByte(static_cast<char>(data[i]), consoleCommandBuffer);
    }
  });

  // Start server
  server.begin();
  handServer.begin();
  handServer.setNoDelay(true);
  handUdp.begin(HAND_UDP_PORT);

  // Wait, turn off leds, and update the screen.
  delay(1000);
  RGBALLoff();
  screenUpdate("Lets Go!", 2);
}

void loop() {
  // Print every 5 seconds (non-blocking)
  if ((unsigned long)(millis() - last_print_time) > 5000) {
    WebSerial.print(F("IP address: "));
    WebSerial.println(WiFi.localIP());
    WebSerial.printf("Uptime: %lums\n", millis());
    WebSerial.printf("Free heap: %" PRIu32 "\n", ESP.getFreeHeap());
    last_print_time = millis();
  }

  WebSerial.loop();

  // UDP: each datagram is one command line (or a bare "Q" liveness probe). Drain everything that
  // arrived since the last loop; only the LAST line matters for a setpoint stream, but each is
  // cheap, and applying them in order keeps "J:" semantics identical to the TCP path.
  for (int len = handUdp.parsePacket(); len > 0; len = handUdp.parsePacket()) {
    char pkt[COMMAND_BUFFER_LIMIT + 1];
    int n = handUdp.read(pkt, COMMAND_BUFFER_LIMIT);
    if (n <= 0) continue;
    pkt[n] = '\0';
    // liveness probe: "Q" (optionally newline-terminated) -> "K:<uptime ms>\n" back to the sender
    if ((n == 1 || (n == 2 && pkt[1] == '\n') || (n == 3 && pkt[1] == '\r' && pkt[2] == '\n')) && pkt[0] == 'Q') {
      handUdp.beginPacket(handUdp.remoteIP(), handUdp.remotePort());
      handUdp.printf("K:%lu\n", millis());
      handUdp.endPacket();
      continue;
    }
    udpCommandBuffer = "";              // a datagram never continues a previous one
    for (int i = 0; i < n; ++i) handleIncomingByte(pkt[i], udpCommandBuffer);
    if (udpCommandBuffer.length() > 0) handleIncomingByte('\n', udpCommandBuffer);  // unterminated line
  }

  if (!handClient || !handClient.connected()) {
    WiFiClient candidate = handServer.available();
    if (candidate) {
      if (handClient) {
        handClient.stop();
      }
      handClient = candidate;
      handClient.setNoDelay(true);
      jointCommandBuffer = "";  // drop any stale partial line from a previous client
      WebSerial.println(F("Joint client connected"));
    }
  } else {
    while (handClient.available()) {
      char c = static_cast<char>(handClient.read());
      handleIncomingByte(c, jointCommandBuffer);
    }
    if (!handClient.connected()) {
      handClient.stop();
      WebSerial.println(F("Joint client disconnected"));
    }
  }

  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    handleIncomingByte(inChar, consoleCommandBuffer);
  }
}
