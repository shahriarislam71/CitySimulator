from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import math
import random
import time

# =========================================================
# BASIC WINDOW / WORLD CONFIG
# =========================================================
WINDOW_W = 1000
WINDOW_H = 800

WORLD_MIN = -520
WORLD_MAX = 520
GROUND_Z = 0

ROAD_HALF_WIDTH = 80
SIDEWALK_WIDTH = 18

PLAYER_GROUND_Z = 15
PLAYER_EYE_HEIGHT = 24

FOV_Y = 120

# =========================================================
# GLOBAL GAME STATE
# =========================================================
buildings = []
trees = []
cars = []
people = []

player = {
    "x": 0.0,
    "y": -250.0,
    "z": PLAYER_GROUND_Z,
    "angle": 90.0,
    "mode": "walk",          # walk / car
    "camera_mode": "third",  # first / third
    "jumping": False,
    "jump_velocity": 0.0,
    "alive": True,
    "speed_walk": 6.0,
    "speed_car": 12.0,
    "turn_walk": 4.0,
    "turn_car": 3.0,
}

cheat_mode = False
game_over = False
accident_count = 0
game_start_time = time.time()
final_survival_time = 0.0

# =========================================================
# COMMON UTILITY FUNCTIONS
# =========================================================
def deg_to_rad(deg):
    return deg * math.pi / 180.0

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def distance2d(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def inside_world(x, y, margin=0):
    return (WORLD_MIN + margin <= x <= WORLD_MAX - margin and
            WORLD_MIN + margin <= y <= WORLD_MAX - margin)

def circle_rect_collision(cx, cy, radius, rx, ry, rw, rd):
    half_w = rw / 2.0
    half_d = rd / 2.0

    closest_x = clamp(cx, rx - half_w, rx + half_w)
    closest_y = clamp(cy, ry - half_d, ry + half_d)

    dx = cx - closest_x
    dy = cy - closest_y

    return (dx * dx + dy * dy) <= (radius * radius)

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# =========================================================
# MEMBER 1 SECTION
# ENVIRONMENT / CITY / BUILDINGS / TREES / WORLD DESIGN
# =========================================================

def reserved_road_area(x, y, padding=0):
    return abs(x) <= ROAD_HALF_WIDTH + padding or abs(y) <= ROAD_HALF_WIDTH + padding

def building_overlap(x, y, w, d):
    for b in buildings:
        dx = abs(x - b["x"])
        dy = abs(y - b["y"])
        if dx < (w / 2 + b["w"] / 2 + 26) and dy < (d / 2 + b["d"] / 2 + 26):
            return True
    return False

def tree_overlap(x, y):
    for b in buildings:
        if circle_rect_collision(x, y, 14, b["x"], b["y"], b["w"] + 20, b["d"] + 20):
            return True
    for t in trees:
        if distance2d(x, y, t["x"], t["y"]) < 30:
            return True
    return False

def generate_buildings():
    global buildings
    buildings = []

    count = 28
    attempts = 0

    while len(buildings) < count and attempts < 3000:
        attempts += 1

        x = random.randint(WORLD_MIN + 90, WORLD_MAX - 90)
        y = random.randint(WORLD_MIN + 90, WORLD_MAX - 90)

        # keep center roads clear
        if reserved_road_area(x, y, padding=50):
            continue

        # keep player spawn area clear
        if distance2d(x, y, 0, -250) < 150:
            continue

        w = random.randint(55, 95)
        d = random.randint(55, 95)
        h = random.randint(100, 260)

        if building_overlap(x, y, w, d):
            continue

        buildings.append({
            "x": x,
            "y": y,
            "w": w,
            "d": d,
            "h": h,
            "color": (
                random.uniform(0.25, 0.42),
                random.uniform(0.25, 0.42),
                random.uniform(0.38, 0.68),
            )
        })

def generate_trees():
    global trees
    trees = []

    count = 42
    attempts = 0

    while len(trees) < count and attempts < 4000:
        attempts += 1

        x = random.randint(WORLD_MIN + 30, WORLD_MAX - 30)
        y = random.randint(WORLD_MIN + 30, WORLD_MAX - 30)

        if reserved_road_area(x, y, padding=18):
            continue

        if distance2d(x, y, 0, -250) < 90:
            continue

        if tree_overlap(x, y):
            continue

        trees.append({"x": x, "y": y})

def draw_lane_lines():
    glColor3f(1.0, 0.95, 0.2)

    # vertical dashed line
    y = WORLD_MIN
    while y < WORLD_MAX:
        glBegin(GL_QUADS)
        glVertex3f(-2, y, 1.2)
        glVertex3f(2, y, 1.2)
        glVertex3f(2, y + 30, 1.2)
        glVertex3f(-2, y + 30, 1.2)
        glEnd()
        y += 55

    # horizontal dashed line
    x = WORLD_MIN
    while x < WORLD_MAX:
        glBegin(GL_QUADS)
        glVertex3f(x, -2, 1.2)
        glVertex3f(x + 30, -2, 1.2)
        glVertex3f(x + 30, 2, 1.2)
        glVertex3f(x, 2, 1.2)
        glEnd()
        x += 55

def draw_ground():
    # grass
    glBegin(GL_QUADS)
    glColor3f(0.16, 0.46, 0.20)
    glVertex3f(WORLD_MIN, WORLD_MIN, 0)
    glVertex3f(WORLD_MAX, WORLD_MIN, 0)
    glVertex3f(WORLD_MAX, WORLD_MAX, 0)
    glVertex3f(WORLD_MIN, WORLD_MAX, 0)
    glEnd()

    # vertical road
    glBegin(GL_QUADS)
    glColor3f(0.15, 0.15, 0.17)
    glVertex3f(-ROAD_HALF_WIDTH, WORLD_MIN, 0.5)
    glVertex3f(ROAD_HALF_WIDTH, WORLD_MIN, 0.5)
    glVertex3f(ROAD_HALF_WIDTH, WORLD_MAX, 0.5)
    glVertex3f(-ROAD_HALF_WIDTH, WORLD_MAX, 0.5)
    glEnd()

    # horizontal road
    glBegin(GL_QUADS)
    glColor3f(0.15, 0.15, 0.17)
    glVertex3f(WORLD_MIN, -ROAD_HALF_WIDTH, 0.5)
    glVertex3f(WORLD_MAX, -ROAD_HALF_WIDTH, 0.5)
    glVertex3f(WORLD_MAX, ROAD_HALF_WIDTH, 0.5)
    glVertex3f(WORLD_MIN, ROAD_HALF_WIDTH, 0.5)
    glEnd()

    # sidewalks
    sidewalk = ROAD_HALF_WIDTH + SIDEWALK_WIDTH
    glBegin(GL_QUADS)
    glColor3f(0.58, 0.58, 0.60)

    # left sidewalk
    glVertex3f(-sidewalk, WORLD_MIN, 0.8)
    glVertex3f(-ROAD_HALF_WIDTH, WORLD_MIN, 0.8)
    glVertex3f(-ROAD_HALF_WIDTH, WORLD_MAX, 0.8)
    glVertex3f(-sidewalk, WORLD_MAX, 0.8)

    # right sidewalk
    glVertex3f(ROAD_HALF_WIDTH, WORLD_MIN, 0.8)
    glVertex3f(sidewalk, WORLD_MIN, 0.8)
    glVertex3f(sidewalk, WORLD_MAX, 0.8)
    glVertex3f(ROAD_HALF_WIDTH, WORLD_MAX, 0.8)

    # bottom sidewalk
    glVertex3f(WORLD_MIN, -sidewalk, 0.8)
    glVertex3f(WORLD_MAX, -sidewalk, 0.8)
    glVertex3f(WORLD_MAX, -ROAD_HALF_WIDTH, 0.8)
    glVertex3f(WORLD_MIN, -ROAD_HALF_WIDTH, 0.8)

    # top sidewalk
    glVertex3f(WORLD_MIN, ROAD_HALF_WIDTH, 0.8)
    glVertex3f(WORLD_MAX, ROAD_HALF_WIDTH, 0.8)
    glVertex3f(WORLD_MAX, sidewalk, 0.8)
    glVertex3f(WORLD_MIN, sidewalk, 0.8)

    glEnd()

    draw_lane_lines()

def draw_boundary():
    glColor3f(0.78, 0.78, 0.82)

    # left
    glPushMatrix()
    glTranslatef(WORLD_MIN, 0, 25)
    glScalef(5, WORLD_MAX - WORLD_MIN, 50)
    glutSolidCube(1)
    glPopMatrix()

    # right
    glPushMatrix()
    glTranslatef(WORLD_MAX, 0, 25)
    glScalef(5, WORLD_MAX - WORLD_MIN, 50)
    glutSolidCube(1)
    glPopMatrix()

    # bottom
    glPushMatrix()
    glTranslatef(0, WORLD_MIN, 25)
    glScalef(WORLD_MAX - WORLD_MIN, 5, 50)
    glutSolidCube(1)
    glPopMatrix()

    # top
    glPushMatrix()
    glTranslatef(0, WORLD_MAX, 25)
    glScalef(WORLD_MAX - WORLD_MIN, 5, 50)
    glutSolidCube(1)
    glPopMatrix()

def draw_building(b):
    glPushMatrix()
    glTranslatef(b["x"], b["y"], b["h"] / 2.0)

    r, g, bb = b["color"]

    # main body
    glColor3f(r, g, bb)
    glPushMatrix()
    glScalef(b["w"], b["d"], b["h"])
    glutSolidCube(1)
    glPopMatrix()

    # rooftop tower
    glColor3f(min(r + 0.08, 1), min(g + 0.08, 1), min(bb + 0.08, 1))
    glPushMatrix()
    glTranslatef(0, 0, b["h"] * 0.36)
    glScalef(b["w"] * 0.45, b["d"] * 0.45, b["h"] * 0.28)
    glutSolidCube(1)
    glPopMatrix()

    glPopMatrix()

def draw_tree(t):
    # trunk
    glPushMatrix()
    glTranslatef(t["x"], t["y"], 14)
    glColor3f(0.42, 0.22, 0.08)
    glScalef(7, 7, 28)
    glutSolidCube(1)
    glPopMatrix()

    # leaves 1
    glPushMatrix()
    glTranslatef(t["x"], t["y"], 36)
    glColor3f(0.05, 0.62, 0.18)
    glutSolidSphere(13, 14, 14)
    glPopMatrix()

    # leaves 2
    glPushMatrix()
    glTranslatef(t["x"], t["y"], 48)
    glColor3f(0.10, 0.72, 0.22)
    glutSolidSphere(10, 14, 14)
    glPopMatrix()

def draw_static_world():
    draw_ground()
    draw_boundary()

    for b in buildings:
        draw_building(b)

    for t in trees:
        draw_tree(t)

# =========================================================
# MEMBER 2 SECTION
# PLAYER / CONTROLS / CAMERA / MODE SWITCH / RESTART
# =========================================================

def player_radius():
    return 14 if player["mode"] == "walk" else 18

def collides_with_building(nx, ny):
    r = player_radius()
    for b in buildings:
        if circle_rect_collision(nx, ny, r, b["x"], b["y"], b["w"], b["d"]):
            return True
    return False

def collides_with_tree(nx, ny):
    r = player_radius()
    for t in trees:
        if distance2d(nx, ny, t["x"], t["y"]) < r + 12:
            return True
    return False

def move_player_forward(direction):
    if game_over:
        return

    speed = player["speed_walk"] if player["mode"] == "walk" else player["speed_car"]
    rad = deg_to_rad(player["angle"])

    dx = math.cos(rad) * speed * direction
    dy = math.sin(rad) * speed * direction

    nx = player["x"] + dx
    ny = player["y"] + dy

    margin = player_radius() + 5

    if not inside_world(nx, ny, margin):
        return
    if collides_with_building(nx, ny):
        return
    if collides_with_tree(nx, ny):
        return

    player["x"] = nx
    player["y"] = ny

def rotate_player(direction):
    if game_over:
        return

    turn = player["turn_walk"] if player["mode"] == "walk" else player["turn_car"]
    player["angle"] += turn * direction

    if player["angle"] >= 360:
        player["angle"] -= 360
    elif player["angle"] < 0:
        player["angle"] += 360

def update_jump():
    if player["mode"] != "walk":
        player["z"] = PLAYER_GROUND_Z
        player["jumping"] = False
        player["jump_velocity"] = 0.0
        return

    if player["jumping"]:
        player["z"] += player["jump_velocity"]
        player["jump_velocity"] -= 1.2

        if player["z"] <= PLAYER_GROUND_Z:
            player["z"] = PLAYER_GROUND_Z
            player["jumping"] = False
            player["jump_velocity"] = 0.0

def draw_player():
    glPushMatrix()
    glTranslatef(player["x"], player["y"], player["z"])
    glRotatef(player["angle"], 0, 0, 1)

    if player["mode"] == "walk":
        # torso
        glColor3f(0.15, 0.85, 0.95)
        glPushMatrix()
        glTranslatef(0, 0, 4)
        glScalef(14, 10, 20)
        glutSolidCube(1)
        glPopMatrix()

        # head
        glColor3f(1.0, 0.84, 0.72)
        glPushMatrix()
        glTranslatef(0, 0, 18)
        glutSolidSphere(5.5, 12, 12)
        glPopMatrix()

        # front marker
        glColor3f(1.0, 1.0, 0.0)
        glPushMatrix()
        glTranslatef(0, 10, 6)
        glutSolidSphere(2.5, 10, 10)
        glPopMatrix()

    else:
        # controllable car body
        glColor3f(0.10, 0.95, 0.25)
        glPushMatrix()
        glScalef(30, 46, 12)
        glutSolidCube(1)
        glPopMatrix()

        # cabin
        glColor3f(0.12, 0.15, 0.16)
        glPushMatrix()
        glTranslatef(0, 0, 9)
        glScalef(18, 24, 10)
        glutSolidCube(1)
        glPopMatrix()

        # headlights
        glColor3f(1.0, 1.0, 0.7)
        glPushMatrix()
        glTranslatef(-7, 23, 0)
        glutSolidSphere(2.4, 10, 10)
        glPopMatrix()

        glPushMatrix()
        glTranslatef(7, 23, 0)
        glutSolidSphere(2.4, 10, 10)
        glPopMatrix()

        # wheels
        glColor3f(0.05, 0.05, 0.05)
        wheel_positions = [(-10, -15), (10, -15), (-10, 15), (10, 15)]
        for wx, wy in wheel_positions:
            glPushMatrix()
            glTranslatef(wx, wy, -4)
            glutSolidSphere(4, 10, 10)
            glPopMatrix()

    glPopMatrix()

def reset_game():
    global cheat_mode, game_over, accident_count, game_start_time, final_survival_time

    player["x"] = 0.0
    player["y"] = -250.0
    player["z"] = PLAYER_GROUND_Z
    player["angle"] = 90.0
    player["mode"] = "walk"
    player["camera_mode"] = "third"
    player["jumping"] = False
    player["jump_velocity"] = 0.0
    player["alive"] = True

    cheat_mode = False
    game_over = False
    accident_count = 0
    final_survival_time = 0.0
    game_start_time = time.time()

    generate_city()

def keyboardListener(key, x, y):
    global cheat_mode

    if key == b' ':
        if not game_over and player["mode"] == "walk" and not player["jumping"]:
            player["jumping"] = True
            player["jump_velocity"] = 10.0

    elif key == b'e' or key == b'E':
        if not game_over:
            if player["mode"] == "walk":
                player["mode"] = "car"
                player["z"] = 10
                player["jumping"] = False
                player["jump_velocity"] = 0.0
            else:
                player["mode"] = "walk"
                player["z"] = PLAYER_GROUND_Z

    elif key == b'v' or key == b'V':
        if player["camera_mode"] == "third":
            player["camera_mode"] = "first"
        else:
            player["camera_mode"] = "third"

    elif key == b'c' or key == b'C':
        cheat_mode = not cheat_mode

    elif key == b'r' or key == b'R':
        reset_game()

def specialKeyListener(key, x, y):
    if key == GLUT_KEY_UP:
        move_player_forward(1)
    elif key == GLUT_KEY_DOWN:
        move_player_forward(-1)
    elif key == GLUT_KEY_LEFT:
        rotate_player(1)
    elif key == GLUT_KEY_RIGHT:
        rotate_player(-1)

def mouseListener(button, state, x, y):
    pass

def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y, WINDOW_W / WINDOW_H, 0.1, 2200)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    px = player["x"]
    py = player["y"]
    pz = player["z"]

    rad = deg_to_rad(player["angle"])
    fx = math.cos(rad)
    fy = math.sin(rad)

    if player["camera_mode"] == "first":
        cam_x = px
        cam_y = py
        cam_z = pz + PLAYER_EYE_HEIGHT

        look_x = px + fx * 120
        look_y = py + fy * 120
        look_z = pz + PLAYER_EYE_HEIGHT

    else:
        back_dist = 90 if player["mode"] == "walk" else 135
        cam_x = px - fx * back_dist
        cam_y = py - fy * back_dist
        cam_z = pz + 70

        look_x = px + fx * 40
        look_y = py + fy * 40
        look_z = pz + 20

    gluLookAt(
        cam_x, cam_y, cam_z,
        look_x, look_y, look_z,
        0, 0, 1
    )

