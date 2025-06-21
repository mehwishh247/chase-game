#include <SPI.h>

const int numRows = 3;
const int numCols = 5;
const int totalTiles = numRows * numCols;

// 2D mapping table for tile pins: tilePins[row][col]
const uint8_t tilePins[3][5] = {
  {2, 3, 4, 5, 6},     // Row 0 (cols 0–4)
  {7, 8, 14, 15, 16},  // Row 1 (cols 0–4)
  {17, 18, 19, 20, 21} // Row 2 (cols 0–4)
};

// SPI chip select pins for the two MCP3008 chips
const int CS1 = 10; // MCP3008 #1
const int CS2 = 11; // MCP3008 #2

// Output LED pins (keeping for backward compatibility)
const int ledPins[totalTiles] = {
  2, 3, 4, 5, 6,     // Row 0 (cols 0–4)
  7, 8, 14, 15, 16,  // Row 1 (cols 0–4)
  17, 18, 19, 20, 21 // Row 2 (cols 0–4)
};

int brightnessValues[totalTiles]; // 0–255 for each tile
unsigned long lastPressTime[totalTiles]; // for debounce
const int debounceDelay = 300; // milliseconds
const int pressThreshold = 15; // ADC value threshold

// Function to map brightness string to PWM value
int mapBrightness(const String& brightness) {
  if (brightness == "bright" || brightness == "100") {
    return 255;
  } else if (brightness == "dim" || brightness == "40") {
    return 100;
  } else if (brightness == "low" || brightness == "10") {
    return 25;
  } else if (brightness == "off" || brightness == "0") {
    return 0;
  } else {
    // Try to parse as percentage (0-100)
    int percent = brightness.toInt();
    if (percent >= 0 && percent <= 100) {
      return map(percent, 0, 100, 0, 255);
    }
    return 0; // Default to off for invalid values
  }
}

void setup() {
  Serial.begin(9600);
  SPI.begin();

  pinMode(CS1, OUTPUT);
  pinMode(CS2, OUTPUT);
  digitalWrite(CS1, HIGH); // idle high
  digitalWrite(CS2, HIGH);


  // Set LED pins as output using the 2D mapping
  for (int row = 0; row < numRows; row++) {
    for (int col = 0; col < numCols; col++) {
      int pin = tilePins[row][col];
      pinMode(pin, OUTPUT);
      analogWrite(pin, 0);
      int index = row * numCols + col;
      brightnessValues[index] = 0;
      lastPressTime[index] = 0;
    }
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
      String brightness = command.substring(10);
      int pwmValue = mapBrightness(brightness);
      for (int row = 0; row < numRows; row++) {
        for (int col = 0; col < numCols; col++) {
          int index = row * numCols + col;
          brightnessValues[index] = pwmValue;
        }
      }

    } else if (command.startsWith("light")) {
      int space1 = command.indexOf(' ');
      int space2 = command.indexOf(' ', space1 + 1);
      int space3 = command.indexOf(' ', space2 + 1);

      if (space1 != -1 && space2 != -1 && space3 != -1) {
        int row = command.substring(space1 + 1, space2).toInt();
        int col = command.substring(space2 + 1, space3).toInt();
        String brightness = command.substring(space3 + 1);

        if (row >= 0 && row < numRows && col >= 0 && col < numCols) {
          int pwmValue = mapBrightness(brightness);
          int index = row * numCols + col;
          brightnessValues[index] = pwmValue;
        }
      }
    }
  }
}

void updateLEDs() {
  for (int row = 0; row < numRows; row++) {
    for (int col = 0; col < numCols; col++) {
      int pin = tilePins[row][col];
      int index = row * numCols + col;
      analogWrite(pin, brightnessValues[index]);
    }
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
