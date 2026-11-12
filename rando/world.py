"""Scans the user's extracted romfs and builds the list of items and item locations.

Nothing here is bundled game data: actor names, IDs, positions and English text are all
read from the romfs the user points the program at.
"""
import os
import re
from collections import defaultdict

from . import formats as F

DUNGEONS = {
    "InsideTheDekuTree": "child", "DodongoCavern": "child", "InsideJabuJabuBelly": "child",
    "BottomOfTheWell": "child", "ForestTemple": "adult", "FireTemple": "adult",
    "WaterTemple": "adult", "ShadowTemple": "adult", "SpiritTemple": "both",
    "IceCavern": "adult", "GerudoTrainingGround": "adult", "InsideGanonCastle": "adult",
    "GanonCastle": "adult",
}
SKIP_FOLDERS = {"BancBasedResource", "DreamWorld", "SageRoom"}

ITEM_PREFIXES = ("Item_", "Obj_", "TBox_", "Tbox_", "Weapon_", "Shop_", "Pouch_")
JUNK = {"Rupee_Green", "Rupee_Blue", "Rupee_Red", "Rupee_Purple", "Rupee_Gold", "Heart",
        "MagicJar_Small", "MagicJar_Large", "ArrowBundle_Small", "ArrowBundle_Medium",
        "ArrowBundle_Large", "DekuNutBundle", "DekuSeedBundle", "BombBundle_Small",
        "BombchuBundle_Small", "BombchuBundle_Medium", "BombchuBundle_Large",
        "DekuStickBundle_Small", "ScrubBusinessSeed", "Shield_Deku", "Shield_Hylian"}


def canon(actor):
    """'TBox_Rupee_Red' / 'Obj_Rupee_Red' -> 'Rupee_Red'; 'Item_Hookshot' -> 'Hookshot'."""
    for p in ITEM_PREFIXES:
        if actor.startswith(p):
            actor = actor[len(p):]
            break
    return {"GerudoValley_Heart_Piece": "Heart_Piece"}.get(actor, actor)


class Location:
    def __init__(self, **kw):
        self.id = kw["id"]                 # stable ID (survives regeneration)
        self.name = kw["name"]             # readable name for the spoiler log
        self.region = kw["region"]         # Banc folder name (logic region)
        self.dungeon = kw.get("dungeon")   # dungeon folder or None
        self.kind = kw["kind"]             # chest | freestanding | heart_container | gs | event
        self.category = kw.get("category", self.kind)  # song | reward | npc | fairy | house ...
        self.ages = kw["ages"]             # set of "child"/"adult"
        self.vanilla = kw["vanilla"]       # canonical item key (dungeon items get @Dungeon)
        self.vanilla_actor = kw["vanilla_actor"]
        self.stage_refs = kw.get("stage_refs", [])   # [(banc relpath, hash)]
        self.event_refs = kw.get("event_refs", [])   # [(evfl relpath, field offset)]
        self.presence = kw.get("presence", "")
        self.get_event = kw.get("get_event", "")
        self.conditional = kw.get("conditional", False)
        self.pos = kw.get("pos")
        self.room = kw.get("room")
        self.rule_key = kw.get("rule_key")   # explicit logic rule for events / specials
        self.upgrade_ok = kw.get("upgrade_ok", False)   # an upgrade-giving location that may still be shuffled

    def __repr__(self):
        return "<Location %s>" % self.name


