#include <Arduino.h>
#include <WiFi.h>
#include <WiFiAP.h>
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
String jointCommandBuffer;
const size_t COMMAND_BUFFER_LIMIT = 160;
const int STREAM_DEFAULT_SPEED = 900;

// Define wifi SSIDs and passwords
const char* ssid = "change me";                       // Your WiFi SSID
const char* password = "change me";  // Your WiFi Password
const char* apSsid = "HANDY";                   // Your WiFi SSID
const char* apPassword = "12345678";            // Your WiFi Password

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

void handleIncomingByte(char c);
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
      handleIncomingByte(static_cast<char>(data[i]));
    }
  });

  // Start server
  server.begin();
  handServer.begin();
  handServer.setNoDelay(true);

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

  if (!handClient || !handClient.connected()) {
    WiFiClient candidate = handServer.available();
    if (candidate) {
      if (handClient) {
        handClient.stop();
      }
      handClient = candidate;
      handClient.setNoDelay(true);
      WebSerial.println(F("Joint client connected"));
    }
  } else {
    while (handClient.available()) {
      char c = static_cast<char>(handClient.read());
      handleIncomingByte(c);
    }
    if (!handClient.connected()) {
      handClient.stop();
      WebSerial.println(F("Joint client disconnected"));
    }
  }

  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    handleIncomingByte(inChar);
  }
}
