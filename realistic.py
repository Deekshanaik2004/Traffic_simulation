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

# Clock
clock = pygame.time.Clock()
FPS = 60

# Directions
DIRECTIONS = ["N", "E", "S", "W"]

# Adaptive timing parameters
MIN_GREEN = 5.0  # seconds each green must last at least this long
MAX_GREEN = 30.0  # if green lasts this long, controller will consider switching anyway
STARVE_TIME = 25.0  # if a lane hasn't had green for this long, it's prioritized
SAFE_DISTANCE = 45  # Minimum distance between cars in queue
SPAWN_CHANCE = 20  # Higher number → fewer vehicles

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
    # Traffic lights (shifted to sides)
    for i, direction in enumerate(DIRECTIONS):
        is_active = i == light_index
        light_color = GREEN if is_active else RED
        if direction == "N":
            draw_traffic_light(WIDTH // 2 - 45, HEIGHT // 2 - 130, light_color)
        elif direction == "E":
            draw_traffic_light(WIDTH // 2 + 70, HEIGHT // 2 - 15, light_color)
        elif direction == "S":
            draw_traffic_light(WIDTH // 2 + 45, HEIGHT // 2 + 60, light_color)
        elif direction == "W":
            draw_traffic_light(WIDTH // 2 - 70, HEIGHT // 2 - 15, light_color)

def draw_vehicle(screen, x, y, direction, sprite_type, vehicle_length, vehicle_width):
    if sprite_type == 'car':
        body_color = (0, 0, 255)  # blue
    elif sprite_type == 'bus':
        body_color = (255, 165, 0)  # orange
    elif sprite_type == 'ambulance':
        body_color = (255, 255, 255)  # white
    elif sprite_type == 'fire':
        body_color = (255, 0, 0)  # red
    else:
        body_color = (0, 0, 255)

    if direction in ["N", "S"]:
        # Vertical vehicle
        body_w = vehicle_width - 4
        body_h = vehicle_length - 10
        # Body
        pygame.draw.rect(screen, body_color, (x + 2, y + 5, body_w, body_h))
        # Wheels
        pygame.draw.ellipse(screen, (0, 0, 0), (x - 1, y + 5, 4, 8))   # left front
        pygame.draw.ellipse(screen, (0, 0, 0), (x + vehicle_width - 3, y + 5, 4, 8))  # right front
        pygame.draw.ellipse(screen, (0, 0, 0), (x - 1, y + 5 + body_h - 22, 4, 8))  # left rear
        pygame.draw.ellipse(screen, (0, 0, 0), (x + vehicle_width - 3, y + 5 + body_h - 22, 4, 8)) # right rear
        # Additional details
        if sprite_type == 'bus':
            # Windows (filled)
            num_windows = 5 if sprite_type == 'bus' else 3
            for i in range(num_windows):
                win_y = y + 8 + 8 * i
                if win_y + 5 < y + 5 + body_h:
                    pygame.draw.rect(screen, (200, 200, 255), (x + 3, win_y, body_w - 2, 5))
        elif sprite_type == 'ambulance':
            # Red cross
            cross_y = y + body_h // 2
            pygame.draw.line(screen, (255, 0, 0), (x + 5, cross_y), (x + vehicle_width - 5, cross_y), 2)
            pygame.draw.line(screen, (255, 0, 0), (x + vehicle_width // 2, cross_y - 5), (x + vehicle_width // 2, cross_y + 5), 2)
        elif sprite_type == 'fire':
            # Ladder
            pygame.draw.line(screen, (255, 255, 0), (x + 2, y + 2), (x + vehicle_width - 2, y + 2), 2)
            for i in range(6):
                pygame.draw.line(screen, (255, 255, 0), (x + 2 + 3 * i, y + 2), (x + 2 + 3 * i, y + 8), 1)
        elif sprite_type == 'car':
            # Windshield
            pygame.draw.polygon(screen, (200, 200, 200), [(x + 4, y + 8), (x + vehicle_width - 4, y + 8), (x + vehicle_width // 2, y + 3)])
    else:
        # Horizontal vehicle
        body_h = vehicle_length - 10  # along x
        body_w = vehicle_width - 4   # along y
        # Body
        pygame.draw.rect(screen, body_color, (x + 5, y + 2, body_h, body_w))
        # Wheels
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5, y - 1, 8, 4))   # top left
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5, y + vehicle_width - 3, 8, 4))  # bottom left
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5 + body_h - 22, y - 1, 8, 4))  # top right
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5 + body_h - 22, y + vehicle_width - 3, 8, 4)) # bottom right
        # Additional details
        if sprite_type == 'bus':
            # Windows (filled)
            num_windows = 5 if sprite_type == 'bus' else 3
            for i in range(num_windows):
                win_x = x + 8 + 8 * i
                if win_x + 5 < x + 5 + body_h:
                    pygame.draw.rect(screen, (200, 200, 255), (win_x, y + 3, 5, body_w - 2))
        elif sprite_type == 'ambulance':
            # Red cross
            cross_x = x + body_h // 2
            pygame.draw.line(screen, (255, 0, 0), (cross_x, y + 5), (cross_x, y + vehicle_width - 5), 2)
            pygame.draw.line(screen, (255, 0, 0), (cross_x - 5, y + vehicle_width // 2), (cross_x + 5, y + vehicle_width // 2), 2)
        elif sprite_type == 'fire':
            # Ladder
            pygame.draw.line(screen, (255, 255, 0), (x + 2, y + 2), (x + 2, y + vehicle_width - 2), 2)
            for i in range(6):
                pygame.draw.line(screen, (255, 255, 0), (x + 2, y + 2 + 3 * i), (x + 8, y + 2 + 3 * i), 1)
        elif sprite_type == 'car':
            # Windshield
            pygame.draw.polygon(screen, (200, 200, 200), [(x + 8, y + 4), (x + 8, y + vehicle_width - 4), (x + 3, y + vehicle_width // 2)])

class Car:
    SPEED = 2

    def __init__(self, direction, vehicle_type):
        self.direction = direction
        self.vehicle_type = vehicle_type
        self.sprite_type = vehicle_type
        self.vehicle_length = 60 if self.sprite_type == 'bus' else 40
        self.vehicle_width = 20
        self.stopped = False
        self.committed = False
        self.queued_time = None
        self.spawn_time = time.time()
        self.crossed = False
        if direction == "N":
            self.x = WIDTH // 2 - 15
            self.y = -self.vehicle_length
        elif direction == "S":
            self.x = WIDTH // 2 + 15
            self.y = HEIGHT + self.vehicle_length
        elif direction == "E":
            self.x = WIDTH + self.vehicle_length
            self.y = HEIGHT // 2 - 15
        elif direction == "W":
            self.x = -self.vehicle_length
            self.y = HEIGHT // 2 + 15

    @property
    def is_emergency(self):
        return self.vehicle_type in ("ambulance", "fire")

    def _near_intersection_region(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        if self.direction == "N":
            return self.y + self.vehicle_length >= cy - 300
        if self.direction == "S":
            return self.y - self.vehicle_length <= cy + 300
        if self.direction == "E":
            return self.x - self.vehicle_length <= cx + 300
        if self.direction == "W":
            return self.x + self.vehicle_length >= cx - 300

    def will_move_this_frame(self, cars):
        front_car = self.get_front_car(cars)
        if self.direction == "N":
            stop_line = HEIGHT // 2 - 60
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y + self.vehicle_length < stop_line and self.safe_to_move(front_car)):
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
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x + self.vehicle_length < stop_line and self.safe_to_move(front_car)):
                return True
            return False

    def move(self, cars):
        front_car = self.get_front_car(cars)
        will_move = self.will_move_this_frame(cars)
        if not will_move and self.queued_time is None and not self.committed and self._near_intersection_region():
            self.queued_time = time.time()
        if self.direction == "N":
            stop_line = HEIGHT // 2 - 60
            if not self.committed and self.can_pass() and self.y + self.vehicle_length >= stop_line:
                self.committed = True
                if self.queued_time is not None:
                    record_wait_time(self.queued_time)
                    self.queued_time = None
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y + self.vehicle_length < stop_line and self.safe_to_move(front_car)):
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
            if not self.committed and self.can_pass() and self.x + self.vehicle_length >= stop_line:
                self.committed = True
                if self.queued_time is not None:
                    record_wait_time(self.queued_time)
                    self.queued_time = None
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x + self.vehicle_length < stop_line and self.safe_to_move(front_car)):
                self.x += Car.SPEED
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
            return front_car.y - (self.y + self.vehicle_length) > SAFE_DISTANCE
        elif self.direction == "S":
            return self.y - (front_car.y + front_car.vehicle_length) > SAFE_DISTANCE
        elif self.direction == "E":
            return self.x - (front_car.x + front_car.vehicle_length) > SAFE_DISTANCE
        elif self.direction == "W":
            return front_car.x - (self.x + self.vehicle_length) > SAFE_DISTANCE

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
        return DIRECTIONS[light_index] == self.direction

    def draw(self):
        draw_vehicle(SCREEN, self.x, self.y, self.direction, self.sprite_type, self.vehicle_length, self.vehicle_width)

cars = []

def spawn_too_close(direction):
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
    if random.randint(0, SPAWN_CHANCE) == 0:
        direction = random.choice(DIRECTIONS)
        if spawn_too_close(direction):
            return
        r = random.random()
        if r < 0.5:
            vehicle_type = "car"
        elif r < 0.98:
            vehicle_type = "bus"
        elif r < 0.99:
            vehicle_type = "ambulance"
        else:
            vehicle_type = "fire"
        cars.append(Car(direction, vehicle_type))


# Adaptive controller state
light_index = 0
last_switch_time = time.time()
last_served = {d: time.time() for d in DIRECTIONS}

def get_queue_counts():
    counts = {d: 0 for d in DIRECTIONS}
    for c in cars:
        counts[c.direction] += 1
    return counts

def choose_next_direction(exclude_dir=None):
    counts = get_queue_counts()
    now = time.time()
    starving = [d for d in DIRECTIONS if now - last_served.get(d, 0) >= STARVE_TIME]
    if exclude_dir:
        starving = [d for d in starving if d != exclude_dir]
    if starving:
        best = max(starving, key=lambda d: counts.get(d, 0))
        return DIRECTIONS.index(best)
    if counts:
        max_count = max(counts.values())
    else:
        max_count = 0
    if max_count == 0:
        return light_index
    best_dirs = [d for d, cnt in counts.items() if cnt == max_count]
    if exclude_dir:
        best_dirs = [d for d in best_dirs if d != exclude_dir]
        if not best_dirs:
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
emergency_direction = None

# Metrics variables
sim_start_time = time.time()
total_wait_time = 0.0
total_served_waits = 0
throughput_count = 0

def record_wait_time(queued_time):
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
    avg_wait = get_average_wait()
    tpm = get_throughput_per_minute()
    counts = get_queue_counts()
    queued_counts = {d: 0 for d in DIRECTIONS}
    for c in cars:
        if c.queued_time is not None:
            queued_counts[c.direction] += 1
    lines = [
        f"Avg wait (s): {avg_wait:.2f}",
        f"Throughput (total): {throughput_count}",
        f"Throughput (per min): {tpm:.2f}",
        f"Queue N: {queued_counts['N']} E: {queued_counts['E']} S: {queued_counts['S']} W: {queued_counts['W']}",
        f"Total vehicles on road: {len(cars)}"
    ]
    padding = 8
    box_w = 260
    box_h = 20 * len(lines) + padding * 2
    box_x = 10
    box_y = 10
    s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 160))
    SCREEN.blit(s, (box_x, box_y))
    for i, line in enumerate(lines):
        txt = FONT.render(line, True, (255, 255, 255))
        SCREEN.blit(txt, (box_x + padding, box_y + padding + i * 20))

# Main loop
MAX_VEHICLE_SIZE = 60
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    now = time.time()
    elapsed = now - last_switch_time
    emergency_cars = [c for c in cars if c.is_emergency]
    if emergency_cars:
        def dist_to_center(car):
            cx, cy = WIDTH // 2, HEIGHT // 2
            car_center_x = car.x + (car.vehicle_width / 2 if car.direction in ["N", "S"] else car.vehicle_length / 2)
            car_center_y = car.y + (car.vehicle_length / 2 if car.direction in ["N", "S"] else car.vehicle_width / 2)
            return (car_center_x - cx) ** 2 + (car_center_y - cy) ** 2
        prioritized = min(emergency_cars, key=dist_to_center)
        desired_dir = prioritized.direction
        if (not emergency_override) or (emergency_direction != desired_dir):
            emergency_override = True
            emergency_direction = desired_dir
            light_index = DIRECTIONS.index(emergency_direction)
            last_served[emergency_direction] = now
            last_switch_time = now
    else:
        if emergency_override:
            just_cleared = emergency_direction
            emergency_override = False
            emergency_direction = None
            last_served[just_cleared] = now
            next_idx = choose_next_direction(exclude_dir=just_cleared)
            light_index = next_idx
            last_switch_time = now
        else:
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
    draw_intersection()
    spawn_car()
    for car in cars[:]:
        car.move(cars)
        car.draw()
    new_cars = []
    for car in cars:
        if -MAX_VEHICLE_SIZE <= car.x <= WIDTH + MAX_VEHICLE_SIZE and -MAX_VEHICLE_SIZE <= car.y <= HEIGHT + MAX_VEHICLE_SIZE:
            new_cars.append(car)
        else:
            if car.crossed:
                throughput_count += 1
            if car.queued_time is not None:
                record_wait_time(car.queued_time)
                car.queued_time = None
    cars = new_cars
    draw_metrics()
    pygame.display.update()
    clock.tick(FPS)