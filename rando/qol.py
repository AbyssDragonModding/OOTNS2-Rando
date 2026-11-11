"""Quality-of-life patches that are not tied to item placement."""
import os
import struct

from . import formats as F

# --- Anju's cucco minigame -------------------------------------------------------------
# The fence count is compared against a constant 7 in the minigame's logic module
# (compare node: Int_A = 7, Int_B = live fence count). Anju's event flow also keeps a
# "cuccos remaining" counter that starts at 7 and is compared with 7 for her dialogue.
ANJU_AINB = "Logic/MiniGame_CatchCucco_c69b.logic.module.ainb"
ANJU_FLOW = "Event/EventFlow/Minigame_CatchCucco.bfevfl.zs"
ANJU_COUNTER = "Npc_Hylia_049_Child_HowManyCuccos"


def _ainb_const_offsets(data, param_name, value):
    """Offsets of constant (unlinked) int inputs named `param_name` holding `value`.
    AINB input entries are 16 bytes: name offset, link (0xFFFF = constant), flags, value."""
    pool = struct.unpack_from("<I", data, 0x24)[0]
    target = data.find(param_name.encode() + b"\0", pool)
    if target < 0:
        return []
    name_off = target - pool
    hits = []
    for o in range(0x74, pool - 16, 4):
        n, link, flags, v = struct.unpack_from("<IIIi", data, o)
        if (n & 0x7FFFFFFF) == name_off and link == 0xFFFF and flags in (0x01800000, 0x00800000) and v == value:
            hits.append(o + 12)
    return hits


def _ainb_repoint_string_const(data, param_name, old, new):
    """Point every constant string input `param_name` == `old` at `new` (appended to the string
    pool, which is the last section of the file). Returns (new_data, count)."""
    pool = struct.unpack_from("<I", data, 0x24)[0]
    if not data.endswith(b"\0") or data.find(b"\0" + old.encode() + b"\0", pool - 1) < 0:
        return data, 0
    old_off = data.find(b"\0" + old.encode() + b"\0", pool - 1) + 1 - pool
    hits = _ainb_const_offsets(data, param_name, old_off)
    if not hits:
        return data, 0
    out = bytearray(data)
    new_off = len(out) - pool
    out += new.encode() + b"\0"
    for h in hits:
        struct.pack_into("<i", out, h, new_off)
    return bytes(out), len(hits)


# --- Saria's Song ------------------------------------------------------------------------
# Two child-meadow logic modules start the song scene (and move Saria for it) only when
# DoorOfTime_IsAfter_Step01_Exp (met Zelda) is true; they are re-pointed to "owns an ocarina".
SARIA_AINBS = ["Logic/SacredForestMeadow_Child_Prefab_3265.logic.module.ainb",
               "Logic/SacredForestMeadow_Child_Prefab_bbc3.logic.module.ainb"]


def patch_saria_song(world, emit, progress, read, old_flag, new_flag):
    for rel in SARIA_AINBS:
        if not os.path.exists(os.path.join(world.romfs, *rel.split("/"))):
            progress("warning: %s not found; Saria's Song still needs Zelda" % rel)
            continue
        orig = read(rel)[0]
        new, n = _ainb_repoint_string_const(orig, "GameDataNameBoolExp", old_flag, new_flag)
        if n != 1:
            progress("warning: Saria's Song check in %s not recognised (%d matches); skipped" % (rel, n))
            continue
        emit(rel, orig, new, None, compressed=False)


# --- Gold Skulltula death sets its save flag -----------------------------------------------------
# A Gold Skulltula's own save flag (its Bool64bitKey, via ActorGameDataSetting NoRespawn) is normally set by the
# token: the Skulltula's AI writes the flag into the dropped token's "GoldTokenGmdHash" and the token's AI sets
# it on pickup. Its death procedure explicitly turns the flag write off (IsSetGmdRespawnFlagToFalse False).
# A shuffled drop is an ordinary pickup without the token AI, so the Skulltula and its item came back whenever
# the room reloaded. Turn the write on for the death reasons that drop an item, so killing it is permanent.
# (Giving the drop the token's AI instead, in 0.2.1, stopped the drop from spawning at all.)
GS_DEATH = "System/CombinationDataTableData/Enemy_Skulltula_Gold_game__death__DeathReasonProcedures.pp__CombinationDataTableData.bgyml"


def patch_gs_death(world, emit, progress, read):
    if not os.path.exists(os.path.join(world.romfs, *GS_DEATH.split("/"))):
        progress("warning: Gold Skulltula death settings not found; shuffled Skulltulas may respawn")
        return
    orig = read(GS_DEATH)[0]
    root = F.byml_load(orig)
    n = 0
    for key, cell in root.get("CellList", {}).items():
        if isinstance(cell, dict) and "IsSetGmdRespawnFlagToFalse" in cell:
            cell["IsSetGmdRespawnFlagToFalse"] = True
            n += 1
    if not n:
        progress("warning: Gold Skulltula death settings not recognised; shuffled Skulltulas may respawn")
        return
    emit(GS_DEATH, orig, F.byml_dump(root, version=F.BymlReader(orig).ver), None, compressed=False)


