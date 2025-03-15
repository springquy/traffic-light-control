# simulation.py
import random
import time
import threading
import pygame
import sys
import socket
import json

pygame.init()

# -------------------------
# PARAMETERS
# -------------------------
yellowTime = 3  # Fixed yellow light duration (seconds)

# Traffic signal variables (initially set with NS red and EW green; later updated from the server)
EWgreen = 15
EWyellow = 0
EWred = 0

NSgreen = 0
NSyellow = 0
NSred = 18

# Variables for controlling the traffic signal cycle
phase_start_signal = 0       # Set to 1 when a red phase cycle begins; then reset to 0
recording_red_phase = False    # True when recording data during the red phase

# Speed values for different vehicle types (pixels per frame)
speeds = {'car': 2.25, 'bus': 1.8, 'truck': 2.0, 'motorcycle': 2.5}
directionNumbers = {0: 'east', 1: 'south', 2: 'west', 3: 'north'}

# Initial coordinates for spawning vehicles (these values are adjusted after each vehicle is created)
x = {
    'east':  [0, 0, 0],
    'south': [312, 340, 368],
    'west':  [800, 800, 800],
    'north': [403, 431, 459]
}
y = {
    'east':  [403, 431, 459],
    'south': [0, 0, 0],
    'west':  [312, 340, 368],
    'north': [800, 800, 800]
}

# Lane thickness in pixels
LANE_THICKNESS = 28

# Lane center positions (do not change)
laneCenters = {
    'east':  [417, 445, 473],
    'south': [326, 354, 382],
    'west':  [326, 354, 382],
    'north': [417, 445, 473]
}

# Dictionary to keep track of vehicles on each lane for each direction
vehicles = {
    'east':  {0: [], 1: [], 2: [], 'crossed': 0},
    'south': {0: [], 1: [], 2: [], 'crossed': 0},
    'west':  {0: [], 1: [], 2: [], 'crossed': 0},
    'north': {0: [], 1: [], 2: [], 'crossed': 0}
}

# Vehicle type mapping
vehicleTypes = {0: 'car', 1: 'bus', 2: 'truck', 3: 'motorcycle'}

# Coordinates for drawing traffic signals and their timers on screen
signalCoods = [(175, 500), (265, 175), (535, 265), (505, 535)]
signalTimerCoods = [(275, 500), (265, 275), (505, 265), (505, 505)]

# Stop line positions for each direction and default stopping positions
stopLines = {
    'east': 280,
    'south': 280,
    'west': 520,
    'north': 520
}
defaultStop = {
    'east': 270,
    'south': 270,
    'west': 530,
    'north': 530
}

stoppingGap = 10  # Gap between vehicles when stopped
movingGap = 10    # Gap between vehicles while moving

# Vehicle types allowed to spawn
allowedVehicleTypes = {'car': True, 'bus': True, 'truck': True, 'motorcycle': True}
allowedVehicleTypesList = []
simulation = pygame.sprite.Group()  # Group for all vehicle sprites

# Vehicle spawn delays (in seconds)
spawn_delays = [1.0, 2.0, 3.0]
current_spawn_index = 1  # Default spawn delay is 2.0 seconds
vehicleGenerationDelay = spawn_delays[current_spawn_index]

# Vehicle multiplier: each simulated vehicle represents multiple real vehicles
vehicleMultiplier = 3

# -------------------------------------------------------------------
# FUNCTION: Count the number of vehicles on a lane based on position
# -------------------------------------------------------------------
def countVehiclesOnLane(direction, lane):
    count = 0
    if direction in ('east', 'west'):
        center = laneCenters[direction][lane]
        top = center - LANE_THICKNESS / 2
        bottom = center + LANE_THICKNESS / 2
        for v in simulation:
            if v.direction == direction and v.lane == lane:
                w, h = v.image.get_size()
                if (v.y + h > top) and (v.y < bottom):
                    count += 1
    else:
        center = laneCenters[direction][lane]
        left = center - LANE_THICKNESS / 2
        right = center + LANE_THICKNESS / 2
        for v in simulation:
            if v.direction == direction and v.lane == lane:
                w, h = v.image.get_size()
                if (v.x + w > left) and (v.x < right):
                    count += 1
    return count

