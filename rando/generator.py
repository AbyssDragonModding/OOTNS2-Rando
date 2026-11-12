"""Item placement (assumed fill), validation, patch writing and spoiler log."""
import hashlib
import json
import os
import random
import time
from collections import Counter, defaultdict

from . import formats as F
from . import gamedata
from . import logic as L
from . import settings as S
from .pickups import PickupCloner
from .qol import (patch_anju, patch_dodongo_bag_bombs, patch_egg_hatch_guard, patch_gs_death,
                  patch_ocarina_bridge, patch_open_forest_mido, patch_saria_song, patch_song_teaching,
                  patch_small_chests, patch_kokiri_schedules, patch_big_poe_one)
from .shops import ShopPatcher
from .world import World, JUNK

VERSION = "0.4.3"
BOMB_LIFT_PARAM = "Component/LiftableParam/Item_Bomb.game__component__LiftableParam.bgyml"
BOMB_PACKS = ["Pack/Actor/Item_Bomb.pack.zs", "Pack/Actor/Npc_Hylia_ImperialSoldier_Bomb.pack.zs",
              "Pack/Actor/Obj_BombFlower_A_01.pack.zs", "Pack/Actor/Obj_BombFlower_A_04.pack.zs",
              "Pack/Actor/Obj_BombFlower_Fruit_For_Break_Obj_DeathMtTrail_BrokenRock_A_01.pack.zs"]
BRACELET_GRADE = 3655598229      # LiftableGrade granted by the Goron Bracelet
DEFAULT_GRADE = 3069107721       # grade of pots, small rocks, Bombchus (no bracelet needed)
SKIP_SETTING = "Event/EventSetting/EventSettingComponent/SkipSetting/DisableSkip.engine__event__SkipSetting.bgyml"
SHOP_FORBIDDEN = {"Heart_Piece", "Heart_Container", "Token_Gold", "Bottle", "Bottle_Milk", "Bottle_Letter",
                  "WeirdEgg", "ZeldaLetter", "BombBag_Medium", "BulletBag_Medium", "Quiver_Medium",
                  "Wallet_Medium", "Wallet_Large"}
UPGRADES = {"Wallet_Medium", "Wallet_Large", "BombBag_Medium", "BombBag_Large"}
REWARDS = {"Stone_Forest", "Stone_Fire", "Stone_Water", "Medal_Forest", "Medal_Fire", "Medal_Water",
           "Medal_Shadow", "Medal_Spirit", "Medal_Light"}
SHOP_FORBIDDEN |= REWARDS

# Skip Child Zelda: the checks whose items a new save already owns (gamedata.grant_start_items)
START_LOCATIONS = ("event:HC Zeldas Letter", "event:HC Malon Egg", "event:Song from Impa")
# Items the save can't simply be given (they need ammo, capacity, hearts, magic or a bottle slot set up too)
START_DENY_PREFIXES = ("Heart_", "Token_Gold", "Bottle", "BombBag_", "Quiver_", "BulletBag_", "Wallet_", "NutBag_",
                       "StickBag_", "Range_", "FairyBless_", "Arrow_", "Bombchu", "Bomb", "Deku", "Rupee_",
                       "MagicJar_", "ArrowBundle", "ScrubBusinessSeed")


class GenerationError(Exception):
    pass


# Refills that are useless without their container: the item a chest checks for before giving them.
# Bombchus count against the Bomb Bag (Item_Bombchu's PouchContentParam: MaxNumGameData "Bomb"), so without a
# bag they are lost: the get message says "5 Bombchus" but the count stays at 0.
REFILL_CONTAINERS = (("ArrowBundle", "Item_Range_Bow"), ("BombBundle", "Item_BombBag_Small"),
                     ("BombchuBundle", "Item_BombBag_Small"), ("DekuSeedBundle", "Item_Range_SlingShot"))
REFILL_FALLBACK = "Rupee_Blue"

# Maps & Compasses "Start With": what their checks hold instead (item, weight). Never progression.
START_WITH_BONUS = [("Rupee_Blue", 3), ("Rupee_Red", 5), ("Rupee_Purple", 4), ("Rupee_Gold", 2),
                    ("BombchuBundle_Medium", 2), ("ArrowBundle_Large", 2), ("DekuNutBundle", 1),
                    ("Heart_Piece", 1)]


