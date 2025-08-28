Traffic Intersection Simulation
Overview
This project is a Pygame-based simulation of a traffic intersection with adaptive traffic light control. Cars approach from four directions (North, East, South, West), and the traffic lights dynamically adjust based on queue lengths and timing constraints to optimize traffic flow. The simulation includes a visual representation of roads, traffic lights, and cars, with collision avoidance and realistic movement logic.
Features

Intersection Layout: A crossroad with vertical and horizontal roads, a yellow box at the center, and lane lines.
Traffic Lights: Each direction has a traffic light with red, yellow, and green signals. Only one direction is green at a time.
Adaptive Traffic Control: 
Minimum green time (MIN_GREEN = 5.0 seconds) ensures each direction gets sufficient time.
Maximum green time (MAX_GREEN = 30.0 seconds) prevents any direction from monopolizing green.
Starvation prevention (STARVE_TIME = 25.0 seconds) prioritizes directions that haven't had green recently.
The controller chooses the next green direction based on queue sizes, prioritizing starving lanes or the largest queue.


Car Behavior:
Cars spawn randomly at the edges of the screen with a configurable spawn chance (SPAWN_CHANCE).
Cars stop at red lights and move on green, maintaining a safe distance (SAFE_DISTANCE = 45 pixels) from the car in front.
Cars crossing the stop line during green are marked as "committed" and continue through the intersection.


Collision Avoidance: Cars check for safe distances to prevent collisions within the same lane.
Visuals: Roads are gray, cars are blue rectangles, and traffic lights are shown with black boxes and colored circles.

Requirements

Python 3.x
Pygame library (pip install pygame)

How to Run

Ensure Python and Pygame are installed.
Save the provided Python code as traffic_simulation.py.
Run the script:python traffic_simulation.py


The simulation window will open, showing the intersection and traffic flow.

Controls

Close Window: Click the window's close button to exit the simulation.

Configuration
The following constants in the code can be adjusted to tweak the simulation:

WIDTH, HEIGHT: Window dimensions (default: 800x800 pixels).
FPS: Frames per second (default: 60).
SPAWN_CHANCE: Controls car spawn frequency (higher = fewer cars, default: 50).
SAFE_DISTANCE: Minimum distance between cars in the same lane (default: 45 pixels).
MIN_GREEN: Minimum time a direction stays green (default: 5.0 seconds).
MAX_GREEN: Maximum time a direction stays green before considering a switch (default: 30.0 seconds).
STARVE_TIME: Time after which a direction is considered "starving" and prioritized (default: 25.0 seconds).
Car.SPEED: Speed of cars (default: 2 pixels per frame).

Notes

The simulation runs indefinitely until the window is closed.
Cars are removed once they exit the screen boundaries.
The adaptive traffic controller ensures fairness by prioritizing directions with longer queues or those that haven't had green in a while.
The code is designed for desktop Pygame and does not include Pyodide compatibility for browser execution.

Limitations

The simulation assumes a simple intersection with straight-through traffic only (no turns).
No pedestrian or complex vehicle interactions are modeled.
The traffic light system uses a basic adaptive algorithm; more advanced models (e.g., real-time sensor data) are not implemented.
