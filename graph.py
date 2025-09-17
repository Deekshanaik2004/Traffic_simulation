# graph.py
import pygame
import sys
import random
import time
import threading
import sounddevice as sd
import numpy as np

pygame.init()

WIDTH, HEIGHT = 900, 800
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Traffic Intersection Simulation (State Machine + Virtual IoT Clearance)")

# Colors
ROAD_COLOR = (50, 50, 50)
LINE_COLOR = (255, 255, 255)
BOX_COLOR = (255, 255, 0)
SIGNAL_BOX = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BG_COLOR = (34, 139, 34)
PANEL_BG_ALPHA = 200

clock = pygame.time.Clock()
FPS = 60

DIRECTIONS = ["N", "E", "S", "W"]

# Timing / parameters
MIN_GREEN = 5.0
MAX_GREEN = 30.0
STARVE_TIME = 25.0
SAFE_DISTANCE = 15
SPAWN_CHANCE = 15  # the lower, the more often vehicles spawn (random modulus)

FONT = pygame.font.SysFont("Arial", 16)
SMALL_FONT = pygame.font.SysFont("Arial", 12)
def draw_bar_graphs(vehicle_counts, avg_wait_times):
    # Horizontal bar graph (top-right)
    start_x, start_y = WIDTH - 200, 50
    bar_width, max_bar_length = 20, 150
    for i, dir in enumerate(DIRECTIONS):
        length = int((vehicle_counts[dir] / max(vehicle_counts.values(), 1)) * max_bar_length)
        pygame.draw.rect(SCREEN, (0, 255, 0), (start_x, start_y + i * 30, length, bar_width))
        label = SMALL_FONT.render(f"{dir}: {vehicle_counts[dir]}", True, (255, 255, 255))
        SCREEN.blit(label, (start_x + 160, start_y + i * 30))

    # Vertical bar graph (bottom-left)
    start_x, start_y = 50, HEIGHT - 250
    bar_width, max_bar_height = 20, 250
    for i, dir in enumerate(DIRECTIONS):
        height = int((avg_wait_times[dir] / max(avg_wait_times.values(), 1)) * max_bar_height)
        pygame.draw.rect(SCREEN, (255, 0, 0), (start_x + i * 40, start_y + (max_bar_height - height), bar_width, height))
        label = SMALL_FONT.render(f"{dir}", True, (255, 255, 255))
        SCREEN.blit(label, (start_x + i * 40, start_y + max_bar_height + 5))


# ----- Drawing helpers -----
def draw_traffic_light(x, y, active_color):
    pygame.draw.rect(SCREEN, SIGNAL_BOX, (x, y, 30, 70), border_radius=5)
    colors = [RED, YELLOW, GREEN]
    for i, color in enumerate(colors):
        light_color = color if color == active_color else (100, 100, 100)
        pygame.draw.circle(SCREEN, light_color, (x + 15, y + 10 + 25 * i), 7)