# Capacity upgrades that several locations hand out as "Bigger". In a chest they become progressive with the
# game's conditional-chest check: own the Bigger one (CheckActor) -> the Biggest (Substitute), else Bigger.
PROGRESSIVE_UPGRADES = {"BombBag_Medium": ("Item_BombBag_Medium", "Item_BombBag_Large"),
                        "BulletBag_Medium": ("Item_BulletBag_Medium", "Item_BulletBag_Large"),
                        "Quiver_Medium": ("Item_Quiver_Medium", "Item_Quiver_Large"),
                        "Wallet_Medium": ("Item_Wallet_Medium", "Item_Wallet_Large")}
# The Skulltula House wallets go into the pool as two Adult's Wallets that only chests may hold: a chest's
# conditional check gives the Giant's Wallet if you already own the Adult's one. Handed out by an event, a
# Giant's Wallet found first could later be "downgraded" by the Adult's Wallet.
PROGRESSIVE_WALLET = "Wallet_Medium"


# Chest "get" events that act out the vanilla item. Get_StoneOfForest_GetSword (the Kokiri Sword chest) plays
# Dm_Kokiri_0063, where Link swings the sword: he ends up holding a Kokiri Sword that isn't in the save, so
# it is gone after reloading. A randomized chest uses the normal chest event instead.
ITEM_GET_EVENTS = {"Get_StoneOfForest_GetSword"}



def refill_container(item):
    """Pouch actor a refill needs (e.g. arrows -> Bow), or None for anything else."""
    return next((c for prefix, c in REFILL_CONTAINERS if item.startswith(prefix)), None)


def _is_song(item):
    return item.startswith("Melody_")


def _dungeon_item_type(item):
    if item.startswith("Dungeon_SmallKey"):
        return "small_keys"
    if item.startswith("Dungeon_BossKey"):
        return "boss_keys"
    if item.startswith(("Dungeon_Map", "Dungeon_Compass")):
        return "maps_compasses"
    return None


