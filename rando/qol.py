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


# --- Open forest: Mido has already let you pass -------------------------------------------------
# Clearing Mido's blocker flag only removes his invisible wall. Where he stands comes from his AI schedule
# (Component/AIScheduleParam/Npc_Kokiri_Mido_Child): he guards the path until Meet_DekuTree_IsAfter_Step02_Exp,
# i.e. until the "Meet the Deku Tree" quest reaches Step02, which his own flow does after the sword-and-shield
# check (then Step03). The opening cutscene (OpeningEvent) starts that quest at Step01; with Open forest it
# starts it at Step03 instead, the state the quest is in right after Mido steps aside. The Deku Tree scene
# (Dm_Kokiri_0075) still completes it.
OPENING_FLOW = "Event/EventFlow/OpeningEvent.bfevfl.zs"
MIDO_DONE_STEP = "Step03"


def patch_open_forest_mido(world, emit, progress, read):
    data, dname = read(OPENING_FLOW)
    ev = F.EvflFile(data)
    hits = [e for fc in ev.flowcharts for e in fc["events"]
            if e.get("action") == "EventExecuteProgressChallengeStep" and isinstance(e.get("params"), dict)
            and e["params"].get("ChallengeName") == "Meet_DekuTree" and e["params"].get("StepName") == "Step01"]
    if len(hits) != 1:
        progress("warning: opening quest step not recognised (%d matches); Mido may still block the Deku Tree"
                 % len(hits))
        return False
    ev.set_string_param(hits[0]["ptrs"]["StepName"], MIDO_DONE_STEP)
    F.EvflFile(ev.data())                                   # sanity: must still parse
    emit(OPENING_FLOW, data, ev.data(), dname)
    return True


# --- Shuffle Ocarinas: no goodbye on the forest bridge ---------------------------------------------
# Saria's goodbye (Goto_HyruleCastle :KokiriForest_ArriveLostWood -> Dm_Kokiri_0150 / 0155, which give the Fairy
# Ocarina) is requested by the bridge area trigger only while Dm_Kokiri_0150 hasn't been played
# (HoldGameDataHavePlayedEvent, EventName "Dm_Kokiri_0150"). Point that check at Dm_Kokiri_0045 instead, the
# greeting outside Link's house that always plays first (it opens the house door), so the trigger never fires.
# Marking 0150 as seen in the save did the same, but Saria's forest AI schedule and logic also read that flag
# and treated her as gone from the start, so the greeting played without her.
OCARINA_BRIDGE_AINB = "Logic/KokiriForest_Child_Level_All_02_ddcd.logic.module.ainb"
OCARINA_BRIDGE_EVENT = "Dm_Kokiri_0150"
OCARINA_BRIDGE_ALWAYS_PLAYED = "Dm_Kokiri_0045"


def patch_ocarina_bridge(world, emit, progress, read):
    if not os.path.exists(os.path.join(world.romfs, *OCARINA_BRIDGE_AINB.split("/"))):
        return False
    orig = read(OCARINA_BRIDGE_AINB)[0]
    new, n = _ainb_repoint_string_const(orig, "EventName", OCARINA_BRIDGE_EVENT, OCARINA_BRIDGE_ALWAYS_PLAYED)
    if n != 1:
        progress("note: forest bridge trigger not recognised (%d matches); marking Saria's goodbye as seen instead"
                 % n)
        return False
    emit(OCARINA_BRIDGE_AINB, orig, new, None, compressed=False)
    return True


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


# --- Small Chests Only: big chests become small ones, with the small chest's short opening ------------------
# Obj_TBox_A_02 (big) and A_03 (Boss Key) are built on A_01 (their packs carry Obj_TBox_A_01's ActorParam), so
# the stage actor's Gyaml can simply change. Which opening plays is the chest's GetEventName blackboard string:
# Dm_SY_TreasureboxSmall for A_01, Dm_SY_Treasurebox (the long one) for A_02. About 30 big chests override it
# per placement (Dynamic.GetEventName, a row of RSDB/EventSetting) with a script that ends in a jump to
# Dm_SY_Treasurebox, so in 0.4.0 they kept the long opening. Pointing those jumps at Dm_SY_TreasureboxSmall
# (0.4.1) left the chests unopenable. Now:
#  - scripts that only add a Navi line or a camera move before the big opening are dropped from the chest, so it
#    opens like any small chest (the same as the randomized Kokiri Sword chest, see generator.ITEM_GET_EVENTS);
#  - chests whose script runs story events stay vanilla big chests.
SMALL_CHEST = {"Obj_TBox_A_02": "Obj_TBox_A_01", "Obj_TBox_A_03": "Obj_TBox_A_01",
               "Obj_TBox_A_02_NoBake": "Obj_TBox_A_01_NoBake", "Obj_TBox_A_03_NoBake": "Obj_TBox_A_01_NoBake"}
# Story scripts: quest steps, cutscenes, Ruto, a minigame's state.
BIG_CHEST_STORY_EVENTS = {
    "SageOfSpirit_NaboorIsTakenAway",           # Nabooru is taken (Spirit quest Step07, Dm_DesertColossus_0030)
    "SageOfWater_MelodyGet_Water",              # Sheik teaches the Serenade (Water quest Step04/05)
    "InsideJabuJabuBelly_TreasureBoxWithRuto09", "InsideJabuJabuBelly_TreasureBoxWithRuto12",   # Ruto
    "MiniGame_DampeRace_OpenGoalTBox",          # Dampe race goal chest state
    "InsideGanonCastle_Get_Gauntlet_Gold",      # Dm_InsideGanonCastle_0006
    "SubEvent_GetIceArrow_OpenTBox",            # completes the Ice Arrow side quest
    "Get_StoneOfForest_GetSword",               # Kokiri Sword scene (dropped already when that chest is randomized)
}


