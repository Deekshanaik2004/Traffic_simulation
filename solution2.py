import pygame
import sys
import random
import time

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 800, 800
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Traffic Intersection Simulation (with Emergency Priority & Metrics)")

# Colors
ROAD_COLOR = (50, 50, 50)
LINE_COLOR = (255, 255, 255)
BOX_COLOR = (255, 255, 0)
SIGNAL_BOX = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BG_COLOR = (34, 139, 34)
CAR_COLOR = (0, 0, 255)

# Clock
clock = pygame.time.Clock()
FPS = 60

# Directions
DIRECTIONS = ["N", "E", "S", "W"]

# Adaptive timing parameters
MIN_GREEN = 5.0      # seconds each green must last at least this long
MAX_GREEN = 30.0     # if green lasts this long, controller will consider switching anyway
STARVE_TIME = 25.0   # if a lane hasn't had green for this long, it's prioritized

SAFE_DISTANCE = 45  # Minimum distance between cars in queue
SPAWN_CHANCE = 50   # Higher number → fewer normal cars (was 20 before)
EMERGENCY_SPAWN_CHANCE = 800  # Rare emergency spawn

# Font for metrics
FONT = pygame.font.SysFont("Arial", 16)

def draw_traffic_light(x, y, active_color):
    pygame.draw.rect(SCREEN, SIGNAL_BOX, (x, y, 30, 70), border_radius=5)
    colors = [RED, YELLOW, GREEN]
    for i, color in enumerate(colors):
        light_color = color if color == active_color else (100, 100, 100)
        pygame.draw.circle(SCREEN, light_color, (x + 15, y + 10 + 25 * i), 7)

