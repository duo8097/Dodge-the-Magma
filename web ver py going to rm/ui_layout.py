import pygame


def ui(value, scale):
    return max(1, int(round(value * scale)))


def get_menu_button_rects(width, scale):
    button_w = ui(340, scale)
    button_h = ui(38, scale)
    center_x = width // 2
    left = center_x - button_w // 2
    top = ui(282, scale)
    gap = ui(42, scale)
    return {
        "start": pygame.Rect(left, top, button_w, button_h),
        "shop": pygame.Rect(left, top + gap, button_w, button_h),
        "exit": pygame.Rect(left, top + gap * 2, button_w, button_h),
    }


def get_shop_item_rects(width, scale):
    item_w = ui(500, scale)
    item_h = ui(70, scale)
    left = width // 2 - item_w // 2
    top = ui(220, scale)
    gap = ui(85, scale)
    return [
        pygame.Rect(left, top + gap * index, item_w, item_h)
        for index in range(3)
    ]


def get_shop_back_rect(width, scale):
    back_w = ui(240, scale)
    back_h = ui(34, scale)
    return pygame.Rect(
        width // 2 - back_w // 2,
        ui(484, scale),
        back_w,
        back_h,
    )


def get_pause_menu_rects(width, scale):
    button_w = ui(320, scale)
    button_h = ui(36, scale)
    left = width // 2 - button_w // 2
    top = ui(300, scale)
    gap = ui(42, scale)
    return {
        "resume": pygame.Rect(left, top, button_w, button_h),
        "menu": pygame.Rect(left, top + gap, button_w, button_h),
        "quit": pygame.Rect(left, top + gap * 2, button_w, button_h),
    }


def get_gameover_button_rects(width, scale):
    button_w = ui(320, scale)
    button_h = ui(34, scale)
    left = width // 2 - button_w // 2
    top = ui(346, scale)
    gap = ui(38, scale)
    return {
        "retry": pygame.Rect(left, top, button_w, button_h),
        "menu": pygame.Rect(left, top + gap, button_w, button_h),
        "shop": pygame.Rect(left, top + gap * 2, button_w, button_h),
        "quit": pygame.Rect(left, top + gap * 3, button_w, button_h),
    }


def get_action_rects(width, height, scale):
    btn_size = ui(56, scale)
    right = width - ui(16, scale) - btn_size
    bottom = height - ui(12, scale) - btn_size
    shield_top = bottom - btn_size - ui(8, scale)
    return (
        pygame.Rect(right, shield_top, btn_size, btn_size),
        pygame.Rect(right, bottom, btn_size, btn_size),
    )


def get_pause_btn_rect(width, scale):
    return pygame.Rect(width - ui(74, scale), ui(88, scale), ui(54, scale), ui(34, scale))


def get_joy_origin(height, scale, joy_radius):
    offset = ui(16, scale)
    bottom = ui(12, scale)
    return (offset + joy_radius, height - bottom - joy_radius)
