"""Glitchless logic for the remake, modelled on the classic randomizer's region rules.

It is deliberately conservative: every location inside a dungeon requires all the items
needed to *finish* that dungeon, and overworld grottos/hidden spots assume explosives etc.
That keeps seeds beatable even where the remake's exact layout is unknown, at the cost of
making some items appear a little later than strictly necessary.

Items are canonical keys (see world.canon), e.g. "Hookshot", "Melody_SariaSong".
"""
from collections import Counter

# Item keys the logic looks at. Anything else is never required -> treated as junk by the fill.
PROGRESSION = {
    "Sword_Kokiri", "Range_SlingShot", "Boomerang", "BombBag_Small", "BombBag_Medium", "BombBag_Large",
    "Hookshot", "Longshot", "Range_Bow", "Hammer", "HeavyBoot", "HoverBoot",
    "Gauntlet_Goron", "Gauntlet_Silver", "Gauntlet_Gold", "Scale_Silver", "Scale_Gold",
    "Arrow_Fire", "Arrow_Light", "DinFire", "GlassTruth", "Shield_Mirror",
    "Bottle", "Bottle_Milk", "Bottle_Letter", "WeirdEgg", "ZeldaLetter", "Token_Gerudo",
    "Wallet_Medium", "Wallet_Large", "Token_Gold",
    "Stone_Forest", "Stone_Fire", "Stone_Water", "Medal_Shadow", "Medal_Spirit",
    "Melody_ZeldaLullaby", "Melody_EponaSong", "Melody_SariaSong", "Melody_SunSong",
    "Melody_TimeSong", "Melody_StormSong", "Melody_ForestMinuet", "Melody_FireBolero",
    "Melody_WaterSerenade", "Melody_ShadowNocturne", "Melody_SpiritRequiem", "Melody_LightPrelude",
    "Ocarina_Fairy", "Ocarina_Time",
}

# Two-tier items: the higher tier may only be placed where the lower tier is required,
# so the player can never pick the stronger version up first.
TIERS = [("Hookshot", "Longshot"), ("Gauntlet_Silver", "Gauntlet_Gold"), ("Scale_Silver", "Scale_Gold"),
         ("BombBag_Small", "BombBag_Medium"), ("BombBag_Medium", "BombBag_Large"),
         ("Wallet_Medium", "Wallet_Large")]
LOWER_TIER = {hi: lo for lo, hi in TIERS}


class State:
    """Items the player has; region/age helpers are cached per state."""

    def __init__(self, items=None):
        self.items = Counter(items or ())
        self._c = {}

    def copy(self):
        return State(self.items)

    def add(self, item, n=1):
        self.items[item] += n
        self._c.clear()

    def has(self, item, n=1):
        return self.items[item] >= n

    def __getattr__(self, name):          # cached derived predicates, e.g. s.adult
        if name.startswith("_") or name not in RULES:
            raise AttributeError(name)
        c = self._c
        if name not in c:
            c[name] = False                # guards against accidental recursion
            c[name] = bool(RULES[name](self))
        return c[name]


# Regions a child can reach before leaving a closed Kokiri Forest (the Deku Tree itself excluded).
FOREST_REGIONS = {"KokiriForest", "LostWood", "SacredForestMeadow"}


def _all(*xs):
    return all(xs)


# --------------------------------------------------------------------------- primitives
# Generation options the rules depend on (set by the generator before filling).
OPTIONS = {"free_bombs": True, "open_forest": "closed", "open_zora": "closed", "open_door": "closed",
           "saria_song_ocarina": True, "dodongo_bag_bombs": False,
           "shuffle_ocarinas": False}


def set_options(st):
    OPTIONS.update(free_bombs=bool(st["free_bombs"]), open_forest=st["open_forest"], open_zora=st["open_zora"],
                   open_door=st["open_door"], saria_song_ocarina=bool(st["saria_song_ocarina"]),
                   dodongo_bag_bombs=bool(st["dodongo_bag_bombs"]),
                   shuffle_ocarinas=bool(st["shuffle_ocarinas"]))