def draw_intersection():
    # draw background and roads
    SCREEN.fill(BG_COLOR)
    pygame.draw.rect(SCREEN, ROAD_COLOR, (WIDTH // 2 - 60, 0, 120, HEIGHT))
    pygame.draw.rect(SCREEN, ROAD_COLOR, (0, HEIGHT // 2 - 60, WIDTH, 120))
    # central box
    pygame.draw.rect(SCREEN, BOX_COLOR, (WIDTH // 2 - 60, HEIGHT // 2 - 60, 120, 120), width=3)
    # lane separators
    pygame.draw.line(SCREEN, LINE_COLOR, (WIDTH // 2 - 30, 0), (WIDTH // 2 - 30, HEIGHT), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (WIDTH // 2 + 30, 0), (WIDTH // 2 + 30, HEIGHT), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (0, HEIGHT // 2 - 30), (WIDTH, HEIGHT // 2 - 30), 2)
    pygame.draw.line(SCREEN, LINE_COLOR, (0, HEIGHT // 2 + 30), (WIDTH, HEIGHT // 2 + 30), 2)

def draw_vehicle(screen, x, y, direction, sprite_type, vehicle_length, vehicle_width):
    """
    Draws top-down rectangle vehicle oriented according to direction.
    x,y are top-left coordinates as existing code expects.
    """
    if sprite_type == 'car':
        body_color = (0, 0, 255)
    elif sprite_type == 'bus':
        body_color = (255, 165, 0)
    elif sprite_type == 'ambulance':
        body_color = (255, 255, 255)
    elif sprite_type == 'fire':
        body_color = (255, 0, 0)
    else:
        body_color = (0, 0, 255)

    if direction in ["N", "S"]:
        body_w = vehicle_width - 4
        body_h = vehicle_length - 10
        pygame.draw.rect(screen, body_color, (x + 2, y + 5, body_w, body_h))
        pygame.draw.ellipse(screen, (0, 0, 0), (x - 1, y + 5, 4, 8))
        pygame.draw.ellipse(screen, (0, 0, 0), (x + vehicle_width - 3, y + 5, 4, 8))
        pygame.draw.ellipse(screen, (0, 0, 0), (x - 1, y + 5 + body_h - 22, 4, 8))
        pygame.draw.ellipse(screen, (0, 0, 0), (x + vehicle_width - 3, y + 5 + body_h - 22, 4, 8))
        if sprite_type == 'bus':
            num_windows = 5
            for i in range(num_windows):
                win_y = y + 8 + 8 * i
                if win_y + 5 < y + 5 + body_h:
                    pygame.draw.rect(screen, (200, 200, 255), (x + 3, win_y, body_w - 2, 5))
        elif sprite_type == 'ambulance':
            cross_y = y + body_h // 2
            pygame.draw.line(screen, (255, 0, 0), (x + 5, cross_y), (x + vehicle_width - 5, cross_y), 2)
            pygame.draw.line(screen, (255, 0, 0), (x + vehicle_width // 2, cross_y - 5), (x + vehicle_width // 2, cross_y + 5), 2)
        elif sprite_type == 'fire':
            pygame.draw.line(screen, (255, 255, 0), (x + 2, y + 2), (x + vehicle_width - 2, y + 2), 2)
            for i in range(6):
                pygame.draw.line(screen, (255, 255, 0), (x + 2 + 3 * i, y + 2), (x + 2 + 3 * i, y + 8), 1)
        elif sprite_type == 'car':
            pygame.draw.polygon(screen, (200, 200, 200), [(x + 4, y + 8), (x + vehicle_width - 4, y + 8), (x + vehicle_width // 2, y + 3)])
    else:
        body_h = vehicle_length - 10
        body_w = vehicle_width - 4
        pygame.draw.rect(screen, body_color, (x + 5, y + 2, body_h, body_w))
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5, y - 1, 8, 4))
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5, y + vehicle_width - 3, 8, 4))
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5 + body_h - 22, y - 1, 8, 4))
        pygame.draw.ellipse(screen, (0, 0, 0), (x + 5 + body_h - 22, y + vehicle_width - 3, 8, 4))
        if sprite_type == 'bus':
            num_windows = 5
            for i in range(num_windows):
                win_x = x + 8 + 8 * i
                if win_x + 5 < x + 5 + body_h:
                    pygame.draw.rect(screen, (200, 200, 255), (win_x, y + 3, 5, body_w - 2))
        elif sprite_type == 'ambulance':
            cross_x = x + body_h // 2
            pygame.draw.line(screen, (255, 0, 0), (cross_x, y + 5), (cross_x, y + vehicle_width - 5), 2)
            pygame.draw.line(screen, (255, 0, 0), (cross_x - 5, y + vehicle_width // 2), (cross_x + 5, y + vehicle_width // 2), 2)
        elif sprite_type == 'fire':
            pygame.draw.line(screen, (255, 255, 0), (x + 2, y + 2), (x + 2, y + vehicle_width - 2), 2)
            for i in range(6):
                pygame.draw.line(screen, (255, 255, 0), (x + 2, y + 2 + 3 * i), (x + 8, y + 2 + 3 * i), 1)
        elif sprite_type == 'car':
            pygame.draw.polygon(screen, (200, 200, 200), [(x + 8, y + 4), (x + 8, y + vehicle_width - 4), (x + 3, y + vehicle_width // 2)])

# ----- Vehicle class -----
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
            # eastbound cars front car should be the one with smaller x than this
            same_lane_cars = [car for car in same_lane_cars if car.x < self.x]
            return max(same_lane_cars, key=lambda c: c.x, default=None)
        elif self.direction == "W":
            same_lane_cars = [car for car in same_lane_cars if car.x > self.x]
            return min(same_lane_cars, key=lambda c: c.x, default=None)

    def can_pass(self):
        return DIRECTIONS[light_index] == self.direction and light_state == "GREEN"

    def draw(self):
        # draw this vehicle using the shared draw_vehicle()
        draw_vehicle(SCREEN, self.x, self.y, self.direction, self.sprite_type, self.vehicle_length, self.vehicle_width)

# ----- Simulation lists / helpers -----
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
        if r < 0.7:
            vehicle_type = "car"
        else:
            vehicle_type = "bus"
        cars.append(Car(direction, vehicle_type))

# ----- Light state machine -----
light_index = 0
light_state = "GREEN"  # GREEN, START_SWITCH, WAIT_CLEAR, DELAY
green_start_time = time.time()
switch_request_time = None
clear_start_time = None
delay_start_time = None

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
        # no queues; rotate to next to avoid permanent same dir
        return (light_index + 1) % 4
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

# ----- Emergency & metrics -----
emergency_override = False
emergency_direction = None

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
    # small translucent box at top-left with overall metrics (keeps original behavior)
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
        f"Total vehicles on road: {len(cars)}",
        f"Light State: {light_state} | Green Dir: {DIRECTIONS[light_index]}"
    ]
    padding = 8
    box_w = 340
    box_h = 20 * len(lines) + padding * 2
    box_x = 10
    box_y = 10
    s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 160))
    SCREEN.blit(s, (box_x, box_y))
    for i, line in enumerate(lines):
        txt = FONT.render(line, True, (255, 255, 255))
        SCREEN.blit(txt, (box_x + padding, box_y + padding + i * 20))

# ----- Bar graphs integration (top-right: counts, bottom-right: waits) -----
def draw_bar_graphs():
    counts = get_queue_counts()
    # compute average wait per direction using queued_time lists (current waiting vehicles)
    wait_times = {d: [] for d in DIRECTIONS}
    for c in cars:
        if c.queued_time is not None:
            wait_times[c.direction].append(time.time() - c.queued_time)
    avg_wait_dir = {}
    for d in DIRECTIONS:
        avg_wait_dir[d] = sum(wait_times[d]) / len(wait_times[d]) if wait_times[d] else 0.0

    # --- Top-right: Horizontal vehicle count bars (in green box) ---
    graph_w = 320
    graph_h = 220
    padding_top = 80  # space from top
    padding_right = 11
    x_offset = WIDTH - graph_w - padding_right
    y_offset = padding_top

    # background box
    pygame.draw.rect(SCREEN, (0, 115, 0), (x_offset, y_offset, graph_w, graph_h), border_radius=10)
    inner_padding = 10

    # Title
    title = FONT.render("Vehicle Counts", True, (255, 255, 255))
    SCREEN.blit(title, (x_offset + inner_padding, y_offset + inner_padding))

    counts_area_top = y_offset + inner_padding + 24
    counts_area_left = x_offset + inner_padding + 90
    counts_area_width = graph_w - (inner_padding * 2) - 100
    bar_height = 22
    spacing = 38

    max_queue = max(counts.values()) if any(counts.values()) else 1
    for i, dir in enumerate(DIRECTIONS):
        count = counts[dir]
        length = int((count / max_queue) * counts_area_width) if max_queue > 0 else 0
        bar_x = counts_area_left
        bar_y = counts_area_top + i * spacing
        # background (track)
        pygame.draw.rect(SCREEN, (25, 25, 25), (bar_x, bar_y, counts_area_width, bar_height), border_radius=6)
        # actual bar
        pygame.draw.rect(SCREEN, (0, 200, 0), (bar_x, bar_y, length, bar_height), border_radius=6)
        # direction label
        dir_label = FONT.render(f"{dir}", True, (255, 255, 255))
        SCREEN.blit(dir_label, (x_offset + inner_padding + 8, bar_y + (bar_height // 2) - 8))
        # numeric count (position right after bar; handle overflow)
        count_label = FONT.render(str(count), True, (255, 255, 255))
        if length + 12 < counts_area_width:
            SCREEN.blit(count_label, (bar_x + length + 8, bar_y + (bar_height // 2) - 8))
        else:
            SCREEN.blit(count_label, (bar_x + counts_area_width - 20, bar_y + (bar_height // 2) - 8))

    # legend
    small = pygame.font.SysFont("Arial", 12)
    legend1 = small.render("Counts →", True, (255, 255, 255))
    SCREEN.blit(legend1, (x_offset + graph_w - inner_padding - 70, y_offset + inner_padding + 4))

    # --- Bottom-right: Vertical average wait bars (in separate box) ---
    graph_w2 = 300
    graph_h2 = 200
    padding_bottom = 100
    x_offset2 = WIDTH - graph_w2 - padding_right
    y_offset2 = HEIGHT - graph_h2 - padding_bottom

    # background box
    pygame.draw.rect(SCREEN, (80, 0, 0), (x_offset2, y_offset2, graph_w2, graph_h2), border_radius=10)

    # title
    title2 = FONT.render("Avg Wait (s) per Direction", True, (255, 255, 255))
    SCREEN.blit(title2, (x_offset2 + inner_padding, y_offset2 + inner_padding))

    # plotting area
    vert_area_top = y_offset2 + inner_padding + 26
    vert_area_height = graph_h2 - (inner_padding * 2) - 40
    bar_w = 34
    gap = 22

    waits = [avg_wait_dir[d] for d in DIRECTIONS]
    max_wait = max(max(waits), 1.0)  # avoid 0

    # small axis line
    axis_y = vert_area_top + vert_area_height + 6
    pygame.draw.line(SCREEN, (200, 200, 200), (x_offset2 + inner_padding + 6, axis_y), (x_offset2 + inner_padding + 6 + (bar_w + gap) * len(DIRECTIONS) - gap, axis_y), 2)

    for i, dir in enumerate(DIRECTIONS):
        wtime = avg_wait_dir[dir]
        height = int((wtime / max_wait) * vert_area_height) if max_wait > 0 else 0
        bar_x = x_offset2 + inner_padding + 6 + i * (bar_w + gap)
        bar_y = vert_area_top + (vert_area_height - height)
        pygame.draw.rect(SCREEN, (220, 60, 60), (bar_x, bar_y, bar_w, height), border_radius=6)
        # direction label under bar
        txt_dir = FONT.render(dir, True, (255, 255, 255))
        SCREEN.blit(txt_dir, (bar_x + (bar_w // 2) - 6, axis_y + 6))
        # numeric wait above bar
        txt_wait = SMALL_FONT.render(f"{wtime:.1f}s", True, (255, 255, 255))
        SCREEN.blit(txt_wait, (bar_x + (bar_w // 2) - 10, bar_y - 16))

    # small legend
    legend_wait = small.render("Current queued avg (s)", True, (255, 255, 255))
    SCREEN.blit(legend_wait, (x_offset2 + graph_w2 - inner_padding - 170, y_offset2 + graph_h2 - inner_padding - 18))

# ----- Audio / Siren detection UI -----
BUTTON_RECT = pygame.Rect(10, 10 + 20 * 7 + 16, 260, 30)
listening_for_siren = False
audio_thread = None
audio_lock = threading.Lock()
last_audio_trigger = 0
audio_cooldown = 3.0
fs = 44100
chunk_duration = 1.0
freq_low = 500
freq_high = 2000
energy_threshold = 0.005

def set_green_for_emergency(direction):
    global light_state, light_index, green_start_time, switch_request_time, clear_start_time, delay_start_time, last_switch_time
    # Set the light_index to emergency direction and force immediate GREEN state
    light_index = DIRECTIONS.index(direction)
    light_state = "GREEN"
    green_start_time = time.time()
    switch_request_time = None
    clear_start_time = None
    delay_start_time = None
    last_switch_time = time.time()
    last_served[direction] = time.time()

def audio_listener_loop():
    global listening_for_siren, cars, emergency_override, emergency_direction, light_index, last_served, last_switch_time, last_audio_trigger
    while listening_for_siren:
        try:
            rec = sd.rec(int(chunk_duration * fs), samplerate=fs, channels=1, dtype='float32')
            sd.wait()
            sig = rec.flatten()
            if sig.size == 0:
                continue
            win = np.hanning(len(sig))
            sig_win = sig * win
            fft = np.abs(np.fft.rfft(sig_win))
            freqs = np.fft.rfftfreq(len(sig_win), 1.0 / fs)
            band_idx = np.where((freqs >= freq_low) & (freqs <= freq_high))[0]
            if band_idx.size == 0:
                continue
            band_energy = np.sum(fft[band_idx])
            total_energy = np.sum(fft) + 1e-9
            ratio = band_energy / total_energy
            now = time.time()
            if ratio > energy_threshold and now - last_audio_trigger > audio_cooldown:
                last_audio_trigger = now
                vehicle_type = random.choice(["ambulance", "fire"])
                direction = random.choice(DIRECTIONS)
                with audio_lock:
                    if not spawn_too_close(direction):
                        cars.append(Car(direction, vehicle_type))
                        prioritized_dir = direction
                        # Immediately set emergency override and switch to that direction using the state machine:
                        emergency_override = True
                        emergency_direction = prioritized_dir
                        # Force state machine to green for emergency
                        set_green_for_emergency(prioritized_dir)
        except Exception:
            time.sleep(0.1)
    return

MAX_VEHICLE_SIZE = 60

# ----- Virtual IoT clearance function -----
def intersection_clear():
    """
    Virtual IoT sensor: return True if no vehicle is inside the central intersection box.
    Intersection box is WIDTH//2 - 60 .. +60 and HEIGHT//2 -60 .. +60.
    """
    left = WIDTH//2 - 60
    right = WIDTH//2 + 60
    top = HEIGHT//2 - 60
    bottom = HEIGHT//2 + 60
    for c in cars:
        # compute approximate bounding box of car as drawn
        if c.direction in ("N", "S"):
            rect_left = c.x + 2
            rect_top = c.y + 5
            rect_right = rect_left + max(1, c.vehicle_width - 4)
            rect_bottom = rect_top + max(1, c.vehicle_length - 10)
        else:
            # E/W oriented
            rect_left = c.x + 5
            rect_top = c.y + 2
            rect_right = rect_left + max(1, c.vehicle_length - 10)
            rect_bottom = rect_top + max(1, c.vehicle_width - 4)

        # check overlap with central box
        if not (rect_right < left or rect_left > right or rect_bottom < top or rect_top > bottom):
            # vehicle overlaps central area => intersection NOT clear
            return False
    return True

# ----- Main loop -----
def main_loop():
    global listening_for_siren, audio_thread, light_state, light_index, green_start_time, switch_request_time
    global clear_start_time, delay_start_time, emergency_override, emergency_direction, throughput_count, last_served

    # A small pre-spawn so simulation isn't empty initially
    for _ in range(12):
        spawn_car()

    # visual debug message when WAIT_CLEAR is active
    wait_clear_msg = ""

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                listening_for_siren = False
                if audio_thread and audio_thread.is_alive():
                    audio_thread.join(timeout=0.5)
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if BUTTON_RECT.collidepoint(event.pos):
                    # toggle listening
                    if not listening_for_siren:
                        listening_for_siren = True
                        audio_thread = threading.Thread(target=audio_listener_loop, daemon=True)
                        audio_thread.start()
                    else:
                        listening_for_siren = False

        now = time.time()

        # spawn and move vehicles
        spawn_car()
        for car in cars[:]:
            car.move(cars)

        # remove off-screen cars and account throughput/waits
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

        # emergency detection and override handling
        emergency_cars = [c for c in new_cars if c.is_emergency]
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
                # Force emergency green using state machine helper
                set_green_for_emergency(desired_dir)
        else:
            if emergency_override and not listening_for_siren:
                just_cleared = emergency_direction
                emergency_override = False
                emergency_direction = None
                last_served[just_cleared] = now
                # request a switch out of the just cleared direction
                if light_state == "GREEN":
                    light_state = "START_SWITCH"
                    switch_request_time = time.time()

        cars[:] = new_cars

        # ----- State Machine (with IoT clearance every cycle) -----
        if light_state == "GREEN":
            elapsed_green = now - green_start_time
            need_switch = False
            if elapsed_green >= MAX_GREEN:
                need_switch = True
            elif elapsed_green >= MIN_GREEN:
                suggested = choose_next_direction()
                if suggested != light_index:
                    need_switch = True
            if need_switch and not emergency_override:
                light_state = "START_SWITCH"
                switch_request_time = now

        elif light_state == "START_SWITCH":
            # Enter WAIT_CLEAR so that IoT sensors check the intersection each cycle
            light_state = "WAIT_CLEAR"
            clear_start_time = time.time()
            wait_clear_msg = "Waiting for intersection to clear..."  # visual message

        elif light_state == "WAIT_CLEAR":
            # Check virtual IoT sensors: don't switch until intersection clear
            if intersection_clear():
                # intersection clear now, start the 3s grace delay
                light_state = "DELAY"
                delay_start_time = time.time()
                wait_clear_msg = "Intersection clear — delaying 3s before switch"
            else:
                # keep waiting; remain in WAIT_CLEAR state
                wait_clear_msg = "Waiting for intersection to clear..."
                # nothing else here — we stay until clear

        elif light_state == "DELAY":
            # After intersection was clear, wait additional grace period (3 seconds)
            if now - delay_start_time >= 1.0:
                prev_dir = DIRECTIONS[light_index]
                next_idx = choose_next_direction(exclude_dir=prev_dir)
                light_index = next_idx
                light_state = "GREEN"
                green_start_time = time.time()
                last_served[DIRECTIONS[light_index]] = time.time()
                wait_clear_msg = ""

        # ----- Rendering -----
        draw_intersection()

        # draw vehicles
        for car in cars:
            car.draw()

        # draw signals (so they appear over vehicles)
        for i, direction in enumerate(DIRECTIONS):
            is_active = (i == light_index and light_state == "GREEN")
            light_color = GREEN if is_active else RED
            if direction == "N":
                draw_traffic_light(WIDTH // 2 - 45, HEIGHT // 2 - 130, light_color)
            elif direction == "E":
                draw_traffic_light(WIDTH // 2 + 70, HEIGHT // 2 - 15, light_color)
            elif direction == "S":
                draw_traffic_light(WIDTH // 2 + 45, HEIGHT // 2 + 60, light_color)
            elif direction == "W":
                draw_traffic_light(WIDTH // 2 - 70, HEIGHT // 2 - 15, light_color)

        # draw left-top metrics (original compact panel)
        draw_metrics()

        # draw graphs (top-right counts, bottom-right average waits)
        draw_bar_graphs()

        # Draw WAIT_CLEAR visual message (center-top, small translucent box)
        if wait_clear_msg:
            msg_w = 360
            msg_h = 30
            msg_x = (WIDTH - msg_w) // 2
            msg_y = 8
            s = pygame.Surface((msg_w, msg_h), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            SCREEN.blit(s, (msg_x, msg_y))
            txt = FONT.render(wait_clear_msg, True, (255, 255, 255))
            SCREEN.blit(txt, (msg_x + 10, msg_y + 6))

        # draw audio button (left)
        mouse_pos = pygame.mouse.get_pos()
        if BUTTON_RECT.collidepoint(mouse_pos):
            pygame.draw.rect(SCREEN, (220, 220, 0), BUTTON_RECT, border_radius=4)
        else:
            pygame.draw.rect(SCREEN, (200, 200, 0), BUTTON_RECT, border_radius=4)
        if listening_for_siren:
            txt = FONT.render("Listening for Siren (click to stop)", True, (0, 0, 0))
        else:
            txt = FONT.render("Start Siren Detection (click to start)", True, (0, 0, 0))
        SCREEN.blit(txt, (BUTTON_RECT.x + 6, BUTTON_RECT.y + 6))

        pygame.display.update()
        clock.tick(FPS)

if __name__ == "__main__":
    main_loop()
