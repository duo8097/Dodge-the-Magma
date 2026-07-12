import asyncio
import os
import ctypes
import math
import pygame
import random
import sys
import json
import platform
from functools import lru_cache

from ui_layout import (
    get_action_rects as layout_action_rects,
    get_gameover_button_rects as layout_gameover_button_rects,
    get_joy_origin as layout_joy_origin,
    get_menu_button_rects as layout_menu_button_rects,
    get_pause_btn_rect as layout_pause_btn_rect,
    get_pause_menu_rects as layout_pause_menu_rects,
    get_shop_back_rect as layout_shop_back_rect,
    get_shop_item_rects as layout_shop_item_rects,
    ui,
)

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS and hasattr(ctypes, "windll"):
    ctypes.windll.user32.SetProcessDPIAware()
pygame.init()

# ---------- SAVE ----------
SAVE_FILE = "save.json"
TARGET_FPS = 60
FRAME_MS = 1000 / TARGET_FPS
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
MIN_WIDTH = 640
MIN_HEIGHT = 480
JUMP_STRENGTH_MIN = -36
JUMP_STRENGTH_MAX = -12
GROUND_OFFSET = 90
PLAYER_SIZE = 50
MAGMA_SIZE = 30
COIN_SIZE = 20
DASH_SPEED = 19
MAGMA_BASE_SPEED = 6.2
MAGMA_MAX_SPEED = 13
MAGMA_SCORE_SCALE = 0.06
COIN_FALL_SPEED = 5
SHOP_ITEMS = [
    {
        "key": pygame.K_1,
        "label": "1",
        "title": "SPEED +1",
        "cost": 20,
        "color": (100, 200, 255),
        "desc": "Faster movement",
    },
    {
        "key": pygame.K_2,
        "label": "2",
        "title": "JUMP -2",
        "cost": 30,
        "color": (80, 255, 120),
        "desc": "Stronger jump",
    },
    {
        "key": pygame.K_3,
        "label": "3",
        "title": "SHIELD UPGRADE",
        "cost": 100,
        "color": (255, 220, 70),
        "desc": "Longer shield",
    },
]

coins = 0
player_speed = 8
jump_strength = -22
shield_cooldown_real = 300
shield_time_real = 120
save_dirty = False
last_save_tick = 0
AUTO_SAVE_INTERVAL = 5000
magma_glow_surface = None
SAVE_CACHE = None
SAVE_ERROR_LOG = []
SAVE_ERROR_LOG_MAX = 8
last_save_error = ""


def log_save_error(message):
    global last_save_error
    last_save_error = message
    SAVE_ERROR_LOG.append(message)
    if len(SAVE_ERROR_LOG) > SAVE_ERROR_LOG_MAX:
        del SAVE_ERROR_LOG[0]
    print(f"[save] {message}", file=sys.stderr)


def clamp_jump_value(value):
    return clamp(value, JUMP_STRENGTH_MIN, JUMP_STRENGTH_MAX)


def normalize_player_stats():
    global jump_strength
    jump_strength = clamp_jump_value(jump_strength)


def save_game():
    global save_dirty, last_save_tick, SAVE_CACHE, last_save_error
    data = {
        "coins": coins,
        "player_speed": player_speed,
        "jump_strength": jump_strength,
        "shield_cooldown_real": shield_cooldown_real,
        "shield_time_real": shield_time_real,
    }
    SAVE_CACHE = data
    try:
        temp_file = f"{SAVE_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, SAVE_FILE)
        saved_to_disk = True
        last_save_error = ""
    except OSError as exc:
        saved_to_disk = False
        log_save_error(f"save failed: {exc}")
    save_dirty = False
    last_save_tick = pygame.time.get_ticks()
    return saved_to_disk


def queue_save():
    global save_dirty
    save_dirty = True


def load_game():
    global coins, player_speed, jump_strength, SAVE_CACHE
    global shield_cooldown_real, shield_time_real
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        data = SAVE_CACHE
    except Exception as exc:
        log_save_error(f"load failed: {exc}")
        data = None

    if not data:
        return

    coins = data.get("coins", coins)
    player_speed = data.get("player_speed", player_speed)
    jump_strength = data.get("jump_strength", jump_strength)
    shield_cooldown_real = data.get(
        "shield_cooldown_real", shield_cooldown_real
    )
    shield_time_real = data.get("shield_time_real", shield_time_real)
    normalize_player_stats()


def get_safe_window_resolution():
    display_info = pygame.display.Info()
    return (
        max(MIN_WIDTH, display_info.current_w or DEFAULT_WIDTH),
        max(MIN_HEIGHT, display_info.current_h or DEFAULT_HEIGHT),
    )