# -------------------------------------------------------------------
# FUNCTION: Count vehicle types for a given direction
# -------------------------------------------------------------------
def countVehicleTypesOnDirection(direction):
    counts = {'car': 0, 'bus': 0, 'truck': 0, 'motorcycle': 0}
    for lane in (0, 1, 2):
        for v in vehicles[direction][lane]:
            if v.vehicleClass in counts:
                counts[v.vehicleClass] += 1
    return counts

# -------------------------------------------------------------------
# FUNCTION: Send/Receive traffic signal data from the control server
# -------------------------------------------------------------------
def update_signal_timings():
    global EWgreen, NSgreen, EWred, NSred, phase_start_signal
    
    directions = ['east', 'south', 'west', 'north']
    data = {}
    for d in directions:
        counts = countVehicleTypesOnDirection(d)
        # Scale the counts by the vehicle multiplier
        scaled_counts = {k: vehicleMultiplier * v for k, v in counts.items()}
        data[d] = scaled_counts
        
    # Send data based on the current phase; note that we send the simulation's red_time (managed internally)
    data["phase_start"] = phase_start_signal
    data["red_time_eastwest"] = EWred
    data["red_time_northsouth"] = NSred

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', 12345))
        s.sendall(json.dumps(data).encode())
        response = s.recv(4096)
        s.close()
        timings = json.loads(response.decode())
        # Update both green and red signal values from the control server
        new_EWgreen = timings.get("eastwest_green", None)
        new_NSgreen = timings.get("northsouth_green", None)
        new_EWred   = timings.get("eastwest_red", None)
        new_NSred   = timings.get("northsouth_red", None)
        
        # Only update if the current signals are in a waiting state (equal to 0)
        if new_EWgreen is not None and new_EWgreen >= 15 and EWgreen == 0:
            EWgreen = new_EWgreen
            NSred = new_EWred if new_EWred is not None else EWgreen + yellowTime
        if new_NSgreen is not None and new_NSgreen >= 15 and NSgreen == 0:
            NSgreen = new_NSgreen
            EWred = new_NSred if new_NSred is not None else NSgreen + yellowTime

        print("(external):", timings)
    except Exception as e:
        print("Error updating signal timings:", e)

# -------------------------------------------------------------------
# THREAD FUNCTION: Continuously update signal timings every second
# -------------------------------------------------------------------
def signal_update_thread():
    while True:
        update_signal_timings()
        time.sleep(1)