def bombs(s):
    bag = s.has("BombBag_Small") or s.has("BombBag_Medium") or s.has("BombBag_Large")
    # Bag bombs are lifted objects in the remake: without the bomb patch they need the Goron Bracelet.
    return bag and (OPTIONS["free_bombs"] or s.has("Gauntlet_Goron") or str2(s))
def hookshot(s): return s.has("Hookshot") or s.has("Longshot")
def longshot(s): return s.has("Longshot")
def bow(s): return s.has("Range_Bow")
def lens(s): return s.has("GlassTruth")
def dins(s): return s.has("DinFire")
def scale(s): return s.has("Scale_Silver") or s.has("Scale_Gold")
def str2(s): return s.has("Gauntlet_Silver") or s.has("Gauntlet_Gold")
def str3(s): return s.has("Gauntlet_Gold")
def bottle(s):
    # Ruto's Letter becomes an empty bottle only when it is delivered (impossible if King Zora starts moved)
    letter = s.has("Bottle_Letter") and s.zd_child and OPTIONS["open_zora"] != "open"
    return s.has("Bottle") or s.has("Bottle_Milk") or letter
def ocarina(s):
    # vanilla: Saria hands over the Fairy Ocarina when you leave the forest after the Deku Tree
    if s.has("Ocarina_Fairy") or s.has("Ocarina_Time"):
        return True
    return not OPTIONS["shuffle_ocarinas"] and s.deku_done
def song(s, k): return s.has("Melody_" + k) and ocarina(s)
def stones(s): return s.has("Stone_Forest") and s.has("Stone_Fire") and s.has("Stone_Water")
def tokens(s, n): return s.has("Token_Gold", n)


RULES = {}


def rule(fn):
    RULES[fn.__name__] = fn
    return fn


# --------------------------------------------------------------------------- age / regions
@rule
def deku_done(s): return s.has("Sword_Kokiri") and s.has("Range_SlingShot")   # shield is bought in the forest shop
@rule
def child_out(s): return OPTIONS["open_forest"] != "closed" or s.deku_done   # exit blocker until Gohma
@rule
def adult(s):
    if OPTIONS["open_door"] == "open":
        return s.hf_child                                               # Door of Time starts open
    return stones(s) and s.child_out and s.has("Melody_TimeSong")       # Ocarina of Time is vanilla
@rule
def epona(s): return s.adult and song(s, "EponaSong")
@rule
def hf_child(s): return s.child_out
@rule
def zelda_met(s): return s.hf_child and s.has("WeirdEgg")
@rule
def dmt_child(s): return s.hf_child and s.has("ZeldaLetter")
@rule
def dmc_child(s): return s.dmt_child and bombs(s)
@rule
def dmc_adult(s): return s.adult and (bombs(s) or s.has("Hammer"))
@rule
def zr_child(s): return s.hf_child and bombs(s)
@rule
def zd_child(s): return s.zr_child and song(s, "ZeldaLullaby")
@rule
def zd_adult(s): return s.adult and song(s, "ZeldaLullaby")
@rule
def zf_child(s): return s.zd_child and (OPTIONS["open_zora"] == "open" or s.has("Bottle_Letter"))
@rule
def zf_adult(s): return s.zd_adult and (OPTIONS["open_zora"] == "open" or s.zf_child)   # King Zora moved
@rule
def gv_adult(s): return s.adult and (longshot(s) or s.epona)
@rule
def gf_adult(s): return s.gv_adult
@rule
def card(s): return s.has("Token_Gerudo")
@rule
def wasteland(s): return s.gf_adult and s.card and lens(s) and (s.has("HoverBoot") or longshot(s))
@rule
def colossus_child(s): return song(s, "SpiritRequiem")
@rule
def colossus_adult(s): return s.adult and (s.wasteland or song(s, "SpiritRequiem"))
@rule
def goron_tunic(s): return s.adult and (bombs(s) or bow(s) or s.has("Wallet_Medium"))
@rule
def zora_tunic(s): return s.zd_adult and ((s.zf_adult and bottle(s)) or s.has("Wallet_Large"))


