import yaml
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


class YAMLHandlerError(Exception):
    """Raised when a YAML file is malformed or internally inconsistent."""


class YAMLHandler:
    HANDLE_DIVISOR_DEFAULT = 20.0

    def __init__(self, materials: Path, patterns: Path, crafts: Path):
        self.materials_path = Path(materials)
        self.patterns_path = Path(patterns)
        self.crafts_path = Path(crafts)
        self.reload()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def reload(self) -> None:
        mat_raw = self._load_yaml(self.materials_path)
        pat_raw = self._load_yaml(self.patterns_path)
        crf_raw = self._load_yaml(self.crafts_path)

        # -- materials
        self.materials_meta = mat_raw.get("metadata", {})
        self.materials: Dict[str, dict] = mat_raw.get("materials", {})

        # -- patterns
        self.patterns_meta = pat_raw.get("metadata", {})
        self.patterns: Dict[str, dict] = pat_raw.get("patterns", {})
        self.part_types: Dict[str, dict] = pat_raw.get("part_types", {})
        self.stat_rules: Dict[str, dict] = pat_raw.get("stat_rules", {})
        self.geometry: Dict[str, Any] = pat_raw.get("geometry", {})

        # -- crafts
        self.crafts_meta = crf_raw.get("metadata", {})
        self.stations: Dict[str, dict] = crf_raw.get("stations", {})
        self.recipes: Dict[str, dict] = crf_raw.get("recipes", {})

        self._validate()

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        if not path.exists():
            raise YAMLHandlerError(f"Missing YAML file: {path}")
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            where = f" (line {mark.line + 1}, col {mark.column + 1})" if mark else ""
            raise YAMLHandlerError(f"Failed to parse {path.name}{where}: {e}") from e
        if not isinstance(data, dict):
            raise YAMLHandlerError(f"{path.name} did not parse to a mapping.")
        return data

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        errors: List[str] = []
        warnings: List[str] = []

        # ---- materials ----
        for mid, mat in self.materials.items():
            for field in ("name", "tier", "category", "status"):
                if field not in mat:
                    errors.append(f"material '{mid}' missing '{field}'")
            tier = mat.get("tier")
            if isinstance(tier, int) and not (1 <= tier <= 9):
                errors.append(f"material '{mid}' tier {tier} outside 1..9")
            for stat in ("resistance", "damage", "defense", "speed"):
                if stat not in mat.get("status", {}):
                    errors.append(f"material '{mid}' missing status.{stat}")
            colors = mat.get("colors", [])
            if isinstance(tier, int) and colors:
                expected = 1 if tier <= 3 else 2 if tier <= 6 else 3
                if len(colors) != expected:
                    warnings.append(
                        f"material '{mid}' tier {tier} has {len(colors)} colours, "
                        f"expected {expected}"
                    )

        # ---- part_types ----
        if not self.part_types:
            errors.append("no part_types defined")
        known_tags = {t for m in self.materials.values() for t in m.get("tags", [])}
        for pid, pt in self.part_types.items():
            role = pt.get("role")
            if role not in self.stat_rules:
                errors.append(f"part_type '{pid}' role '{role}' has no stat_rule")
            tags = pt.get("accepted_tags", [])
            if not tags:
                errors.append(f"part_type '{pid}' has no accepted_tags")
            for t in tags:
                if t not in known_tags:
                    errors.append(
                        f"part_type '{pid}' accepts tag '{t}' but no material has it"
                    )

        # ---- usability: every part-usable material should fit a part ----
        usable: set = set()
        for pt in self.part_types.values():
            tags = set(pt.get("accepted_tags", []))
            for mid, m in self.materials.items():
                if tags & set(m.get("tags", [])):
                    usable.add(mid)
        for mid, m in self.materials.items():
            if not m.get("part_usable", True):
                continue
            if mid not in usable:
                warnings.append(
                    f"material '{mid}' is not accepted by any part_type "
                    f"(tags: {m.get('tags', [])}) - add tags, or set "
                    f"part_usable: false if this is intentional"
                )
        # ---- patterns ----
        for pat_id, pat in self.patterns.items():
            parts = pat.get("parts") or []
            if not parts:
                errors.append(f"pattern '{pat_id}' has no parts")
            for i, slot in enumerate(parts):
                pt_id = slot.get("part_type")
                if pt_id not in self.part_types:
                    errors.append(
                        f"pattern '{pat_id}' slot '{slot.get('slot', f'#{i}')}' "
                        f"uses unknown part_type '{pt_id}'"
                    )

        # ---- recipes ----
        for rid, recipe in self.recipes.items():
            rtype = recipe.get("type")
            if rtype == "alloy":
                out = recipe.get("output")
                if out not in self.materials:
                    errors.append(f"recipe '{rid}' outputs unknown material '{out}'")
                station = recipe.get("station")
                if station not in self.stations:
                    errors.append(f"recipe '{rid}' uses unknown station '{station}'")
                qty = recipe.get("output_qty", 1)
                if not isinstance(qty, int) or qty <= 0:
                    errors.append(f"recipe '{rid}' output_qty must be a positive int")
                for inp, n in (recipe.get("inputs") or {}).items():
                    if inp not in self.materials:
                        errors.append(f"recipe '{rid}' input '{inp}' is not a material")
                    if not isinstance(n, int) or n <= 0:
                        errors.append(f"recipe '{rid}' input '{inp}' qty must be positive int")
            elif rtype == "assemble":
                pat_id = recipe.get("pattern")
                if pat_id not in self.patterns:
                    errors.append(f"recipe '{rid}' references unknown pattern '{pat_id}'")
                station = recipe.get("station")
                if station not in self.stations:
                    errors.append(f"recipe '{rid}' uses unknown station '{station}'")
            else:
                errors.append(f"recipe '{rid}' has unknown type '{rtype}'")

        # ---- every alloy material should be producible ----
        alloy_outputs = {r.get("output") for r in self.recipes.values()
                         if r.get("type") == "alloy"}
        for mid, mat in self.materials.items():
            if mat.get("alloy") and mid not in alloy_outputs:
                warnings.append(
                    f"material '{mid}' is marked alloy:true but no recipe produces it"
                )

        if warnings:
            for w in warnings:
                print(f"[yaml] warning: {w}")
        if errors:
            bullet = "\n  - ".join(errors)
            raise YAMLHandlerError(f"Data errors:\n  - {bullet}")

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def material(self, mid: str) -> dict:
        try:
            return self.materials[mid]
        except KeyError:
            raise YAMLHandlerError(f"Unknown material id: '{mid}'")

    def pattern(self, pid: str) -> dict:
        try:
            return self.patterns[pid]
        except KeyError:
            raise YAMLHandlerError(f"Unknown pattern id: '{pid}'")

    def part_type(self, ptid: str) -> dict:
        try:
            return self.part_types[ptid]
        except KeyError:
            raise YAMLHandlerError(f"Unknown part_type id: '{ptid}'")

    def station(self, sid: str) -> dict:
        try:
            return self.stations[sid]
        except KeyError:
            raise YAMLHandlerError(f"Unknown station id: '{sid}'")

    def materials_with_tag(self, tag: str) -> List[str]:
        return [mid for mid, m in self.materials.items() if tag in m.get("tags", [])]

    def materials_for_part(self, part_type_id: str) -> List[str]:
        pt = self.part_type(part_type_id)
        tags = set(pt.get("accepted_tags", []))
        return [
            mid for mid, m in self.materials.items()
            if tags & set(m.get("tags", []))
        ]

    def materials_for_slot(self, pattern_id: str, slot_name: str) -> List[str]:
        pat = self.pattern(pattern_id)
        for slot in pat.get("parts", []):
            if slot.get("slot") == slot_name:
                return self.materials_for_part(slot["part_type"])
        raise YAMLHandlerError(f"pattern '{pattern_id}' has no slot '{slot_name}'")

    # ------------------------------------------------------------------
    # Recipes
    # ------------------------------------------------------------------

    def recipes_for(self, output_id: str) -> List[dict]:
        """All recipes producing `output_id` (returned as (id, recipe) tuples)."""
        return [
            (rid, r) for rid, r in self.recipes.items()
            if r.get("type") == "alloy" and r.get("output") == output_id
        ]

    def assembly_recipe(self, pattern_id: str) -> Optional[dict]:
        """The station needed to assemble `pattern_id`, or None if hand-craftable."""
        for r in self.recipes.values():
            if r.get("type") == "assemble" and r.get("pattern") == pattern_id:
                return r
        return None

    def can_assemble(self, pattern_id: str, station_id: Optional[str]) -> bool:
        r = self.assembly_recipe(pattern_id)
        if r is None:
            return True
        return r.get("station") == station_id

    # ------------------------------------------------------------------
    # Alloy expansion
    # ------------------------------------------------------------------

    def expand_alloy(
        self,
        material_id: str,
        recipe_id: Optional[str] = None,
        _visited: Optional[set] = None,
    ) -> Dict[str, int]:
        """
        Recursively expand an alloy into base-material quantities, using one
        recipe per step. If recipe_id is None and multiple recipes exist for a
        step, the first one found is used. Use `expand_alloy_alternatives` to
        enumerate every possible cost.
        """
        if _visited is None:
            _visited = set()
        if material_id in _visited:
            raise YAMLHandlerError(f"Alloy cycle detected at '{material_id}'")

        recipe = None
        if recipe_id is not None:
            recipe = self.recipes.get(recipe_id)
            if recipe is None:
                raise YAMLHandlerError(f"Unknown recipe '{recipe_id}'")
        else:
            candidates = self.recipes_for(material_id)
            recipe = candidates[0][1] if candidates else None

        if recipe is None:
            return {material_id: 1}

        _visited.add(material_id)
        totals: Dict[str, int] = {}
        for inp, qty in recipe.get("inputs", {}).items():
            for base, base_qty in self.expand_alloy(inp, None, _visited).items():
                totals[base] = totals.get(base, 0) + base_qty * qty
        _visited.discard(material_id)
        return totals

    def expand_alloy_alternatives(self, material_id: str) -> List[Dict[str, Any]]:
        """
        Return every possible base-cost expansion for `material_id`.
        Each entry: { recipe_id, cost: {mat: qty}, total: int }
        """
        results = []
        for rid, _ in self.recipes_for(material_id):
            try:
                cost = self.expand_alloy(material_id, recipe_id=rid)
            except YAMLHandlerError:
                continue
            results.append({
                "recipe_id": rid,
                "cost": cost,
                "total": sum(cost.values()),
            })
        results.sort(key=lambda x: x["total"])
        return results

    # ------------------------------------------------------------------
    # Stat computation
    # ------------------------------------------------------------------

    def part_stats(self, material_id: str, part_type_id: str) -> dict:
        m = self.material(material_id)
        pt = self.part_type(part_type_id)
        return {
            "material": material_id,
            "part_type": part_type_id,
            "role": pt["role"],
            "stats": dict(m.get("status", {})),
            "trait": m.get("trait"),
        }

    def compute_tool_stats(
        self,
        pattern_id: str,
        materials_by_slot: Dict[str, Union[str, List[str]]],
    ) -> dict:
        pat = self.pattern(pattern_id)

        resolved: List[Tuple[dict, List[str]]] = []
        for slot in pat.get("parts", []):
            sid = slot["slot"]
            count = int(slot.get("count", 1))
            required = bool(slot.get("required", True))
            if sid not in materials_by_slot:
                if required:
                    raise YAMLHandlerError(
                        f"pattern '{pattern_id}' missing required slot '{sid}'"
                    )
                continue
            val = materials_by_slot[sid]
            mids = [val] * count if isinstance(val, str) else list(val)
            if len(mids) != count:
                raise YAMLHandlerError(
                    f"slot '{sid}' expects {count} material(s), got {len(mids)}"
                )
            for mid in mids:
                if mid not in self.materials:
                    raise YAMLHandlerError(f"slot '{sid}' uses unknown material '{mid}'")
            resolved.append((slot, mids))

        buckets: Dict[str, List[Tuple[dict, str]]] = {r: [] for r in self.stat_rules}
        for slot, mids in resolved:
            pt = self.part_type(slot["part_type"])
            role = slot.get("role") or pt["role"]
            buckets.setdefault(role, [])
            for mid in mids:
                buckets[role].append((slot, mid))

        order = ["head", "guard", "binding", "cord", "handle", "tip", "coating"]
        base = {"damage": 0.0, "resistance": 0.0, "speed": 0.0, "defense": 0.0}
        for role in order:
            if role in self.stat_rules:
                self._apply_rule(base, buckets.get(role, []), self.stat_rules[role])

        traits: List[dict] = []
        for role, items in buckets.items():
            for slot, mid in items:
                t = self.material(mid).get("trait")
                if t:
                    traits.append({
                        "source": "material",
                        "slot": slot["slot"],
                        "material": mid,
                        "trait": t,
                    })
        for t in pat.get("innate_traits", []):
            traits.append({"source": "pattern", "trait": t})

        return {
            "stats": {k: round(v, 2) for k, v in base.items()},
            "traits": traits,
            "attack": pat.get("attack"),
            "mining": pat.get("mining"),
            "projectile": pat.get("projectile"),
            "assembly": self.assembly_recipe(pattern_id),
        }

    def _apply_rule(self, base: dict, items: List[Tuple[dict, str]], rule: dict) -> None:
        if not items:
            return

        mode = rule.get("mode", "trait_only")
        fields = rule.get("fields", ["damage", "resistance", "speed", "defense"])
        scale = float(rule.get("scale", 1.0))
        aggregate = rule.get("aggregate", "sum")
        divisor = float(rule.get("divisor", self.HANDLE_DIVISOR_DEFAULT))

        def get(mid: str, field: str) -> float:
            return float(self.material(mid).get("status", {}).get(field, 0))

        if mode == "additive":
            for field in fields:
                vals = [get(mid, field) for _, mid in items]
                base[field] += self._aggregate(vals, aggregate) * scale

        elif mode == "multiplier":
            for field in fields:
                contribution = sum(get(mid, field) / divisor for _, mid in items)
                base[field] *= (1.0 + contribution)

        elif mode == "trait_only":
            pass

        else:
            raise YAMLHandlerError(f"Unknown stat rule mode: '{mode}'")

        for field, amount in (rule.get("bonus") or {}).items():
            base[field] = base.get(field, 0.0) + amount * len(items)

    @staticmethod
    def _aggregate(values: Iterable[float], how: str) -> float:
        vals = list(values)
        if not vals:
            return 0.0
        if how == "sum":
            return sum(vals)
        if how == "mean":
            return sum(vals) / len(vals)
        if how == "max":
            return max(vals)
        if how == "min":
            return min(vals)
        raise YAMLHandlerError(f"Unknown aggregate: '{how}'")


# ----------------------------------------------------------------------
# Smoke test - run with:  python -m data.scripts.yaml_handler
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import os
    root = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
    h = YAMLHandler(
        root / "data" / "materials.yaml",
        root / "data" / "patterns.yaml",
        root / "data" / "crafts.yaml",
    )

    print("Materials:", len(h.materials))
    print("Patterns :", len(h.patterns))
    print("Part types:", len(h.part_types))
    print("Recipes  :", len(h.recipes))
    print("Stations :", len(h.stations))

    print("\nTitanium true cost:", h.expand_alloy("titanium"))
    print("Steel alternatives:")
    for alt in h.expand_alloy_alternatives("steel"):
        print(" ", alt)

    print("\n--- Diamond Short Sword ---")
    print(h.compute_tool_stats("short_sword", {
        "head": "diamond", "guard": "silver", "handle": "titanium",
    })["stats"])

    print("\n--- Bamboo Bow ---")
    print(h.compute_tool_stats("bow", {
        "upper_limb": "bamboo", "lower_limb": "bamboo", "string": "string",
    })["stats"])