# Curated reward events. Each entry patches every "give item" node in the flow whose item
# parameter equals `vanilla` (optionally filtered by the `via` sub-flow name).
EVENT_LOCATIONS = [
    # songs
    dict(name="Song from Impa", flow="Dm_MelodyGet_Zelda", vanilla="Item_Melody_ZeldaLullaby", category="song", rule="song_impa"),
    dict(name="Song from Malon", flow="Dm_MelodyGet_Epona", vanilla="Item_Melody_EponaSong", category="song", rule="song_malon"),
    dict(name="Song from Saria", flow="Dm_MelodyGet_Saria", vanilla="Item_Melody_SariaSong", category="song", rule="song_saria"),
    dict(name="Song from Royal Familys Tomb", flow="Dm_MelodyGet_Sun_03", vanilla="Item_Melody_SunSong", category="song", rule="song_tomb"),
    dict(name="Song from Windmill", flow="Dm_MelodyGet_Storm", vanilla="Item_Melody_StormSong", category="song", rule="song_windmill"),
    dict(name="Song from Ocarina of Time", flow="Dm_MelodyGet_Time", vanilla="Item_Melody_TimeSong", category="song", rule="song_oot"),
    # Zelda throws the Ocarina of Time at the moat in the same flow (shuffled with "Shuffle Ocarinas")
    dict(name="HF Ocarina of Time", flow="Dm_MelodyGet_Time", vanilla="Item_Ocarina_Time", category="ocarina", rule="oot_gift"),
    dict(name="Sheik in Forest", flow="Dm_MelodyGet_Forest", vanilla="Item_Melody_ForestMinuet", category="song", rule="song_minuet"),
    dict(name="Sheik in Crater", flow="Dm_MelodyGet_Fire", vanilla="Item_Melody_FireBolero", category="song", rule="song_bolero"),
    dict(name="Sheik in Ice Cavern", flow="Dm_MelodyGet_Water", vanilla="Item_Melody_WaterSerenade", category="song", rule="song_serenade"),
    dict(name="Sheik in Kakariko", flow="Dm_MelodyGet_Shadow", vanilla="Item_Melody_ShadowNocturne", category="song", rule="song_nocturne"),
    dict(name="Sheik at Colossus", flow="Dm_MelodyGet_Spilit", vanilla="Item_Melody_SpiritRequiem", category="song", rule="song_requiem"),
    dict(name="Sheik at Temple", flow="Dm_MelodyGet_Shine", vanilla="Item_Melody_LightPrelude", category="song", rule="song_prelude"),
    # dungeon rewards
    dict(name="Queen Gohma (Kokiri Emerald)", flow="Dm_Kokiri_0130", vanilla="Item_Stone_Forest", category="reward", rule="deku_done"),
    dict(name="King Dodongo (Goron Ruby)", flow="Dm_DeathMtTrail_0025", vanilla="Item_Stone_Fire", category="reward", rule="dodongo_done"),
    dict(name="Barinade (Zora Sapphire)", flow=["Dm_ZoraFountain_0030", "Dm_InsideJabu_Jabu_0030"], vanilla="Item_Stone_Water", category="reward", rule="jabu_done"),
    dict(name="Phantom Ganon (Forest Medallion)", flow="Dm_Awake_Forest_Get", vanilla="Item_Medal_Forest", category="reward", rule="forest_done"),
    dict(name="Volvagia (Fire Medallion)", flow="Dm_Awake_Fire_Get", vanilla="Item_Medal_Fire", category="reward", rule="fire_done"),
    dict(name="Morpha (Water Medallion)", flow="Dm_Awake_Water_Get", vanilla="Item_Medal_Water", category="reward", rule="water_done"),
    dict(name="Bongo Bongo (Shadow Medallion)", flow="Dm_Awake_Shadow_Get", vanilla="Item_Medal_Shadow", category="reward", rule="shadow_done"),
    dict(name="Twinrova (Spirit Medallion)", flow="Dm_Awake_Spirit_Get", vanilla="Item_Medal_Spirit", category="reward", rule="spirit_done"),
    dict(name="Rauru (Light Medallion)", flow="Dm_SageRoom_0005", vanilla="Item_Medal_Light", category="reward", rule="adult"),
    # great fairies
    dict(name="DMT Great Fairy Reward", flow="Dm_FairyFountain_Power", vanilla="Item_FairyBless_MP", category="fairy", rule="fairy_dmt"),
    dict(name="DMC Great Fairy Reward", flow="Dm_FairyFountain_Wisdom", vanilla="Item_FairyBless_MPDouble", category="fairy", rule="fairy_dmc"),
    dict(name="OGC Great Fairy Reward", flow="Dm_FairyFountain_Courage", vanilla="Item_FairyBless_DefenseDouble", category="fairy", rule="fairy_ogc"),
    dict(name="HC Great Fairy Reward", flow="Dm_FairyFountain_Din", vanilla="Item_DinFire", category="fairy", rule="fairy_hc"),
    dict(name="ZF Great Fairy Reward", flow="Dm_FairyFountain_Frore", vanilla="Item_FaroreWind", category="fairy", rule="fairy_zf"),
    dict(name="Colossus Great Fairy Reward", flow="Dm_FairyFountain_Nayru", vanilla="Item_NayruLove", category="fairy", rule="fairy_colossus"),
    # NPCs and minigames
    dict(name="HC Malon Egg", flow="Goto_HyruleCastle", vanilla="Item_WeirdEgg", category="npc", rule="hc_child"),
    dict(name="HC Zeldas Letter", flow="Dm_HrlCastle_0050", vanilla="Item_ZeldaLetter", category="npc", rule="zelda"),
    dict(name="GC Darunias Joy", flow="Dm_Goron_0030", vanilla="Item_Gauntlet_Goron", category="npc", rule="darunia"),
    # Hot Rodder Goron: gives the Bigger Bomb Bag, or the Biggest if you already own the Bigger one
    # (bowling). Both give nodes get the random item; the reward is one-time (GoronCity_GetBombBag_fromGoron006).
    dict(name="GC Rolling Goron", flow="Npc_Goron_006_Child", vanilla="Item_BombBag_Medium", also=["Item_BombBag_Large"],
         category="npc", rule="rolling_goron", upgrade_ok=True),
    # Capacity-upgrade minigames. Each gives "Bigger", or "Biggest" if you already own the Bigger one, and
    # is guarded by its own one-time flag, so both give nodes can carry the random item:
    #   LW targets: LostWood_HitTargetOfDekuScrub_FirstClear; galleries: MiniGame_HitTarget_HrlCity_Get_BulletBag /
    #   _Kakariko_Get_Quiver; bowling: MiniGame_BombchuBowling_ClearSecondTime / _ClearThirdTime;
    #   horseback archery: MiniGame_HorseBackArchery_Get_Quiver. Later wins give their usual rupees.
    dict(name="LW Target in Woods", flow="Dm_LostWood_0040", vanilla="Item_BulletBag_Medium", also=["Item_BulletBag_Large"],
         category="npc", rule="lw_target", upgrade_ok=True),
    dict(name="Market Shooting Gallery Reward", flow="MiniGame_HitTarget", vanilla="Item_BulletBag_Medium",
         also=["Item_BulletBag_Large"], category="npc", rule="market_gallery", upgrade_ok=True),
    dict(name="Kak Shooting Gallery Reward", flow="MiniGame_HitTarget", vanilla="Item_Quiver_Medium",
         also=["Item_Quiver_Large"], category="npc", rule="kak_gallery", upgrade_ok=True),
    dict(name="Market Bombchu Bowling Bomb Bag", flow="MiniGame_BombchuBowling", vanilla="Item_BombBag_Medium",
         also=["Item_BombBag_Large"], category="npc", rule="bowling", upgrade_ok=True),
    dict(name="Market Bombchu Bowling Piece of Heart", flow="MiniGame_BombchuBowling", vanilla="Obj_Heart_Piece",
         category="npc", rule="bowling"),
    dict(name="GF HBA Quiver", flow="Minigame_HorsebackArchery", vanilla="Item_Quiver_Medium", also=["Item_Quiver_Large"],
         category="npc", rule="hba", upgrade_ok=True),
    dict(name="ZD Diving Minigame", flow="MiniGame_Diving", vanilla="Item_Scale_Silver", category="npc", rule="zd_child"),
    dict(name="Hideout Gerudo Membership Card", flow="Dm_Gerudo_0025", vanilla="Item_Token_Gerudo", category="npc", rule="gerudo_card"),
    dict(name="ToT Light Arrows Cutscene", flow="Dm_TimeTemple_0130", vanilla="Item_Arrow_Light", category="npc", rule="light_arrows"),
    dict(name="Kak Anju as Child", flow="Minigame_CatchCucco", vanilla="Item_Bottle", category="npc", rule="kak_child"),
    # Talon's first win only ("marry Malon?" branch, NpcCommon_HandOver_NpcToPlayer_NoDisplay). The flow's other two
    # milk nodes are buying milk (30 rupees, GetInEventInBottle) and refilling a bottle on later wins (..._EmptyBottle):
    # randomized, they handed out the random item again and again.
    dict(name="LLR Talons Chickens", flow="Minigame_FindOutCucco", vanilla="Item_Bottle_Milk",
         via="HandOver_NpcToPlayer_NoDisplay", category="npc", rule="llr_child"),
    # end of the adult trade sequence (the trade items themselves stay vanilla): Biggoron's claim-check reward
    dict(name="DMT Biggoron", flow="Npc_Goron_Biggoron_Adult", vanilla="Item_Sword_Biggoron", category="npc", rule="biggoron"),
    # the ghost shop in the adult Market: selling Big Poes up to 1000 points gives a bottle (later sales: rupees)
    dict(name="Market Big Poe Bottle", flow="Npc_Hylia_048_BottleShop", vanilla="Item_Bottle", category="npc", rule="big_poes"),
    dict(name="LH Child Fishing", flow="MiniGame_Fishing", vanilla="Obj_Heart_Piece", category="npc", rule="fishing_child"),
    dict(name="LH Adult Fishing", flow="MiniGame_Fishing", vanilla="Item_Scale_Gold", category="npc", rule="fishing_adult"),
    dict(name="LH Lab Dive", flow="Npc_Hylia_045_Child", vanilla="Obj_Heart_Piece", category="npc", rule="lab_dive"),
    dict(name="ZR Frogs Song Game", flow="MiniGame_FrogTenors", vanilla="Obj_Heart_Piece", via="Dm_SY_GetInEvent", category="npc", rule="frogs"),
    dict(name="ZR Frogs Bug Game", flow="MiniGame_FrogTenors", vanilla="Obj_Heart_Piece", via="MushiToriGame", category="npc", rule="frogs"),
    dict(name="Graveyard Dampe Gravedigging Tour", flow="Npc_Hylia_Dampe_001", vanilla="Obj_Heart_Piece", via="DiggingHoleTour", category="npc", rule="graveyard_child"),
    dict(name="Graveyard Dampe Race Reward", flow="Npc_Hylia_Dampe_001", vanilla="Obj_Heart_Piece", via="NotNpc_Dampe", category="npc", rule="graveyard_adult"),
    dict(name="LW Skull Kid", flow="Npc_SkullKid_Child", vanilla="Obj_Heart_Piece", category="npc", rule="skull_kid"),
    dict(name="LW Ocarina Memory Game", flow="Npc_SkullKid_Child_02", vanilla="Obj_Heart_Piece", category="npc", rule="memory_game"),
    dict(name="Kak Adult Villager Reward", flow="Npc_Hylia_001_Adult", vanilla="Obj_Heart_Piece", category="npc", rule="kak_adult_hook"),
    dict(name="Market Lost Dog", flow="SubEvent_FindRichard", vanilla="Obj_Heart_Piece", category="npc", rule="market_child"),
    dict(name="GF Horseback Archery", flow="Minigame_HorsebackArchery", vanilla="Obj_Heart_Piece", category="npc", rule="hba"),
    # skulltula house
    # the wallets are shuffled as two progressive chest wallets (generator.PROGRESSIVE_WALLET)
    dict(name="Kak 10 Gold Skulltula Reward", flow="GatheringTokenGold", vanilla="Item_Wallet_Medium", category="house", rule="tokens10",
         upgrade_ok=True),
    dict(name="Kak 20 Gold Skulltula Reward", flow="GatheringTokenGold", vanilla="Item_AgonyStone", category="house", rule="tokens20"),
    dict(name="Kak 30 Gold Skulltula Reward", flow="GatheringTokenGold", vanilla="Item_Wallet_Large", category="house", rule="tokens30",
         upgrade_ok=True),
    dict(name="Kak 40 Gold Skulltula Reward", flow="GatheringTokenGold", vanilla="Item_BombchuBundle_Large", category="house", rule="tokens40"),
    dict(name="Kak 50 Gold Skulltula Reward", flow="GatheringTokenGold", vanilla="Obj_Heart_Piece", category="house", rule="tokens50"),
]