# --------------------------------------------------------------------------- dungeons ("done" = whole dungeon)
@rule
def dodongo_done(s):
    # The entrance boulder only reacts to the special bomb flower next to it (Goron Bracelet), unless
    # the bag-bomb patch is on; inside, bombs or bomb flowers both work.
    entry = s.has("Gauntlet_Goron") or (OPTIONS["dodongo_bag_bombs"] and bombs(s))
    return s.dmt_child and entry
@rule
def jabu_done(s): return s.zf_child and bottle(s) and s.has("Boomerang")
@rule
def botw_done(s): return s.hf_child and song(s, "StormSong") and lens(s) and bombs(s)
@rule
def forest_done(s): return s.adult and hookshot(s) and bow(s)
@rule
def fire_done(s): return _all(s.dmc_adult, s.goron_tunic, s.has("Hammer"), bombs(s), hookshot(s), bow(s),
                              song(s, "TimeSong"))
@rule
def water_done(s): return _all(s.adult, s.has("HeavyBoot"), s.zora_tunic, song(s, "ZeldaLullaby"), longshot(s),
                               bow(s), song(s, "TimeSong"))
@rule
def shadow_done(s): return _all(s.adult, song(s, "ShadowNocturne"), dins(s), lens(s), s.has("HoverBoot"),
                                hookshot(s), bombs(s), song(s, "ZeldaLullaby"))
@rule
def spirit_done(s): return _all(s.colossus_adult, song(s, "SpiritRequiem"), str2(s), hookshot(s), bombs(s),
                                lens(s), s.has("Shield_Mirror"), bow(s), s.has("Boomerang"))
@rule
def ice_done(s): return s.zf_adult and bottle(s)
@rule
def gtg_done(s): return _all(s.gf_adult, s.card, bow(s), hookshot(s), lens(s), s.has("HeavyBoot"), s.has("Hammer"),
                             str2(s), song(s, "TimeSong"), bombs(s))
@rule
def bridge(s): return s.adult and s.has("Medal_Shadow") and s.has("Medal_Spirit")
@rule
def ganon_done(s): return _all(s.bridge, hookshot(s), lens(s), s.has("Hammer"), str3(s), s.has("HoverBoot"),
                               bombs(s), s.has("Arrow_Fire"), s.has("Arrow_Light"), bow(s), bottle(s),
                               s.has("Shield_Mirror"), song(s, "ZeldaLullaby"), song(s, "TimeSong"))
@rule
def win(s): return s.ganon_done


DUNGEON_RULE = {
    "InsideTheDekuTree": "deku_done", "DodongoCavern": "dodongo_done", "InsideJabuJabuBelly": "jabu_done",
    "BottomOfTheWell": "botw_done", "ForestTemple": "forest_done", "FireTemple": "fire_done",
    "WaterTemple": "water_done", "ShadowTemple": "shadow_done", "SpiritTemple": "spirit_done",
    "IceCavern": "ice_done", "GerudoTrainingGround": "gtg_done", "InsideGanonCastle": "ganon_done",
    "GanonCastle": "ganon_done",
}