# --- Dungeon restart point ---------------------------------------------------------------------
# Each dungeon quest's GameSafetySetting names a NoEscapeRangeAreaBox ("NoEscapeArea_<x>") and a
# StartPos anchor ("StartPos_<x>"), normally the boss room and its door. A save loaded inside the box
# while the quest is active restarts at the anchor. Stretch the boxes over the whole dungeon and point
# the setting at a new anchor ("StartPos_Rando_<dungeon>", a copy of the entrance start point).
# The original anchors stay where they are: bosses link to them (Gohma references
# StartPos_Get_StoneOfForest and puts Link there when the fight starts), so moving them warps Link to
# the entrance mid-fight.
DUNGEON_ENTRANCES = {
    "InsideTheDekuTree": "Entrance", "DodongoCavern": "DodongoCavern_MountainTrailSide",
    "InsideJabuJabuBelly": "InsideJabuJabuBelly_FromZoraFountain", "ForestTemple": "ForestTemple",
    "FireTemple": "FireTemple", "WaterTemple": "WaterTemple_FromLakeHylia", "ShadowTemple": "Entrance",
    "SpiritTemple": "SpiritTemple_Entrance", "BottomOfTheWell": "Well_KakarikoSide",
    "InsideGanonCastle": "Entrance",
}
NO_ESCAPE_MARGIN = 40.0
# boxes that also exist in a stage outside the dungeon (Ganon's tower uses Defeat_Ganon too); the
# setting row is global, so pointing it at a dungeon-only anchor would break the other stage
SHARED_NO_ESCAPE = {"NoEscapeArea_Defeat_Ganon"}


def _new_actor_hash(seed, taken):
    import hashlib
    n = 0
    while True:
        h = int.from_bytes(hashlib.sha1(("%s/%d" % (seed, n)).encode()).digest()[:8], "little")
        if h and h not in taken:
            return h
        n += 1


def patch_dungeon_restart(world, emit, progress, read):
    import copy
    import glob
    gss_rel = world._find("RSDB", "GameSafetySetting")
    gss_data, gss_dname = read(gss_rel)
    gss = F.byml_load(gss_data)
    gss_changed = False
    for dg, entrance in DUNGEON_ENTRANCES.items():
        rels = sorted(os.path.relpath(p, world.romfs).replace("\\", "/")
                      for p in glob.glob(os.path.join(world.romfs, "Banc", dg, dg + "_*.bcett.byml.zs")))
        roots = {}
        for rel in rels:
            data, dname = read(rel)
            roots[rel] = (data, dname, F.byml_load(data))
        actors = [a for _, _, r in roots.values() for a in r.get("Actors", [])]
        anchor = next((a for a in actors if a.get("Gyaml") == "StartPos" and a.get("Name") == entrance), None)
        pts = [a["Translate"] for a in actors if "Translate" in a]
        if anchor is None or not pts:
            progress("warning: %s entrance not found; dungeon restart unchanged there" % dg)
            continue
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        tmpl = type(pts[0][0])
        boxes = set()
        changed_rels = set()
        for rel, (data, dname, r) in roots.items():
            for a in r.get("Actors", []):
                name = str(a.get("Name", ""))
                if (a.get("Gyaml") == "NoEscapeRangeAreaBox" and name.startswith("NoEscapeArea_")
                        and name not in SHARED_NO_ESCAPE):
                    a["Translate"] = [tmpl((lo[i] + hi[i]) / 2) for i in range(3)]
                    a["Scale"] = [tmpl(hi[i] - lo[i] + 2 * NO_ESCAPE_MARGIN) for i in range(3)]
                    a.pop("Rotate", None)
                    boxes.add(name)
                    changed_rels.add(rel)
        rows = [row for row in gss if row.get("NoEscapeRangeAreaName") in boxes]
        if not rows:
            progress("note: %s has no quest restart area; dungeon restart unchanged there" % dg)
            continue
        # the new anchor goes in the same file as the entrance start point
        new_name = "StartPos_Rando_" + dg
        taken = {int(a["Hash"]) for a in actors if "Hash" in a}
        new = copy.deepcopy(anchor)
        h = type(anchor["Hash"])(_new_actor_hash(new_name, taken))
        new["Hash"] = h
        new["Name"] = new_name
        new.pop("Links", None)
        if isinstance(new.get("Phive"), dict) and isinstance(new["Phive"].get("Placement"), dict):
            new["Phive"]["Placement"]["ID"] = h
        for rel, (data, dname, r) in roots.items():
            if any(a is anchor for a in r.get("Actors", [])):
                r["Actors"].append(new)
                changed_rels.add(rel)
                break
        for rel in sorted(changed_rels):
            data, dname, r = roots[rel]
            emit(rel, data, F.byml_dump(r), dname)
        for row in rows:
            row["NoEscapeRangeAnchorName"] = new_name
            gss_changed = True
    if gss_changed:
        emit(gss_rel, gss_data, F.byml_dump(gss, version=F.BymlReader(gss_data).ver), gss_dname)