class Plan:
    """Which locations are shuffled and which items go into the pool."""

    def __init__(self, world, st, seed_key=""):
        self.world, self.st, self.seed_key = world, st, seed_key
        self.rules = {l.id: L.location_rule(l) for l in world.locations}
        self._choose_shop_slots(seed_key)
        self.fixed, self.shuffled = {}, []
        self.forced = {}      # unshuffled locations that still get a different item (patched like placements)
        excluded = set(st["excluded_locations"])
        for loc in world.locations:
            if self._is_shuffled(loc):
                self.shuffled.append(loc)
            else:
                self.fixed[loc.id] = loc.vanilla
                if loc.vanilla == "Bottle_Letter" and st["open_zora"] == "open":
                    # King Zora is already moved: the letter would be a dead item, give an empty bottle
                    self.fixed[loc.id] = self.forced[loc.id] = "Bottle"
        self.excluded = {l.id for l in self.shuffled if l.id in excluded or l.name in excluded}
        self.start_locs = set(START_LOCATIONS) if st["skip_child_zelda"] else set()
        self._grantable = {}
        self.pool = [l.vanilla for l in self.shuffled]
        self._adjust_pool()

    def _choose_shop_slots(self, seed_key):
        """Shopsanity: pick N shop-exclusive shelves per shop and give each a price."""
        self.shop_chosen, self.shop_prices = set(), {}
        n = 0 if self.st["shopsanity"] == "off" else int(self.st["shopsanity"])
        if not n:
            return
        rng = random.Random(hashlib.sha256(("shops|" + seed_key).encode()).digest())
        by_shop = defaultdict(list)
        for loc in self.world.locations:
            if loc.kind == "shop":
                by_shop[loc.shop].append(loc)
        for shop in sorted(by_shop):
            slots = sorted(by_shop[shop], key=lambda l: l.id)
            for loc in rng.sample(slots, min(n, len(slots))):
                self.shop_chosen.add(loc.id)
                self.shop_prices[loc.id] = rng.randint(10, 99)   # child wallet holds 99

    def _is_shuffled(self, loc):
        st, item = self.st, loc.vanilla
        if loc.kind == "shop":
            return loc.id in self.shop_chosen
        dtype = _dungeon_item_type(item)
        if dtype:
            if st[dtype] == "vanilla":
                return False
            if loc.kind == "freestanding" and not st["shuffle_freestanding"] and st[dtype] == "vanilla":
                return False
            return True
        if item == "Sword_Kokiri" and not st["shuffle_kokiri_sword"]:
            return False
        if item in UPGRADES and not loc.upgrade_ok:
            return False
        if item == "WeirdEgg" and not st["shuffle_weird_egg"]:
            return False
        if loc.category == "ocarina":
            return st["shuffle_ocarinas"]
        cat = loc.category
        if cat == "song":
            return st["shuffle_songs"] != "vanilla"
        if cat == "reward":
            return st["shuffle_rewards"] != "vanilla"
        if cat == "npc":
            return st["shuffle_npc"]
        if cat == "fairy":
            return st["shuffle_fairies"]
        if cat == "house":
            return st["shuffle_house"]
        if cat == "gs":
            t = st["tokensanity"]
            return t == "all" or (t == "dungeons" and loc.dungeon) or (t == "overworld" and not loc.dungeon)
        if cat == "freestanding":
            return st["shuffle_freestanding"]
        if cat == "rupee":
            return st["shuffle_rupees"]
        if cat == "heart_container":
            return st["shuffle_heart_containers"]
        return cat == "chest"

    def _adjust_pool(self):
        st = self.st
        if st["open_zora"] == "open":
            # Ruto's Letter can't be delivered with an open Fountain; an empty bottle takes its place
            self.pool = ["Bottle" if i == "Bottle_Letter" else i for i in self.pool]
        if st["shuffle_house"]:
            self.pool = [PROGRESSIVE_WALLET if i == "Wallet_Large" else i for i in self.pool]
        if st["shuffle_ocarinas"]:
            # Saria's bridge gift is switched off (gamedata.planned_changes); her Fairy Ocarina replaces junk
            rng = random.Random(hashlib.sha256(("ocarina|" + self.seed_key).encode()).digest())
            junk = sorted(i for i, x in enumerate(self.pool) if x in JUNK)
            if junk:
                self.pool[rng.choice(junk)] = "Ocarina_Fairy"
            else:
                self.pool.append("Ocarina_Fairy")
        if st["maps_compasses"] == "remove":
            self.pool = ["Rupee_Blue" if _dungeon_item_type(i) == "maps_compasses" else i for i in self.pool]
        elif st["maps_compasses"] == "start_with":
            # the save already has them (gamedata.planned_changes); their checks get a random bonus
            rng = random.Random(hashlib.sha256(("start_maps|" + self.seed_key).encode()).digest())
            items, weights = zip(*START_WITH_BONUS)
            self.pool = [rng.choices(items, weights)[0] if _dungeon_item_type(i) == "maps_compasses" else i
                         for i in self.pool]
        if st["item_pool"] in ("scarce", "minimal"):
            seen = Counter()
            new = []
            for i in self.pool:
                if i in ("Heart_Piece", "Heart_Container"):
                    seen[i] += 1
                    if st["item_pool"] == "minimal" or seen[i] % 2 == 0:
                        i = "Rupee_Red"
                new.append(i)
            self.pool = new

    def grantable(self, item):
        """Skip Child Zelda: can a new save simply own `item` (its 'obtained' flag plus a pouch count of 1)?"""
        if item not in self._grantable:
            ok = "@" not in item and item not in REWARDS and not item.startswith(START_DENY_PREFIXES)
            if ok and not _is_song(item):
                from . import gamedata
                try:
                    ok = gamedata.pouch_entry_exists(self.world, self.world.actor_for(item, "event"))
                except KeyError:
                    ok = False
            self._grantable[item] = ok
        return self._grantable[item]

    # which shuffled locations may receive `item`
    def allowed(self, loc, item):
        st = self.st
        if loc.id in self.excluded and (item in L.PROGRESSION or _dungeon_item_type(item) or item in REWARDS):
            return False
        if loc.id in self.start_locs and not self.grantable(item):
            return False
        if item == PROGRESSIVE_WALLET and loc.kind != "chest":
            return False
        is_reward_loc, is_song_loc = loc.category == "reward", loc.category == "song"
        if st["shuffle_rewards"] != "anywhere":
            if item in REWARDS:
                return is_reward_loc
            if is_reward_loc:
                return False
        if _is_song(item):
            if st["shuffle_songs"] == "song":
                return is_song_loc
        elif is_song_loc and st["shuffle_songs"] == "song":
            return False
        if item == "Range_SlingShot" and st["open_forest"] == "closed":
            # the Deku Tree needs it and a closed forest cannot be left before the Deku Tree is done
            if not L.is_deku_slingshot_chest(loc) and (loc.dungeon or loc.region not in L.FOREST_REGIONS):
                return False
        if "@" in item:                       # dungeon items stay in their own dungeon
            return loc.dungeon == item.split("@")[1]
        if loc.kind == "shop":                # a shelf needs a pouch actor with its own pack
            if item in SHOP_FORBIDDEN:        # shelves restock: a stackable item would be infinite
                return False
            try:
                return self.world.actor_exists(self.world.actor_for(item, "event"))
            except KeyError:
                return False
        return True