# =========================================================
# MEMBER 3 SECTION
# CARS / PEOPLE / TURNING / ACCIDENT / TIMER / HUD
# =========================================================

def generate_cars():
    global cars
    cars = []

    colors = [
        (0.90, 0.16, 0.16),
        (0.15, 0.45, 0.90),
        (0.10, 0.75, 0.20),
        (0.95, 0.75, 0.15),
        (0.80, 0.20, 0.80),
        (0.95, 0.50, 0.10),
    ]

    # vertical road cars
    for i in range(6):
        cars.append({
            "x": random.choice([-25, 25]),
            "y": random.randint(WORLD_MIN + 40, WORLD_MAX - 40),
            "angle": 90 if i % 2 == 0 else 270,
            "speed": random.uniform(2.0, 3.4),
            "w": 26,
            "d": 42,
            "lane": "vertical",
            "color": random.choice(colors),
            "turned_recently": False,
        })

    # horizontal road cars
    for i in range(6):
        cars.append({
            "x": random.randint(WORLD_MIN + 40, WORLD_MAX - 40),
            "y": random.choice([-25, 25]),
            "angle": 0 if i % 2 == 0 else 180,
            "speed": random.uniform(2.0, 3.4),
            "w": 42,
            "d": 26,
            "lane": "horizontal",
            "color": random.choice(colors),
            "turned_recently": False,
        })