# --- Dodongo's Cavern boulder and bag bombs ------------------------------------------------------
# Logic/DeathMountainTrail_Child_Prefab_ffa7: the boulder (node 7, ActorLogicDeathProcComplete) breaks
# when its break event runs. The event is requested by node 14 = OperateAND(node 6 output 5, node 5),
# where node 6 is the special bomb flower's own logic (its fruit state) and node 5 = OR of the three
# "BombFruit" sensors. Node 20 is a sensor for "Item_Bomb" (bag bombs) that vanilla doesn't use there.
# Patch: node 14 becomes OperateOR, and its flower-state input becomes node 20's hit output, so either
# a bag bomb near the boulder or a bomb-flower fruit triggers the break.
DODONGO_AINB = "Logic/DeathMountainTrail_Child_Prefab_ffa7.logic.module.ainb"


def _ainb_node(data, i):
    return 0x74 + struct.unpack_from("<I", data, 0x0C)[0] * 0x18 + i * 0x3C


def _ainb_node_name(data, i):
    pool = struct.unpack_from("<I", data, 0x24)[0]
    off = struct.unpack_from("<I", data, _ainb_node(data, i) + 8)[0]
    return data[pool + off:data.index(b"\0", pool + off)].decode()


def patch_dodongo_bag_bombs(world, emit, progress, read):
    from .gamedata import mm3
    rel = DODONGO_AINB
    if not os.path.exists(os.path.join(world.romfs, *rel.split("/"))):
        progress("warning: Dodongo's Cavern boulder logic not found; bag bombs still can't open it")
        return False
    data = bytearray(read(rel)[0])
    names = {i: _ainb_node_name(data, i) for i in (5, 6, 7, 14, 20)}
    expect = {5: "OperateOR", 6: "ActorLogicBombFlowerGrassBreakBreakDeathMtTrailBrokenRock",
              7: "ActorLogicDeathProcComplete", 14: "OperateAND", 20: "HoldActorObserverBySensorHitInfo"}
    pool = struct.unpack_from("<I", data, 0x24)[0]
    item_bomb = data.find(b"\0Item_Bomb\0", pool) + 1 - pool
    multi, multi_end = struct.unpack_from("<II", data, 0x38)[0], struct.unpack_from("<I", data, 0x30)[0]
    pair = None
    for o in range(multi, multi_end - 8, 8):
        if struct.unpack_from("<HH", data, o) == (6, 5) and struct.unpack_from("<HH", data, o + 8) == (5, 1):
            pair = o
    if names != expect or item_bomb <= 0 or pair is None:
        progress("warning: Dodongo's Cavern boulder logic not recognised; bag-bomb patch skipped")
        return False
    n14, n5 = _ainb_node(data, 14), _ainb_node(data, 5)
    struct.pack_into("<I", data, n14 + 8, struct.unpack_from("<I", data, n5 + 8)[0])   # name -> OperateOR
    struct.pack_into("<I", data, n14 + 0xC, mm3("OperateOR"))                            # name hash
    struct.pack_into("<HH", data, pair, 20, 0)                                           # flower state -> Item_Bomb sensor hit
    emit(rel, read(rel)[0], bytes(data), None, compressed=False)
    return True


# --- Songs: the teaching sub-flow also hands out the vanilla song -------------------------------
# Dm_SY_Ocarina's LearningOcarinaPlayAuto / ...ForSeek entries add the song being taught (by
# MelodyType) with EventTriggerAddOrRemovePouchContent, on top of each song event's own give node.
# With songs shuffled, set those adds to 0 so a song location only gives its randomized item.
SONG_TEACH_FLOW = "Event/EventFlow/Dm_SY_Ocarina.bfevfl.zs"
TAUGHT_SONGS = {"Item_Melody_ZeldaLullaby", "Item_Melody_EponaSong", "Item_Melody_SariaSong", "Item_Melody_SunSong",
                "Item_Melody_TimeSong", "Item_Melody_StormSong", "Item_Melody_ForestMinuet", "Item_Melody_FireBolero",
                "Item_Melody_WaterSerenade", "Item_Melody_SpiritRequiem", "Item_Melody_ShadowNocturne",
                "Item_Melody_LightPrelude"}


