# traffic-light-control
AI-powered traffic light system that dynamically adjusts signal timing based on real-time vehicle density, reducing congestion and improving urban mobility.


## 1. Arduino Setup

- **File:** `arduino/arduino.ino`  
- **Purpose:** Controls the physical traffic lights via shift registers and 7-segment displays.  
- **Instructions:**
  1. Open `arduino.ino` in the Arduino IDE.
  2. Select the correct **Board** (e.g., Arduino Uno) and the correct **Port** (COM port on Windows or `/dev/ttyUSBx` on Linux/Mac).
  3. Upload the code to your Arduino board.

## 2. AI Vehicle Detection (Camera Scripts)

There are two scripts for AI-based vehicle detection, each designed for a different video or perspective:

- **`EWcamera.py`**: Detects vehicles traveling East-West.  
- **`NScamera.py`**: Detects vehicles traveling North-South.

**To run either script:**

1. Make sure you have the necessary Python libraries installed (see [Requirements](#requirements)).
2. Open a terminal/command prompt in the `final` folder.
3. Run:
   ```bash
   python EWcamera.py