def generate_people():
    global people
    people = []

    for _ in range(14):
        side = random.choice(["left", "right", "top", "bottom"])

        if side == "left":
            x = random.randint(WORLD_MIN + 40, -ROAD_HALF_WIDTH - SIDEWALK_WIDTH - 25)
            y = random.randint(WORLD_MIN + 40, WORLD_MAX - 40)
        elif side == "right":
            x = random.randint(ROAD_HALF_WIDTH + SIDEWALK_WIDTH + 25, WORLD_MAX - 40)
            y = random.randint(WORLD_MIN + 40, WORLD_MAX - 40)
        elif side == "top":
            x = random.randint(WORLD_MIN + 40, WORLD_MAX - 40)
            y = random.randint(ROAD_HALF_WIDTH + SIDEWALK_WIDTH + 25, WORLD_MAX - 40)
        else:
            x = random.randint(WORLD_MIN + 40, WORLD_MAX - 40)
            y = random.randint(WORLD_MIN + 40, -ROAD_HALF_WIDTH - SIDEWALK_WIDTH - 25)

        people.append({
            "x": x,
            "y": y,
            "angle": random.choice([0, 90, 180, 270]),
            "speed": random.uniform(0.8, 1.7),
            "radius": 10
        })

def generate_city():
    generate_buildings()
    generate_trees()
    generate_cars()
    generate_people()