def patch_small_chests(world, emit, progress, read):
    swapped = dropped = kept = 0
    banc = os.path.join(world.romfs, "Banc")
    keys = [k.encode() for k in SMALL_CHEST]
    for dp, _, fns in sorted(os.walk(banc)):
        for fn in sorted(fns):
            if not fn.endswith(".bcett.byml.zs"):
                continue
            rel = os.path.relpath(os.path.join(dp, fn), world.romfs).replace(os.sep, "/")
            orig, dname = read(rel)
            if not any(k in orig for k in keys):
                continue
            root = F.byml_load(orig)
            hit = 0
            for a in root.get("Actors", []):
                small = SMALL_CHEST.get(a.get("Gyaml"))
                if not small or not world.actor_exists(small):
                    continue
                dyn = a.get("Dynamic") or {}
                script = dyn.get("GetEventName")
                if script in BIG_CHEST_STORY_EVENTS:
                    kept += 1
                    continue
                if script:
                    del dyn["GetEventName"]
                    dropped += 1
                a["Gyaml"] = small
                hit += 1
            if hit:
                swapped += hit
                emit(rel, orig, F.byml_dump(root), dname)
    progress("Small chests: %d big chest placements now small (%d Navi/camera scripts dropped); "
             "%d story chests kept big" % (swapped, dropped, kept))
    return swapped, dropped, kept


# --- Skip Child Zelda: the Kokiri stay where they are before the Hyrule Castle trip ---------------------------
# Every child Kokiri's AI schedule (Component/AIScheduleParam/Npc_Kokiri_*_Child) ends with a condition on
# Goto_HyruleCastle_IsCompleted_Exp: their spots after you've met Zelda. Skip Child Zelda completes that quest
# on a new save, so Mido walked off his post while his invisible wall (KokiriForest_Npc_Kokiri_Mido_Child_Blocker,
# cleared only by his own sword-and-shield talk) stayed: the Deku Tree couldn't be reached (0.4.0 report).
# Dropping that condition keeps the Kokiri on their Deku Tree quest schedules.
KOKIRI_SCHEDULES = "Component/AIScheduleParam"
CASTLE_DONE_EXP = "Goto_HyruleCastle_IsCompleted_Exp"


def patch_kokiri_schedules(world, emit, progress, read):
    folder = os.path.join(world.romfs, *KOKIRI_SCHEDULES.split("/"))
    n = 0
    for fn in sorted(os.listdir(folder)):
        if not (fn.startswith("Npc_Kokiri_") and "_Child." in fn):
            continue
        rel = KOKIRI_SCHEDULES + "/" + fn
        orig = read(rel)[0]
        root = F.byml_load(orig)
        conds = root.get("ConditionalSchedule") or []
        keep = [c for c in conds if c.get("ConditionFlag") != CASTLE_DONE_EXP]
        if len(keep) != len(conds):
            root["ConditionalSchedule"] = keep
            emit(rel, orig, F.byml_dump(root), None, compressed=False)
            n += 1
    if not any(fn.startswith("Npc_Kokiri_Mido_Child") for fn in os.listdir(folder)):
        progress("warning: Mido's schedule not found; he may leave his post with Skip Child Zelda")
    progress("Skip Child Zelda: %d Kokiri schedules keep their before-the-castle spots" % n)
    return n


# --- Big Poe buyer needs only 1 Big Poe ---------------------------------------------------------------------
# Npc_Hylia_048_BottleShop (the adult Market ghost shop) gives 100 points per Big Poe. Before each sale it compares
# GhostShop_CouponNum with 900 (EventQueryIsGameDataInt): below it's a normal sale, at 900 or more it's the final
# sale (Sell_AfterCheckingLoseMoney_900), which completes SubEvent_GhostShop and gives his reward. Comparing with 0
# makes the first sale the final one. After the quest is complete the shop no longer reaches this check.
GHOST_SHOP_FLOW = "Event/EventFlow/Npc_Hylia_048_BottleShop.bfevfl.zs"
GHOST_SHOP_POINTS = "GhostShop_CouponNum"


def patch_big_poe_one(world, emit, progress, read):
    data, dname = read(GHOST_SHOP_FLOW)
    ev = F.EvflFile(data)
    hits = [e for fc in ev.flowcharts for e in fc["events"]
            if e.get("query") == "EventQueryIsGameDataInt" and isinstance(e.get("params"), dict)
            and e["params"].get("GameDataName") == GHOST_SHOP_POINTS and e["params"].get("Value") == 900
            and "#int:Value" in e["ptrs"]]
    if len(hits) != 1:
        progress("warning: Big Poe buyer's 900-point check not found (%d matches); he still wants ten" % len(hits))
        return False
    ev.set_int_param(hits[0]["ptrs"]["#int:Value"], 0)
    F.EvflFile(ev.data())                                   # sanity: must still parse
    emit(GHOST_SHOP_FLOW, data, ev.data(), dname)
    progress("Big Poe buyer: one Big Poe is enough")
    return True
