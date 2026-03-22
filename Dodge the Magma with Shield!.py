import os
import ctypes
import math
import pygame
import random
import sys
import json
import threading

ctypes.windll.user32.SetProcessDPIAware()
pygame.init()

# ---------- SAVE ----------
SAVE_FILE = "save.json"

coins = 0
player_speed = 8
jump_strength = -22
shield_cooldown_real = 300
shield_time_real = 120
save_dirty = False
last_save_tick = 0
AUTO_SAVE_INTERVAL = 5000
glow_surface_cache = {}
magma_glow_surface = None
trail_surface_cache = {}


def save_game():
    global save_dirty, last_save_tick
    data = {
        "coins": coins,
        "player_speed": player_speed,
        "jump_strength": jump_strength,
        "shield_cooldown_real": shield_cooldown_real,
        "shield_time_real": shield_time_real,
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    save_dirty = False
    last_save_tick = pygame.time.get_ticks()


def queue_save():
    global save_dirty
    save_dirty = True


def load_game():
    global coins, player_speed, jump_strength
    global shield_cooldown_real, shield_time_real
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            coins = data.get("coins", coins)
            player_speed = data.get("player_speed", player_speed)
            jump_strength = data.get("jump_strength", jump_strength)
            shield_cooldown_real = data.get(
                "shield_cooldown_real", shield_cooldown_real
            )
            shield_time_real = data.get("shield_time_real", shield_time_real)
    except Exception:
        save_game()


# ---------- THREAD INPUT ----------
command = ""
command_lock = threading.Lock()


def read_input():
    global command
    while True:
        try:
            cmd = input(">> ")
            with command_lock:
                command = cmd
        except Exception:
            break


def get_safe_window_resolution():
    default_width = 1280
    default_height = 720
    display_info = pygame.display.Info()
    max_width = max(640, display_info.current_w - 120)
    max_height = max(480, display_info.current_h - 120)

    try:
        raw = input("Resolution: ").split()
        width, height = map(int, raw[:2])
    except Exception:
        width, height = default_width, default_height

    if width <= 0 or height <= 0:
        width, height = default_width, default_height

    width = max(640, min(max_width, width))
    height = max(480, min(max_height, height))
    return width, height


# ---------- SCREEN ----------
mode = int(input("1 fullscreen | 0 window: "))

if mode == 1:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WIDTH, HEIGHT = screen.get_size()
else:
    WIDTH, HEIGHT = get_safe_window_resolution()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("DODGE THE MAGMA")
# get window handle
hwnd = pygame.display.get_wm_info()['window']

# 1. tạm thời set topmost
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

# 2. set foreground
ctypes.windll.user32.SetForegroundWindow(hwnd)

# 3. remove topmost để normal lại
ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

clock = pygame.time.Clock()

threading.Thread(target=read_input, daemon=True).start()

# ---------- FONT ----------
font = pygame.font.SysFont("Consolas", 28)
small_font = pygame.font.SysFont("Consolas", 22)
big_font = pygame.font.SysFont("Consolas", 48)

load_game()

# ---------- COLORS ----------
WHITE = (255, 255, 255)
RED = (255, 80, 70)
ORANGE = (255, 160, 60)
BLUE = (100, 200, 255)
GREEN = (80, 255, 120)
YELLOW = (255, 220, 70)
PURPLE = (160, 130, 255)
BG = (10, 10, 20)
GRID = (30, 30, 60)
PANEL = (0, 0, 0)


# ---------- HELPERS ----------
def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def draw_box(x, y, w, h, color=PANEL, border=WHITE, border_radius=10):
    pygame.draw.rect(screen, color, (x, y, w, h), border_radius=border_radius)
    pygame.draw.rect(
        screen, border, (x, y, w, h), 2, border_radius=border_radius
    )


def draw_text(text, y, color=WHITE, font_ref=font):
    rendered = font_ref.render(text, True, color)
    screen.blit(rendered, (WIDTH // 2 - rendered.get_width() // 2, y))


def draw_bar(x, y, w, h, ratio, fill_color, label, border_color=WHITE):
    ratio = clamp(ratio, 0, 1)
    pygame.draw.rect(screen, (25, 25, 35), (x, y, w, h), border_radius=8)
    pygame.draw.rect(screen, border_color, (x, y, w, h), 2, border_radius=8)
    if ratio > 0:
        inner_w = max(0, int((w - 4) * ratio))
        pygame.draw.rect(
            screen,
            fill_color,
            (x + 2, y + 2, inner_w, h - 4),
            border_radius=7,
        )
    label_surf = small_font.render(label, True, WHITE)
    screen.blit(label_surf, (x + 8, y + h // 2 - label_surf.get_height() // 2))


def get_glow_surface(radius, color, alpha):
    key = (radius, color, alpha)
    if key not in glow_surface_cache:
        surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(
            surface, (*color, alpha), (radius * 2, radius * 2), radius
        )
        pygame.draw.circle(
            surface,
            (*color, alpha // 2),
            (radius * 2, radius * 2),
            int(radius * 1.5),
        )
        glow_surface_cache[key] = surface
    return glow_surface_cache[key]


def get_magma_glow_surface():
    global magma_glow_surface
    if magma_glow_surface is None:
        magma_glow_surface = pygame.Surface((72, 72), pygame.SRCALPHA)
        pygame.draw.circle(magma_glow_surface, (255, 110, 50, 80), (36, 36), 18)
        pygame.draw.circle(magma_glow_surface, (255, 70, 40, 50), (36, 36), 26)
    return magma_glow_surface


def get_trail_surface(size, alpha):
    key = (size[0], size[1], alpha)
    if key not in trail_surface_cache:
        surface = pygame.Surface((size[0] + 30, size[1] + 30), pygame.SRCALPHA)
        pygame.draw.rect(
            surface,
            (120, 210, 255, alpha),
            (15, 15, size[0], size[1]),
            border_radius=12,
        )
        trail_surface_cache[key] = surface
    return trail_surface_cache[key]


def draw_glow_circle(center, radius, color, alpha=70):
    glow = get_glow_surface(radius, color, alpha)
    screen.blit(glow, (center[0] - radius * 2, center[1] - radius * 2))


def reset_run():
    global score, game_state, velocity_y, jumps_left, jump_hold_time
    global player_vx, player_pos_x, player_pos_y, coyote_time, jump_buffer_time
    global dash_velocity, dash_duration, dash_cooldown, dash_trail
    global shield, shield_time, shield_cooldown, shield_flash
    global magma_list, coin_list, next_magma_spawn, next_coin_spawn
    global player, facing, gameover_input_unlock_at

    score = 0
    game_state = "game"
    gameover_input_unlock_at = 0
    player.x = WIDTH // 2
    player.bottom = HEIGHT - 50
    player_pos_x = float(player.x)
    player_pos_y = float(player.y)
    velocity_y = 0.0
    player_vx = 0.0
    jumps_left = max_jumps
    jump_hold_time = 0
    coyote_time = 0
    jump_buffer_time = 0
    dash_velocity = 0.0
    dash_duration = 0
    dash_cooldown = 0
    dash_trail = []
    shield = False
    shield_time = 0
    shield_cooldown = 0
    shield_flash = 0
    magma_list.clear()
    coin_list.clear()
    facing = 1
    now = pygame.time.get_ticks()
    next_magma_spawn = now + 300
    next_coin_spawn = now + 900


def spawn_magma_pattern():
    pattern = random.choices(
        ["single", "double", "cluster", "zigzag"],
        weights=[45, 20, 25, 10],
        k=1,
    )[0]
    spawn_x = random.randint(20, max(20, WIDTH - 50))
    pieces = []

    if pattern == "single":
        pieces.append(pygame.Rect(spawn_x, -30, 30, 30))
    elif pattern == "double":
        offset = random.choice([40, 55])
        pieces.append(pygame.Rect(clamp(spawn_x, 0, WIDTH - 30), -30, 30, 30))
        pieces.append(
            pygame.Rect(clamp(spawn_x + offset, 0, WIDTH - 30), -30, 30, 30)
        )
    elif pattern == "cluster":
        offsets = [-44, -12, 20, 52]
        for off in random.sample(offsets, k=random.randint(3, 4)):
            pieces.append(
                pygame.Rect(clamp(spawn_x + off, 0, WIDTH - 30), -30, 30, 30)
            )
    else:
        lane = random.randint(0, 3)
        for i in range(4):
            x = clamp(spawn_x + (i - lane) * 34, 0, WIDTH - 30)
            pieces.append(pygame.Rect(x, -30 - i * 10, 30, 30))

    magma_list.extend(pieces)


def spawn_coin_pattern():
    pattern = random.choices(
        ["single", "zigzag", "line", "reward"],
        weights=[42, 28, 20, 10],
        k=1,
    )[0]
    base_x = random.randint(15, max(15, WIDTH - 35))
    base_y = -20
    coins_to_add = []

    if pattern == "single":
        coins_to_add.append(pygame.Rect(base_x, base_y, 20, 20))
    elif pattern == "zigzag":
        for i in range(5):
            x = clamp(base_x + (-1) ** i * (18 + i * 2), 0, WIDTH - 20)
            y = base_y - i * 22
            coins_to_add.append(pygame.Rect(x, y, 20, 20))
    elif pattern == "line":
        for i in range(4):
            x = clamp(base_x + i * 26, 0, WIDTH - 20)
            coins_to_add.append(pygame.Rect(x, base_y - i * 8, 20, 20))
    else:
        for i in range(3):
            x = clamp(base_x + i * 34 - 34, 0, WIDTH - 20)
            y = base_y - abs(i - 1) * 18
            coins_to_add.append(pygame.Rect(x, y, 20, 20))

    coin_list.extend(coins_to_add)


def draw_player():
    body_color = BLUE if not shield else (135, 240, 255)
    lean = int(clamp(velocity_y / 4, -4, 4))
    body = pygame.Rect(player.x, player.y, player.width, player.height)
    body.inflate_ip(-4, -4)

    pygame.draw.rect(
        screen,
        (20, 40, 65),
        body.move(0, 4),
        border_radius=14,
    )
    pygame.draw.rect(
        screen,
        body_color,
        body.move(lean, 0),
        border_radius=14,
    )

    eye_x = body.centerx + (7 if facing > 0 else -14)
    pygame.draw.rect(
        screen,
        WHITE,
        (eye_x, body.y + 12, 5, 5),
        border_radius=2,
    )
    pygame.draw.rect(
        screen,
        (20, 20, 30),
        (eye_x + 1, body.y + 13, 2, 2),
        border_radius=1,
    )


def draw_magma(m):
    glow = get_magma_glow_surface()
    screen.blit(glow, (m.centerx - 36, m.centery - 36))

    pygame.draw.rect(screen, (130, 35, 20), m.inflate(-4, -4), border_radius=6)
    pygame.draw.rect(screen, RED, m, border_radius=6)
    pygame.draw.rect(screen, ORANGE, m.inflate(-14, -14), border_radius=4)


def draw_coin(c, tick):
    pulse = 1 + int((math.sin(tick * 0.02) + 1) * 1.5)
    pygame.draw.circle(screen, (200, 160, 20), c.center, 11 + pulse // 3)
    pygame.draw.circle(screen, YELLOW, c.center, 8 + pulse // 4)
    pygame.draw.circle(screen, WHITE, (c.centerx - 3, c.centery - 3), 2)
    pygame.draw.line(
        screen, WHITE, (c.centerx - 6, c.centery), (c.centerx + 6, c.centery), 1
    )
    pygame.draw.line(
        screen, WHITE, (c.centerx, c.centery - 6), (c.centerx, c.centery + 6), 1
    )


# ---------- PLAYER ----------
player = pygame.Rect(WIDTH // 2, HEIGHT - 100, 50, 50)
player_pos_x = float(player.x)
player_pos_y = float(player.y)
velocity_y = 0.0
player_vx = 0.0
gravity = 1.35
run_accel = 0.9
run_friction = 0.80
run_max_speed = player_speed
max_jumps = 2
jumps_left = max_jumps
jump_hold_max = 12
jump_hold_time = 0
facing = 1
coyote_max = 6
coyote_time = 0
jump_buffer_max = 6
jump_buffer_time = 0


# ---------- DASH ----------
dash_velocity = 0.0
dash_duration = 0
dash_cooldown = 0
dash_trail = []
dash_trail_timer = 0


# ---------- SHIELD ----------
shield = False
shield_time = 0
shield_cooldown = 0
shield_flash = 0


# ---------- OBJECTS ----------
magma_list = []
coin_list = []
next_magma_spawn = pygame.time.get_ticks() + 300
next_coin_spawn = pygame.time.get_ticks() + 900

score = 0
game_state = "menu"
gameover_input_unlock_at = 0


# ---------- UI ----------
def draw_hud():
    panel_x = 10
    panel_y = 10
    draw_box(panel_x, panel_y, 320, 178, (0, 0, 0), WHITE)

    score_surf = font.render(f"SCORE: {score}", True, WHITE)
    coin_surf = font.render(f"COINS: {coins}", True, YELLOW)
    speed_surf = small_font.render(f"SPD: {player_speed}", True, BLUE)
    jump_surf = small_font.render(f"JUMPS: {jumps_left}/{max_jumps}", True, GREEN)
    screen.blit(score_surf, (22, 20))
    screen.blit(coin_surf, (22, 52))
    screen.blit(speed_surf, (22, 90))
    screen.blit(jump_surf, (150, 90))

    dash_ratio = 1 if dash_cooldown <= 0 else 1 - dash_cooldown / 60
    shield_ratio = 1 if shield_cooldown <= 0 else 1 - shield_cooldown / shield_cooldown_real
    draw_bar(20, 120, 280, 22, dash_ratio, BLUE, "DASH")
    draw_bar(20, 148, 280, 22, shield_ratio, GREEN, "SHIELD")

    if shield:
        ready = small_font.render("ACTIVE", True, GREEN)
    elif shield_cooldown <= 0:
        ready = small_font.render("READY", True, WHITE)
    else:
        ready = small_font.render(str(shield_cooldown), True, WHITE)
    screen.blit(ready, (250, 146))


def draw_info_hub():
    hub_w = 220
    hub_h = 72
    hub_x = WIDTH - hub_w - 12
    hub_y = 12
    draw_box(hub_x, hub_y, hub_w, hub_h, (0, 0, 0), WHITE)

    coins_surf = small_font.render(f"COINS: {coins}", True, YELLOW)
    score_surf = small_font.render(f"SCORE: {score}", True, WHITE)
    screen.blit(coins_surf, (hub_x + 16, hub_y + 14))
    screen.blit(score_surf, (hub_x + 16, hub_y + 40))


def draw_menu():
    draw_box(WIDTH // 2 - 260, 170, 520, 340, (0, 0, 0), WHITE)

    y = 210
    gap = 42

    screen.blit(
        big_font.render("DODGE THE MAGMA", True, WHITE),
        (WIDTH // 2 - 230, y),
    )
    y += 72

    draw_text("[ SPACE ] START", y, BLUE)
    y += gap
    draw_text("[ S ] SHOP", y, GREEN)
    y += gap
    draw_text("[ Q ] EXIT", y, RED)
    y += gap
    draw_text(f"COINS: {coins}", y, YELLOW)


def draw_shop():
    draw_box(WIDTH // 2 - 330, 140, 660, 430, (0, 0, 0), WHITE)

    mouse = pygame.mouse.get_pos()
    items = [
        {
            "rect": pygame.Rect(WIDTH // 2 - 250, 220, 500, 70),
            "key": "1",
            "title": "SPEED +1",
            "cost": 20,
            "color": BLUE,
            "desc": "Faster movement",
        },
        {
            "rect": pygame.Rect(WIDTH // 2 - 250, 305, 500, 70),
            "key": "2",
            "title": "JUMP -2",
            "cost": 30,
            "color": GREEN,
            "desc": "Stronger jump",
        },
        {
            "rect": pygame.Rect(WIDTH // 2 - 250, 390, 500, 70),
            "key": "3",
            "title": "SHIELD UPGRADE",
            "cost": 100,
            "color": YELLOW,
            "desc": "Longer shield",
        },
    ]

    draw_text("=== SHOP ===", 180, YELLOW)

    for item in items:
        hovered = item["rect"].collidepoint(mouse)
        fill = (28, 28, 40) if not hovered else (50, 50, 72)
        border = item["color"] if hovered else WHITE
        pygame.draw.rect(screen, fill, item["rect"], border_radius=12)
        pygame.draw.rect(screen, border, item["rect"], 2, border_radius=12)

        icon = small_font.render(f"[{item['key']}]", True, item["color"])
        title = font.render(item["title"], True, WHITE)
        cost = small_font.render(f"{item['cost']} coins", True, YELLOW)
        desc = small_font.render(item["desc"], True, (180, 180, 190))

        screen.blit(icon, (item["rect"].x + 18, item["rect"].y + 16))
        screen.blit(title, (item["rect"].x + 78, item["rect"].y + 12))
        screen.blit(desc, (item["rect"].x + 78, item["rect"].y + 38))
        screen.blit(cost, (item["rect"].right - cost.get_width() - 18, item["rect"].y + 23))

    draw_text("[ ESC ] BACK", 490, WHITE)
    draw_text(f"COINS: {coins}", 528, YELLOW)


def draw_gameover():
    draw_box(WIDTH // 2 - 260, 160, 520, 380, (0, 0, 0), RED)

    y = 200
    gap = 38

    screen.blit(
        big_font.render("GAME OVER", True, RED),
        (WIDTH // 2 - 150, y),
    )
    y += 72

    draw_text(f"SCORE: {score}", y, WHITE)
    y += gap
    draw_text(f"COINS: {coins}", y, YELLOW)
    y += gap
    draw_text("[ SPACE ] RETRY", y, BLUE)
    y += gap
    draw_text("[ M ] MENU", y, GREEN)
    y += gap
    draw_text("[ S ] SHOP", y, YELLOW)
    y += gap
    draw_text("[ Q ] EXIT", y, WHITE)
    if pygame.time.get_ticks() < gameover_input_unlock_at:
        draw_text("Please wait...", y + 36, (180, 180, 180), small_font)


# ---------- LOOP ----------
while True:
    clock.tick(60)
    tick = pygame.time.get_ticks()

    # background grid
    screen.fill(BG)
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, GRID, (0, y), (WIDTH, y))

    # ---------- COMMAND SYSTEM ----------
    with command_lock:
        cmd = command
        command = ""

    if cmd:
        cmd = cmd.lower().strip()

        if cmd == "exit":
            save_game()
            pygame.quit()
            sys.exit()
        elif cmd == "money":
            coins += 100
            queue_save()
            print("+100 coins")
        elif cmd == "god":
            shield = True
            shield_time = 999999
            print("GOD MODE")
        elif cmd == "speed":
            player_speed += 5
            queue_save()
            print("Speed boosted")
        elif cmd == "reset":
            coins = 0
            player_speed = 8
            queue_save()
            print("Reset done")
        else:
            print("Unknown:", cmd)

    if save_dirty and tick - last_save_tick >= AUTO_SAVE_INTERVAL:
        save_game()

    # ---------- EVENTS ----------
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            save_game()
            pygame.quit()
            sys.exit()

        if e.type == pygame.KEYDOWN:
            if game_state == "menu":
                if e.key == pygame.K_SPACE:
                    reset_run()
                if e.key == pygame.K_s:
                    game_state = "shop"
                if e.key == pygame.K_q:
                    save_game()
                    sys.exit()

            elif game_state == "shop":
                if e.key == pygame.K_1 and coins >= 20:
                    player_speed += 1
                    coins -= 20
                    queue_save()
                if e.key == pygame.K_2 and coins >= 30:
                    jump_strength -= 2
                    coins -= 30
                    queue_save()
                if e.key == pygame.K_3 and coins >= 100:
                    shield_cooldown_real = max(120, shield_cooldown_real - 10)
                    shield_time_real += 10
                    coins -= 100
                    queue_save()
                if e.key == pygame.K_ESCAPE:
                    game_state = "menu"

            elif game_state == "gameover":
                if tick >= gameover_input_unlock_at:
                    if e.key == pygame.K_SPACE:
                        reset_run()
                    if e.key == pygame.K_m:
                        game_state = "menu"
                    if e.key == pygame.K_s:
                        game_state = "shop"
                    if e.key == pygame.K_q:
                        save_game()
                        sys.exit()

            elif game_state == "game":
                if e.key == pygame.K_SPACE:
                    jump_buffer_time = jump_buffer_max
                if e.key == pygame.K_q and dash_cooldown <= 0:
                    dash_velocity = 19 * facing
                    dash_duration = 12
                    dash_cooldown = 60
                if e.key == pygame.K_e and shield_cooldown <= 0:
                    shield = True
                    shield_time = shield_time_real
                    shield_cooldown = shield_cooldown_real

        if e.type == pygame.KEYUP and game_state == "game":
            if e.key == pygame.K_SPACE:
                jump_hold_time = 0

    # ---------- GAME ----------
    if game_state == "game":
        keys = pygame.key.get_pressed()
        on_ground = player.bottom >= HEIGHT - 50

        # facing and movement
        move_dir = 0
        if keys[pygame.K_a]:
            move_dir -= 1
        if keys[pygame.K_d]:
            move_dir += 1

        run_max_speed = player_speed
        if move_dir != 0:
            facing = move_dir
            player_vx += move_dir * run_accel
        else:
            player_vx *= run_friction

        player_vx = clamp(player_vx, -run_max_speed, run_max_speed)
        player_pos_x += player_vx
        player.x = int(player_pos_x)

        if player.x < 0:
            player.x = 0
            player_pos_x = float(player.x)
            player_vx = 0
        if player.right > WIDTH:
            player.right = WIDTH
            player_pos_x = float(player.x)
            player_vx = 0

        # variable jump: hold SPACE for a little extra lift
        if keys[pygame.K_SPACE] and jump_hold_time > 0 and velocity_y < 0:
            velocity_y -= 0.75
            jump_hold_time -= 1

        if jump_buffer_time > 0:
            jump_buffer_time -= 1
            if on_ground or coyote_time > 0 or jumps_left > 0:
                velocity_y = jump_strength
                if on_ground or coyote_time > 0:
                    jumps_left = max(0, jumps_left - 1)
                else:
                    jumps_left -= 1
                jump_hold_time = jump_hold_max
                jump_buffer_time = 0

        velocity_y += gravity
        player_pos_y += velocity_y
        player.y = int(player_pos_y)

        if player.bottom >= HEIGHT - 50:
            player.bottom = HEIGHT - 50
            player_pos_y = float(player.y)
            velocity_y = 0
            jumps_left = max_jumps
            jump_hold_time = 0
            coyote_time = coyote_max
        else:
            coyote_time = max(0, coyote_time - 1)

        # dash with wall bounce
        if dash_duration > 0:
            dash_velocity *= 0.95
            player_pos_x += dash_velocity
            player.x = int(player_pos_x)
            dash_duration -= 1

            hit_wall = False
            if player.left <= 0:
                player.left = 0
                player_pos_x = float(player.x)
                hit_wall = True
            elif player.right >= WIDTH:
                player.right = WIDTH
                player_pos_x = float(player.x)
                hit_wall = True

            if hit_wall:
                dash_velocity *= -0.65
                dash_duration = max(0, dash_duration - 2)
                facing = 1 if dash_velocity >= 0 else -1
                dash_trail.append(
                    {
                        "rect": player.copy(),
                        "life": 12,
                        "color": (120, 210, 255),
                    }
                )

        if dash_cooldown > 0:
            dash_cooldown -= 1

        # shield
        if shield:
            shield_time -= 1
            shield_flash = 10
            if shield_time <= 0:
                shield = False
        if shield_cooldown > 0:
            shield_cooldown -= 1
        if shield_flash > 0:
            shield_flash -= 1

        # spawn
        if tick >= next_magma_spawn:
            spawn_magma_pattern()
            next_magma_spawn = tick + random.randint(380, 700)

        if tick >= next_coin_spawn:
            spawn_coin_pattern()
            next_coin_spawn = tick + random.randint(850, 1350)

        # magma speed ramps with score
        magma_speed = min(13, 6.2 + score * 0.06)

        # magma
        magma_to_remove = []
        for m in magma_list:
            m.y += magma_speed
            if m.colliderect(player):
                if shield:
                    magma_to_remove.append(m)
                    shield_flash = 14
                else:
                    coins += score
                    queue_save()
                    game_state = "gameover"
                    gameover_input_unlock_at = tick + 180
                    break
            elif m.top > HEIGHT:
                magma_to_remove.append(m)
                score += 1
        if magma_to_remove:
            removed_ids = {id(m) for m in magma_to_remove}
            magma_list = [m for m in magma_list if id(m) not in removed_ids]

        # coin
        collected_coins = 0
        next_coin_list = []
        for c in coin_list:
            c.y += 5
            if c.colliderect(player):
                collected_coins += 1
            elif c.top > HEIGHT:
                continue
            else:
                next_coin_list.append(c)
        if collected_coins:
            coins += collected_coins
            queue_save()
        coin_list = next_coin_list

        # trail particles
        next_dash_trail = []
        for p in dash_trail:
            p["life"] -= 1
            if p["life"] > 0:
                next_dash_trail.append(p)
        dash_trail = next_dash_trail

        # draw trail
        for p in dash_trail:
            rect = p["rect"]
            alpha = int(20 + p["life"] * 8)
            glow = get_trail_surface((rect.width, rect.height), alpha)
            screen.blit(glow, (rect.x - 15, rect.y - 15))

        # draw world
        for m in magma_list:
            draw_magma(m)

        for c in coin_list:
            draw_coin(c, tick)

        draw_player()

        if shield:
            pulse = 28 + int((math.sin(tick * 0.03) + 1) * 2)
            draw_glow_circle(player.center, pulse, GREEN, 75)
            pygame.draw.circle(screen, GREEN, player.center, pulse, 3)
        elif shield_flash > 0:
            draw_glow_circle(player.center, 28 + shield_flash, BLUE, 60)

        draw_hud()

    elif game_state == "menu":
        draw_menu()
        draw_info_hub()

    elif game_state == "shop":
        draw_shop()
        draw_info_hub()

    elif game_state == "gameover":
        draw_gameover()
        draw_info_hub()

    pygame.display.flip()
