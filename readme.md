# Weapon Blacksmith

A Tinkers'-Construct-style crafting game: every weapon, tool and piece of armor is assembled from individual parts (blade, guard, handle, plate...), and each part is made from a material of your choice.

The game ships with two in-game reference screens — a **Materials Guide** and a **Patterns Guide** — that render every entry as a paginated grid card with its gradient swatch and slot diagram.

## Project layout

Data lives in three YAML files, each with a single responsibility:

| File | Contains |
|---|---|
| `data/materials.yaml` | Every material and its properties (stats, tags, colors, trait). |
| `data/patterns.yaml` | Every craftable item: its slots, part types, attack/mining/projectile geometry, and innate traits. Also the `stat_rules` that decide how part stats combine. |
| `data/crafts.yaml` | Every recipe: alloy smelting and pattern assembly, with station requirements and alternatives. |

`data/scripts/yaml_handler.py` loads all three, validates them, and exposes helpers like `materials_for_slot(...)` and `compute_tool_stats(...)`.

## Materials

Every material has four stats on a **0-10 scale** (higher is better):

| Stat | What it does |
|---|---|
| `resistance` | Durability — how much punishment the part takes before breaking |
| `damage` | Attack power contributed to the finished weapon |
| `defense` | Protection contributed (guards, armor plates, shields) |
| `speed` | How fast the part lets the tool swing or mine |

Each material also has a **tier** (1 = worst, 9 = best), a **category** (`ore` / `alloy` / `natural` / `special`), a **trait** (a special rule that makes it feel different), and a **color palette**.

### Colors

`colors` is a visual identity list, not a stat. The rule is:

- **Tier 1-3** → 1 colour (base tone only)
- **Tier 4-6** → 2 colours (base + shadow/sheen)
- **Tier 7-9** → 3 colours (base + shadow + highlight)

The first entry is always the base tone. The renderer uses the rest for gradients, edge glow and polished highlights, so you can tell a diamond blade from a steel one at a glance. A 3-band palette can also encode state (e.g. vibranium blue → purple → red as it charges).

### Naturals (harvested)

| Tier | Material | Res | Dmg | Def | Spd | Trait |
|:---:|---|:---:|:---:|:---:|:---:|---|
| 1 | Stick | 2 | 1 | 1 | 6 | Cheap |
| 1 | Sapling | 1 | 1 | 1 | 4 | Living Wood |
| 2 | Wood (Oak) | 3 | 2 | 2 | 5 | Shock Absorbing |
| 2 | Bamboo | 2 | 2 | 1 | 8 | Hollow |
| 2 | Leather | 3 | 1 | 4 | 3 | Sure Grip |
| 2 | String (Sinew) | 2 | 1 | 2 | 6 | Binding |
| 3 | Bone | 3 | 3 | 2 | 4 | Splinter |
| 3 | Flint | 2 | 4 | 1 | 4 | Keen Edge |

### Ores (mined)

| Tier | Material | Res | Dmg | Def | Spd | Trait |
|:---:|---|:---:|:---:|:---:|:---:|---|
| 1 | Coal (Carbon) | 1 | 1 | 1 | 2 | Brittle |
| 2 | Copper | 3 | 3 | 2 | 5 | Malleable |
| 2 | Tin | 3 | 2 | 3 | 4 | Soft |
| 3 | Iron | 4 | 4 | 4 | 4 | Reliable |
| 3 | Lead | 3 | 5 | 5 | 2 | Heavy |
| 3 | Magnetite | 4 | 3 | 4 | 3 | Magnetic |
| 4 | Nickel | 5 | 4 | 5 | 4 | Corrosion Proof |
| 4 | Silver | 4 | 4 | 3 | 6 | Hallowed |
| 6 | Gold | 4 | 7 | 3 | 7 | Gilded |
| 7 | Diamond | 8 | 7 | 7 | 6 | Razor Edge |
| 7 | Platinum | 7 | 8 | 6 | 6 | Unyielding |

### Alloys (crafted)

Alloys cannot be mined — they are made at a station. Recipes live in `crafts.yaml`.

| Tier | Material | Res | Dmg | Def | Spd | Trait | Recipe | Station |
|:---:|---|:---:|:---:|:---:|:---:|---|---|---|
| 3 | Bronze | 5 | 4 | 4 | 5 | Ancient Alloy | 3 Copper + 1 Tin | Smeltery |
| 4 | Brass | 5 | 5 | 4 | 6 | Low Friction | 2 Copper + 1 Iron | Smeltery |
| 5 | Steel | 6 | 6 | 5 | 5 | Tempered | 2 Iron + 2 Coal | Bloomery |
| 5 | Aluminium | 5 | 5 | 3 | 8 | Lightweight | 3 Coal + 2 Iron | Smeltery |
| 5 | Invar | 6 | 5 | 6 | 4 | Dimensionally Stable | 3 Iron + 2 Nickel | Smeltery |
| 5 | Blooderium | 5 | 4 | 3 | 5 | Bloodthirst | 3 Iron + 2 Leather | Bloomery |
| 6 | Electrum | 5 | 7 | 3 | 8 | Electromagnetic | 2 Magnetite + 1 Gold | Smeltery |
| 6 | Rose Gold | 5 | 7 | 4 | 7 | Warm Glow | 3 Copper + 1 Gold | Smeltery |
| 8 | Titanium | 8 | 8 | 8 | 6 | Aerospace | 2 Iron + 1 Aluminium | Blast Furnace |
| 9 | Carbonado | 10 | 10 | 8 | 6 | Apex Edge | 2 Diamond + 2 Obsidian | Blast Furnace |

