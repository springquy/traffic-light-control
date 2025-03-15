# control.py
import socket
import json
import time
import serial

# --- Algorithm Parameters ---
alpha = 0.4            # Smoothing factor for MA (Exponential Moving Average)
lower_threshold = 1    # Lower threshold
upper_threshold = 200  # Upper threshold
T_min = 15             # Minimum green light duration (seconds)
T_max = 45             # Maximum green light duration (seconds)
yellowTime = 3         # Fixed yellow light duration (seconds)

# Initial MA values for the East-West and North-South directions
MA_eastwest = 0
MA_northsouth = 0

# Global variables for managing the data collection cycle
cycle_records = []       # List to store per-second data records during a cycle
cycle_active = False     # Flag indicating whether a data collection cycle is active
computed_signals = None  # Stores the computed signals after sufficient data is collected

# Store the initial red_time value for each direction
start_red_time_eastwest = None
start_red_time_northsouth = None

# --- Additional variables to store computed values from the previous cycle ---
last_computed_eastwest = 0
last_computed_northsouth = 0

# Global Serial object for communication with Arduino
arduino_ser = None

def send_to_arduino(red_time, direction):
    """
    Sends data to Arduino in the format "redTime,direction\n"
    For example: "15,EW\n"
    
    Parameters:
        red_time (int): The red light time value to be sent.
        direction (str): Direction identifier ("EW" for East-West or "NS" for North-South).
    
    Note:
        This function requires an active serial connection with the Arduino.
    """
    global arduino_ser
    if arduino_ser is None:
        print("Arduino connection not open.")
        return
    cmd = f"{red_time},{direction}\n"
    try:
        arduino_ser.write(cmd.encode('utf-8'))
        print("Sent command to Arduino:", cmd.strip())
    except Exception as e:
        print("Error sending data to Arduino:", e)
    