class Filler:
    def __init__(self, plan, rng):
        self.plan, self.rng = plan, rng
        self.locs = {l.id: l for l in plan.world.locations}
        self.placed = {}
        self.no_logic = plan.st["logic_rules"] == "none"

    def contents(self):
        out = dict(self.plan.fixed)
        out.update(self.placed)
        return out

    def sweep(self, base_items, contents=None):
        """Collect everything reachable starting from base_items. Returns (state, collected_ids, spheres)."""
        contents = self.contents() if contents is None else contents
        s = L.State(base_items)
        got, spheres = set(), []
        pending = [lid for lid in contents]
        while True:
            new = [lid for lid in pending if lid not in got and self.plan.rules[lid](s)]
            if not new:
                break
            spheres.append(new)
            for lid in new:
                got.add(lid)
                s.items[contents[lid]] += 1
            s._c.clear()
            pending = [lid for lid in pending if lid not in got]
        return s, got, spheres

    def place_group(self, items, unplaced_rest, tries=25):
        """Assumed fill for `items`, retried locally (a fresh order each time) before giving up."""
        snapshot = dict(self.placed)
        for t in range(tries):
            try:
                return self._place_group(items, unplaced_rest)
            except GenerationError:
                self.placed = dict(snapshot)
                if t == tries - 1:
                    raise

    def _place_group(self, items, unplaced_rest):
        items = list(items)
        self.rng.shuffle(items)
        # most constrained first: higher-tier items, then other progression, then the rest
        items.sort(key=lambda i: 0 if i in L.LOWER_TIER else (1 if i in L.PROGRESSION else 2))
        remaining = list(items)
        for item in items:
            remaining.remove(item)
            empty = [l for l in self.plan.shuffled if l.id not in self.placed and self.plan.allowed(l, item)]
            if not empty:
                raise GenerationError("no free location can hold %s" % item)
            if self.no_logic or item not in L.PROGRESSION:
                cands = empty
            else:
                base = [i for i in remaining + unplaced_rest if i in L.PROGRESSION]
                state, got, _ = self.sweep(base)
                cands = [l for l in empty if self.plan.rules[l.id](state)]
                lower = L.LOWER_TIER.get(item)
                if lower and cands:
                    # without the lower tier and without other copies of this item (e.g. two Bigger Bomb Bags)
                    without = L.State(i for i in state.items.elements() if i not in (lower, item))
                    tiered = [l for l in cands if not self.plan.rules[l.id](without)]
                    if not tiered:
                        raise GenerationError("no location for %s that requires %s" % (item, lower))
                    cands = tiered
                if not cands:
                    raise GenerationError("no reachable location for %s" % item)
            loc = self.rng.choice(cands)
            self.placed[loc.id] = item

    def run(self):
        plan = self.plan
        pool = list(plan.pool)
        anywhere = plan.st["shuffle_rewards"] == "anywhere"
        groups = [
            [i for i in pool if "@" in i],
            [] if anywhere else [i for i in pool if i in REWARDS],
            [i for i in pool if _is_song(i)],
        ]
        used = Counter()
        for g in groups:
            used.update(g)
        rest = list((Counter(pool) - used).elements())
        prog_rest = [i for i in rest if i in L.PROGRESSION]
        junk_rest = [i for i in rest if i not in L.PROGRESSION]
        later = groups[1] + groups[2] + prog_rest
        # dungeon items first (they are the most constrained), then rewards, songs, other progression
        self.place_group(groups[0], [i for i in later if i in L.PROGRESSION])
        self.place_group(groups[1], [i for i in groups[2] + prog_rest if i in L.PROGRESSION])
        self.place_group(groups[2], [i for i in prog_rest if i in L.PROGRESSION])
        self.place_group(prog_rest, [])
        self.rng.shuffle(junk_rest)
        for lid in sorted(plan.start_locs):
            # Skip Child Zelda: fill an empty start check with junk the save can grant (a shield, Farore's Wind...)
            loc = self.locs[lid]
            if lid in self.placed or loc not in plan.shuffled:
                continue
            item = next((i for i in junk_rest if plan.allowed(loc, i)), None)
            if item is None:
                raise GenerationError("no item the save can grant for %s" % loc.name)
            junk_rest.remove(item)
            self.placed[lid] = item
        empty = [l for l in plan.shuffled if l.id not in self.placed]
        junk_rest.sort(key=lambda i: 0 if i in SHOP_FORBIDDEN else 1)   # restricted junk first
        self.rng.shuffle(empty)
        refills = plan.st.get("refill_needs_item")
        for item in junk_rest:
            spot = None
            if item in PROGRESSIVE_UPGRADES:
                # chests make repeat copies progressive (see write_patches); prefer them
                spot = next((l for l in empty if l.id not in self.placed and l.kind == "chest"
                             and plan.allowed(l, item)), None)
            elif refills and refill_container(item):
                # only chests can check for the container; elsewhere the refill becomes a blue rupee
                spot = next((l for l in empty if l.id not in self.placed and l.kind == "chest"
                             and plan.allowed(l, item)), None)
                if spot is None:
                    item = REFILL_FALLBACK
            if spot is None:
                spot = next((l for l in empty if l.id not in self.placed and plan.allowed(l, item)), None)
            if spot is None:
                raise GenerationError("no location left for %s" % item)
            self.placed[spot.id] = item


