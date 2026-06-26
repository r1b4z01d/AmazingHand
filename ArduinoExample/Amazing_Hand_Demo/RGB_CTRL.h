
// WS2812:
#include <Adafruit_NeoPixel.h>
#define BRIGHTNESS  100

int RAINBOW_STATUS = 0;

Adafruit_NeoPixel matrix = Adafruit_NeoPixel(NUMPIXELS, RGB_LED, NEO_GRB + NEO_KHZ800);


void InitRGB(){
  matrix.setBrightness(BRIGHTNESS);
  matrix.begin();
  matrix.show();
}

void colorWipe(uint8_t c, uint8_t wait) 
{
  for(uint16_t i=0; i<matrix.numPixels(); i++) {
    matrix.setPixelColor(i, c);
    matrix.show();
    delay(wait);
  }
}


void RGBALLoff(){
  colorWipe(matrix.Color(0, 0, 0), 0);
}


void setSingleLED(uint16_t LEDnum, uint32_t c)
{
  matrix.setPixelColor(LEDnum, c);
  matrix.show();
}

void RGBoff(){
  setSingleLED(0, matrix.Color(0, 0, 0));
  setSingleLED(1, matrix.Color(0, 0, 0));
}

void RGBcolor(byte Rinput, byte Ginput, byte Binput){
  setSingleLED(0, matrix.Color(Rinput, Ginput, Binput));
  setSingleLED(1, matrix.Color(Rinput, Ginput, Binput));
}


void ctrlAllLED(int totalNum, int inputR, int inputG, int inputB){
  for(int i = 0; i<totalNum; i++){
    setSingleLED(i, matrix.Color(inputR, inputG, inputB));
    delay(1);
  }
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
    return matrix.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } 
  else if(WheelPos < 170) {
    WheelPos -= 85;
    return matrix.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } 
  else {
    WheelPos -= 170;
    return matrix.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}


void rainbow(uint8_t wait) {
  uint16_t i, j;
  for(j=0; j<256; j++) {
    for(i=0; i<matrix.numPixels(); i++) {
      matrix.setPixelColor(i, Wheel((i*1+j) & 255));
    }
    matrix.show();
    if(!RAINBOW_STATUS){RGBALLoff();break;}
    delay(wait);
  }
}

void red(){RGBcolor(255, 0, 0);}
void orange(){RGBcolor(255, 127, 0);}
void yellow(){RGBcolor(255, 255, 0);}
void green(){RGBcolor(0, 255, 0);}
void springGreen(){RGBcolor(0, 255, 127);}
void cyan(){RGBcolor(0, 255, 255);}
void skyBlue(){RGBcolor(0, 127, 255);}
void blue(){RGBcolor(0, 0, 255);}
void violet(){RGBcolor(127, 0, 255);}
void magenta(){RGBcolor(255, 0, 255);}
void pink(){RGBcolor(255, 0, 127);}
void white(){RGBcolor(255, 255, 255);}