# -------------------------------------------------------------------
# CLASS: Vehicle
# Represents a vehicle sprite in the simulation.
# -------------------------------------------------------------------
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, dir_number, direction):
        super().__init__()
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.dir_number = dir_number
        self.direction = direction
        self.crossed = 0  # Flag indicating whether the vehicle has crossed the stop line

        # Load the vehicle image based on its type and direction
        path = f"images/{direction}/{vehicleClass}.png"
        self.image = pygame.image.load(path)
        rect = self.image.get_rect()

        # Set initial position based on the spawn coordinates
        self.x = x[direction][lane]
        self.y = y[direction][lane]

        # Append this vehicle to the corresponding lane list
        lane_vehicles = vehicles[direction][lane]
        lane_vehicles.append(self)

        # Determine the stopping position based on preceding vehicle in the lane
        if len(lane_vehicles) > 1:
            prev = lane_vehicles[-2]
            if prev.crossed == 0:
                if direction == 'east':
                    self.stop = prev.stop - rect.width - stoppingGap
                elif direction == 'west':
                    self.stop = prev.stop + rect.width + stoppingGap
                elif direction == 'south':
                    self.stop = prev.stop - rect.height - stoppingGap
                elif direction == 'north':
                    self.stop = prev.stop + rect.height + stoppingGap
            else:
                self.stop = defaultStop[direction]
        else:
            self.stop = defaultStop[direction]

        # Update the spawn coordinate for the next vehicle in the lane
        if direction == 'east':
            x[direction][lane] -= (rect.width + stoppingGap)
        elif direction == 'west':
            x[direction][lane] += (rect.width + stoppingGap)
        elif direction == 'south':
            y[direction][lane] -= (rect.height + stoppingGap)
        elif direction == 'north':
            y[direction][lane] += (rect.height + stoppingGap)

        simulation.add(self)

    def move(self):
        rect = self.image.get_rect()
        lane_vehicles = vehicles[self.direction][self.lane]

        margin = 50
        screen_width, screen_height = 800, 800
        # Remove the vehicle if it moves out of screen bounds (with a margin)
        if ((self.direction == 'east' and self.x > screen_width + margin) or
            (self.direction == 'west' and self.x + rect.width < -margin) or
            (self.direction == 'south' and self.y > screen_height + margin) or
            (self.direction == 'north' and self.y + rect.height < -margin)):
            simulation.remove(self)
            if self in lane_vehicles:
                lane_vehicles.remove(self)
            return

        # Movement logic based on direction and current signal state
        if self.direction == 'east':
            if self.crossed == 0:
                if (self.x + rect.width) > stopLines['east']:
                    self.crossed = 1
                if ((self.x + rect.width <= self.stop) or (EWgreen > 0 and NSyellow == 0) or EWyellow > 0):
                    self._moveForward(lane_vehicles, axis='x', step=self.speed, forward=True)
            else:
                self._moveForward(lane_vehicles, axis='x', step=self.speed, forward=True)
        elif self.direction == 'west':
            if self.crossed == 0:
                if self.x < stopLines['west']:
                    self.crossed = 1
                if ((self.x >= self.stop) or (EWgreen > 0 and NSyellow == 0) or EWyellow > 0):
                    self._moveForward(lane_vehicles, axis='x', step=-self.speed, forward=False)
            else:
                self._moveForward(lane_vehicles, axis='x', step=-self.speed, forward=False)
        elif self.direction == 'south':
            if self.crossed == 0:
                if (self.y + rect.height) > stopLines['south']:
                    self.crossed = 1
                if ((self.y + rect.height <= self.stop) or (NSgreen > 0 and EWyellow == 0) or NSyellow > 0):
                    self._moveForward(lane_vehicles, axis='y', step=self.speed, forward=True)
            else:
                self._moveForward(lane_vehicles, axis='y', step=self.speed, forward=True)
        elif self.direction == 'north':
            if self.crossed == 0:
                if self.y < stopLines['north']:
                    self.crossed = 1
                if ((self.y >= self.stop) or (NSgreen > 0 and EWyellow == 0) or NSyellow > 0):
                    self._moveForward(lane_vehicles, axis='y', step=-self.speed, forward=False)
            else:
                self._moveForward(lane_vehicles, axis='y', step=-self.speed, forward=False)

    def _moveForward(self, lane_vehicles, axis='x', step=1.0, forward=True):
        idx = lane_vehicles.index(self)
        if idx == 0:
            if axis == 'x':
                self.x += step
            else:
                self.y += step
        else:
            front_car = lane_vehicles[idx - 1]
            rect_self = self.image.get_rect()
            rect_front = front_car.image.get_rect()
            if axis == 'x':
                if forward:
                    if (self.x + rect_self.width) < (front_car.x - movingGap):
                        self.x += step
                else:
                    if self.x > (front_car.x + rect_front.width + movingGap):
                        self.x += step
            else:
                if forward:
                    if (self.y + rect_self.height) < (front_car.y - movingGap):
                        self.y += step
                else:
                    if self.y > (front_car.y + rect_front.height + movingGap):
                        self.y += step

