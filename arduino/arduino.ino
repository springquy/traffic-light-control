// arduino.ino

#include <ShiftRegister74HC595.h>

// Shift registers for displaying numbers
ShiftRegister74HC595<4> sr_EW(8, 9, 10);  // EW group (East-West)
ShiftRegister74HC595<4> sr_NS(11, 12, 13); // NS group (North-South)

// Binary codes for digits 0–9 (active-low configuration)
uint8_t numberB[] = {
  B11000000, // 0
  B11111001, // 1
  B10100100, // 2
  B10110000, // 3
  B10011001, // 4
  B10010010, // 5
  B10000011, // 6
  B11111000, // 7
  B10000000, // 8
  B10011000  // 9
};

// EW signal pin definitions
const int EW_green_east  = 22;
const int EW_yellow_east = 24;
const int EW_red_east    = 26;
const int EW_green_west  = 23;
const int EW_yellow_west = 25;
const int EW_red_west    = 27;

// NS signal pin definitions
const int NS_green_north  = 28;
const int NS_yellow_north = 30;
const int NS_red_north    = 32;
const int NS_green_south  = 29;
const int NS_yellow_south = 31;
const int NS_red_south    = 33;

// Turn off all EW signals
void turnOffEW() {
  digitalWrite(EW_green_east, LOW);
  digitalWrite(EW_yellow_east, LOW);
  digitalWrite(EW_red_east, LOW);
  digitalWrite(EW_green_west, LOW);
  digitalWrite(EW_yellow_west, LOW);
  digitalWrite(EW_red_west, LOW);
}

// Turn off all NS signals
void turnOffNS() {
  digitalWrite(NS_green_north, LOW);
  digitalWrite(NS_yellow_north, LOW);
  digitalWrite(NS_red_north, LOW);
  digitalWrite(NS_green_south, LOW);
  digitalWrite(NS_yellow_south, LOW);
  digitalWrite(NS_red_south, LOW);
}

/*
  displayNumberGroup:
  Displays a number (0–99) on a 7-segment module by sending a 4-byte array: [tens, ones, tens, ones].
*/
void displayNumberGroup(ShiftRegister74HC595<4>& sr, int num) {
  if (num < 0) num = 0;
  if (num > 99) num = 99;
  int tens = num / 10;
  int ones = num % 10;
  uint8_t digits[4] = { numberB[tens], numberB[ones], numberB[tens], numberB[ones] };
  sr.setAll(digits);
}

void setup() {
  Serial.begin(9600);
  
  // Initialize EW pins
  pinMode(EW_green_east, OUTPUT);
  pinMode(EW_yellow_east, OUTPUT);
  pinMode(EW_red_east, OUTPUT);
  pinMode(EW_green_west, OUTPUT);
  pinMode(EW_yellow_west, OUTPUT);
  pinMode(EW_red_west, OUTPUT);
  
  // Initialize NS pins
  pinMode(NS_green_north, OUTPUT);
  pinMode(NS_yellow_north, OUTPUT);
  pinMode(NS_red_north, OUTPUT);
  pinMode(NS_green_south, OUTPUT);
  pinMode(NS_yellow_south, OUTPUT);
  pinMode(NS_red_south, OUTPUT);
  
  // Turn off all signals and initialize displays to "00"
  turnOffEW();
  turnOffNS();
  displayNumberGroup(sr_EW, 0);
  displayNumberGroup(sr_NS, 0);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    // Expected input format: "redTime,direction"
    // Example: "15,EW" means:
    // - EW group displays redTime (red light)
    // - NS group displays (redTime - 3) (green if redTime > 3, otherwise yellow)
    int commaIndex = input.indexOf(',');
    if (commaIndex < 0) return;  // Invalid input
    
    String timeStr = input.substring(0, commaIndex);
    String dirStr  = input.substring(commaIndex + 1);
    timeStr.trim();
    dirStr.trim();
    
    int redTime = timeStr.toInt();
    if (redTime <= 0) return;  // Invalid input
    
    int oppositeTime = (redTime > 3) ? redTime - 3 : redTime;
    
    // Update signals based on the direction
    turnOffEW();
    turnOffNS();
    
    if (dirStr.equalsIgnoreCase("EW")) {
      // EW group is red; NS group shows oppositeTime
      displayNumberGroup(sr_EW, redTime);
      displayNumberGroup(sr_NS, oppositeTime);
      digitalWrite(EW_red_east, HIGH);
      digitalWrite(EW_red_west, HIGH);
      if (redTime > 3) {
        digitalWrite(NS_green_north, HIGH);
        digitalWrite(NS_green_south, HIGH);
      } else {
        digitalWrite(NS_yellow_north, HIGH);
        digitalWrite(NS_yellow_south, HIGH);
      }
    }
    else if (dirStr.equalsIgnoreCase("NS")) {
      // NS group is red; EW group shows oppositeTime
      displayNumberGroup(sr_NS, redTime);
      displayNumberGroup(sr_EW, oppositeTime);
      digitalWrite(NS_red_north, HIGH);
      digitalWrite(NS_red_south, HIGH);
      if (redTime > 3) {
        digitalWrite(EW_green_east, HIGH);
        digitalWrite(EW_green_west, HIGH);
      } else {
        digitalWrite(EW_yellow_east, HIGH);
        digitalWrite(EW_yellow_west, HIGH);
      }
    }
    // Wait for new serial data (no automatic countdown)
  }
}