def draw_car(c, highlight=False):
    glPushMatrix()
    glTranslatef(c["x"], c["y"], 10)
    glRotatef(c["angle"], 0, 0, 1)

    body_color = (1.0, 0.3, 0.2) if highlight else c.get("color", (0.9, 0.1, 0.1))

    # lower body
    glColor3f(*body_color)
    glPushMatrix()
    glScalef(c["w"], c["d"], 12)
    glutSolidCube(1)
    glPopMatrix()

    # upper cabin
    glColor3f(0.15, 0.2, 0.35)
    glPushMatrix()
    glTranslatef(0, 0, 9)
    glScalef(c["w"] * 0.6, c["d"] * 0.55, 10)
    glutSolidCube(1)
    glPopMatrix()

    # headlights
    glColor3f(1.0, 1.0, 0.7)
    glPushMatrix()
    glTranslatef(-c["w"] * 0.22, c["d"] * 0.52, 1)
    glutSolidSphere(2.2, 10, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(c["w"] * 0.22, c["d"] * 0.52, 1)
    glutSolidSphere(2.2, 10, 10)
    glPopMatrix()

    # wheels
    glColor3f(0.05, 0.05, 0.05)
    wheel_positions = [
        (-c["w"] * 0.38, -c["d"] * 0.35),
        ( c["w"] * 0.38, -c["d"] * 0.35),
        (-c["w"] * 0.38,  c["d"] * 0.35),
        ( c["w"] * 0.38,  c["d"] * 0.35),
    ]
    for wx, wy in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, -4)
        glutSolidSphere(4, 10, 10)
        glPopMatrix()

    glPopMatrix()

