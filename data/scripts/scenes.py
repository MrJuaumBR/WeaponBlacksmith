import sys
import pygame

from functools import lru_cache

from lunaengine.core import Scene, LunaEngine
from lunaengine.ui import *
from lunaengine.graphics import SpriteSheet

from data.config import APP_ATLAS, APP_YAML_HANDLER
from data.rpg.mods import translate


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
    "throwing": (100, 220, 200),
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
    "armor_plate":    (220, 180, 100),
    "armor_lining":   (160, 200, 160),
    "armor_fastener": (180, 180, 190),
}


# ---------------------------------------------------------------------------
# Gradient surface (also used as the tint source for sprites)
# ---------------------------------------------------------------------------

def _gradient_surface(width, height, colors, border=True):
    """Vertical gradient through a list of RGB tuples.

    With a single colour this is a flat fill; with two or three it blends
    between them. The optional 1px border is useful for card swatches, but
    is switched off when the gradient is used as a tint mask on a sprite.
    """
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

    if border:
        pygame.draw.rect(surf, (200, 200, 220, 255), (0, 0, width, height), 1)
    return surf


# ---------------------------------------------------------------------------
# Sprite sheet access - shared for ingot and gem ball
# ---------------------------------------------------------------------------
# The textures.png sheet is laid out in 64x64 cells.
#
#   Ingot (metals, ores, woods, leathers, etc.)
#     cell (0, 0), sprite occupying (0, 17) .. (63, 45)  -> 64 x 29
#
#   Ball (gems - diamond, carbonado, and any future gem)
#     sprite occupying the second 64x64 cell (64, 0) .. (127, 63)
#
# Sprite dimensions below are the exact sizes, not the cell size.

_INGOT_RECT = pygame.Rect(0, 17, 64, 29)
_BALL_RECT  = pygame.Rect(64, 0, 64, 64)

_sprite_cache: dict = {}


def _get_sprite(key, rect):
    """Extract a white sprite from the shared textures sheet, once."""
    if key in _sprite_cache:
        return _sprite_cache[key]

    try:
        sheet = SpriteSheet.from_atlas("textures", APP_ATLAS)
        sprite = sheet.get_sprite_at_rect(rect).copy()
        _sprite_cache[key] = sprite
    except Exception as exc:
        _sprite_cache[key] = None
        print(f"[materials] sprite '{key}' unavailable, falling back: {exc}")

    return _sprite_cache[key]


def _get_ingot_sprite():
    return _get_sprite("ingot", _INGOT_RECT)


def _get_ball_sprite():
    return _get_sprite("ball", _BALL_RECT)


def _sprite_for_material(mat):
    """Pick the right icon: ball for gems, ingot for everything else."""
    tags = mat.get("tags", [])
    if "gem" in tags:
        return _get_ball_sprite()
    return _get_ingot_sprite()


# ---------------------------------------------------------------------------
# Tinting
# ---------------------------------------------------------------------------

def _tinted(sprite, colors, size):
    """Return `sprite` tinted with a palette and scaled to `size`.

    One colour: SpriteSheet.tint(..., blend_mode="multiply").
    Two or three colours: multiply a vertical palette gradient onto the white
    sprite. BLEND_RGB_MULT only touches RGB, so the sprite's alpha - including
    anti-aliased edges - is preserved.
    """
    if sprite is None:
        return None

    if size != sprite.get_size():
        sprite = pygame.transform.scale(sprite, size)

    if len(colors) == 1:
        return SpriteSheet.tint(sprite, colors[0], intensity=1.0, blend_mode="multiply")

    gradient = _gradient_surface(
        sprite.get_width(), sprite.get_height(), colors, border=False
    )
    tinted = sprite.copy()
    tinted.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return tinted


# ---------------------------------------------------------------------------
# Panel builders (card image area)
# ---------------------------------------------------------------------------