# sub-flows / actions that hand an item to the player
_GIFT_SUB = re.compile(r"^(Dm_SY_GetInEvent|GetPouchContent|GetInEvent_EggHatche|Dm_SY_Get)$|HandOver_NpcToPlayer"
                       r"|TakenReward|DiggingHoleTour_Demo$|GetInEvent|MushiToriGame")
_ITEM_KEYS = ("ActorName", "ReveiveItem", "ReceiveItem", "TakenRewardActor", "DropActorName", "Actor")

STAGE_KINDS = [
    (r"^Obj_TBox_GlassTruth", "chest", "Invisible Chest"),
    (r"^Obj_TBox_A_06", "chest", "Chest"),
    (r"^Obj_TBox_A_0[1235]", "chest", "Chest"),
    (r"^Obj_(Arrow_Fire|Bottle_Letter)$", "freestanding", "Freestanding"),
    (r"^Obj_Heart_Container$", "heart_container", "Heart Container"),
    (r"^Obj_(GerudoValley_)?Heart_Piece$", "freestanding", "Freestanding Heart Piece"),
    (r"^Obj_Dungeon_SmallKey$", "freestanding", "Freestanding Small Key"),
    # green/blue/red/purple rupees lying in the world; each has its own save flag (Bool64bitKey),
    # so an item placed there is collected once. Silver rupees are puzzle pieces and stay vanilla.
    (r"^Obj_Rupee_(Green|Blue|Red|Purple)$", "rupee", "Freestanding Rupee"),
    (r"^Enemy_Skulltula_Gold$", "gs", "Gold Skulltula"),
]