# Overworld regions: (child access, adult access, extra requirement for grottos/hidden spots)
REGIONS = {
    "KokiriForest": (lambda s: True, lambda s: s.adult, lambda s, age: bombs(s) and song(s, "StormSong")),
    "LostWood": (lambda s: True, lambda s: s.adult, lambda s, age: bombs(s)),
    "SacredForestMeadow": (lambda s: s.has("Sword_Kokiri"), lambda s: s.adult, lambda s, age: bombs(s)),
    "HyruleField": (lambda s: s.hf_child, lambda s: s.adult,
                    lambda s, age: bombs(s) and scale(s) and (age == "child" or hookshot(s))),
    "Market": (lambda s: s.hf_child, lambda s: s.adult, lambda s, age: True),
    "HyruleCastle": (lambda s: s.hf_child, lambda s: s.adult, lambda s, age: bombs(s)),
    "KakarikoVillage": (lambda s: s.hf_child, lambda s: s.adult,
                        lambda s, age: bombs(s) and (age == "child" or hookshot(s))),
    "Graveyard": (lambda s: s.hf_child, lambda s: s.adult,
                  lambda s, age: bombs(s) and song(s, "SunSong") and song(s, "ZeldaLullaby")),
    "DeathMountainTrail": (lambda s: s.dmt_child, lambda s: s.adult, lambda s, age: bombs(s)),
    "DeathMountainCrater": (lambda s: s.dmc_child, lambda s: s.dmc_adult,
                            lambda s, age: bombs(s) and (age == "child" or (s.goron_tunic and hookshot(s)))),
    "GoronCity": (lambda s: s.dmt_child, lambda s: s.adult, lambda s, age: bombs(s) and (age == "child" or str2(s))),
    "ZoraRiver": (lambda s: s.zr_child, lambda s: s.adult,
                  lambda s, age: bombs(s) and (age == "child" or s.has("HoverBoot"))),
    "ZoraDomain": (lambda s: s.zd_child, lambda s: s.zd_adult, lambda s, age: True),
    "ZoraFountain": (lambda s: s.zf_child, lambda s: s.zf_adult,
                     lambda s, age: scale(s) if age == "child" else s.has("HeavyBoot")),
    "GerudoValley": (lambda s: s.hf_child, lambda s: s.gv_adult,
                     lambda s, age: bombs(s) and (scale(s) if age == "child" else (s.has("Hammer") and hookshot(s)))),
    "GerudoFortress": (lambda s: s.hf_child, lambda s: s.gf_adult, lambda s, age: hookshot(s) and s.card),
    "HountedWasteland": (lambda s: False, lambda s: s.wasteland, lambda s, age: True),
    "DesertColossus": (lambda s: s.colossus_child, lambda s: s.colossus_adult,
                       lambda s, age: bombs(s) and (age == "child" or longshot(s))),
}

# Locations with their own rule (events and special freestanding items)
SPECIAL = {
    "song_impa": lambda s: s.zelda_met,
    "song_malon": lambda s: s.hf_child and ocarina(s),
    # Sacred Forest Meadow (child, needs the sword) with an ocarina; meeting Zelda only without the setting
    "song_saria": lambda s: s.has("Sword_Kokiri") and ocarina(s) and (OPTIONS["saria_song_ocarina"] or s.zelda_met),
    "song_tomb": lambda s: s.hf_child and song(s, "ZeldaLullaby"),
    "song_windmill": lambda s: s.adult and ocarina(s),
    "song_oot": lambda s: s.hf_child and stones(s),
    # same scene; she teaches the Song of Time right after, so expect an ocarina in hand when shuffled
    "oot_gift": lambda s: s.hf_child and stones(s) and (not OPTIONS["shuffle_ocarinas"] or ocarina(s)),
    "song_minuet": lambda s: s.adult,
    "song_bolero": lambda s: s.dmc_adult,
    "song_serenade": lambda s: s.ice_done,
    "song_nocturne": lambda s: s.adult and s.forest_done and s.fire_done and s.water_done,
    "song_requiem": lambda s: s.adult and s.wasteland,
    "song_prelude": lambda s: s.adult and s.forest_done,
    "adult": lambda s: s.adult,
    "fairy_dmt": lambda s: (s.dmt_child or s.adult) and bombs(s) and song(s, "ZeldaLullaby"),
    "fairy_dmc": lambda s: s.dmc_adult and s.has("Hammer") and song(s, "ZeldaLullaby"),
    "fairy_ogc": lambda s: s.adult and str3(s) and song(s, "ZeldaLullaby"),
    "fairy_hc": lambda s: s.hf_child and bombs(s) and song(s, "ZeldaLullaby"),
    "fairy_zf": lambda s: s.zf_child and bombs(s) and song(s, "ZeldaLullaby"),
    "fairy_colossus": lambda s: s.colossus_child and bombs(s) and song(s, "ZeldaLullaby"),
    "hc_child": lambda s: s.hf_child,
    "zelda": lambda s: s.zelda_met,
    "darunia": lambda s: s.dmt_child and song(s, "ZeldaLullaby") and song(s, "SariaSong"),
    "zd_child": lambda s: s.zd_child,
    "rolling_goron": lambda s: s.dmt_child and bombs(s),        # stop him with a bomb as child
    "lw_target": lambda s: s.has("Range_SlingShot"),            # Deku Scrub targets in the Lost Woods (child)
    "market_gallery": lambda s: s.hf_child and s.has("Range_SlingShot"),
    "kak_gallery": lambda s: s.adult and bow(s),
    "bowling": lambda s: s.hf_child and bombs(s),
    "gerudo_card": lambda s: s.gf_adult and hookshot(s),
    "light_arrows": lambda s: s.adult and s.has("Medal_Shadow") and s.has("Medal_Spirit"),
    "kak_child": lambda s: s.hf_child,
    "llr_child": lambda s: s.hf_child,
    "fishing_child": lambda s: s.hf_child,
    "fishing_adult": lambda s: s.adult,
    "lab_dive": lambda s: s.hf_child and s.has("Scale_Gold"),
    "frogs": lambda s: s.zr_child and all(song(s, k) for k in (
        "ZeldaLullaby", "EponaSong", "SariaSong", "SunSong", "TimeSong", "StormSong")),
    "graveyard_child": lambda s: s.hf_child,
    "graveyard_adult": lambda s: s.adult,
    "skull_kid": lambda s: song(s, "SariaSong"),
    "memory_game": lambda s: ocarina(s),
    "kak_adult_hook": lambda s: s.adult and hookshot(s),
    "market_child": lambda s: s.hf_child,
    "hba": lambda s: s.gf_adult and s.card and s.epona and bow(s),
    "tokens10": lambda s: s.hf_child and tokens(s, 10),
    "tokens20": lambda s: s.hf_child and tokens(s, 20),
    "tokens30": lambda s: s.hf_child and tokens(s, 30),
    "tokens40": lambda s: s.hf_child and tokens(s, 40),
    "tokens50": lambda s: s.hf_child and tokens(s, 50),
    "fire_arrows": lambda s: s.adult and bow(s) and s.water_done,
    "shop_kokiri": lambda s: True,
    "shop_goron": lambda s: s.dmt_child or s.adult,
    "shop_zora": lambda s: s.zd_child or s.zd_adult,
    "shop_bombchu": lambda s: s.hf_child,
    "rutos_letter": lambda s: s.hf_child and scale(s),
}