def draw_person(p):
    glPushMatrix()
    glTranslatef(p["x"], p["y"], 10)

    # legs / body
    glColor3f(0.95, 0.82, 0.20)
    glPushMatrix()
    glScalef(8, 8, 18)
    glutSolidCube(1)
    glPopMatrix()

    # head
    glColor3f(1.0, 0.83, 0.68)
    glPushMatrix()
    glTranslatef(0, 0, 15)
    glutSolidSphere(5, 12, 12)
    glPopMatrix()

    glPopMatrix()

def person_valid(nx, ny):
    if not inside_world(nx, ny, 15):
        return False

    if reserved_road_area(nx, ny, padding=5):
        return False

    for b in buildings:
        if circle_rect_collision(nx, ny, 10, b["x"], b["y"], b["w"] + 6, b["d"] + 6):
            return False

    return True

def near_intersection(c):
    return abs(c["x"]) < 12 and abs(c["y"]) < 12

def choose_turn():
    return random.choice(["straight", "left", "right"])

def apply_turn(c, decision):
    old_angle = c["angle"]

    if decision == "straight":
        return

    if decision == "left":
        c["angle"] = (c["angle"] + 90) % 360
    elif decision == "right":
        c["angle"] = (c["angle"] - 90) % 360

    # update lane type
    if c["lane"] == "vertical":
        c["lane"] = "horizontal"
        # snap to horizontal lane
        if c["angle"] == 0:
            c["y"] = -25
        elif c["angle"] == 180:
            c["y"] = 25
        else:
            c["angle"] = old_angle
            c["lane"] = "vertical"
            return
    else:
        c["lane"] = "vertical"
        # snap to vertical lane
        if c["angle"] == 90:
            c["x"] = 25
        elif c["angle"] == 270:
            c["x"] = -25
        else:
            c["angle"] = old_angle
            c["lane"] = "horizontal"
            return

    c["turned_recently"] = True