def process_data(conn, data):
    """
    Processes incoming data from the socket connection.
    
    The function performs the following tasks:
      - Validates the input data.
      - Initiates a new data collection cycle when the red_time threshold is met.
      - Records each data entry and sends a countdown command to Arduino.
      - Once red_time reaches 1, it computes the traffic signals based on weighted traffic flows.
      - Resets the cycle after computation.
    
    Parameters:
        conn (socket.socket): The socket connection object.
        data (dict): Incoming JSON data containing red_time values and traffic counts.
    
    Returns:
        dict: A dictionary indicating the status and message or the computed signals.
    """
    global cycle_records, cycle_active, computed_signals, MA_eastwest, MA_northsouth
    global start_red_time_eastwest, start_red_time_northsouth
    global last_computed_eastwest, last_computed_northsouth

    red_time_eastwest = data.get("red_time_eastwest")
    red_time_northsouth = data.get("red_time_northsouth")

    if red_time_eastwest is None or red_time_northsouth is None:
        print("Invalid data: missing red_time for one of the directions.")
        return {"status": "ignored", "message": "Missing red_time data."}

    threshold = 15  # Minimum threshold to start a cycle

    # --- Start a New Cycle ---
    if not cycle_active and (red_time_eastwest >= threshold or red_time_northsouth >= threshold):
        cycle_active = True
        # If a computed value exists from the previous cycle and is above threshold, use it.
        start_red_time_eastwest = last_computed_eastwest if last_computed_eastwest >= threshold \
                                                         else (red_time_eastwest if red_time_eastwest >= threshold else 0)
        start_red_time_northsouth = last_computed_northsouth if last_computed_northsouth >= threshold \
                                                             else (red_time_northsouth if red_time_northsouth >= threshold else 0)
        
        # Reset computed values after using them
        last_computed_eastwest = 0
        last_computed_northsouth = 0
        
        cycle_records = []
        cycle_records.append(data)
        
        print(f"\nRecord 1: start_red_time_eastwest={start_red_time_eastwest}, start_red_time_northsouth={start_red_time_northsouth}")

        if start_red_time_eastwest >= threshold:
            send_to_arduino(start_red_time_eastwest, "EW")
        if start_red_time_northsouth >= threshold:
            send_to_arduino(start_red_time_northsouth, "NS")

        return {"status": "recording", "message": "Recorded first entry."}

    # --- Continue Recording Data ---
    if cycle_active:
        # Record data if the active direction (with red_time > 0) is within the range from the initial value down to 1.
        cond_EW = (start_red_time_eastwest != 0 and red_time_eastwest >= 1 
                   and red_time_eastwest <= start_red_time_eastwest and red_time_eastwest >= 1)
        cond_NS = (start_red_time_northsouth != 0 and red_time_northsouth >= 1 
                   and red_time_northsouth <= start_red_time_northsouth and red_time_northsouth >= 1)
        
        if cond_EW or cond_NS:
            cycle_records.append(data)
            record_num = len(cycle_records)
            print(f"Record {record_num}: red_time_eastwest={red_time_eastwest}, red_time_northsouth={red_time_northsouth}")
            
            # For each record, send a countdown command to Arduino.
            if cond_EW:
                send_to_arduino(red_time_eastwest, "EW")
            elif cond_NS:
                send_to_arduino(red_time_northsouth, "NS")
            
            # When red_time reaches 1, record the final entry and compute the signals.
            if (cond_EW and red_time_eastwest == 1) or (cond_NS and red_time_northsouth == 1):
                # Calculate total traffic flow using weights (illustrative example)
                # Define weight factors for different vehicle types.
                weights = {'car': 1, 'bus': 2, 'truck': 3, 'motorcycle': 0.5}
                total_flow_east = total_flow_west = total_flow_north = total_flow_south = 0

                for record in cycle_records:
                    total_flow_east += sum(weights[k] * record.get('east', {}).get(k, 0) for k in weights)
                    total_flow_west += sum(weights[k] * record.get('west', {}).get(k, 0) for k in weights)
                    total_flow_north += sum(weights[k] * record.get('north', {}).get(k, 0) for k in weights)
                    total_flow_south += sum(weights[k] * record.get('south', {}).get(k, 0) for k in weights)
                    
                num_records = len(cycle_records)  # Total number of records collected
                flow_rate_east  = total_flow_east  / num_records if num_records > 0 else 0
                flow_rate_west  = total_flow_west  / num_records if num_records > 0 else 0
                flow_rate_north = total_flow_north / num_records if num_records > 0 else 0
                flow_rate_south = total_flow_south / num_records if num_records > 0 else 0

                flow_eastwest = flow_rate_east + flow_rate_west
                flow_northsouth = flow_rate_north + flow_rate_south

                # Update the MA values with the new flow rates
                MA_eastwest = alpha * flow_eastwest + (1 - alpha) * MA_eastwest
                MA_northsouth = alpha * flow_northsouth + (1 - alpha) * MA_northsouth

                # Clamp the MA values between lower and upper thresholds
                effective_eastwest = max(lower_threshold, min(MA_eastwest, upper_threshold))
                effective_northsouth = max(lower_threshold, min(MA_northsouth, upper_threshold))
                
                # Print MA and effective values for debugging
                print(f"MA_eastwest = {MA_eastwest}, MA_northsouth = {MA_northsouth}")
                print(f"effective_eastwest = {effective_eastwest}, effective_northsouth = {effective_northsouth}")

                total_effective = effective_eastwest + effective_northsouth
                if total_effective == 0:
                    green_eastwest = T_min
                    green_northsouth = T_min
                else:
                    green_eastwest = T_min + (T_max - T_min) * ((effective_eastwest - lower_threshold) / (upper_threshold - lower_threshold))
                    green_northsouth = T_min + (T_max - T_min) * ((effective_northsouth - lower_threshold) / (upper_threshold - lower_threshold))

                green_eastwest = max(T_min, min(int(round(green_eastwest)), T_max))
                green_northsouth = max(T_min, min(int(round(green_northsouth)), T_max))

                # Only send signals for the direction that is currently in a red state:
                if cond_EW:
                    computed_signals = {
                        "eastwest_green": green_eastwest,
                        "northsouth_red": green_eastwest + yellowTime
                    }
                    # Since North-South is red, update its new red time for the next cycle.
                    last_computed_northsouth = computed_signals["northsouth_red"]
                    print("Computed signals:", computed_signals)
                elif cond_NS:
                    computed_signals = {
                        "northsouth_green": green_northsouth,
                        "eastwest_red": green_northsouth + yellowTime
                    }
                    # Since East-West is red, update its new red time for the next cycle.
                    last_computed_eastwest = computed_signals["eastwest_red"]
                    print("Computed signals:", computed_signals)

                # Reset the cycle immediately after computation
                cycle_active = False
                cycle_records = []
                start_red_time_eastwest = 0
                start_red_time_northsouth = 0
                
                return computed_signals
            else:
                return {"status": "recording", "message": f"Recorded entry {record_num}."}
    
    print("No action taken.")
    return {"status": "waiting", "red_time_eastwest": red_time_eastwest, "red_time_northsouth": red_time_northsouth}


def main():
    """
    Main function to start the TCP server and manage the Arduino connection.
    
    The function performs the following steps:
      - Sets up a TCP socket server on localhost (port 12345).
      - Prompts the user for the COM port name to establish communication with Arduino.
      - Listens for incoming connections, receives and decodes JSON data.
      - Processes the incoming vehicle data and sends back the computed result.
      - Handles cleanup of socket and Arduino connection on exit.
    """
    global arduino_ser
    host = 'localhost'
    port = 12345
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    print("Server started on port", port)
    
    # Prompt the user to enter the COM port name for Arduino communication (e.g., COM4)
    com_port = input("Enter COM port name (e.g., COM4): ").strip()
    baud_rate = 9600
    try:
        arduino_ser = serial.Serial(com_port, baud_rate, timeout=1)
        time.sleep(2)  # Wait for Arduino to reset after opening the port
        print("Successfully connected to Arduino on", com_port)
    except Exception as e:
        print("Unable to open Arduino port", com_port, ":", e)
        # Continue running the server without sending commands to Arduino
    
    try:
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(4096)
                if not data:
                    continue
                try:
                    vehicle_data = json.loads(data.decode())
                except Exception as e:
                    print("Error decoding JSON:", e)
                    continue
                result = process_data(conn, vehicle_data)
                response = json.dumps(result, ensure_ascii=False)
                conn.sendall(response.encode())
    except KeyboardInterrupt:
        print("Server stopped by user (Ctrl+C).")
    finally:
        s.close()
        if arduino_ser is not None:
            arduino_ser.close()
            print("Closed Arduino connection.")
        print("Server shut down.")


if __name__ == "__main__":
    main()