def _sprite_panel(img_w, img_h, sprite, colors):
    """Compose the card image area: top-lit slot, tinted sprite centred, border.

    Falls back to a gradient bar if `sprite` is None.
    """
    panel = pygame.Surface((img_w, img_h), pygame.SRCALPHA)

    for y in range(img_h):
        t = y / max(1, img_h - 1)
        shade = int(34 - 10 * t)
        pygame.draw.line(panel, (shade, shade, shade + 8, 255), (0, y), (img_w, y))

    pygame.draw.rect(panel, (58, 58, 74, 255), (0, 0, img_w, img_h), 1, border_radius=4)

    if sprite is not None:
        base_w, base_h = sprite.get_size()
        # Integer scaling so pixel art stays crisp, whatever the sprite size.
        max_scale_w = max(1, int(img_w * 0.75) // base_w)
        max_scale_h = max(1, int(img_h * 0.75) // base_h)
        scale = max(1, min(max_scale_w, max_scale_h))

        target_w = base_w * scale
        target_h = base_h * scale

        tinted = _tinted(sprite, colors, (target_w, target_h))
        if tinted is not None:
            panel.blit(tinted, ((img_w - target_w) // 2, (img_h - target_h) // 2))
            return panel

    # Fallback: gradient bar.
    grad = _gradient_surface(img_w - 16, max(8, img_h // 2), colors)
    panel.blit(grad, (8, (img_h - grad.get_height()) // 2))
    return panel


@lru_cache(maxsize=128)
def _ingot_panel(img_w, img_h, colors):
    return _sprite_panel(img_w, img_h, _get_ingot_sprite(), colors)


@lru_cache(maxsize=128)
def _ball_panel(img_w, img_h, colors):
    return _sprite_panel(img_w, img_h, _get_ball_sprite(), colors)


# ---------------------------------------------------------------------------
# Pattern slot diagram
# ---------------------------------------------------------------------------

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
        self.return_scene = "main_menu"
        self.items = items
        self._build()

    def _build(self):
        sx, sy, sm = self.ratio.x, self.ratio.y, self.ratio.med

        self.add_ui_element(TextLabel(
            self.WIDTH // 2, int(18 * sy),
            translate(self.TITLE), int(32 * sm),
            pivot=(0.5, 0),
        ))

        cols = self.COLS
        rows = (len(self.items) + cols - 1) // cols

        gap_x = int(self.GAP * sx)
        gap_y = int(self.GAP * sy)

        max_grid_w = int(self.WIDTH - 60)
        max_card_w = (max_grid_w - (cols - 1) * gap_x) // cols

        card_w = int(self.DESIRED_CARD_W * sx)
        card_w = min(card_w, max_card_w)
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
        back.set_on_click(self._go_back)
        self.add_ui_element(back)

    def on_enter(self, previous_scene=None, *args, **kwargs):
        self.return_scene = "rpg_town" if previous_scene == "rpg_town" else "main_menu"

    def _go_back(self):
        self.engine.set_scene(self.return_scene)

    def _build_card(self, item, x, y):
        raise NotImplementedError

    def render(self, renderer):
        renderer.fill_screen(ThemeManager.get_color("background"))


# ---------------------------------------------------------------------------
# Materials grid (ingot for most, ball for gems)
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

        colors = tuple(_hex_to_rgb(c) for c in mat.get("colors", ["#808080"]))

        # Gems (diamond, carbonado, any future 'gem'-tagged material) show as
        # a tinted ball; everything else shows as a tinted ingot.
        sprite = _sprite_for_material(mat)
        panel = _sprite_panel(img_w, img_h, sprite, colors)

        card.add_child(ImageLabel(
            pad, pad, panel,
            width=int(img_w), height=int(img_h),
        ))

        title_y = pad + img_h + int(6 * sm)
        card.add_child(TextLabel(
            pad, title_y,
            _compact_name(mat.get("name", mid)),
            int(26 * sm),
            color=(240, 240, 250), pivot=(0, 0),
        ))

        meta_y = title_y + int(32 * sm)
        category = mat.get("category", "")
        meta = f"{category.title()} · Tier {mat.get('tier', '?')}"
        card.add_child(TextLabel(
            pad, meta_y,
            meta, int(16 * sm),
            color=_MATERIAL_CATEGORY_COLORS.get(category, (180, 180, 190)),
            pivot=(0, 0),
        ))

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
# Patterns grid (slot diagram)
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

        line_y = meta_y + int(26 * sm)
        for i, line in enumerate(self._mechanics_lines(pat)[:3]):
            card.add_child(TextLabel(
                pad, line_y + i * int(18 * sm),
                line, int(14 * sm),
                color=(200, 200, 215), pivot=(0, 0),
            ))

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
            translate("Weapon Blacksmith"), 72 * self.ratio.med,
            pivot=(0.5, 0.0),
        ))

        adventure_btn = Button(
            self.WIDTH // 2, 280 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            translate("Start Adventure"), 28 * self.ratio.med,
            pivot=(0.5, 0),
        )
        materials_btn = Button(
            self.WIDTH // 2, 336 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            translate("Materials Guide"), 28 * self.ratio.med,
            pivot=(0.5, 0),
        )
        patterns_btn = Button(
            self.WIDTH // 2, 392 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            translate("Patterns Guide"), 28 * self.ratio.med,
            pivot=(0.5, 0),
        )
        exit_btn = Button(
            self.WIDTH // 2, 448 * self.ratio.y,
            320 * self.ratio.x, 46 * self.ratio.y,
            translate("Exit"), 28 * self.ratio.med,
            pivot=(0.5, 0),
        )

        adventure_btn.set_on_click(lambda: self.engine.set_scene("rpg_characters"))
        materials_btn.set_on_click(lambda: self.engine.set_scene("materials"))
        patterns_btn.set_on_click(lambda: self.engine.set_scene("patterns"))
        exit_btn.set_on_click(self._exit)

        self.add_ui_element(adventure_btn)
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
