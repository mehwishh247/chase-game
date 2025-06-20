#include <SPI.h>

const int numRows = 3;
const int numCols = 5;
const int totalTiles = numRows * numCols;

// SPI chip select pins for the two MCP3008 chips
const int CS1 = 10; // MCP3008 #1
const int CS2 = 11; // MCP3008 #2

// Output LED pins
const int ledPins[totalTiles] = {
  2, 3, 4, 5, 6,     // Row 0 (cols 0–4)
  7, 8, 14, 15, 16,  // Row 1 (cols 0–4)
  17, 18, 19, 20, 21 // Row 2 (cols 0–4)
};

int brightnessValues[totalTiles]; // 0–255 for each tile
unsigned long lastPressTime[totalTiles]; // for debounce
const int debounceDelay = 300; // milliseconds
const int pressThreshold = 15; // ADC value threshold

void setup() {
  Serial.begin(9600);
  SPI.begin();

  // Set LED pins as output
  for (int i = 0; i < totalTiles; i++) {
    pinMode(ledPins[i], OUTPUT);
    analogWrite(ledPins[i], 0);
    brightnessValues[i] = 0;
    lastPressTime[i] = 0;
  }

  Serial.println("Arduino ready.");
}

void loop() {
  handleSerialCommands();
  readFSRsAndSendPressed();
  updateLEDs();
}

void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.startsWith("light_all")) {
      int brightness = command.substring(10).toInt();
      brightness = constrain(map(brightness, 0, 100, 0, 255), 0, 255);
      for (int i = 0; i < totalTiles; i++) {
        brightnessValues[i] = brightness;
      }

    } else if (command.startsWith("light")) {
      int space1 = command.indexOf(' ');
      int space2 = command.indexOf(' ', space1 + 1);
      int space3 = command.indexOf(' ', space2 + 1);

      if (space1 != -1 && space2 != -1 && space3 != -1) {
        int row = command.substring(space1 + 1, space2).toInt();
        int col = command.substring(space2 + 1, space3).toInt();
        int brightness = command.substring(space3 + 1).toInt();

        int index = row * numCols + col;
        if (index >= 0 && index < totalTiles) {
          brightness = constrain(map(brightness, 0, 100, 0, 255), 0, 255);
          brightnessValues[index] = brightness;
        }
      }
    }
  }
}

void updateLEDs() {
  for (int i = 0; i < totalTiles; i++) {
    analogWrite(ledPins[i], brightnessValues[i]);
  }
}

void readFSRsAndSendPressed() {
  for (int i = 0; i < totalTiles; i++) {
    int adcVal = readADC(i);
    if (adcVal > pressThreshold) {
      unsigned long now = millis();
      if (now - lastPressTime[i] > debounceDelay) {
        int row = i / numCols;
        int col = i % numCols;
        Serial.print("pressed ");
        Serial.print(row);
        Serial.print(" ");
        Serial.println(col);
        lastPressTime[i] = now;
      }
    }
  }
}

int readADC(int index) {
  int chip = (index < 8) ? 1 : 2;
  int channel = (index < 8) ? index : (index - 8);

  int csPin = (chip == 1) ? CS1 : CS2;

  digitalWrite(csPin, LOW);
  SPI.transfer(0x01); // Start bit
  int command = 0x80 | (channel << 4);
  int highBits = SPI.transfer(command);
  int lowBits = SPI.transfer(0x00);
  digitalWrite(csPin, HIGH);

  return ((highBits & 0x03) << 8) | lowBits;
}