def update_cars():
    for c in cars:
        if near_intersection(c) and not c["turned_recently"]:
            decision = choose_turn()
            apply_turn(c, decision)

        rad = deg_to_rad(c["angle"])
        c["x"] += math.cos(rad) * c["speed"]
        c["y"] += math.sin(rad) * c["speed"]

        # reset turn flag after leaving center
        if abs(c["x"]) > 40 or abs(c["y"]) > 40:
            c["turned_recently"] = False

        # stay inside world
        if c["lane"] == "vertical":
            c["x"] = 25 if c["angle"] == 90 else -25 if c["angle"] == 270 else c["x"]

            if c["y"] > WORLD_MAX - 20:
                c["y"] = WORLD_MIN + 20
            elif c["y"] < WORLD_MIN + 20:
                c["y"] = WORLD_MAX - 20

        else:
            c["y"] = -25 if c["angle"] == 0 else 25 if c["angle"] == 180 else c["y"]

            if c["x"] > WORLD_MAX - 20:
                c["x"] = WORLD_MIN + 20
            elif c["x"] < WORLD_MIN + 20:
                c["x"] = WORLD_MAX - 20

def update_people():
    for p in people:
        if random.random() < 0.03:
            p["angle"] = random.choice([0, 90, 180, 270])

        rad = deg_to_rad(p["angle"])
        nx = p["x"] + math.cos(rad) * p["speed"]
        ny = p["y"] + math.sin(rad) * p["speed"]

        if person_valid(nx, ny):
            p["x"] = nx
            p["y"] = ny
        else:
            p["angle"] = random.choice([0, 90, 180, 270])