# The three Deku Tree scrub-drop rupees (ScrubDekuRupee_*) appear inside the beaten scrub's flower
# (Presence Enemy_Scrub_Deku_ItemDrop_0N). A rupee there can be collected, but an item in that spot sits behind
# the flower's collision and can't be picked up (0.4.2 report), so they stay vanilla.
SCRUB_DROP_FLAG = "Enemy_Scrub_Deku_ItemDrop"
SPECIAL_RULES = {"Obj_Arrow_Fire": "fire_arrows", "Obj_Bottle_Letter": "rutos_letter"}

# Shopsanity: shelf types that are only ever placed in one shop, so re-targeting the shelf's
# actor pack changes exactly one shop. Deku Shield and the tunics are left alone (logic buys them).
SHOPS = [
    ("Kokiri Shop", "KokiriForest", "shop_kokiri",
     ["Shop_DekuNutBundle_02", "Shop_DekuSeedBundle_01", "Shop_DekuStickBundle_Medium"]),
    ("Goron Shop", "GoronCity", "shop_goron", ["Shop_BombBundle_02", "Shop_BombBundle_03", "Shop_BombBundle_04"]),
    ("Zora Shop", "ZoraDomain", "shop_zora", ["Shop_ArrowBundle_02", "Shop_ArrowBundle_03"]),
    ("Bombchu Shop", "Market", "shop_bombchu", ["Shop_BombchuBundle_%02d" % i for i in range(1, 9)]),
]
# what the vanilla shelf contributes to the item pool (a generic ammo pickup)
SHOP_JUNK = {"DekuNut": "DekuNutBundle", "DekuSeed": "DekuSeedBundle", "DekuStick": "DekuStickBundle_Small",
             "BombBundle": "BombBundle_Small", "Arrow": "ArrowBundle_Medium", "Bombchu": "BombchuBundle_Small"}


