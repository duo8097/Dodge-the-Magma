import asyncio
import importlib.util
from pathlib import Path

import pygame


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
BG = (10, 10, 20)
GRID = (30, 30, 60)
WHITE = (255, 255, 255)
BLUE = (100, 200, 255)
GREEN = (80, 255, 120)
MUTED = (140, 140, 180)
PANEL = (0, 0, 0)
TARGET_FPS = 60

OPTIONS = [
    {
        "title": "DESKTOP",
        "subtitle": "Keyboard mode, classic controls",
        "file": "Dodge the Magma Desktop for pygbag.py",
        "color": BLUE,
    },
    {
        "title": "TAP",
        "subtitle": "Touch controls, mobile-friendly flow",
        "file": "Dodge the Magma Tap Controls for pygbag.py",
        "color": GREEN,
    },
]


def load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draw_center_text(screen, font, text, y, color):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=(screen.get_width() // 2, y)))


def get_option_rects(width, height):
    card_w = min(460, width - 120)
    card_h = 110
    gap = 24
    left = width // 2 - card_w // 2
    start_y = height // 2 - card_h - gap // 2
    return [
        pygame.Rect(left, start_y + index * (card_h + gap), card_w, card_h)
        for index in range(len(OPTIONS))
    ]


async def choose_mode():
    pygame.init()
    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT))
    info = pygame.display.Info()
    width = max(960, info.current_w or screen.get_width())
    height = max(540, info.current_h or screen.get_height())
    if screen.get_size() != (width, height):
        screen = pygame.display.set_mode((width, height))

    pygame.display.set_caption("Dodge the Magma - Choose Mode")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("Consolas", 54)
    card_font = pygame.font.SysFont("Consolas", 34)
    sub_font = pygame.font.SysFont("Consolas", 22)
    hint_font = pygame.font.SysFont("Consolas", 20)

    while True:
        clock.tick(TARGET_FPS)
        screen.fill(BG)

        for x in range(0, width, 40):
            pygame.draw.line(screen, GRID, (x, 0), (x, height))
        for y in range(0, height, 40):
            pygame.draw.line(screen, GRID, (0, y), (width, y))

        draw_center_text(screen, title_font, "CHOOSE YOUR MODE", 120, WHITE)
        draw_center_text(
            screen,
            sub_font,
            "Pick desktop or tap, then let the magma games begin.",
            168,
            MUTED,
        )

        option_rects = get_option_rects(width, height)
        mouse_pos = pygame.mouse.get_pos()

        for index, (option, rect) in enumerate(zip(OPTIONS, option_rects), start=1):
            hovered = rect.collidepoint(mouse_pos)
            fill = (20, 20, 30) if not hovered else (34, 34, 52)
            border = option["color"] if hovered else WHITE
            pygame.draw.rect(screen, PANEL, rect, border_radius=14)
            pygame.draw.rect(screen, fill, rect.inflate(-4, -4), border_radius=12)
            pygame.draw.rect(screen, border, rect, 2, border_radius=14)

            badge = hint_font.render(f"[ {index} ]", True, option["color"])
            title = card_font.render(option["title"], True, WHITE)
            subtitle = sub_font.render(option["subtitle"], True, MUTED)

            screen.blit(badge, (rect.x + 22, rect.y + 18))
            screen.blit(title, (rect.x + 22, rect.y + 46))
            screen.blit(subtitle, (rect.x + 180, rect.y + 50))

        draw_center_text(
            screen,
            hint_font,
            "Press 1 or 2, or click a card.",
            height - 56,
            MUTED,
        )
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return OPTIONS[0]
                if event.key == pygame.K_2:
                    return OPTIONS[1]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for option, rect in zip(OPTIONS, option_rects):
                    if rect.collidepoint(event.pos):
                        return option

        await asyncio.sleep(0)


async def run_selected_mode(option):
    if option is None:
        return

    module_path = BASE_DIR / option["file"]
    module = load_module(module_path, f"launcher_{option['title'].lower()}")
    if not hasattr(module, "main"):
        raise RuntimeError(f"{module_path.name} does not expose main()")
    await module.main()


async def main():
    option = await choose_mode()
    await run_selected_mode(option)


if __name__ == "__main__":
    asyncio.run(main())