def check_accident():
    global accident_count, game_over, final_survival_time

    if game_over:
        return

    pr = player_radius()

    for c in cars:
        if distance2d(player["x"], player["y"], c["x"], c["y"]) < (pr + 20):
            accident_count += 1
            if not cheat_mode:
                game_over = True
                player["alive"] = False
                final_survival_time = time.time() - game_start_time
            return

def draw_dynamic_objects():
    for c in cars:
        draw_car(c)

    for p in people:
        draw_person(p)

def draw_hud():
    survival = final_survival_time if game_over else (time.time() - game_start_time)

    draw_text(10, 770, "3D City Simulator: Safe Walking And Driving")
    draw_text(10, 740, f"Mode: {player['mode'].upper()}")
    draw_text(10, 710, f"Camera: {player['camera_mode'].upper()}")
    draw_text(10, 680, f"Cheat Mode: {'ON' if cheat_mode else 'OFF'}")
    draw_text(10, 650, f"Accident Count: {accident_count}")
    draw_text(10, 620, f"Survival Time: {survival:.1f} s")

    draw_text(10, 580, "Controls:")
    draw_text(10, 550, "UP / DOWN = Move")
    draw_text(10, 520, "LEFT / RIGHT = Rotate")
    draw_text(10, 490, "SPACE = Jump")
    draw_text(10, 460, "E = Switch Player / Car")
    draw_text(10, 430, "V = First / Third Person")
    draw_text(10, 400, "C = Cheat Mode")
    draw_text(10, 370, "R = Restart")

    if game_over:
        draw_text(355, 760, "ACCIDENT! SIMULATION OVER")
        draw_text(390, 730, "Press R to Restart")

# =========================================================
# MAIN UPDATE / DRAW FLOW
# =========================================================

def update_game():
    if not game_over:
        update_jump()
        update_cars()
        update_people()
        check_accident()

def idle():
    update_game()
    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_W, WINDOW_H)

    setupCamera()

    draw_static_world()
    draw_dynamic_objects()
    draw_player()
    draw_hud()

    glutSwapBuffers()

# =========================================================
# OPENGL INIT / MAIN
# =========================================================

def init():
    glClearColor(0.42, 0.72, 0.95, 1.0)  # brighter sky
    glEnable(GL_DEPTH_TEST)

def main():
    generate_city()

    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(100, 50)
    glutCreateWindow(b"3D City Simulator - Final Project")

    init()

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutMainLoop()

if __name__ == "__main__":
    main()