def run_startup_screen(startup):
    return (*get_safe_window_resolution(), False)


# ---------- SCREEN ----------
WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT

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
CONSOLE_BG = (0, 0, 0, 210)
CONSOLE_TEXT = (200, 200, 220)
CONSOLE_CMD = (100, 200, 255)
CONSOLE_OK = (80, 255, 120)
CONSOLE_ERR = (255, 80, 70)
CONSOLE_INFO = (140, 140, 180)
CONSOLE_MAX_LINES = 8
JOY_RADIUS = 55
JOY_KNOB_R = 22
JOY_DEAD = 0.15
JOY_JUMP_THRESHOLD = -0.5

clock = pygame.time.Clock()
screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT))
info = pygame.display.Info()
WIDTH = max(MIN_WIDTH, info.current_w or screen.get_width())
HEIGHT = max(MIN_HEIGHT, info.current_h or screen.get_height())
if screen.get_size() != (WIDTH, HEIGHT):
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
UI_SCALE = WIDTH / 1280
font = pygame.font.SysFont("Consolas", ui(28, UI_SCALE))
small_font = pygame.font.SysFont("Consolas", ui(22, UI_SCALE))
big_font = pygame.font.SysFont("Consolas", ui(48, UI_SCALE))

pygame.display.set_caption("DODGE THE MAGMA")
if IS_WINDOWS and hasattr(ctypes, "windll"):
    window_info = pygame.display.get_wm_info()
    hwnd = window_info.get("window")
    if hwnd:
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

load_game()

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


@lru_cache(maxsize=64)
def get_glow_surface(radius, color, alpha):
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
    return surface


def get_magma_glow_surface():
    global magma_glow_surface
    if magma_glow_surface is None:
        magma_glow_surface = pygame.Surface((72, 72), pygame.SRCALPHA)
        pygame.draw.circle(magma_glow_surface, (255, 110, 50, 80), (36, 36), 18)
        pygame.draw.circle(magma_glow_surface, (255, 70, 40, 50), (36, 36), 26)
    return magma_glow_surface


@lru_cache(maxsize=96)
def get_trail_surface(size, alpha):
    surface = pygame.Surface((size[0] + 30, size[1] + 30), pygame.SRCALPHA)
    pygame.draw.rect(
        surface,
        (120, 210, 255, alpha),
        (15, 15, size[0], size[1]),
        border_radius=12,
    )
    return surface


def draw_glow_circle(center, radius, color, alpha=70):
    glow = get_glow_surface(radius, color, alpha)
    screen.blit(glow, (center[0] - radius * 2, center[1] - radius * 2))


def sync_player_x(reset_velocity=False):
    global player_pos_x, player_vx
    max_x = WIDTH - player.width
    clamped_x = clamp(player_pos_x, 0.0, float(max_x))
    hit_wall = clamped_x != player_pos_x
    player_pos_x = clamped_x
    player.x = int(player_pos_x)
    if hit_wall and reset_velocity:
        player_vx = 0.0
    return hit_wall