def draw_intersection():
    SCREEN.fill(BG_COLOR)

    # Roads
    pygame.draw.rect(SCREEN, ROAD_COLOR, (WIDTH // 2 - 60, 0, 120, HEIGHT))  # Vertical
    pygame.draw.rect(SCREEN, ROAD_COLOR, (0, HEIGHT // 2 - 60, WIDTH, 120))  # Horizontal

    # Yellow box
    pygame.draw.rect(SCREEN, BOX_COLOR, (WIDTH // 2 - 60, HEIGHT // 2 - 60, 120, 120), width=3)

    # Lane lines
    pygame.draw.line(SCREEN, LINE_COLOR, (WIDTH // 2 - 30, 0), (WIDTH // 2 - 30, HEIGHT), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (WIDTH // 2 + 30, 0), (WIDTH // 2 + 30, HEIGHT), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (0, HEIGHT // 2 - 30), (WIDTH, HEIGHT // 2 - 30), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (0, HEIGHT // 2 + 30), (WIDTH, HEIGHT // 2 + 30), 2)

    # Traffic lights
    for i, direction in enumerate(DIRECTIONS):
        is_active = i == light_index
        light_color = GREEN if is_active else RED

        if direction == "N":
            draw_traffic_light(WIDTH // 2 - 15, HEIGHT // 2 - 130, light_color)
        elif direction == "E":
            draw_traffic_light(WIDTH // 2 + 100, HEIGHT // 2 - 15, light_color)
        elif direction == "S":
            draw_traffic_light(WIDTH // 2 - 15, HEIGHT // 2 + 60, light_color)
        elif direction == "W":
            draw_traffic_light(WIDTH // 2 - 130, HEIGHT // 2 - 15, light_color)

class Car:
    WIDTH = 20
    HEIGHT = 40
    SPEED = 2

    def __init__(self, direction, vehicle_type="normal"):
        """
        vehicle_type: "normal", "ambulance", "fire"
        Ambulance -> white rectangular box
        Fire van -> red rectangular box
        """
        self.direction = direction
        self.vehicle_type = vehicle_type
        self.stopped = False
        self.committed = False   # flag for cars inside intersection
        self.queued_time = None  # when the car joined a queue (waiting)
        self.spawn_time = time.time()
        self.crossed = False     # whether it crossed the intersection center (counts towards throughput)

        # spawn positions depend on direction
        if direction == "N":
            # cars travel downwards (y increases)
            self.x = WIDTH // 2 - 15
            self.y = -Car.HEIGHT
        elif direction == "S":
            # cars travel upwards (y decreases)
            self.x = WIDTH // 2 + 15
            self.y = HEIGHT + Car.HEIGHT
        elif direction == "E":
            # cars travel leftwards (x decreases)
            self.x = WIDTH + Car.HEIGHT
            self.y = HEIGHT // 2 - 15
        elif direction == "W":
            # cars travel rightwards (x increases)
            self.x = -Car.HEIGHT
            self.y = HEIGHT // 2 + 15

    @property
    def is_emergency(self):
        return self.vehicle_type in ("ambulance", "fire")

    def _near_intersection_region(self):
        # determine if car is close enough to the intersection to be considered in a queue region
        cx, cy = WIDTH // 2, HEIGHT // 2
        if self.direction == "N":
            return self.y + Car.HEIGHT >= cy - 300  # within 300 px above center
        if self.direction == "S":
            return self.y - Car.HEIGHT <= cy + 300
        if self.direction == "E":
            return self.x - Car.HEIGHT <= cx + 300
        if self.direction == "W":
            return self.x + Car.HEIGHT >= cx - 300

    def will_move_this_frame(self, cars):
        """Return True if the car would move this frame according to traffic rules (without updating position)."""
        front_car = self.get_front_car(cars)
        if self.direction == "N":
            stop_line = HEIGHT // 2 - 60
            # movement condition (mirror of move())
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y + Car.HEIGHT < stop_line and self.safe_to_move(front_car)):
                return True
            return False

        elif self.direction == "S":
            stop_line = HEIGHT // 2 + 60
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y > stop_line and self.safe_to_move(front_car)):
                return True
            return False

        elif self.direction == "E":
            stop_line = WIDTH // 2 + 60
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x > stop_line and self.safe_to_move(front_car)):
                return True
            return False

        elif self.direction == "W":
            stop_line = WIDTH // 2 - 60
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x + Car.HEIGHT < stop_line and self.safe_to_move(front_car)):
                return True
            return False

    def move(self, cars):
        front_car = self.get_front_car(cars)

        # Before moving, compute whether we would move. This helps determine queued_time.
        will_move = self.will_move_this_frame(cars)

        # If car would NOT move, and it's near intersection, and it's not already recorded as queued, set queued_time.
        if not will_move and self.queued_time is None and not self.committed and self._near_intersection_region():
            # Car is effectively stopped / waiting (either due to red light or queue in front)
            self.queued_time = time.time()

        # Movement and committed handling
        if self.direction == "N":
            stop_line = HEIGHT // 2 - 60
            # mark committed when crossing stop line while allowed
            if not self.committed and self.can_pass() and self.y + Car.HEIGHT >= stop_line:
                self.committed = True
                # when committed becomes True, if queued_time exists, the wait ended now
                if self.queued_time is not None:
                    record_wait_time(self.queued_time)
                    self.queued_time = None

            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y + Car.HEIGHT < stop_line and self.safe_to_move(front_car)):
                self.y += Car.SPEED

        elif self.direction == "S":
            stop_line = HEIGHT // 2 + 60
            if not self.committed and self.can_pass() and self.y <= stop_line:
                self.committed = True
                if self.queued_time is not None:
                    record_wait_time(self.queued_time)
                    self.queued_time = None
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y > stop_line and self.safe_to_move(front_car)):
                self.y -= Car.SPEED

        elif self.direction == "E":
            stop_line = WIDTH // 2 + 60
            if not self.committed and self.can_pass() and self.x <= stop_line:
                self.committed = True
                if self.queued_time is not None:
                    record_wait_time(self.queued_time)
                    self.queued_time = None
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x > stop_line and self.safe_to_move(front_car)):
                self.x -= Car.SPEED

        elif self.direction == "W":
            stop_line = WIDTH // 2 - 60
            if not self.committed and self.can_pass() and self.x + Car.HEIGHT >= stop_line:
                self.committed = True
                if self.queued_time is not None:
                    record_wait_time(self.queued_time)
                    self.queued_time = None
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x + Car.HEIGHT < stop_line and self.safe_to_move(front_car)):
                self.x += Car.SPEED

        # Mark crossed once car passes the center box area (used to count throughput)
        if not self.crossed:
            if self.direction == "N" and self.y >= HEIGHT // 2:
                self.crossed = True
            if self.direction == "S" and self.y <= HEIGHT // 2:
                self.crossed = True
            if self.direction == "E" and self.x <= WIDTH // 2:
                self.crossed = True
            if self.direction == "W" and self.x >= WIDTH // 2:
                self.crossed = True

    def safe_to_move(self, front_car):
        if not front_car:
            return True
        if self.direction == "N":
            return front_car.y - (self.y + Car.HEIGHT) > SAFE_DISTANCE
        elif self.direction == "S":
            return self.y - (front_car.y + Car.HEIGHT) > SAFE_DISTANCE
        elif self.direction == "E":
            return self.x - (front_car.x + Car.HEIGHT) > SAFE_DISTANCE
        elif self.direction == "W":
            return front_car.x - (self.x + Car.HEIGHT) > SAFE_DISTANCE

    def get_front_car(self, cars):
        same_lane_cars = [car for car in cars if car.direction == self.direction and car != self]
        if self.direction == "N":
            same_lane_cars = [car for car in same_lane_cars if car.y > self.y]
            return min(same_lane_cars, key=lambda c: c.y, default=None)
        elif self.direction == "S":
            same_lane_cars = [car for car in same_lane_cars if car.y < self.y]
            return max(same_lane_cars, key=lambda c: c.y, default=None)
        elif self.direction == "E":
            same_lane_cars = [car for car in same_lane_cars if car.x < self.x]
            return max(same_lane_cars, key=lambda c: c.x, default=None)
        elif self.direction == "W":
            same_lane_cars = [car for car in same_lane_cars if car.x > self.x]
            return min(same_lane_cars, key=lambda c: c.x, default=None)

    def can_pass(self):
        # can pass only if its direction has green (light_index)
        return DIRECTIONS[light_index] == self.direction

    def draw(self):
        # choose color based on vehicle type
        if self.vehicle_type == "ambulance":
            color = (255, 255, 255)  # white
        elif self.vehicle_type == "fire":
            color = (200, 0, 0)  # red-ish for fire van
        else:
            color = CAR_COLOR

        if self.direction in ["N", "S"]:
            pygame.draw.rect(SCREEN, color, (self.x, self.y, Car.WIDTH, Car.HEIGHT))
        else:
            pygame.draw.rect(SCREEN, color, (self.x, self.y, Car.HEIGHT, Car.WIDTH))


cars = []

def spawn_too_close(direction):
    # Prevent spawning if another car is too close to spawn point
    for c in cars:
        if c.direction != direction:
            continue
        if direction == "N" and c.y < SAFE_DISTANCE:
            return True
        if direction == "S" and c.y > HEIGHT - SAFE_DISTANCE:
            return True
        if direction == "E" and c.x > WIDTH - SAFE_DISTANCE:
            return True
        if direction == "W" and c.x < SAFE_DISTANCE:
            return True
    return False

def spawn_car():
    """
    Spawns either a normal car (most of the time) or rarely an emergency vehicle.
    Uses SPAWN_CHANCE for normal cars and EMERGENCY_SPAWN_CHANCE for emergencies.
    """
    # First, possibly spawn an emergency vehicle (rare)
    if random.randint(0, EMERGENCY_SPAWN_CHANCE) == 0:
        direction = random.choice(DIRECTIONS)
        vehicle_type = random.choice(["ambulance", "fire"])  # randomly ambulance or fire van
        if not spawn_too_close(direction):
            cars.append(Car(direction, vehicle_type))
        return

    # Otherwise maybe spawn a normal car
    if random.randint(0, SPAWN_CHANCE) == 0:
        direction = random.choice(DIRECTIONS)
        if not spawn_too_close(direction):
            cars.append(Car(direction, "normal"))

# Adaptive controller state
light_index = 0
last_switch_time = time.time()
# track when each direction last had green (for starvation prevention)
last_served = {d: time.time() for d in DIRECTIONS}

def get_queue_counts():
    counts = {d: 0 for d in DIRECTIONS}
    for c in cars:
        counts[c.direction] += 1
    return counts

def choose_next_direction(exclude_dir=None):
    """
    Decide which direction should be green next.
    Priority rules:
      1. If any lane is starving (not served in STARVE_TIME), prioritize the starving lane with largest queue.
      2. Otherwise pick the lane with the largest queue.
      3. If all zero, keep current lane.
    If exclude_dir is set, that direction will not be selected (used to force the emergency direction to turn red after passing).
    """
    counts = get_queue_counts()
    now = time.time()

    # find starving lanes
    starving = [d for d in DIRECTIONS if now - last_served.get(d, 0) >= STARVE_TIME]
    if exclude_dir:
        starving = [d for d in starving if d != exclude_dir]
    if starving:
        best = max(starving, key=lambda d: counts.get(d, 0))
        return DIRECTIONS.index(best)

    # otherwise pick lane with highest queue
    if counts:
        max_count = max(counts.values())
    else:
        max_count = 0

    if max_count == 0:
        return light_index  # keep current when no cars anywhere

    best_dirs = [d for d, cnt in counts.items() if cnt == max_count]
    if exclude_dir:
        best_dirs = [d for d in best_dirs if d != exclude_dir]
        if not best_dirs:
            # pick first non-excluded direction
            for d in DIRECTIONS:
                if d != exclude_dir:
                    return DIRECTIONS.index(d)
            return light_index

    current_dir = DIRECTIONS[light_index]
    if current_dir in best_dirs:
        return light_index

    return DIRECTIONS.index(best_dirs[0])

# Emergency override state
emergency_override = False
emergency_direction = None  # string like "N","E"... when emergency active

# Metrics variables
sim_start_time = time.time()
total_wait_time = 0.0     # sum of wait times for cars that waited
total_served_waits = 0    # number of cars which waited (used to compute average wait)
throughput_count = 0      # number of cars that actually passed intersection (counted when they leave screen after crossing center)

def record_wait_time(queued_time):
    """Called when a car starts crossing after waiting -> update running totals."""
    global total_wait_time, total_served_waits
    if queued_time is None:
        return
    wait = time.time() - queued_time
    total_wait_time += wait
    total_served_waits += 1

def get_average_wait():
    if total_served_waits == 0:
        return 0.0
    return total_wait_time / total_served_waits

def get_throughput_per_minute():
    elapsed_minutes = (time.time() - sim_start_time) / 60.0
    if elapsed_minutes <= 0:
        return 0.0
    return throughput_count / elapsed_minutes

def draw_metrics():
    # Prepare strings
    avg_wait = get_average_wait()
    tpm = get_throughput_per_minute()
    counts = get_queue_counts()
    queued_counts = {d: 0 for d in DIRECTIONS}
    # queued = cars that currently have queued_time set (waiting in line)
    for c in cars:
        if c.queued_time is not None:
            queued_counts[c.direction] += 1

    # Build display lines
    lines = [
        f"Avg wait (s): {avg_wait:.2f}",
        f"Throughput (total): {throughput_count}",
        f"Throughput (per min): {tpm:.2f}",
        f"Queue N: {queued_counts['N']}  E: {queued_counts['E']}  S: {queued_counts['S']}  W: {queued_counts['W']}",
        f"Total vehicles on road: {len(cars)}"
    ]

    # Draw a semi-transparent background box for readability
    padding = 8
    box_w = 260
    box_h = 20 * len(lines) + padding * 2
    box_x = 10
    box_y = 10
    s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)  # per-pixel alpha
    s.fill((0, 0, 0, 160))  # black with alpha
    SCREEN.blit(s, (box_x, box_y))

    # Render lines
    for i, line in enumerate(lines):
        txt = FONT.render(line, True, (255, 255, 255))
        SCREEN.blit(txt, (box_x + padding, box_y + padding + i * 20))

# Main loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    now = time.time()
    elapsed = now - last_switch_time

    # --- Emergency detection & override logic ---
    # Find any emergency vehicles currently in the scene
    emergency_cars = [c for c in cars if c.is_emergency]

    if emergency_cars:
        # If there is at least one emergency vehicle, override lights immediately
        # Choose which emergency to prioritize if multiple: pick the one closest to center (intersection)
        def dist_to_center(car):
            cx, cy = WIDTH // 2, HEIGHT // 2
            car_center_x = car.x + (Car.WIDTH / 2 if car.direction in ["N", "S"] else Car.HEIGHT / 2)
            car_center_y = car.y + (Car.HEIGHT / 2 if car.direction in ["N", "S"] else Car.WIDTH / 2)
            return (car_center_x - cx) ** 2 + (car_center_y - cy) ** 2

        prioritized = min(emergency_cars, key=dist_to_center)
        desired_dir = prioritized.direction

        # if not already in emergency override or different emergency direction, switch immediately
        if (not emergency_override) or (emergency_direction != desired_dir):
            emergency_override = True
            emergency_direction = desired_dir
            light_index = DIRECTIONS.index(emergency_direction)
            last_served[emergency_direction] = now
            last_switch_time = now

    else:
        # no emergency vehicles in the scene
        if emergency_override:
            # an emergency just left — make that direction red again, then resume normal operation.
            just_cleared = emergency_direction
            emergency_override = False
            emergency_direction = None
            last_served[just_cleared] = now
            # choose next excluding the just cleared direction so it turns red immediately
            next_idx = choose_next_direction(exclude_dir=just_cleared)
            light_index = next_idx
            last_switch_time = now
        else:
            # Normal adaptive operation
            if elapsed >= MIN_GREEN:
                next_index = choose_next_direction()
                if next_index != light_index:
                    light_index = next_index
                    last_switch_time = now
                    last_served[DIRECTIONS[light_index]] = now
                else:
                    if elapsed >= MAX_GREEN:
                        counts = get_queue_counts()
                        other_candidates = [d for d in DIRECTIONS if d != DIRECTIONS[light_index]]
                        if any(counts[d] > 0 for d in other_candidates):
                            best_other = max(other_candidates, key=lambda d: counts[d])
                            if counts[best_other] > 0:
                                light_index = DIRECTIONS.index(best_other)
                                last_switch_time = now
                                last_served[DIRECTIONS[light_index]] = now

    # Draw and spawn
    draw_intersection()
    spawn_car()

    # Move & draw cars
    for car in cars:
        car.move(cars)
        car.draw()

    # Remove cars outside screen bounds (they've passed)
    new_cars = []
    for car in cars:
        if -Car.HEIGHT <= car.x <= WIDTH + Car.HEIGHT and -Car.HEIGHT <= car.y <= HEIGHT + Car.HEIGHT:
            new_cars.append(car)
        else:
            # car has left screen - count throughput only if it actually crossed the intersection center
            if car.crossed:
                throughput_count += 1
            # ensure we clear any queued_time for bookkeeping (not strictly necessary)
            if car.queued_time is not None:
                # if it leaves while queued (rare), count that wait as well
                record_wait_time(car.queued_time)
                car.queued_time = None
            # do not keep the car
    cars = new_cars

    # Draw metrics overlay
    draw_metrics()

    # Update display
    pygame.display.update()
    clock.tick(FPS)
