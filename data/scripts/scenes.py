import sys
import pygame

from lunaengine.core import Scene, LunaEngine
from lunaengine.ui import *

from data.config import APP_YAML_HANDLER


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _stat_color(value):
    if value <= 2: return (225, 95, 95)
    if value <= 4: return (230, 160, 70)
    if value <= 6: return (230, 220, 90)
    if value <= 8: return (120, 210, 120)
    return (110, 220, 220)


def _compact_name(name):
    """'Obsidian (Obsidiana)' -> 'Obsidian'. The full form stays in the description."""
    if "(" in name:
        return name.split("(")[0].strip()
    return name


_MATERIAL_CATEGORY_COLORS = {
    "natural": (115, 195, 125),
    "ore":     (120, 160, 230),
    "alloy":   (190, 130, 230),
    "special": (230, 115, 115),
}

_PATTERN_CATEGORY_COLORS = {
    "weapon":   (230, 120, 110),
    "ranged":   (120, 170, 230),
    "throwing": (100, 220, 200),   # NEW - teal
    "armor":    (230, 200, 100),
    "tool":     (120, 200, 140),
}

_ROLE_COLORS = {
    "head":    (220, 130, 100),
    "guard":   (150, 170, 220),
    "binding": (180, 160, 110),
    "cord":    (200, 190, 140),
    "handle":  (140, 190, 140),
    "tip":     (200, 150, 220),
    "coating": (160, 160, 200),
}


# ---------------------------------------------------------------------------
# Surface generators
# ---------------------------------------------------------------------------

def _gradient_surface(width, height, colors):
    width, height = max(1, int(width)), max(1, int(height))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    if not colors:
        surf.fill((128, 128, 128, 255))
    elif len(colors) == 1:
        surf.fill((*colors[0], 255))
    else:
        n = len(colors)
        for y in range(height):
            t = y / max(1, height - 1) * (n - 1)
            idx = min(int(t), n - 2)
            lt = t - idx
            c1, c2 = colors[idx], colors[idx + 1]
            r = int(c1[0] * (1 - lt) + c2[0] * lt)
            g = int(c1[1] * (1 - lt) + c2[1] * lt)
            b = int(c1[2] * (1 - lt) + c2[2] * lt)
            pygame.draw.line(surf, (r, g, b, 255), (0, y), (width, y))

    pygame.draw.rect(surf, (200, 200, 220, 255), (0, 0, width, height), 1)
    return surf