def reset_run():
    global score, game_state, velocity_y, jumps_left, jump_hold_time
    global player_vx, player_pos_x, player_pos_y, coyote_time, jump_buffer_time
    global dash_velocity, dash_duration, dash_cooldown, dash_trail
    global shield, shield_time, shield_cooldown, shield_flash
    global magma_list, coin_list, next_magma_spawn, next_coin_spawn
    global player, facing, gameover_input_unlock_at, joy_knob

    score = 0
    game_state = "game"
    gameover_input_unlock_at = 0
    player.x = WIDTH // 2
    player.bottom = HEIGHT - GROUND_OFFSET
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
    joy_knob = get_joy_origin()
    reset_joy()
    normalize_player_stats()


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
        pieces.append(pygame.Rect(clamp(spawn_x, 0, WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE))
        pieces.append(
            pygame.Rect(clamp(spawn_x + offset, 0, WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE)
        )
    elif pattern == "cluster":
        offsets = [-44, -12, 20, 52]
        for off in random.sample(offsets, k=random.randint(3, 4)):
            pieces.append(
                pygame.Rect(clamp(spawn_x + off, 0, WIDTH - MAGMA_SIZE), -MAGMA_SIZE, MAGMA_SIZE, MAGMA_SIZE)
            )
    else:
        lane = random.randint(0, 3)
        for i in range(4):
            x = clamp(spawn_x + (i - lane) * 34, 0, WIDTH - MAGMA_SIZE)
            pieces.append(pygame.Rect(x, -MAGMA_SIZE - i * 10, MAGMA_SIZE, MAGMA_SIZE))

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
        coins_to_add.append(pygame.Rect(base_x, base_y, COIN_SIZE, COIN_SIZE))
    elif pattern == "zigzag":
        for i in range(5):
            x = clamp(base_x + (-1) ** i * (18 + i * 2), 0, WIDTH - COIN_SIZE)
            y = base_y - i * 22
            coins_to_add.append(pygame.Rect(x, y, COIN_SIZE, COIN_SIZE))
    elif pattern == "line":
        for i in range(4):
            x = clamp(base_x + i * 26, 0, WIDTH - COIN_SIZE)
            coins_to_add.append(pygame.Rect(x, base_y - i * 8, COIN_SIZE, COIN_SIZE))
    else:
        for i in range(3):
            x = clamp(base_x + i * 34 - 34, 0, WIDTH - COIN_SIZE)
            y = base_y - abs(i - 1) * 18
            coins_to_add.append(pygame.Rect(x, y, COIN_SIZE, COIN_SIZE))

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
player = pygame.Rect(WIDTH // 2, HEIGHT - 100, PLAYER_SIZE, PLAYER_SIZE)
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
console_open = False
console_input = ""
console_log = []
joy_active = False
joy_knob = (0.0, 0.0)
joy_dx = 0.0
joy_dy = 0.0
joy_jumped = False


def update_timer(value, amount):
    return max(0.0, value - amount)


def console_exec(cmd):
    global coins, player_speed, shield, shield_time, jump_strength
    cmd = cmd.strip().lower()
    if cmd == "money":
        coins += 100
        queue_save()
        return ("+100 coins", CONSOLE_OK)
    if cmd == "god":
        shield = True
        shield_time = 999999
        return ("god mode ON", CONSOLE_OK)
    if cmd == "speed":
        player_speed += 2
        queue_save()
        return (f"speed -> {player_speed}", CONSOLE_OK)
    if cmd == "reset":
        coins = 0
        player_speed = 8
        jump_strength = -22
        normalize_player_stats()
        queue_save()
        return ("reset done", CONSOLE_OK)
    if cmd == "help":
        return (" reset | exit | save | help", CONSOLE_INFO)
    if cmd == "exit":
        save_game()
        return ("closing run", CONSOLE_INFO)
    if cmd == "save":
        saved_to_disk = save_game()
        return (
            "save synced to save.json"
            if saved_to_disk
            else f"save cached in memory ({last_save_error or 'disk unavailable'})",
            CONSOLE_OK,
        )
    if cmd == "":
        return None
    return (f"unknown: {cmd}", CONSOLE_ERR)


def draw_console():
    h = 180
    y0 = HEIGHT - h
    overlay = pygame.Surface((WIDTH, h), pygame.SRCALPHA)
    overlay.fill(CONSOLE_BG)
    screen.blit(overlay, (0, y0))
    pygame.draw.line(screen, (60, 60, 120), (0, y0), (WIDTH, y0), 1)

    header = small_font.render("CHEAT CONSOLE  [ ESC close ]", True, CONSOLE_INFO)
    screen.blit(header, (14, y0 + 8))

    line_h = 22
    start_y = y0 + 32
    for i, (text, color) in enumerate(console_log[-CONSOLE_MAX_LINES:]):
        line_surface = small_font.render(text, True, color)
        screen.blit(line_surface, (14, start_y + i * line_h))

    input_y = HEIGHT - 30
    pygame.draw.line(screen, (60, 60, 120), (0, input_y - 4), (WIDTH, input_y - 4), 1)
    prompt = small_font.render("$ " + console_input, True, CONSOLE_CMD)
    screen.blit(prompt, (14, input_y))

    if (pygame.time.get_ticks() // 500) % 2 == 0:
        cursor_x = 14 + prompt.get_width() + 2
        pygame.draw.rect(screen, CONSOLE_CMD, (cursor_x, input_y + 2, 2, 18))


def get_joy_origin():
    return layout_joy_origin(HEIGHT, UI_SCALE, JOY_RADIUS)


def update_joy(mx, my):
    global joy_dx, joy_dy, joy_knob
    center_x, center_y = get_joy_origin()
    offset_x = mx - center_x
    offset_y = my - center_y
    distance = math.sqrt(offset_x * offset_x + offset_y * offset_y)
    clamped = min(distance, JOY_RADIUS - JOY_KNOB_R)
    angle = math.atan2(offset_y, offset_x)
    joy_knob = (
        center_x + math.cos(angle) * clamped,
        center_y + math.sin(angle) * clamped,
    )
    raw_dx = offset_x / JOY_RADIUS
    raw_dy = offset_y / JOY_RADIUS
    joy_dx = 0.0 if abs(raw_dx) < JOY_DEAD else clamp(raw_dx, -1.0, 1.0)
    joy_dy = 0.0 if abs(raw_dy) < JOY_DEAD else clamp(raw_dy, -1.0, 1.0)


def reset_joy():
    global joy_active, joy_dx, joy_dy, joy_jumped
    joy_active = False
    joy_dx = 0.0
    joy_dy = 0.0
    joy_jumped = False


def draw_joystick():
    center_x, center_y = get_joy_origin()
    overlay = pygame.Surface((JOY_RADIUS * 2 + 8, JOY_RADIUS * 2 + 8), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (0, 0, 0, 100), (JOY_RADIUS + 4, JOY_RADIUS + 4), JOY_RADIUS)
    screen.blit(overlay, (center_x - JOY_RADIUS - 4, center_y - JOY_RADIUS - 4))
    pygame.draw.circle(screen, (40, 40, 60), (center_x, center_y), JOY_RADIUS, 1)
    pygame.draw.circle(screen, (60, 60, 90), (center_x, center_y), 3)
    knob_x, knob_y = (int(joy_knob[0]), int(joy_knob[1])) if joy_active else (center_x, center_y)
    knob_color = (200, 200, 220) if joy_active else (80, 80, 110)
    pygame.draw.circle(screen, knob_color, (knob_x, knob_y), JOY_KNOB_R)
    pygame.draw.circle(
        screen,
        (255, 255, 255) if joy_active else (100, 100, 140),
        (knob_x, knob_y),
        JOY_KNOB_R,
        2,
    )


def get_action_rects():
    return layout_action_rects(WIDTH, HEIGHT, UI_SCALE)


joy_knob = get_joy_origin()


def draw_action_btns():
    shield_rect, dash_rect = get_action_rects()
    shield_color = GREEN if (shield or shield_cooldown <= 0) else (58, 58, 90)
    pygame.draw.circle(screen, (0, 0, 0), shield_rect.center, shield_rect.w // 2)
    pygame.draw.circle(screen, shield_color, shield_rect.center, shield_rect.w // 2, 2)
    shield_label = small_font.render("SHLD", True, shield_color)
    screen.blit(shield_label, shield_label.get_rect(center=shield_rect.center))

    dash_color = BLUE if dash_cooldown <= 0 else (58, 58, 90)
    pygame.draw.circle(screen, (0, 0, 0), dash_rect.center, dash_rect.w // 2)
    pygame.draw.circle(screen, dash_color, dash_rect.center, dash_rect.w // 2, 2)
    dash_label = small_font.render("DASH", True, dash_color)
    screen.blit(dash_label, dash_label.get_rect(center=dash_rect.center))


def get_pause_btn_rect():
    return layout_pause_btn_rect(WIDTH, UI_SCALE)


def draw_pause_btn():
    rect = get_pause_btn_rect()
    pygame.draw.rect(screen, (0, 0, 0), rect, border_radius=8)
    pygame.draw.rect(screen, WHITE, rect, 1, border_radius=8)
    label = small_font.render("II", True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))


def get_menu_button_rects():
    return layout_menu_button_rects(WIDTH, UI_SCALE)


def get_shop_item_rects():
    return layout_shop_item_rects(WIDTH, UI_SCALE)


def get_shop_back_rect():
    return layout_shop_back_rect(WIDTH, UI_SCALE)


def get_pause_menu_rects():
    return layout_pause_menu_rects(WIDTH, UI_SCALE)


def get_gameover_button_rects():
    return layout_gameover_button_rects(WIDTH, UI_SCALE)


# ---------- UI ----------
def draw_hud():
    panel_x = 10
    panel_y = 10
    draw_box(panel_x, panel_y, 320, 108, (0, 0, 0), WHITE)

    score_surf = font.render(f"SCORE: {score}", True, WHITE)
    coin_surf = font.render(f"COINS: {coins}", True, YELLOW)
    speed_surf = small_font.render(f"SPD: {player_speed}", True, BLUE)
    jump_surf = small_font.render(f"JUMPS: {jumps_left}/{max_jumps}", True, GREEN)
    screen.blit(score_surf, (22, 20))
    screen.blit(coin_surf, (22, 52))
    screen.blit(speed_surf, (22, 90))
    screen.blit(jump_surf, (150, 90))


def draw_ability_bar():
    icon_size = 34
    bar_w = 110
    bar_h = 12
    slot_gap = 24
    icon_bar_gap = 10
    slot_w = icon_size + icon_bar_gap + bar_w

    slots = [
        {
            "label": "DASH",
            "key": "TAP",
            "ratio": 1.0 if dash_cooldown <= 0 else 1 - dash_cooldown / 60,
            "color": BLUE,
            "active": dash_cooldown <= 0,
        },
        {
            "label": "SHIELD",
            "key": "TAP",
            "ratio": 1.0 if shield_cooldown <= 0 else 1 - shield_cooldown / shield_cooldown_real,
            "color": GREEN,
            "active": shield or shield_cooldown <= 0,
        },
    ]

    total_w = slot_w * 2 + slot_gap
    start_x = WIDTH // 2 - total_w // 2
    center_y = HEIGHT - 55

    for i, slot in enumerate(slots):
        x = start_x + i * (slot_w + slot_gap)

        # --- icon: can giua doc ---
        icon_y = center_y - icon_size // 2
        icon_border = slot["color"] if slot["active"] else (58, 58, 90)
        icon_bg = (10, 22, 12) if slot["color"] == GREEN else (10, 16, 32)
        icon_bg = icon_bg if slot["active"] else (17, 17, 34)
        pygame.draw.rect(screen, icon_bg, (x, icon_y, icon_size, icon_size), border_radius=6)
        pygame.draw.rect(screen, icon_border, (x, icon_y, icon_size, icon_size), 1, border_radius=6)

        if slot["active"]:
            pygame.draw.circle(screen, slot["color"], (x + icon_size - 6, icon_y + 6), 3)

        # --- text + bar: ben phai icon ---
        bar_x = x + icon_size + icon_bar_gap

        label_h = small_font.get_height()
        key_h = small_font.get_height()
        content_h = label_h + 4 + bar_h + 4 + key_h
        text_y = center_y - content_h // 2

        label_surface = small_font.render(slot["label"], True, (180, 180, 210))
        screen.blit(label_surface, (bar_x, text_y))

        bar_y = text_y + label_h + 4
        pygame.draw.rect(screen, (26, 26, 46), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(screen, (58, 58, 90), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

        fill_w = max(0, int(bar_w * clamp(slot["ratio"], 0, 1)))
        if fill_w > 0:
            pygame.draw.rect(screen, slot["color"], (bar_x, bar_y, fill_w, bar_h), border_radius=6)

        key_surface = small_font.render(slot["key"], True, (90, 90, 120))
        screen.blit(key_surface, (bar_x, bar_y + bar_h + 4))


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
    buttons = get_menu_button_rects()

    y = 210
    gap = 42

    screen.blit(
        big_font.render("DODGE THE MAGMA", True, WHITE),
        (WIDTH // 2 - 230, y),
    )
    y += 72

    for key, color, label in (
        ("start", BLUE, "START"),
        ("shop", GREEN, "SHOP"),
        ("exit", RED, "EXIT"),
    ):
        rect = buttons[key]
        pygame.draw.rect(screen, (18, 18, 30), rect, border_radius=10)
        pygame.draw.rect(screen, color, rect, 2, border_radius=10)
        text = font.render(label, True, WHITE)
        screen.blit(text, text.get_rect(center=rect.center))
        y += gap
    draw_text(f"COINS: {coins}", y, YELLOW)


def draw_shop():
    draw_box(WIDTH // 2 - 330, 140, 660, 430, (0, 0, 0), WHITE)

    mouse = pygame.mouse.get_pos()
    item_rects = get_shop_item_rects()
    back_rect = get_shop_back_rect()

    draw_text("=== SHOP ===", 180, YELLOW)

    for item, item_rect in zip(SHOP_ITEMS, item_rects):
        hovered = item_rect.collidepoint(mouse)
        fill = (28, 28, 40) if not hovered else (50, 50, 72)
        border = item["color"] if hovered else WHITE
        pygame.draw.rect(screen, fill, item_rect, border_radius=12)
        pygame.draw.rect(screen, border, item_rect, 2, border_radius=12)

        icon = small_font.render(f"[{item['label']}]", True, item["color"])
        title = font.render(item["title"], True, WHITE)
        cost = small_font.render(f"{item['cost']} coins", True, YELLOW)
        desc = small_font.render(item["desc"], True, (180, 180, 190))

        screen.blit(icon, (item_rect.x + 18, item_rect.y + 16))
        screen.blit(title, (item_rect.x + 78, item_rect.y + 12))
        screen.blit(desc, (item_rect.x + 78, item_rect.y + 38))
        screen.blit(cost, (item_rect.right - cost.get_width() - 18, item_rect.y + 23))

    pygame.draw.rect(screen, (18, 18, 30), back_rect, border_radius=10)
    pygame.draw.rect(screen, WHITE, back_rect, 2, border_radius=10)
    back_text = small_font.render("BACK", True, WHITE)
    screen.blit(back_text, back_text.get_rect(center=back_rect.center))
    draw_text(f"COINS: {coins}", 528, YELLOW)


def draw_pause():
    draw_box(WIDTH // 2 - 250, 180, 500, 260, (0, 0, 0), BLUE)
    buttons = get_pause_menu_rects()
    draw_text("PAUSED", 225, BLUE, big_font)
    for key, color, label in (
        ("resume", WHITE, "RESUME"),
        ("menu", GREEN, "MENU"),
        ("quit", RED, "SAVE & QUIT"),
    ):
        rect = buttons[key]
        pygame.draw.rect(screen, (18, 18, 30), rect, border_radius=10)
        pygame.draw.rect(screen, color, rect, 2, border_radius=10)
        text = small_font.render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))


def draw_gameover():
    draw_box(WIDTH // 2 - 260, 160, 520, 380, (0, 0, 0), RED)
    buttons = get_gameover_button_rects()

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
    for key, color, label in (
        ("retry", BLUE, "RETRY"),
        ("menu", GREEN, "MENU"),
        ("shop", YELLOW, "SHOP"),
        ("quit", WHITE, "EXIT"),
    ):
        rect = buttons[key]
        pygame.draw.rect(screen, (18, 18, 30), rect, border_radius=10)
        pygame.draw.rect(screen, color, rect, 2, border_radius=10)
        text = small_font.render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))
        y += gap
    if pygame.time.get_ticks() < gameover_input_unlock_at:
        draw_text("Please wait...", y + 36, (180, 180, 180), small_font)


# ---------- LOOP ----------
async def main():
    global coin_list, dash_trail, game_state, gameover_input_unlock_at
    global coins, player_speed, jump_strength, shield_cooldown_real, shield_time_real
    global console_open, console_input, jump_buffer_time
    global dash_velocity, dash_duration, dash_cooldown, shield, shield_time
    global shield_cooldown, jump_hold_time, facing, player_vx, player_pos_x
    global player_pos_y, velocity_y, jumps_left, coyote_time, shield_flash
    global magma_list, next_magma_spawn, next_coin_spawn, score
    global joy_active, joy_jumped

    running = True
    while running:
        dt = min(2.0, clock.tick(TARGET_FPS) / FRAME_MS)
        tick = pygame.time.get_ticks()

        screen.fill(BG)
        grid_step = max(24, ui(40, UI_SCALE))
        for x in range(0, WIDTH, grid_step):
            pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, grid_step):
            pygame.draw.line(screen, GRID, (0, y), (WIDTH, y))

        if save_dirty and tick - last_save_tick >= AUTO_SAVE_INTERVAL:
            save_game()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                save_game()
                return

            if e.type == pygame.MOUSEBUTTONDOWN and not console_open:
                mouse_x, mouse_y = e.pos

                if game_state == "menu":
                    menu_buttons = get_menu_button_rects()
                    if menu_buttons["start"].collidepoint(mouse_x, mouse_y):
                        reset_run()
                    elif menu_buttons["shop"].collidepoint(mouse_x, mouse_y):
                        game_state = "shop"
                    elif menu_buttons["exit"].collidepoint(mouse_x, mouse_y):
                        save_game()
                        return

                elif game_state == "shop":
                    for item, item_rect in zip(SHOP_ITEMS, get_shop_item_rects()):
                        if item_rect.collidepoint(mouse_x, mouse_y) and coins >= item["cost"]:
                            if item["label"] == "1":
                                player_speed += 1
                            elif item["label"] == "2":
                                jump_strength = clamp_jump_value(jump_strength - 2)
                            else:
                                shield_cooldown_real = max(120, shield_cooldown_real - 10)
                                shield_time_real += 10
                            coins -= item["cost"]
                            queue_save()
                    if get_shop_back_rect().collidepoint(mouse_x, mouse_y):
                        game_state = "menu"

                elif game_state == "pause":
                    pause_buttons = get_pause_menu_rects()
                    if pause_buttons["resume"].collidepoint(mouse_x, mouse_y):
                        game_state = "game"
                    elif pause_buttons["menu"].collidepoint(mouse_x, mouse_y):
                        game_state = "menu"
                        reset_joy()
                    elif pause_buttons["quit"].collidepoint(mouse_x, mouse_y):
                        save_game()
                        return

                elif game_state == "gameover":
                    if tick >= gameover_input_unlock_at:
                        gameover_buttons = get_gameover_button_rects()
                        if gameover_buttons["retry"].collidepoint(mouse_x, mouse_y):
                            reset_run()
                        elif gameover_buttons["menu"].collidepoint(mouse_x, mouse_y):
                            game_state = "menu"
                        elif gameover_buttons["shop"].collidepoint(mouse_x, mouse_y):
                            game_state = "shop"
                        elif gameover_buttons["quit"].collidepoint(mouse_x, mouse_y):
                            save_game()
                            return

                elif game_state == "game":
                    if get_pause_btn_rect().collidepoint(mouse_x, mouse_y):
                        game_state = "pause"
                        reset_joy()
                        continue

                    shield_rect, dash_rect = get_action_rects()
                    joy_center_x, joy_center_y = get_joy_origin()
                    joy_distance = math.sqrt((mouse_x - joy_center_x) ** 2 + (mouse_y - joy_center_y) ** 2)

                    if joy_distance <= JOY_RADIUS + 20:
                        joy_active = True
                        update_joy(mouse_x, mouse_y)

                    if shield_rect.collidepoint(mouse_x, mouse_y) and shield_cooldown <= 0:
                        shield = True
                        shield_time = shield_time_real
                        shield_cooldown = shield_cooldown_real

                    if dash_rect.collidepoint(mouse_x, mouse_y) and dash_cooldown <= 0:
                        dash_velocity = DASH_SPEED * facing
                        dash_duration = 12
                        dash_cooldown = 60

            if e.type == pygame.MOUSEMOTION and joy_active and game_state == "game":
                update_joy(*e.pos)

            if e.type == pygame.MOUSEBUTTONUP:
                reset_joy()

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKQUOTE:
                    console_open = not console_open
                    console_input = ""
                    continue

                if console_open:
                    if e.key == pygame.K_ESCAPE:
                        console_open = False
                        console_input = ""
                    elif e.key == pygame.K_RETURN:
                        result = console_exec(console_input)
                        if result:
                            console_log.append((f"$ {console_input}", CONSOLE_CMD))
                            console_log.append(result)
                            if result[0] == "closing run":
                                return
                        console_input = ""
                    elif e.key == pygame.K_BACKSPACE:
                        console_input = console_input[:-1]
                    elif e.unicode and e.unicode.isprintable():
                        console_input += e.unicode
                    continue

                if game_state == "menu":
                    if e.key == pygame.K_SPACE:
                        reset_run()
                    if e.key == pygame.K_s:
                        game_state = "shop"
                    if e.key == pygame.K_q:
                        save_game()
                        return

                elif game_state == "shop":
                    if e.key == pygame.K_1 and coins >= 20:
                        player_speed += 1
                        coins -= 20
                        queue_save()
                    if e.key == pygame.K_2 and coins >= 30:
                        jump_strength = clamp_jump_value(jump_strength - 2)
                        coins -= 30
                        queue_save()
                    if e.key == pygame.K_3 and coins >= 100:
                        shield_cooldown_real = max(120, shield_cooldown_real - 10)
                        shield_time_real += 10
                        coins -= 100
                        queue_save()
                    if e.key == pygame.K_ESCAPE:
                        game_state = "menu"

                elif game_state == "pause":
                    if e.key == pygame.K_ESCAPE:
                        game_state = "game"
                    if e.key == pygame.K_m:
                        game_state = "menu"
                    if e.key == pygame.K_q:
                        save_game()
                        return

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
                            return

                elif game_state == "game":
                    if e.key == pygame.K_SPACE:
                        jump_buffer_time = jump_buffer_max
                    if e.key == pygame.K_q and dash_cooldown <= 0:
                        dash_velocity = DASH_SPEED * facing
                        dash_duration = 12
                        dash_cooldown = 60
                    if e.key == pygame.K_e and shield_cooldown <= 0:
                        shield = True
                        shield_time = shield_time_real
                        shield_cooldown = shield_cooldown_real
                    if e.key == pygame.K_ESCAPE:
                        game_state = "pause"

            if e.type == pygame.KEYUP and game_state == "game":
                if console_open:
                    continue
                if e.key == pygame.K_SPACE:
                    jump_hold_time = 0

        if game_state == "game" and not console_open:
            keys = pygame.key.get_pressed()
            on_ground = player.bottom >= HEIGHT - GROUND_OFFSET

            move_dir = 0
            if keys[pygame.K_a]:
                move_dir -= 1
            if keys[pygame.K_d]:
                move_dir += 1
            if joy_dx != 0:
                move_dir += 1 if joy_dx > 0 else -1

            run_max_speed = player_speed
            if move_dir != 0:
                facing = move_dir
                player_vx += move_dir * run_accel * dt
            else:
                player_vx *= run_friction ** dt

            player_vx = clamp(player_vx, -run_max_speed, run_max_speed)
            player_pos_x += player_vx * dt
            sync_player_x(reset_velocity=True)

            if keys[pygame.K_SPACE] and jump_hold_time > 0 and velocity_y < 0:
                velocity_y -= 0.75 * dt
                jump_hold_time = update_timer(jump_hold_time, dt)

            if joy_dy < JOY_JUMP_THRESHOLD and not joy_jumped:
                jump_buffer_time = jump_buffer_max
                joy_jumped = True
            if joy_dy >= JOY_JUMP_THRESHOLD:
                joy_jumped = False

            if jump_buffer_time > 0:
                jump_buffer_time = update_timer(jump_buffer_time, dt)
                if on_ground or coyote_time > 0 or jumps_left > 0:
                    velocity_y = jump_strength
                    if on_ground or coyote_time > 0:
                        jumps_left = max(0, jumps_left - 1)
                    else:
                        jumps_left -= 1
                    jump_hold_time = jump_hold_max
                    jump_buffer_time = 0

            velocity_y += gravity * dt
            player_pos_y += velocity_y * dt
            player.y = int(player_pos_y)

            if player.bottom >= HEIGHT - GROUND_OFFSET:
                player.bottom = HEIGHT - GROUND_OFFSET
                player_pos_y = float(player.y)
                velocity_y = 0
                jumps_left = max_jumps
                jump_hold_time = 0
                coyote_time = coyote_max
            else:
                coyote_time = update_timer(coyote_time, dt)

            if dash_duration > 0:
                dash_velocity *= 0.95 ** dt
                player_pos_x += dash_velocity * dt
                dash_duration = update_timer(dash_duration, dt)
                hit_wall = sync_player_x()

                if hit_wall:
                    dash_velocity *= -0.65
                    dash_duration = max(0, dash_duration - 2)
                    player_pos_x = clamp(player_pos_x, 0.0, float(WIDTH - player.width))
                    player.x = int(player_pos_x)
                    facing = 1 if dash_velocity >= 0 else -1
                    dash_trail.append(
                        {
                            "rect": player.copy(),
                            "life": 12,
                            "color": (120, 210, 255),
                        }
                    )

            if dash_cooldown > 0:
                dash_cooldown = update_timer(dash_cooldown, dt)

            if shield:
                shield_time = update_timer(shield_time, dt)
                shield_flash = 10
                if shield_time <= 0:
                    shield = False
            if shield_cooldown > 0:
                shield_cooldown = update_timer(shield_cooldown, dt)
            if shield_flash > 0:
                shield_flash = update_timer(shield_flash, dt)

            if tick >= next_magma_spawn:
                spawn_magma_pattern()
                next_magma_spawn = tick + random.randint(380, 700)

            if tick >= next_coin_spawn:
                spawn_coin_pattern()
                next_coin_spawn = tick + random.randint(850, 1350)

            magma_speed = min(MAGMA_MAX_SPEED, MAGMA_BASE_SPEED + score * MAGMA_SCORE_SCALE)

            magma_to_remove = []
            for m in magma_list:
                m.y += int(round(magma_speed * dt))
                if m.colliderect(player):
                    if shield:
                        magma_to_remove.append(m)
                        shield_flash = max(shield_flash, 14)
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

            collected_coins = 0
            next_coin_list = []
            for c in coin_list:
                c.y += int(round(COIN_FALL_SPEED * dt))
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

            next_dash_trail = []
            for p in dash_trail:
                p["life"] = update_timer(p["life"], dt)
                if p["life"] > 0:
                    next_dash_trail.append(p)
            dash_trail = next_dash_trail

            for p in dash_trail:
                rect = p["rect"]
                alpha = int(20 + p["life"] * 8)
                glow = get_trail_surface((rect.width, rect.height), alpha)
                screen.blit(glow, (rect.x - 15, rect.y - 15))

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
            draw_ability_bar()
            draw_joystick()
            draw_action_btns()
            draw_pause_btn()

        elif game_state == "menu":
            draw_menu()
            draw_info_hub()

        elif game_state == "shop":
            draw_shop()
            draw_info_hub()

        elif game_state == "pause":
            draw_pause()
            draw_info_hub()

        elif game_state == "gameover":
            draw_gameover()
            draw_info_hub()

        if console_open:
            draw_console()

        pygame.display.flip()
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