def _seed_rng(seed, settings_string):
    h = hashlib.sha256(("%s|%s|%s" % (VERSION, seed, settings_string)).encode()).digest()
    return random.Random(int.from_bytes(h[:8], "little"))


def generate(romfs, out_dir, settings, seed=None, mod_name=None, progress=print, world=None, exefs=None):
    from .gamecheck import check as check_game
    game = check_game(exefs, romfs)
    if not game.ok:
        raise GenerationError(game.message)
    progress(game.message)
    st = S.normalize(settings)
    L.set_options(st)
    sstr = S.to_string(st)
    if not seed:
        seed = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(10))
    seed = str(seed)
    t0 = time.time()
    world = world or World(romfs, progress)
    progress("Building item pool...")
    plan = Plan(world, st, seed_key="%s|%s|%s" % (VERSION, seed, sstr))

    # locations no item set can reach are treated as excluded (they only get junk)
    filler = Filler(plan, random.Random(0))
    everything = [i for i in plan.pool if i in L.PROGRESSION] + list(plan.fixed.values())
    full_state, _, _ = filler.sweep(everything, contents={})
    unreachable = [l for l in plan.shuffled if not plan.rules[l.id](full_state)]
    if unreachable and st["logic_rules"] != "none":
        progress("note: %d location(s) are out of logic and will only hold junk" % len(unreachable))
        plan.excluded |= {l.id for l in unreachable}

    rng = _seed_rng(seed, sstr)
    last_err = None
    for attempt in range(1, 41):
        progress("Placing items (attempt %d)..." % attempt)
        filler = Filler(plan, random.Random(rng.random()))
        try:
            filler.run()
        except GenerationError as e:
            last_err = e
            continue
        if st["logic_rules"] == "none":
            break
        state, got, spheres = filler.sweep([])
        if not state.win:
            last_err = GenerationError("seed not beatable")
            continue
        if st["reachable_locations"] == "all":
            missing = [l for l in plan.shuffled if l.id not in got and l.id not in plan.excluded]
            if missing:
                last_err = GenerationError("%d locations unreachable" % len(missing))
                continue
        break
    else:
        raise GenerationError("could not place items after 40 attempts: %s" % last_err)

    mod_name = mod_name or "OoTR_Remake_%s" % seed
    mod_root = os.path.join(out_dir, mod_name)
    progress("Writing mod files...")
    written = write_patches(world, plan, dict(plan.forced, **filler.placed), os.path.join(mod_root, "romfs"), progress)
    if st["create_spoiler"]:
        write_spoiler(world, plan, filler, seed, sstr, mod_root)
        from .checklist import write_checklist      # contains every placement, so only with the spoiler
        try:
            write_checklist(world, plan, filler, mod_root, VERSION, seed, sstr)
        except ImportError:
            progress("note: checklist.xlsx skipped (openpyxl missing; run Install Requirements.bat)")
    with open(os.path.join(mod_root, "settings.txt"), "w", encoding="utf-8") as fh:
        fh.write("OoTR Remake %s\nSeed: %s\nSettings string: %s\n" % (VERSION, seed, sstr))
    progress("Done in %.1fs: %d files written to %s" % (time.time() - t0, len(written), mod_root))
    return {"seed": seed, "settings_string": sstr, "mod_root": mod_root, "files": written,
            "placements": filler.placed}


