#include <SPI.h>

const int numRows = 3;
const int numCols = 5;
const int totalTiles = numRows * numCols;

// SPI chip select pins
const int CS1 = 10; // MCP3008 #1
const int CS2 = 11; // MCP3008 #2

// Output LED pins
const int ledPins[totalTiles] = {
  2, 3, 4, 5, 6,     // Row 0
  7, 8, 14, 15, 16,  // Row 1
  17, 18, 19, 20, 21 // Row 2
};

const int pressThreshold = 20;

void setup() {
  Serial.begin(9600);
  SPI.begin();

  for (int i = 0; i < totalTiles; i++) {
    pinMode(ledPins[i], OUTPUT);
    analogWrite(ledPins[i], 0);
  }

  Serial.println("Tile test started.");
}

void loop() {
  for (int i = 0; i < totalTiles; i++) {
    int adcVal = readADC(i);
    if (adcVal > pressThreshold) {
      analogWrite(ledPins[i], 255); // Full brightness
    } else {
      analogWrite(ledPins[i], 0); // Off
    }
  }

  delay(20);
}

int readADC(int index) {
  int chip = (index < 8) ? 1 : 2;
  int channel = (index < 8) ? index : (index - 8);
  int csPin = (chip == 1) ? CS1 : CS2;

  digitalWrite(csPin, LOW);
  SPI.transfer(0x01);
  int command = 0x80 | (channel << 4);
  int highBits = SPI.transfer(command);
  int lowBits = SPI.transfer(0x00);
  digitalWrite(csPin, HIGH);

  return ((highBits & 0x03) << 8) | lowBits;
}