### Special

| Tier | Material | Res | Dmg | Def | Spd | Trait |
|:---:|---|:---:|:---:|:---:|:---:|---|
| 8 | Vibranium | 9 | 7 | 9 | 5 | Kinetic Absorption |
| 9 | Obsidian | 9 | 9 | 8 | 5 | Volcanic Glass |

Gold and Lead are deliberate outliers: high damage, poor durability/speed. They are *damage* materials, not *blade* materials — great for a pommel that adds weight, terrible for a blade that has to survive a fight.

Blooderium trades raw stats for sustainability: every hit drains 1 HP from the wielder to restore 3 durability. It cannot drain below 1 HP, so it's a calculated risk rather than a free repair.

Carbonado is the apex alloy — the only material with a perfect 10 in both durability and damage — but the recipe demands two full progression trees' worth of resources.

## Patterns

Every craftable item is defined as a pattern: a list of slots, each pointing at a part type. Part types declare which **tags** they accept, so a diamond can go in a blade but not a binding, and leather can go in a lining but not a chest plate.

### Weapons

| Pattern | Category | Slots | Attack shape |
|---|---|---|---|
| Short Sword | weapon | head, guard, handle | 1×1 box, reach 1, fast |
| Long Sword | weapon | head, guard, handle | 2×1 box, reach 1, normal |
| Dagger | weapon | head, guard, handle | 1×1 box, reach 1, fast |
| Scythe | weapon | head, binding, 2× handle | 3×2 box, reach 1, slow |
| Claws | weapon | head, binding, handle | 1×1 box, reach 1, fast |
| Rapier | weapon | head, guard, handle | 2×1 line, reach 1, fast |
| Broadsword | weapon | head, guard, handle | 2×2 box, reach 1, slow |
| Katana | weapon | head, guard, handle | 2×1 box, reach 1, fast |
| Spear | weapon | head, 2× handle | 3×1 line, reach 1, normal |
| Halberd | weapon | head, binding, 2× handle | 2×1 line, reach 1, normal |
| Battleaxe | weapon | head, binding, handle | 1×2 box, reach 1, slow |
| Warhammer | weapon | head, binding, 2× handle | 1×2 box, reach 1, very slow |
| Mace | weapon | head, handle | 1×1 box, reach 1, normal |

### Ranged

| Pattern | Category | Slots | Projectile |
|---|---|---|---|
| Bow | ranged | 2× limb, string | arc, speed 18, ammo arrow |
| Crossbow | ranged | limb, string, stock, binding | straight, speed 28, ammo bolt |

### Tools

| Pattern | Category | Slots | Use |
|---|---|---|---|
| Pickaxe | tool | head, binding, handle | Mines stone/ore/gem in 1×1, aim up/down |
| Axe | tool | head, handle | Chops wood in 1×2, usable as weapon at 0.8× damage |
| Shovel | tool | head, handle | Digs soft ground in 1×1, aim up/down |
| Hoe | tool | head, handle | Tills dirt/grass into farmland below you |
| Mattock | tool | head, handle | Mines stone + chops wood at 0.75× speed |
| Hammer | tool | head, binding, 2× handle | Mines a 3×2 area at 0.6× speed |
| Excavator | tool | head, binding, 2× handle | Digs a 3×1 strip of soft ground |
| Fishing Rod | tool | rod, line | Casts a hooked projectile, reels in catches |
| Scissors | tool | head, handle | Cuts cloth/string/thread/vines, 0.5× damage |
| Shears | tool | head, handle | Harvests wool/crops/vines, 0.6× damage |

### Armor

| Pattern | Category | Slots | Role |
|---|---|---|---|
| Helmet | armor | plate, lining, fastener | Head protection |
| Chestplate | armor | plate, lining, fastener | Torso protection (largest piece) |
| Leggings | armor | plate, lining | Leg protection |
| Boots | armor | plate, lining | Foot protection, sure footing |
| Shield | armor | plate, fastener | Blocks attacks while raised |

Armor pieces use three new part roles: `armor_plate` (adds `defense` and `resistance`), `armor_lining` (adds `speed`), and `armor_fastener` (trait only). Plate material is the protection choice, lining is the mobility choice.

