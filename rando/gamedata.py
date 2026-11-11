"""Edits to the default save data (GameData/GameDataList), applied when a new file is started.

GameData entries are keyed by MurmurHash3 (seed 0) of the flag name, e.g.
"KokiriForest_Npc_Kokiri_007_Child_Blocker_00". Plain Bool/Int defaults are changed directly;
computed BoolExp flags are formulas over other flags ([opcode, hash] lists, opcode 0 = read a Bool).
"""
import copy

from . import formats as F


def mm3(name, seed=0):
    key = name.encode()
    h, c1, c2, n = seed, 0xCC9E2D51, 0x1B873593, len(key)
    for i in range(0, n // 4 * 4, 4):
        k = int.from_bytes(key[i:i + 4], "little")
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail, k = key[n // 4 * 4:], 0
    for i, b in enumerate(tail):
        k |= b << (8 * i)
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= n
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


# Opening flags
FOREST_EXIT = "KokiriForest_Npc_Kokiri_007_Child_Blocker_00"      # Kokiri boy at the forest exit
FOREST_MIDO = "KokiriForest_Npc_Kokiri_Mido_Child_Blocker"         # Mido in front of the Deku Tree
ZORA_OPEN = ["HavePlayedEvent.Dm_Zora_0010",                       # King Zora reads Ruto's letter and moves
             "Get_StoneOfWater_ReadRutoLetter", "Get_StoneOfWater_TalkedZoraAboutRutoLetter"]
DOOR_OPEN = "Market_Child_TimeTempleDoor_Opened"
EPONA_DONE_EXP = "Get_Epona_IsCompleted_Exp"
EPONA_SONG_OWNED = "IsGet.Item_Melody_EponaSong"

# Dungeon map / compass ownership: DungeonInfo.<dungeon>.IsGetMap / .IsGetCompass (plain Bools)
MAP_DUNGEONS = ["InsideTheDekuTree", "DodongoCavern", "InsideJabuJabuBelly", "ForestTemple", "FireTemple",
                "WaterTemple", "ShadowTemple", "SpiritTemple", "BottomOfTheWell", "IceCavern"]

# Saria's Song: the meadow trigger normally checks DoorOfTime_IsAfter_Step01_Exp (met Zelda).
# A new computed flag "owns an ocarina" replaces that check (see qol.patch_saria_song).
SARIA_GATE_OLD = "DoorOfTime_IsAfter_Step01_Exp"
SARIA_GATE_NEW = "Rando_HasOcarina_Exp"
OCARINA_FLAGS = ["IsGet.Item_Ocarina_Fairy", "IsGet.Item_Ocarina_Time"]

# First-arrival intro scenes that only move the camera/actors, and whose arrival entry (the
# entrance's InitEventName in the stage data, or the shared Dm_SY_BancChangeArrive entry) does
# nothing else: no quest step, flag or sub-flow. Their "played" flag only feeds the entrance check
# (directly, or through InitDemo_* computed flags).
# Left out on purpose because their arrival entry also advances a quest / sets flags:
#   Dm_Deku_0000 (Get_StoneOfForest MeetBoss), Dm_DeathMtTrail_0000 (Get_StoneOfFire DeathMtTrailNpc),
#   Dm_Zora_0000 (Get_StoneOfWater Step03), Dm_DesertColossus_0000 (SageOfSpirit Step04),
#   Dm_HrlCastle_0005 (Goto_HyruleCastle EntryMarket), Dm_DeathMtCrater_0000(+_FromTop) (SageOfFire),
#   Goto_IceCave (SageOfWater Step03), Goto_ShadowTemple (SageOfShadow MeetBoss),
#   Goto_GerudoTrainingGround (SubEvent_GetIceArrow), Goto_SacredForest (Moblin position flag),
#   Dm_Kokiri_0000 / Dm_Goron_0000 / Dm_LostWood_0000 / Dm_HrlField_0000 / Dm_ZoraRiver_0000 (story).
AREA_INTROS = ["Dm_LakeHrl_0000", "Dm_ZoraFountain_0000", "Dm_GanonCastle_0000", "Dm_LostWood_0010",
               "Dm_Kakariko_0000", "Dm_Graveyard_0000", "Dm_HrlCastle_0000", "Dm_Gerudo_0000",
               "Dm_GerudoValley_0000", "Goto_ZoraRiver", "Goto_KakarikoWells", "Goto_FireTemple",
               "Goto_SpritTemple"]


class GameDataPatcher:
    def __init__(self, world, read, emit, progress=print):
        self.world, self.read, self.emit, self.progress = world, read, emit, progress
        self.rel = world._find("GameData", "GameDataList")
        self.orig, self.dname = read(self.rel)
        self.ver = F.BymlReader(self.orig).ver
        self.big = self.orig[:2] == b"BY"
        self.root = F.byml_load(self.orig)
        self.index = {}
        for typ, rows in self.root["Data"].items():
            for r in rows:
                if isinstance(r, dict) and "Hash" in r:
                    self.index[int(r["Hash"])] = (typ, r)
        self.changed = 0

    def _get(self, name, typ):
        hit = self.index.get(mm3(name))
        if hit is None or hit[0] != typ:
            self.progress("warning: save flag %s not found as %s; skipped" % (name, typ))
            return None
        return hit[1]

    def set_bool(self, name, value):
        row = self._get(name, "Bool")
        if row is not None and bool(row["DefaultValue"]) != value:
            row["DefaultValue"] = bool(value)
            self.changed += 1
        return row is not None

    def set_bool_exp_to_flag(self, name, flag):
        """Make computed flag `name` equal to plain Bool `flag`."""
        row = self._get(name, "BoolExp")
        if row is None or self._get(flag, "Bool") is None:
            return False
        tmpl = row["Values"][0]
        op = type(tmpl[0])(0)
        h = type(tmpl[1])(mm3(flag))
        row["Values"] = [[op, h]]
        self.changed += 1
        return True

    def add_bool_exp_any(self, name, flags):
        """Add a new computed flag `name` = flag1 OR flag2 OR ... (plain Bools). BoolExps are not saved."""
        h = mm3(name)
        if h in self.index:
            return False
        if any(self._get(f, "Bool") is None for f in flags):
            return False
        tmpl = self.root["Data"]["BoolExp"][0]
        u64 = type(tmpl["Values"][0][0])
        values = [[u64(0), u64(mm3(flags[0]))]]
        for f in flags[1:]:
            values += [[u64(0), u64(mm3(f))], [u64(4)]]          # 0 = read Bool, 4 = OR
        row = {"Hash": type(tmpl["Hash"])(h), "ResetTypeValue": tmpl["ResetTypeValue"],
               "SaveFileIndex": tmpl["SaveFileIndex"], "Values": values}
        self.root["Data"]["BoolExp"].append(row)
        self.index[h] = ("BoolExp", row)
        self.changed += 1
        return True

    def finish(self):
        if self.changed:
            self.emit(self.rel, self.orig, F.byml_dump(self.root, version=self.ver, big_endian=self.big), self.dname)


def planned_changes(st):
    """Save-data edits for these settings: [(kind, flag, value, setting key, what it does)].
    kind: "bool" (default value), "exp" (computed flag rewritten to read `value`), "new_exp" (added, OR of flags)."""
    out = []
    if st["open_forest"] in ("closed_deku", "open"):
        out.append(("bool", FOREST_EXIT, False, "open_forest", "Kokiri boy / invisible wall at the forest exit is gone"))
    if st["open_forest"] == "open":
        out.append(("bool", FOREST_MIDO, False, "open_forest", "Mido no longer blocks the path to the Deku Tree"))
    if st["open_zora"] == "open":
        for f in ZORA_OPEN:
            out.append(("bool", f, True, "open_zora", "King Zora has already read Ruto's letter and moved aside"))
    if st["open_door"] == "open":
        out.append(("bool", DOOR_OPEN, True, "open_door", "Door of Time starts open"))
    if st["skip_epona_race"]:
        out.append(("exp", EPONA_DONE_EXP, EPONA_SONG_OWNED, "skip_epona_race",
                    "Adult Epona exists once you own Epona's Song (no Ingo race)"))
    if st["skip_area_intros"]:
        for ev in AREA_INTROS:
            out.append(("bool", "HavePlayedEvent." + ev, True, "skip_area_intros", "Intro %s counts as already seen" % ev))
    if st["maps_compasses"] == "start_with":
        for d in MAP_DUNGEONS:
            for f in ("IsGetMap", "IsGetCompass"):
                out.append(("bool", "DungeonInfo.%s.%s" % (d, f), True, "maps_compasses",
                            "Start with the %s %s" % (d, f[5:].lower())))
    if st["shuffle_ocarinas"]:
        # Saria's goodbye on the forest bridge (Goto_HyruleCastle -> Dm_Kokiri_0150 + 0155, the Fairy Ocarina)
        # is requested by an area trigger only while it hasn't been played. Mark it as seen, plus the flag the
        # scene sets on its way to Hyrule Field, so the forest exit works like after the vanilla scene.
        for ev in ("Dm_Kokiri_0150", "Dm_Kokiri_0155"):
            out.append(("bool", "HavePlayedEvent." + ev, True, "shuffle_ocarinas",
                        "Saria's bridge goodbye (Fairy Ocarina gift) counts as already seen"))
    if st["open_forest"] in ("closed_deku", "open") or st["shuffle_ocarinas"]:
        # Hyrule Field uses a "first visit" light table (MainField_Bluesky_First: IsForceMainLight, the sun pinned
        # at one angle) until this flag is set, which vanilla does in Saria's bridge goodbye after the Deku Tree.
        # Leaving the forest early (or skipping that scene) kept the sun frozen; start with the normal day cycle.
        key = "open_forest" if st["open_forest"] in ("closed_deku", "open") else "shuffle_ocarinas"
        out.append(("bool", "HyruleField_ChangeENV", True, key,
                    "Hyrule Field uses its normal day/night lighting instead of the fixed first-visit sun"))
    if st["saria_song_ocarina"]:
        out.append(("new_exp", SARIA_GATE_NEW, OCARINA_FLAGS, "saria_song_ocarina",
                    "True when you own the Fairy Ocarina or Ocarina of Time (replaces the met-Zelda check)"))
    return out


def apply(world, st, read, emit, progress):
    gd = GameDataPatcher(world, read, emit, progress)
    ok = True
    for kind, flag, value, _, _ in planned_changes(st):
        if kind == "bool":
            gd.set_bool(flag, value)
        elif kind == "exp":
            gd.set_bool_exp_to_flag(flag, value)
        elif kind == "new_exp":
            ok = gd.add_bool_exp_any(flag, value) or mm3(flag) in gd.index
    gd.finish()
    return ok
