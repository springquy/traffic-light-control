# Intelligent Traffic Light Control System at Intersections
AI-powered traffic light system that dynamically adjusts signal timing based on real-time vehicle density, reducing congestion and improving urban mobility.

This repository contains:
1. **Arduino code** for controlling traffic lights using shift registers and 7-segment displays (`arduino.ino`).
2. **AI-based vehicle detection** scripts (`EWcamera.py` and `NScamera.py`) using YOLOv8 to count vehicles in different directions.
3. **Simulation** code (`simulation.py`) that generates traffic flow data and sends it to a controller script (`control.py`) for calculating traffic light timings.
4. **Images** and **video** files used for the simulation and AI detection demos.

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
1. Make sure you have the necessary Python libraries installed (see [Requirements](#4-Requirements)).
2. Open a terminal/command prompt in the `final` folder.
3. Run:
```bash
python EWcamera.py
```
or
```bash
python NScamera.py
```
4. The script will attempt to open the corresponding MP4 file (e.g., EWcamera.mp4 or NScamera.mp4) and show detections in real-time.
5. Press `q` to quit the video window.

## 3. Control & Simulation
- `control.py`:
  - Starts a server (TCP socket) that listens for incoming traffic data from `simulation.py`.
  - Processes the data, calculates the appropriate traffic light timings, and sends the results (including red times) to the Arduino via serial.

- `simulation.py`:
  - Simulates traffic flow at an intersection using Pygame.
  - Generates vehicle data (counts per lane) and sends it to `control.py`.
  - Receives updated signal timings and applies them in the simulation environment.

## Steps to Run
### 1. Start the Control Script:
```bash
python control.py
```
- The script will prompt you to enter the Arduino COM port (e.g., `COM4` on Windows, `/dev/ttyUSB0` on Linux).
- The server then waits for data from `simulation.py`.

### 2. Start the Simulation:
```bash
python simulation.py
```
- The simulation window opens, showing the intersection, vehicles, and traffic signals.
- It sends traffic data to `control.py`, which in turn computes new red/green light durations and sends them to the Arduino.

### 3. Observe:
- You can see real-time changes in the Pygame window.
- The Arduino traffic lights should update accordingly if connected correctly.


## 4. Requirements
All required Python packages are listed in the `requirements.txt` file. To install them all in one command, simply open a terminal in the project’s root folder and run:
```bash
pip install -r requirements.txt
```

## 5. Finding the Arduino COM Port
- On Windows, open the Device Manager and check Ports (COM & LPT) to see which COM port the Arduino is connected to (e.g., `COM3`, `COM4`, etc.).
- On Linux or Mac, the port might be something like `/dev/ttyUSB0` or `/dev/ttyACM0`.
You will be prompted for this port when running `control.py`. Enter the exact name of the port.

## 6. Running Python Scripts
In general, to run any Python file in this project:
1. Open a terminal in the `traffic-light-control-main` folder (or navigate there via `cd`).
2. Use the command:
```bash
python <script_name>.py
```
For example:
```bash
python NScamera.py
```