def is_deku_slingshot_chest(loc):
    """The Deku Tree's own Slingshot chest (room 2), opened before the Slingshot is ever needed."""
    return loc.dungeon == "InsideTheDekuTree" and loc.kind == "chest" and loc.vanilla == "Range_SlingShot"


def location_rule(loc):
    """Returns a function State -> bool for a world.Location."""
    if loc.rule_key:
        if loc.rule_key in SPECIAL:
            return SPECIAL[loc.rule_key]
        return RULES[loc.rule_key]
    if loc.kind == "rupee" and loc.region == "ZoraDomain":
        # the six blue rupees lie at the bottom of the Zora's Domain pool
        return lambda s: (s.zd_child and scale(s)) or (s.zd_adult and s.has("HeavyBoot"))
    if is_deku_slingshot_chest(loc):
        return lambda s: s.has("Sword_Kokiri")          # reached before the Slingshot is needed
    if loc.dungeon:
        base = RULES[DUNGEON_RULE[loc.dungeon]]
        if loc.kind == "gs":
            child_dungeon = loc.ages == {"child"}
            return lambda s: base(s) and (s.has("Boomerang") if child_dungeon else hookshot(s))
        return base
    child_ok, adult_ok, extra = REGIONS.get(loc.region, (lambda s: False, lambda s: False, lambda s, a: False))
    kf_free = loc.region == "KokiriForest" and loc.kind == "chest" and (
        loc.vanilla == "Sword_Kokiri" or loc.get_event == "KokiriForest_TreasureBox_NaviChatOff")
    bean_gs = "MagicBeanSoil" in (loc.presence or "")

    def check(s, age):
        if age == "child" and not child_ok(s):
            return False
        if age == "adult" and not adult_ok(s):
            return False
        if kf_free:
            return True
        if loc.kind == "gs":
            if age == "child" and not (s.has("Boomerang") and bombs(s) and (not bean_gs or bottle(s))):
                return False
            if age == "adult" and not (hookshot(s) and bombs(s)):
                return False
        return extra(s, age)

    ages = sorted(loc.ages)
    return lambda s: any(check(s, a) for a in ages)
