import pygame
import sys
import random
import time

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 800, 800
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Traffic Intersection Simulation")

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

# Traffic light state
light_index = 0
last_switch_time = time.time()
SIGNAL_DURATION = 15  # seconds

SAFE_DISTANCE = 45  # Minimum distance between cars in queue
SPAWN_CHANCE = 50  # Higher number → fewer cars (was 20 before)

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

    def __init__(self, direction):
        self.direction = direction
        self.stopped = False
        self.committed = False   # 🚦 new flag for cars inside intersection

        if direction == "N":
            self.x = WIDTH // 2 - 15
            self.y = -Car.HEIGHT
        elif direction == "S":
            self.x = WIDTH // 2 + 15
            self.y = HEIGHT + Car.HEIGHT
        elif direction == "E":
            self.x = WIDTH + Car.HEIGHT
            self.y = HEIGHT // 2 - 15
        elif direction == "W":
            self.x = -Car.HEIGHT
            self.y = HEIGHT // 2 + 15

    def move(self, cars):
        front_car = self.get_front_car(cars)

        if self.direction == "N":
            stop_line = HEIGHT // 2 - 60
            if not self.committed and self.can_pass() and self.y + Car.HEIGHT >= stop_line:
                self.committed = True
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y + Car.HEIGHT < stop_line and self.safe_to_move(front_car)):
                self.y += Car.SPEED

        elif self.direction == "S":
            stop_line = HEIGHT // 2 + 60
            if not self.committed and self.can_pass() and self.y <= stop_line:
                self.committed = True
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.y > stop_line and self.safe_to_move(front_car)):
                self.y -= Car.SPEED

        elif self.direction == "E":
            stop_line = WIDTH // 2 + 60
            if not self.committed and self.can_pass() and self.x <= stop_line:
                self.committed = True
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x > stop_line and self.safe_to_move(front_car)):
                self.x -= Car.SPEED

        elif self.direction == "W":
            stop_line = WIDTH // 2 - 60
            if not self.committed and self.can_pass() and self.x + Car.HEIGHT >= stop_line:
                self.committed = True
            if self.committed or (self.can_pass() and self.safe_to_move(front_car)) or (self.x + Car.HEIGHT < stop_line and self.safe_to_move(front_car)):
                self.x += Car.SPEED

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
        return DIRECTIONS[light_index] == self.direction

    def draw(self):
        if self.direction in ["N", "S"]:
            pygame.draw.rect(SCREEN, (0, 0, 255), (self.x, self.y, Car.WIDTH, Car.HEIGHT))
        else:
            pygame.draw.rect(SCREEN, (0, 0, 255), (self.x, self.y, Car.HEIGHT, Car.WIDTH))

cars = []

def spawn_car():
    # Reduced spawn chance for fewer cars
    if random.randint(0, SPAWN_CHANCE) == 0:
        direction = random.choice(DIRECTIONS)

        # Prevent spawning if another car is too close
        if not any(c.direction == direction and (
            (direction == "N" and c.y < SAFE_DISTANCE) or
            (direction == "S" and c.y > HEIGHT - SAFE_DISTANCE) or
            (direction == "E" and c.x > WIDTH - SAFE_DISTANCE) or
            (direction == "W" and c.x < SAFE_DISTANCE)
        ) for c in cars):
            cars.append(Car(direction))

# Main loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    if time.time() - last_switch_time > SIGNAL_DURATION:
        light_index = (light_index + 1) % 4
        last_switch_time = time.time()

    draw_intersection()
    spawn_car()

    for car in cars:
        car.move(cars)
        car.draw()

    # Remove cars outside screen
    cars = [car for car in cars if -Car.HEIGHT <= car.x <= WIDTH + Car.HEIGHT and -Car.HEIGHT <= car.y <= HEIGHT + Car.HEIGHT]

    pygame.display.update()
    clock.tick(FPS)   