def patch_song_teaching(world, emit, progress, read):
    n = 0
    for rel in (SONG_TEACH_FLOW, SONG_TEACH_FLOW.replace(".bfevfl.zs", ".110.bfevfl.zs")):
        if not os.path.exists(os.path.join(world.romfs, *rel.split("/"))):
            continue
        data, dname = read(rel)
        ev = F.EvflFile(data)
        for fc in ev.flowcharts:
            for e in fc["events"]:
                p = e.get("params")
                if (e.get("action") == "EventTriggerAddOrRemovePouchContent" and isinstance(p, dict)
                        and p.get("Actor") in TAUGHT_SONGS and p.get("Num") == 1 and "#int:Num" in e["ptrs"]
                        and any(x.startswith("LearningOcarina") for x in e["entry_points"])):
                    ev.set_int_param(e["ptrs"]["#int:Num"], 0)
                    n += 1
        if n:
            emit(rel, data, ev.data(), dname)
    if n < len(TAUGHT_SONGS):
        progress("warning: only %d of %d song-teaching gifts found; some songs may also be given vanilla"
                 % (n, len(TAUGHT_SONGS)))


# --- Weird Egg: only hatch when you have it -----------------------------------------------------
# Goto_HyruleCastle "Step03_01_Npc_Navi_StepStart" (query 129) always runs :EggHatch, which removes the
# egg and gives the Wake-Up Cucco. Re-use the flow's unreachable pouch query (event 41,
# "IsExistInPouch Item_AlarmCucco") as "has the Weird Egg?": yes -> the normal hatch (35), no -> skip
# the hatch but still advance the quest step (38).
EGG_FLOW = "Event/EventFlow/Goto_HyruleCastle.bfevfl.zs"


def patch_egg_hatch_guard(world, emit, progress, read):
    data, dname = read(EGG_FLOW)
    ev = F.EvflFile(data)
    evs = ev.flowcharts[0]["events"]
    try:
        q, sel, hatch, step = evs[41], evs[129], evs[35], evs[38]
        ok = (q.get("query") == "EventQueryIsExistInPouch" and q["params"].get("Actor") == "Item_AlarmCucco"
              and not q["entry_points"] and sel.get("query") == "EventQueryPlayerCheckSelectedItem"
              and hatch.get("entry") == "EggHatch" and step.get("action") == "EventExecuteProgressChallengeStep"
              and sorted(v for v, _ in q["cases"]) == [0, 1])
        # only unreachable events (leftover Malon dialogue, 43/45) may point at it
        referenced = any((41 == e.get("next") or 41 in [t for _, t in e.get("cases", [])]) and e["entry_points"]
                         for e in evs)
    except (IndexError, KeyError, AttributeError):
        ok = False
    if not ok or referenced:
        progress("warning: egg hatch event not recognised; the Cucco may hatch without the Weird Egg")
        return
    ev.set_string_param(q["ptrs"]["Actor"], "Item_WeirdEgg")
    ev.set_case_targets(q, {0: 38, 1: 35})
    ev.set_case_targets(sel, {v: 41 for v, _ in sel["cases"]})
    F.EvflFile(ev.data())
    emit(EGG_FLOW, data, ev.data(), dname)


def patch_anju(world, emit, progress, read, cuccos=1):
    src = os.path.join(world.romfs, *ANJU_AINB.split("/"))
    if not os.path.exists(src):
        progress("warning: Anju minigame logic not found; skipped")
        return
    orig = read(ANJU_AINB)[0]
    hits = _ainb_const_offsets(orig, "Int_A", 7)
    if len(hits) != 1:
        progress("warning: Anju minigame check not recognised (%d matches); skipped" % len(hits))
        return
    new = bytearray(orig)
    struct.pack_into("<i", new, hits[0], cuccos)
    emit(ANJU_AINB, orig, bytes(new), None, compressed=False)

    for rel in (ANJU_FLOW, ANJU_FLOW.replace(".bfevfl.zs", ".110.bfevfl.zs")):
        if not os.path.exists(os.path.join(world.romfs, *rel.split("/"))):
            continue
        data, dname = read(rel)
        ev = F.EvflFile(data)
        n = 0
        for fc in ev.flowcharts:
            for e in fc["events"]:
                p = e.get("params")
                if not isinstance(p, dict) or p.get("GameDataName") != ANJU_COUNTER or p.get("Value") != 7:
                    continue
                if e.get("action") == "EventTriggerSetGameDataInt" or e.get("query") == "EventQueryIsGameDataInt":
                    ev.set_int_param(e["ptrs"]["#int:Value"], cuccos)
                    n += 1
        if n:
            emit(rel, data, ev.data(), dname)