def _pattern_diagram_surface(width, height, pattern):
    width, height = max(1, int(width)), max(1, int(height))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((28, 28, 38, 255))

    cat = pattern.get("category", "weapon")
    cat_color = _PATTERN_CATEGORY_COLORS.get(cat, (180, 180, 190))
    for y in range(min(35, height)):
        alpha = int(70 * (1 - y / 35))
        pygame.draw.line(surf, (*cat_color, alpha), (0, y), (width, y))

    parts = pattern.get("parts", [])
    if parts:
        pad = 12
        gap = 4
        n = len(parts)
        avail_h = height - pad * 2 - gap * (n - 1)
        box_h = max(6, avail_h // n)
        y = pad
        for slot in parts:
            role = slot.get("role", "head")
            color = _ROLE_COLORS.get(role, (150, 150, 160))
            pygame.draw.rect(
                surf, color, (pad, y, width - pad * 2, box_h),
                border_radius=3,
            )
            y += box_h + gap

    pygame.draw.rect(surf, (200, 200, 220, 255), (0, 0, width, height), 1)
    return surf


# ---------------------------------------------------------------------------
# Base grid scene
# ---------------------------------------------------------------------------

class _GridGuideScene(Scene):
    TITLE = "Guide"
    COLS = 4
    DESIRED_CARD_W = 210
    DESIRED_CARD_H = 400
    GAP = 12

    def __init__(self, engine, items):
        super().__init__(engine)
        self.items = items
        self._build()

    def _build(self):
        sx, sy, sm = self.ratio.x, self.ratio.y, self.ratio.med

        self.add_ui_element(TextLabel(
            self.WIDTH // 2, int(18 * sy),
            self.TITLE, int(32 * sm),
            pivot=(0.5, 0),
        ))

        cols = self.COLS
        rows = (len(self.items) + cols - 1) // cols

        gap_x = int(self.GAP * sx)
        gap_y = int(self.GAP * sy)

        # -- pick a card width that provably fits inside the window --------
        # WIDTH is treated as actual screen width (matches Button usage in
        # the rest of the project). Cap card width so the full grid fits with
        # a 30px margin on each side, regardless of how WIDTH is measured.
        max_grid_w = int(self.WIDTH - 60)
        max_card_w = (max_grid_w - (cols - 1) * gap_x) // cols

        card_w = int(self.DESIRED_CARD_W * sx)
        card_w = min(card_w, max_card_w)

        # If the screen is unusually narrow and cards get too small, fall back
        # to the design-sized card and let the frame scroll horizontally.
        if card_w < int(150 * sx):
            card_w = int(150 * sx)

        card_h = int(self.DESIRED_CARD_H * sy)

        self.card_w = card_w
        self.card_h = card_h

        grid_w = cols * card_w + (cols - 1) * gap_x
        grid_h = rows * card_h + (rows - 1) * gap_y

        frame_y = int(70 * sy)
        frame_h = self.HEIGHT - frame_y - int(70 * sy)
        frame_w = min(self.WIDTH - 40, grid_w + 40)
        frame_x = (self.WIDTH - frame_w) // 2

        margin_x = max(10, (frame_w - grid_w) // 2)
        content_w = grid_w + margin_x * 2
        content_h = grid_h + 20

        self.scroll = ScrollingFrame(
            int(frame_x), int(frame_y),
            int(frame_w), int(frame_h),
            int(content_w), int(content_h),
            scrollbar_size=int(15 * sm),
            cull_rendering=True,
        )
        self.add_ui_element(self.scroll)

        for idx, item in enumerate(self.items):
            row = idx // cols
            col = idx % cols
            x = margin_x + col * (card_w + gap_x)
            y = 10 + row * (card_h + gap_y)
            card = self._build_card(item, x, y)
            if card is not None:
                self.scroll.add_child(card)

        back = Button(
            int(30 * sx), int(self.HEIGHT - 30 * sy),
            int(110 * sx), int(34 * sy),
            "Back", int(18 * sm),
            pivot=(0, 1),
        )
        back.set_on_click(lambda: self.engine.set_scene("main_menu"))
        self.add_ui_element(back)

    def _build_card(self, item, x, y):
        raise NotImplementedError

    def render(self, renderer):
        renderer.fill_screen(ThemeManager.get_color("background"))


# ---------------------------------------------------------------------------
# Materials grid
# ---------------------------------------------------------------------------

class MaterialsScene(_GridGuideScene):
    TITLE = "Materials Guide"

    def __init__(self, engine: LunaEngine):
        items = sorted(
            APP_YAML_HANDLER.materials.items(),
            key=lambda kv: (
                kv[1].get("tier", 99),
                kv[1].get("name", kv[0]).lower(),
            ),
        )
        super().__init__(engine, items)

    def _build_card(self, item, x, y):
        mid, mat = item
        sm = self.ratio.med

        card = UiFrame(
            int(x), int(y), self.card_w, self.card_h,
            background_color=(32, 32, 42),
            border_color=(60, 60, 75),
            border_width=1,
            corner_radius=6,
            padding=0,
        )

        pad = int(10 * self.ratio.x)
        img_w = self.card_w - 2 * pad
        img_h = int(self.card_h * 0.30)

        colors = [_hex_to_rgb(c) for c in mat.get("colors", ["#808080"])]
        surf = _gradient_surface(img_w, img_h, colors)
        card.add_child(ImageLabel(
            pad, pad, surf,
            width=int(img_w), height=int(img_h),
        ))

        # Title - large, as requested
        title_y = pad + img_h + int(6 * sm)
        card.add_child(TextLabel(
            pad, title_y,
            _compact_name(mat.get("name", mid)),
            int(26 * sm),
            color=(240, 240, 250), pivot=(0, 0),
        ))

        # Meta line - category · tier
        meta_y = title_y + int(32 * sm)
        category = mat.get("category", "")
        meta = f"{category.title()} · Tier {mat.get('tier', '?')}"
        card.add_child(TextLabel(
            pad, meta_y,
            meta, int(16 * sm),
            color=_MATERIAL_CATEGORY_COLORS.get(category, (180, 180, 190)),
            pivot=(0, 0),
        ))

        # Stats - 2x2 grid
        status = mat.get("status", {})
        stat_y = meta_y + int(26 * sm)
        stats = [
            ("Res", status.get("resistance", 0)),
            ("Dmg", status.get("damage",     0)),
            ("Def", status.get("defense",    0)),
            ("Spd", status.get("speed",      0)),
        ]
        col_w = img_w // 2
        row_h = int(20 * sm)
        for i, (label, value) in enumerate(stats):
            row = i // 2
            col = i % 2
            card.add_child(TextLabel(
                pad + col * col_w,
                stat_y + row * row_h,
                f"{label} {value}",
                int(16 * sm),
                color=_stat_color(value), pivot=(0, 0),
            ))

        # Description - LongTextLabel, wrapped
        desc_y = stat_y + 2 * row_h + int(10 * sm)
        desc = mat.get("description", "")
        if desc:
            card.add_child(LongTextLabel(
                pad, desc_y,
                desc,
                width=int(img_w),
                font_size=int(14 * sm),
                color=(190, 190, 205),
                wrap_width=int(img_w),
                line_spacing=int(3 * sm),
                pivot=(0, 0),
            ))

        return card


# ---------------------------------------------------------------------------
# Patterns grid
# ---------------------------------------------------------------------------

class PatternsScene(_GridGuideScene):
    TITLE = "Patterns Guide"

    _CATEGORY_ORDER = {"weapon": 0, "ranged": 1, "throwing": 2, "armor": 3, "tool": 4}

    def __init__(self, engine: LunaEngine):
        items = sorted(
            APP_YAML_HANDLER.patterns.items(),
            key=lambda kv: (
                self._CATEGORY_ORDER.get(kv[1].get("category"), 9),
                kv[1].get("name", kv[0]).lower(),
            ),
        )
        super().__init__(engine, items)

    def _build_card(self, item, x, y):
        pid, pat = item
        sm = self.ratio.med

        card = UiFrame(
            int(x), int(y), self.card_w, self.card_h,
            background_color=(32, 32, 42),
            border_color=(60, 60, 75),
            border_width=1,
            corner_radius=6,
            padding=0,
        )

        pad = int(10 * self.ratio.x)
        img_w = self.card_w - 2 * pad
        img_h = int(self.card_h * 0.30)

        surf = _pattern_diagram_surface(img_w, img_h, pat)
        card.add_child(ImageLabel(
            pad, pad, surf,
            width=int(img_w), height=int(img_h),
        ))

        title_y = pad + img_h + int(6 * sm)
        card.add_child(TextLabel(
            pad, title_y,
            pat.get("name", pid),
            int(26 * sm),
            color=(240, 240, 250), pivot=(0, 0),
        ))

        meta_y = title_y + int(32 * sm)
        category = pat.get("category", "")
        slots = len(pat.get("parts", []))
        meta = f"{category.title()} · {slots} slot{'s' if slots != 1 else ''}"
        card.add_child(TextLabel(
            pad, meta_y,
            meta, int(16 * sm),
            color=_PATTERN_CATEGORY_COLORS.get(category, (180, 180, 190)),
            pivot=(0, 0),
        ))

        # Mechanics lines
        line_y = meta_y + int(26 * sm)
        for i, line in enumerate(self._mechanics_lines(pat)[:3]):
            card.add_child(TextLabel(
                pad, line_y + i * int(18 * sm),
                line, int(14 * sm),
                color=(200, 200, 215), pivot=(0, 0),
            ))

        # Description underneath
        desc_y = line_y + 3 * int(18 * sm) + int(8 * sm)
        desc = pat.get("description", "")
        if desc:
            card.add_child(LongTextLabel(
                pad, desc_y,
                desc,
                width=int(img_w),
                font_size=int(14 * sm),
                color=(190, 190, 205),
                wrap_width=int(img_w),
                line_spacing=int(3 * sm),
                pivot=(0, 0),
            ))

        return card

    @staticmethod
    def _mechanics_lines(pat):
        lines = []
        attack = pat.get("attack")
        if attack:
            lines.append(
                f"{attack.get('width', 1)}x{attack.get('height', 1)} "
                f"reach {attack.get('reach', 1)}"
            )
            lines.append(f"Speed {attack.get('speed', 'normal')}")
        mining = pat.get("mining")
        if mining:
            lines.append(
                f"Mine {mining.get('width', 1)}x{mining.get('height', 1)}"
            )
        proj = pat.get("projectile")
        if proj:
            lines.append(
                f"{proj.get('path', 'straight')} · speed {proj.get('speed', '?')}"
            )
        return lines


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

class MainMenu(Scene):
    def __init__(self, engine: LunaEngine):
        super().__init__(engine)
        self.setup_ui()

    def setup_ui(self):
        self.add_ui_element(TextLabel(
            self.WIDTH // 2, 140 * self.ratio.y,
            "Weapon Blacksmith", 72 * self.ratio.med,
            pivot=(0.5, 0.0),
        ))

        materials_btn = Button(
            self.WIDTH // 2, 280 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            "Materials Guide", 28 * self.ratio.med,
            pivot=(0.5, 0),
        )
        patterns_btn = Button(
            self.WIDTH // 2, 336 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            "Patterns Guide", 28 * self.ratio.med,
            pivot=(0.5, 0),
        )
        exit_btn = Button(
            self.WIDTH // 2, 392 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            "Exit", 28 * self.ratio.med,
            pivot=(0.5, 0),
        )

        materials_btn.set_on_click(lambda: self.engine.set_scene("materials"))
        patterns_btn.set_on_click(lambda: self.engine.set_scene("patterns"))
        exit_btn.set_on_click(self._exit)

        self.add_ui_element(materials_btn)
        self.add_ui_element(patterns_btn)
        self.add_ui_element(exit_btn)

    def _exit(self):
        pygame.quit()
        sys.exit()

    def render(self, renderer):
        renderer.fill_screen(ThemeManager.get_color("background"))

    def update(self, dt):
        pass