# -------------------------------------------------------------------
# FUNCTION: Handle the traffic light cycle
# -------------------------------------------------------------------
def lightCycle():
    global EWgreen, EWyellow, EWred, NSgreen, NSyellow, NSred, yellowTime
    while True:
        # Case: North-South is green and East-West is red
        if NSgreen > 0 and EWred > 0:
            while NSgreen > 0:
                time.sleep(1)
                NSgreen -= 1
                EWred -= 1

            NSyellow = yellowTime
            EWred = yellowTime

            while NSyellow > 0:
                time.sleep(1)
                NSyellow -= 1
                EWred -= 1

        # Case: East-West is green and North-South is red
        elif EWgreen > 0 and NSred > 0:
            while EWgreen > 0:
                time.sleep(1)
                EWgreen -= 1
                NSred -= 1
                
            EWyellow = yellowTime
            NSred = yellowTime
            
            while EWyellow > 0:
                time.sleep(1)
                EWyellow -= 1
                NSred -= 1

        else:
            # If no new signals are received, wait 1 second and re-check
            time.sleep(1)

# -------------------------------------------------------------------
# FUNCTION: Create a new vehicle with random properties
# -------------------------------------------------------------------
def createVehicle():
    vehicle_type = random.choice(allowedVehicleTypesList)
    lane_number = random.randint(0, 2)
    temp = random.randint(0, 99)
    dist = [25, 50, 75, 100]
    if temp < dist[0]:
        direction_number = 0  # east
    elif temp < dist[1]:
        direction_number = 1  # south
    elif temp < dist[2]:
        direction_number = 2  # west
    else:
        direction_number = 3  # north
    dir_str = directionNumbers[direction_number]
    Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, dir_str)

# -------------------------------------------------------------------
# FUNCTION: Draw traffic signals and their timers on the screen
# -------------------------------------------------------------------
def drawSignals(screen, font, white, black, red_vert, yellow_vert, green_vert):
    for i in range(4):
        direction = directionNumbers[i]
        if direction == 'east':
            angle = 270
            if EWgreen > 0 and NSyellow == 0:
                color = 'green'
                timerVal = EWgreen
            elif EWyellow > 0:
                color = 'yellow'
                timerVal = EWyellow
            else:
                color = 'red'
                timerVal = EWred
        elif direction == 'west':
            angle = 90
            if EWgreen > 0 and NSyellow == 0:
                color = 'green'
                timerVal = EWgreen
            elif EWyellow > 0:
                color = 'yellow'
                timerVal = EWyellow
            else:
                color = 'red'
                timerVal = EWred
        elif direction == 'south':
            angle = 180
            if NSgreen > 0 and EWyellow == 0:
                color = 'green'
                timerVal = NSgreen
            elif NSyellow > 0:
                color = 'yellow'
                timerVal = NSyellow
            else:
                color = 'red'
                timerVal = NSred
        else:
            angle = 0
            if NSgreen > 0 and EWyellow == 0:
                color = 'green'
                timerVal = NSgreen
            elif NSyellow > 0:
                color = 'yellow'
                timerVal = NSyellow
            else:
                color = 'red'
                timerVal = NSred

        if color == 'green':
            img = green_vert
        elif color == 'yellow':
            img = yellow_vert
        else:
            img = red_vert

        rotated = pygame.transform.rotate(img, angle)
        screen.blit(rotated, signalCoods[i])
        txt = font.render(str(timerVal), True, white, black)
        if angle != 0:
            txt = pygame.transform.rotate(txt, angle)
        screen.blit(txt, signalTimerCoods[i])