## How part stats combine

Each part role has its own rule, defined under `stat_rules:` in `patterns.yaml`:

| Role | Rule |
|---|---|
| `head` | Additive — the **mean** of each material's damage/resistance/speed across all heads |
| `guard` | Additive — sum of `defense` across guards, plus a flat **+1 resistance** per guard |
| `handle` | Multiplier — each handle contributes `stat / 20` to the item's speed and resistance multiplier |
| `binding` | Trait only — grants the material's trait, no numeric stats |
| `cord` | Trait only |
| `tip` | Additive × 0.5 — optional upgrade, adds half the material's stats |
| `coating` | Additive × 0.25 — optional upgrade, adds a quarter of the material's stats |
| `armor_plate` | Additive — sum of `defense` and `resistance` across plates |
| `armor_lining` | Additive — sum of `speed` across linings |
| `armor_fastener` | Trait only |

This is why **material choice is a real decision**: a wooden handle doesn't just add a little speed, it *multiplies* the whole item's speed. A cheap binding doesn't hurt your numbers, but it decides which trait you inherit. And a titanium blade on a stick handle is only as durable as the stick — or at least, the handle drags the durability multiplier down with it.

Traits from all parts stack, but a part only grants its trait if it is actually present in the recipe.

## Crafting stations

| Station | Tier | Type | Fuels |
|---|:---:|---|---|
| Crafting Table | 0 | hand | none |
| Campfire | 0 | furnace | wood, coal |
| Smeltery | 1 | furnace | coal, wood |
| Bloomery | 2 | furnace | coal |
| Blast Furnace | 3 | furnace | coal |

Patterns without an `assemble` recipe in `crafts.yaml` are craftable by hand. Patterns with one require that station — see `assembly_recipe(pattern_id)` in the handler.

## Adding new content

### A new material

1. Add an entry under `materials:` in `materials.yaml` with a unique `id`, a `category`, a `tier`, four `status` values, a `trait`, and a `colors` list following the 1/2/3 rule.
2. If it is craftable, add a recipe under `recipes:` in `crafts.yaml` and set `alloy: true` on the material.
3. If it should never be a weapon part (like coal), set `part_usable: false`.
4. If a part type should accept it by name (not just by tag), add the material's `id` to that part type's `accepted_tags` — or use the tag system.

### A new pattern

1. Add an entry under `patterns:` in `patterns.yaml` with its `parts` list (each slot has a `part_type` and optional `count`).
2. Add its attack, mining, or projectile block.
3. If it needs a station to assemble, add an `assemble` recipe in `crafts.yaml`.

The validator in `yaml_handler.py` runs on startup and will warn about unknown part types, tags no material provides, missing required slots, and cycles in alloy recipes.


## Idle-RPG adventure

The original Materials and Patterns guides remain available from the title screen and from Hearthglade. Choose **Start Adventure** to create or select one of up to three characters. Each character has independent skill progression, inventory, city access, guild membership, NPC conversations, and an idle task.

- Train nine skills, including Blacksmithing, Mining, Woodcutting, Archery, and Swordmastery.
- Assign a repeating activity, then claim completed cycles and offline rewards (offline credit is capped at eight hours).
- Gather materials that use the existing YAML catalog IDs, forge starter weapons, and explore five skill-gated cities.
- Join one guild, progress its contract, and gain reputation/ranks.
- Talk with five locally authored NPCs. Their response lines are selected from data-driven banks and rotate; there is no Ollama or LLM dependency.
- The game uses an app-local forge-amber and tempered-steel theme with complete dark and light variants.

Progress is stored locally at `~/.weapon_blacksmith/save.json`; set `WEAPON_BLACKSMITH_SAVE` to use a different path. Start the app from the project root with `python app.py`. Run the display-independent game tests with `python -m unittest data.rpg.tests.test_game`. A graphical runtime with LunaEngine's Pygame/OpenGL dependencies is required to open the window.

## Adventure hub and new systems

Hearthglade now uses a clearer hub menu with dedicated screens for the player's
**Inventory**, **Crafting Hall**, **Battle**, **Mods**, skills, cities, guilds,
and NPC dialogue. Inventory supports a scrollable list, live text search, and
sorting by name, quantity, or category. The Crafting Hall groups the Forge,
Crafting Table, Smeltery, Blast Furnace, and expansion stations in one place.

The first battle loop is deterministic and data-friendly: encounters have HP,
retaliation, rewards, and Combat XP, and the Matter mod adds corrupted
encounters in Broken Reality. See [`modding.md`](modding.md) for the JSON/YAML
extension format. The game creates `data/mods/mods.json` on startup and ships
with `mod-pt-br-translation-v0.1.json` and `mod-matter-v0.1.yaml` disabled by
default; enable them from the Mods screen and restart to reload catalogs.