class World:
    def __init__(self, romfs, progress=print):
        self.romfs = romfs
        self.progress = progress
        self.zs = F.ZsContext(romfs)
        self.actor_packs = {n[:-8] for n in os.listdir(os.path.join(romfs, "Pack", "Actor")) if n.endswith(".pack.zs")}
        d, _ = self.zs.read("RSDB/PouchActorInfo.Product.111.rstbl.byml.zs") if os.path.exists(
            os.path.join(romfs, "RSDB/PouchActorInfo.Product.111.rstbl.byml.zs")) else self.zs.read(self._find("RSDB", "PouchActorInfo"))
        self.pouch = {r["__RowId"]: r for r in F.byml_load(d)}
        self._load_text()
        self.locations = []
        self._scan_stages()
        self._scan_events()
        self._scan_shops()
        ids = [l.id for l in self.locations]
        assert len(ids) == len(set(ids)), "duplicate location ids"

    # ------------------------------------------------------------------ helpers
    def _find(self, folder, prefix):
        for n in sorted(os.listdir(os.path.join(self.romfs, folder))):
            if n.startswith(prefix):
                return folder + "/" + n
        raise FileNotFoundError(folder + "/" + prefix)

    def _load_text(self):
        self.item_text, self.region_text = {}, {}
        try:
            mals = self._find("Mals", "USen")
            raw, _ = self.zs.read(mals)
            files = F.sarc_files(raw)
            pc = F.msbt_parse(files["ActorMsg/PouchContent.msbt"])
            self.item_text = {k[:-5]: re.sub(r"\s+", " ", v) for k, v in pc.items() if k.endswith("_Name")}
            self.region_text = F.msbt_parse(files["LocationMsg/Location.msbt"])
        except Exception as e:  # text is cosmetic only
            self.progress("warning: could not read English text (%s)" % e)

    def region_name(self, folder):
        return self.region_text.get(folder, folder)

    def item_name(self, key):
        base = key.split("@")[0]
        for pre in ("Item_", "Obj_", "Weapon_", "TBox_", "Shop_", "Armor_", "Armor_Adult_", "Armor_Child_"):
            t = self.item_text.get(pre + base)
            if t:
                break
        else:
            t = base.replace("_", " ")
        if "@" in key:
            t += " (%s)" % self.region_name(key.split("@")[1])
        return t

    def actor_exists(self, name):
        return name in self.actor_packs

    def actor_for(self, key, context):
        """Actor name to write for canonical item `key` in a given placement context."""
        base = key.split("@")[0]
        order = {
            "chest": ("TBox_", "Item_", "Obj_", "Tbox_", "Weapon_"),
            "event": ("Item_", "Obj_", "Weapon_", "TBox_"),
            "world": ("Obj_", "Item_", "TBox_", "Weapon_"),
        }[context]
        for p in order:
            n = p + base
            if n in self.pouch and self.actor_exists(n):
                return n
        for p in order:
            n = p + base
            if self.actor_exists(n):
                return n
        raise KeyError("no actor for item %s in %s context" % (key, context))

    # ------------------------------------------------------------------ stages
    def _scan_stages(self):
        banc = os.path.join(self.romfs, "Banc")
        merged = {}
        self.shop_places = defaultdict(set)     # Shop_* actor type -> stage folders it is placed in
        folders = sorted(f for f in os.listdir(banc) if os.path.isdir(os.path.join(banc, f)) and f not in SKIP_FOLDERS)
        for i, folder in enumerate(folders):
            self.progress("Scanning stages: %s (%d/%d)" % (folder, i + 1, len(folders)))
            for fn in sorted(os.listdir(os.path.join(banc, folder))):
                if not fn.endswith(".bcett.byml.zs") or fn.startswith("Demo_"):
                    continue
                rel = "Banc/%s/%s" % (folder, fn)
                m = re.search(r"_(Adult|Child)", fn)
                if folder in DUNGEONS:
                    ages = {"child", "adult"} if DUNGEONS[folder] == "both" else {DUNGEONS[folder]}
                elif m:
                    ages = {m.group(1).lower()}
                else:
                    ages = {"child", "adult"}
                data, _ = self.zs.read(rel)
                root = F.byml_load(data)
                for a in root.get("Actors", []):
                    g = a["Gyaml"]
                    if g.startswith("Shop_"):
                        self.shop_places[g].add(folder)
                    dyn = a.get("Dynamic") or {}
                    for pat, kind, label in STAGE_KINDS:
                        if re.search(pat, g):
                            break
                    else:
                        continue
                    if kind == "rupee" and (a.get("Presence") or {}).get("FlagName", "").startswith(SCRUB_DROP_FLAG):
                        continue
                    if kind == "chest":
                        vanilla = dyn.get("Drop__DropActor") or "Obj_Rupee_Green"
                    elif kind == "gs":
                        vanilla = "Obj_Token_Gold"
                    else:
                        vanilla = g
                    key = (folder, int(a["Hash"]))
                    loc = merged.get(key)
                    if loc is None:
                        merged[key] = loc = dict(
                            region=folder, hash=int(a["Hash"]), kind=kind, label=label, actor=g,
                            vanilla_actor=vanilla, ages=set(), refs=[], presence=(a.get("Presence") or {}).get("FlagName", ""),
                            get_event=dyn.get("GetEventName", ""), conditional="Drop__CheckActor" in dyn,
                            pos=tuple(round(float(x), 2) for x in a["Translate"]), room=dyn.get("DefaultDungeonRoomIndex"))
                    loc["ages"] |= ages
                    loc["refs"].append((rel, int(a["Hash"])))
        # stacked minigame prize chests (e.g. the Dampe race goal): keep only the non-junk members
        stacks = defaultdict(list)
        for loc in merged.values():
            if loc["kind"] == "chest":
                stacks[(loc["region"], tuple(round(c) for c in loc["pos"]))].append(loc)
        skip = set()
        for group in stacks.values():
            if len(group) > 1:
                for loc in group:
                    if canon(loc["vanilla_actor"]) in JUNK:
                        skip.add((loc["region"], loc["hash"]))
        counters = defaultdict(int)
        for key in sorted(merged, key=lambda k: (merged[k]["region"], merged[k]["kind"], merged[k]["room"] or 0, merged[k]["pos"])):
            loc = merged[key]
            if key in skip:
                continue
            region = loc["region"]
            dungeon = region if region in DUNGEONS else None
            van = canon(loc["vanilla_actor"])
            if van.startswith("Dungeon_") and dungeon:
                van += "@" + dungeon
            counters[(region, loc["label"])] += 1
            n = counters[(region, loc["label"])]
            room = " (room %s)" % loc["room"] if loc["room"] is not None else ""
            name = "%s %s %d%s" % (self.region_name(region), loc["label"], n, room)
            self.locations.append(Location(
                id="stage:%s:%d" % (region, loc["hash"]), name=name, region=region, dungeon=dungeon,
                kind=loc["kind"], category=loc["kind"], ages=loc["ages"], vanilla=van,
                vanilla_actor=loc["vanilla_actor"], stage_refs=loc["refs"], presence=loc["presence"],
                get_event=loc["get_event"], conditional=loc["conditional"], pos=loc["pos"], room=loc["room"],
                rule_key=SPECIAL_RULES.get(loc["actor"])))

    # ------------------------------------------------------------------ events
    def _scan_events(self):
        cache = {}
        for i, spec in enumerate(EVENT_LOCATIONS):
            self.progress("Scanning events: %s" % spec["name"])
            flows = spec["flow"] if isinstance(spec["flow"], list) else [spec["flow"]]
            refs = []
            for flow in flows:
                for suffix in ("", ".110"):
                    rel = "Event/EventFlow/%s%s.bfevfl.zs" % (flow, suffix)
                    if not os.path.exists(os.path.join(self.romfs, rel)):
                        continue
                    if rel not in cache:
                        data, _ = self.zs.read(rel)
                        cache[rel] = F.EvflFile(data)
                    for vanilla in [spec["vanilla"]] + spec.get("also", []):
                        refs += [(rel, off) for off in self._gift_nodes(cache[rel], vanilla, spec.get("via"))]
            if not refs:
                self.progress("warning: event location '%s' not found; skipped" % spec["name"])
                continue
            self.locations.append(Location(
                id="event:" + spec["name"], name=spec["name"], region=None, dungeon=None, kind="event",
                category=spec["category"], ages=set(), vanilla=canon(spec["vanilla"]),
                vanilla_actor=spec["vanilla"], event_refs=refs, rule_key=spec["rule"],
                upgrade_ok=spec.get("upgrade_ok", False)))

    # ------------------------------------------------------------------ shops
    def _scan_shops(self):
        for shop, folder, rule, types in SHOPS:
            n = 0
            for t in types:
                # only shelves that exist, are placed in this one shop, and have their own pack
                if self.shop_places.get(t) != {folder} or not self.actor_exists(t):
                    continue
                n += 1
                junk = next((v for k, v in SHOP_JUNK.items() if k in t), "Rupee_Blue")
                self.locations.append(Location(
                    id="shop:" + t, name="%s Item %d" % (shop, n), region=folder, dungeon=None, kind="shop",
                    category="shop", ages=set(), vanilla=junk, vanilla_actor=t, rule_key=rule))
                self.locations[-1].shop = shop

    @staticmethod
    def _gift_nodes(ev, item, via=None):
        offs = []
        for fc in ev.flowcharts:
            for e in fc["events"]:
                p = e.get("params")
                if not isinstance(p, dict):
                    continue
                for k in _ITEM_KEYS:
                    if p.get(k) != item or k not in e["ptrs"]:
                        continue
                    ok = False
                    if e["type"] == 4:
                        sub = "%s:%s" % (e.get("flowchart") or "", e.get("entry") or "")
                        ok = bool(_GIFT_SUB.search(e.get("flowchart") or "") or _GIFT_SUB.search(e.get("entry") or ""))
                        if via and via not in sub:
                            ok = False
                    elif e["type"] == 0 and not via:
                        if e.get("action") == "EventTriggerAddOrRemovePouchContent":
                            ok = isinstance(p.get("Num"), int) and p["Num"] > 0
                        elif e.get("action") == "EventTriggerSetForGetWindow":
                            ok = True
                    if ok:
                        offs.append(e["ptrs"][k])
        return offs