# --------------------------------------------------------------------------- patching
def write_patches(world, plan, placed, out_romfs, progress=print):
    zs = world.zs
    locs = {l.id: l for l in world.locations}
    stage_edits = defaultdict(list)   # rel -> [(hash, loc, item)]
    event_edits = defaultdict(list)   # rel -> [(offset, actor)]
    refills = plan.st.get("refill_needs_item")
    for lid, item in placed.items():
        loc = locs[lid]
        needs = refill_container(item) if refills and loc.kind == "chest" else None
        if item == loc.vanilla and not loc.conditional and not needs:
            continue
        for rel, h in loc.stage_refs:
            stage_edits[rel].append((h, loc, item))
        for rel, off in loc.event_refs:
            event_edits[rel].append((off, world.actor_for(item, "event")))

    rt_rel = world._find("System/Resource", "ResourceSizeTable")
    rt_raw, rt_dict = zs.read(rt_rel)
    restbl = F.Restbl(rt_raw)
    current = {}      # rel -> [latest bytes, zstd dict name, compressed?]
    orig_len = {}     # rel -> size of the untouched original (for the size table)

    def read(rel):
        """Latest version of a file: an earlier patch's output if any, else the romfs original."""
        if rel in current:
            return current[rel][0], current[rel][1]
        if rel.endswith(".zs"):
            return zs.read(rel)
        return open(os.path.join(world.romfs, *rel.split("/")), "rb").read(), None

    def emit(rel, orig, new, dict_name, compressed=True):
        if rel not in orig_len:
            orig_len[rel] = len(orig) if rel not in current else len(read(rel)[0])
        current[rel] = [new, dict_name, compressed]

    # items lying in the world need a real pickup actor (see rando/pickups.py)
    pickups = PickupCloner(world, read, emit, restbl, progress)

    for rel, edits in sorted(stage_edits.items()):
        orig, dname = read(rel)
        root = F.byml_load(orig)
        by_hash = defaultdict(list)
        for h, loc, item in edits:
            by_hash[h].append((loc, item))
        hits = 0
        for a in root.get("Actors", []):
            for loc, item in by_hash.get(int(a["Hash"]), []):
                hits += 1
                if loc.kind == "chest":
                    dyn = a.setdefault("Dynamic", {})
                    if dyn.get("GetEventName") in ITEM_GET_EVENTS and item != loc.vanilla:
                        # the chest's own event hands out its vanilla item again (unsaved), so drop it
                        del dyn["GetEventName"]
                    if item in PROGRESSIVE_UPGRADES:
                        bigger, biggest = PROGRESSIVE_UPGRADES[item]
                        if world.actor_exists(bigger) and world.actor_exists(biggest):
                            dyn["Drop__DropActor"] = bigger
                            dyn["Drop__CheckActor"] = bigger
                            dyn["Drop__DropActor_Substitute"] = biggest
                            continue
                    needs = refill_container(item) if refills else None
                    if needs and world.actor_exists(needs):
                        # the game's own conditional chest: owns CheckActor -> Substitute, else DropActor
                        dyn["Drop__DropActor"] = world.actor_for(REFILL_FALLBACK, "chest")
                        dyn["Drop__CheckActor"] = needs
                        dyn["Drop__DropActor_Substitute"] = world.actor_for(item, "chest")
                        continue
                    dyn["Drop__DropActor"] = world.actor_for(item, "chest")
                    dyn.pop("Drop__CheckActor", None)
                    dyn.pop("Drop__DropActor_Substitute", None)
                elif loc.kind == "gs":
                    # the Skulltula's own death now sets its save flag (qol.patch_gs_death)
                    a.setdefault("Dynamic", {})["Drop__DropActor"] = pickups.world_actor(world.actor_for(item, "world"))
                else:
                    a["Gyaml"] = pickups.world_actor(world.actor_for(item, "world"))
        if hits != len(edits):
            raise GenerationError("%s: expected %d actors, patched %d" % (rel, len(edits), hits))
        emit(rel, orig, F.byml_dump(root), dname)

    if plan.st.get("small_chests"):
        patch_small_chests(world, emit, progress, read)

    for rel, edits in sorted(event_edits.items()):
        orig, dname = read(rel)
        ev = F.EvflFile(orig)
        for off, actor in edits:
            ev.set_string_param(off, actor)
        F.EvflFile(ev.data())          # sanity: must still parse
        emit(rel, orig, ev.data(), dname)

    shops = ShopPatcher(world, emit, progress, read)
    for loc in plan.shuffled:
        if loc.kind != "shop":
            continue
        item = placed[loc.id]
        if item == loc.vanilla or item in JUNK:
            continue                          # junk on a shelf: keep the shelf's normal goods
        shops.patch_shelf(loc.vanilla_actor, world.actor_for(item, "event"), plan.shop_prices[loc.id])
    shops.finish()
    pickups.finish()          # after the shops: both edit RSDB/ActorInfo (read() returns the latest)

    if plan.st.get("free_bombs"):
        # Bag bombs share one LiftableParam resource path; every pack that carries a copy must agree,
        # otherwise whichever pack loads first decides. Bomb flowers keep their own (bracelet) grade.
        for rel in BOMB_PACKS:
            if not os.path.exists(os.path.join(world.romfs, *rel.split("/"))):
                continue
            orig, dname = read(rel)
            r0, r1 = F.sarc_file_ranges(orig)[BOMB_LIFT_PARAM]
            sub = orig[r0:r1]
            if F.byml_load(sub).get("LiftGrade") != BRACELET_GRADE:
                continue
            new_sub = F.byml_patch_root_u32(sub, "LiftGrade", DEFAULT_GRADE)
            emit(rel, orig, orig[:r0] + new_sub + orig[r1:], dname)

    bridge_ok = bool(plan.st["shuffle_ocarinas"]) and patch_ocarina_bridge(world, emit, progress, read)
    start_items = [world.actor_for(placed.get(lid, plan.fixed.get(lid)), "event")
                   for lid in sorted(plan.start_locs) if placed.get(lid, plan.fixed.get(lid))]
    gd_ok = gamedata.apply(world, plan.st, read, emit, progress, ocarina_bridge_patched=bridge_ok,
                           start_items=start_items)

    if plan.st.get("saria_song_ocarina"):
        if gd_ok:
            patch_saria_song(world, emit, progress, read, gamedata.SARIA_GATE_OLD, gamedata.SARIA_GATE_NEW)
        else:
            progress("warning: could not add the ocarina save flag; Saria's Song still needs Zelda")

    if plan.st["open_forest"] == "open":
        patch_open_forest_mido(world, emit, progress, read)
    if plan.st["skip_child_zelda"]:
        patch_kokiri_schedules(world, emit, progress, read)
    if plan.st["shuffle_songs"] != "vanilla":
        patch_song_teaching(world, emit, progress, read)
    if plan.st["shuffle_weird_egg"] and plan.st["shuffle_npc"]:
        patch_egg_hatch_guard(world, emit, progress, read)


    if plan.st.get("dodongo_bag_bombs") and not patch_dodongo_bag_bombs(world, emit, progress, read):
        # the logic already counted bag bombs for the entrance, so the seed would not be safe
        raise GenerationError("Dodongo's Cavern boulder logic not recognised in this romfs; "
                              "turn off 'Bag Bombs Open Dodongo's Cavern'")

    if plan.st.get("tokensanity", "off") != "off":
        patch_gs_death(world, emit, progress, read)

    if plan.st.get("anju_one_cucco"):
        patch_anju(world, emit, progress, read)
    if plan.st.get("big_poe_one"):
        patch_big_poe_one(world, emit, progress, read)

    if plan.st.get("skip_cutscenes"):
        # One shared component blocks skipping (opening, credits, title demos); switch it off.
        rel = SKIP_SETTING
        src = os.path.join(world.romfs, *rel.split("/"))
        if os.path.exists(src):
            orig = read(rel)[0]
            root = F.byml_load(orig)
            if root.get("IsDisableSkip"):
                root["IsDisableSkip"] = False
                emit(rel, orig, F.byml_dump(root), None, compressed=False)
        else:
            progress("warning: cutscene skip setting not found in this romfs; skipped")

    written = []
    for rel, (data, dname, compressed) in sorted(current.items()):
        path = os.path.join(out_romfs, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(zs.compress(data, dname) if compressed else data)
        key = rel[:-3] if rel.endswith(".zs") else rel
        old = restbl.get(key)
        if old is not None and len(data) > orig_len[rel]:
            restbl.set(key, old + (len(data) - orig_len[rel]))
        written.append(rel)

    path = os.path.join(out_romfs, *rt_rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(zs.compress(restbl.data(), rt_dict))
    written.append(rt_rel)
    return written


# --------------------------------------------------------------------------- spoiler
def write_spoiler(world, plan, filler, seed, sstr, mod_root):
    os.makedirs(mod_root, exist_ok=True)
    contents = filler.contents()
    locs = {l.id: l for l in world.locations}
    _, _, spheres = filler.sweep([])
    playthrough = []
    for i, sph in enumerate(spheres):
        prog = [(locs[l].name, world.item_name(contents[l])) for l in sph
                if contents[l] in L.PROGRESSION and l in filler.placed]
        if prog:
            playthrough.append(sorted(prog))
    by_region = defaultdict(list)
    for loc in plan.shuffled:
        region = world.region_name(loc.region) if loc.region else "Events"
        name = world.item_name(contents[loc.id])
        if loc.kind == "shop":
            if contents[loc.id] == loc.vanilla or contents[loc.id] in JUNK:
                name = "(normal shop goods)"
            else:
                name += "  [%d rupees]" % plan.shop_prices[loc.id]
        by_region[region].append((loc.name, name))
    lines = ["OoT Remake Randomizer %s" % VERSION, "Seed: %s" % seed, "Settings string: %s" % sstr, "",
             "Settings:"]
    for k, v in S.normalize(plan.st).items():
        lines.append("  %-28s %s" % (S.SPEC[k][3] + ":", v))
    lines += ["", "Playthrough:"]
    for i, sph in enumerate(playthrough, 1):
        lines.append("  Sphere %d" % i)
        lines += ["    %-55s %s" % x for x in sph]
    lines += ["", "Locations:"]
    for region in sorted(by_region):
        lines.append("  %s" % region)
        lines += ["    %-55s %s" % x for x in sorted(by_region[region])]
    with open(os.path.join(mod_root, "spoiler.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(mod_root, "spoiler.json"), "w", encoding="utf-8") as fh:
        json.dump({"version": VERSION, "seed": seed, "settings_string": sstr, "settings": S.normalize(plan.st),
                   "playthrough": playthrough,
                   "locations": {locs[l].name: world.item_name(i) for l, i in sorted(contents.items(),
                                                                                      key=lambda x: locs[x[0]].name)}},
                  fh, indent=1, ensure_ascii=False)