# -------------------------------------------------------------------
# FUNCTION: Draw the counts of different vehicle types on the screen
# -------------------------------------------------------------------
def drawVehicleTypeCounts(screen, font, white, black):
    abbrev = {'car': 'C', 'bus': 'B', 'truck': 'T', 'motorcycle': 'M'}
    dirs = {'east': 'E', 'south': 'S', 'west': 'W', 'north': 'N'}
    y_offset = 100
    for d, d_abbrev in dirs.items():
        type_counts = countVehicleTypesOnDirection(d)
        line = f"{d_abbrev}: " + ", ".join([f"{abbrev[k]}{vehicleMultiplier * v}" for k, v in type_counts.items()])
        txt = font.render(line, True, white, black)
        screen.blit(txt, (10, y_offset))
        y_offset += 30

# -------------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------------
def main():
    global allowedVehicleTypesList, vehicleGenerationDelay, current_spawn_index, vehicleMultiplier
    # Build the list of allowed vehicle types based on configuration
    for i, vtype in enumerate(allowedVehicleTypes):
        if allowedVehicleTypes[vtype]:
            allowedVehicleTypesList.append(i)

    # Start the thread for receiving control data and the traffic light cycle thread
    threading.Thread(target=signal_update_thread, daemon=True).start()
    threading.Thread(target=lightCycle, daemon=True).start()

    black = (0, 0, 0)
    white = (255, 255, 255)
    screen = pygame.display.set_mode((800, 800))
    pygame.display.set_caption("Simulation")

    background = pygame.image.load('images/intersection.png')
    red_vert = pygame.image.load('images/signals/red.png')
    yellow_vert = pygame.image.load('images/signals/yellow.png')
    green_vert = pygame.image.load('images/signals/green.png')

    font = pygame.font.Font(None, 30)
    start_time = time.time()
    clock = pygame.time.Clock()

    last_spawn_time = time.time()

    while True:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    if current_spawn_index > 0:
                        current_spawn_index -= 1
                    vehicleGenerationDelay = spawn_delays[current_spawn_index]
                elif event.key == pygame.K_DOWN:
                    if current_spawn_index < len(spawn_delays) - 1:
                        current_spawn_index += 1
                    vehicleGenerationDelay = spawn_delays[current_spawn_index]
                elif event.key in [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                   pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]:
                    key_mapping = {
                        pygame.K_1: 1,
                        pygame.K_2: 2,
                        pygame.K_3: 3,
                        pygame.K_4: 4,
                        pygame.K_5: 5,
                    }
                    vehicleMultiplier = key_mapping[event.key]

        if not pygame.display.get_active():
            pygame.time.wait(100)
            continue

        current_time = time.time()
        if current_time - last_spawn_time >= vehicleGenerationDelay:
            createVehicle()
            last_spawn_time = current_time

        screen.blit(background, (0, 0))
        elapsed = int(time.time() - start_time)
        time_text = font.render(f"Time: {elapsed}s", True, white, black)
        screen.blit(time_text, (10, 10))
        
        gen_text = font.render(f"Vehicle Delay: {vehicleGenerationDelay:.1f}s", True, white, black)
        screen.blit(gen_text, (10, 40))

        # Calculate and display vehicle counts for each direction
        east_count = vehicleMultiplier * sum(countVehiclesOnLane('east', lane) for lane in (0, 1, 2))
        south_count = vehicleMultiplier * sum(countVehiclesOnLane('south', lane) for lane in (0, 1, 2))
        west_count = vehicleMultiplier * sum(countVehiclesOnLane('west', lane) for lane in (0, 1, 2))
        north_count = vehicleMultiplier * sum(countVehiclesOnLane('north', lane) for lane in (0, 1, 2))
        count_text = font.render(f"E={east_count} S={south_count} W={west_count} N={north_count}", True, white, black)
        screen.blit(count_text, (10, 70))

        drawVehicleTypeCounts(screen, font, white, black)
        drawSignals(screen, font, white, black, red_vert, yellow_vert, green_vert)

        for v in simulation:
            v.move()
            screen.blit(v.image, (v.x, v.y))

        try:
            pygame.display.update()
        except pygame.error:
            pass
        
if __name__ == "__main__":
    main()
