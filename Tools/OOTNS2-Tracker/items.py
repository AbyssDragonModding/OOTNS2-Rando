"""Every tracker cell: its tiers, or its counter.

Icons are given by the name of the PNG the extractor writes (no extension);
"extras/..." ones come from the Common layout archive. The files themselves
are never shipped: they are extracted from the user's own romfs.

A cell's state is a number:
  - tiers cell:   0 = not acquired (first tier's icon, grayscale), 1..N = tier N
  - counter cell: 0 = none (grayscale), 1..max = how many
Left click goes up, right click goes down; neither goes past the ends.
"""
from dataclasses import dataclass, field


@dataclass
class Cell:
    id: str
    tiers: list = field(default_factory=list)  # [(name, icon) or (name, icon, capacity), ...]
    counter: int = 0                            # max count; 0 = a tiers cell
    name: str = ""                              # counter cells: what is counted
    icon: str = ""                              # counter cells: their icon

    @property
    def max_state(self):
        return self.counter or len(self.tiers)

    def icon_for(self, state):
        if self.counter:
            return self.icon
        return self.tiers[max(state, 1) - 1][1]

    def capacity_for(self, state):
        """The capacity a quantity-upgrade tier gives (shown in the cell's corner), or None."""
        if self.counter or state == 0 or len(self.tiers[state - 1]) < 3:
            return None
        return self.tiers[state - 1][2]

    def describe(self, state):
        if self.counter:
            return f"{self.name}: {state}/{self.counter}"
        if state == 0:
            return f"{self.tiers[0][0]} (not acquired)"
        if len(self.tiers) > 1:
            return f"{self.tiers[state - 1][0]} ({state}/{len(self.tiers)})"
        return self.tiers[0][0]


def T(id, *tiers):
    return Cell(id, list(tiers))


def C(id, name, icon, maximum):
    return Cell(id, counter=maximum, name=name, icon=icon)


CELLS = [
    # ---- Items (C buttons) ----
    T("sticks", ("Deku Sticks", "Item_DekuStick")),
    T("nuts", ("Deku Nuts", "Item_DekuNut")),
    T("bombs", ("Bombs", "Item_Bomb")),
    T("bow", ("Fairy Bow", "Weapon_Range_Bow")),
    T("fire_arrow", ("Fire Arrow", "Item_Arrow_Fire")),
    T("dins_fire", ("Din's Fire", "Item_DinFire")),
    T("slingshot", ("Fairy Slingshot", "Weapon_Range_SlingShot")),
    T("fairy_ocarina", ("Fairy Ocarina", "Item_Ocarina_Fairy")),
    T("ocarina_of_time", ("Ocarina of Time", "Item_Ocarina_Time")),
    T("bombchus", ("Bombchus", "Item_Bombchu")),
    T("hookshot", ("Hookshot", "Item_Hookshot"), ("Longshot", "Item_Longshot")),
    T("ice_arrow", ("Ice Arrow", "Item_Arrow_Ice")),
    T("farores_wind", ("Farore's Wind", "Item_FaroreWind")),
    T("boomerang", ("Boomerang", "Item_Boomerang")),
    T("lens", ("Lens of Truth", "Armor_GlassTruth")),
    T("magic_beans", ("Magic Beans", "Item_MagicBean")),
    T("hammer", ("Megaton Hammer", "Item_Hammer")),
    T("light_arrow", ("Light Arrow", "Item_Arrow_Light")),
    T("nayrus_love", ("Nayru's Love", "Item_NayruLove")),
    C("bottles", "Bottles", "Item_Bottle", 4),
    T("ruto_letter", ("Ruto's Letter", "Item_Bottle_Letter")),

    # ---- Capacity upgrades (the number in the corner is the capacity) ----
    T("stick_bag", ("Deku Stick Capacity (10)", "Item_StickBag_Small", 10),
      ("Deku Stick Capacity (20)", "Item_StickBag_Medium", 20), ("Deku Stick Capacity (30)", "Item_StickBag_Large", 30)),
    T("nut_bag", ("Deku Nut Capacity (20)", "Item_NutBag_Small", 20),
      ("Deku Nut Capacity (30)", "Item_NutBag_Medium", 30), ("Deku Nut Capacity (40)", "Item_NutBag_Large", 40)),
    T("bomb_bag", ("Bomb Bag (20)", "Item_BombBag_Small", 20), ("Big Bomb Bag (30)", "Item_BombBag_Medium", 30),
      ("Biggest Bomb Bag (40)", "Item_BombBag_Large", 40)),
    T("quiver", ("Quiver (30)", "Item_Quiver_Small", 30), ("Big Quiver (40)", "Item_Quiver_Medium", 40),
      ("Biggest Quiver (50)", "Item_Quiver_Large", 50)),
    T("bullet_bag", ("Bullet Bag (30)", "Item_BulletBag_Small", 30), ("Big Bullet Bag (40)", "Item_BulletBag_Medium", 40),
      ("Biggest Bullet Bag (50)", "Item_BulletBag_Large", 50)),
    T("wallet", ("Child's Wallet (99)", "Item_Wallet_Small", 99), ("Adult's Wallet (200)", "Item_Wallet_Medium", 200),
      ("Giant's Wallet (500)", "Item_Wallet_Large", 500)),

    # ---- Trade quests and masks ----
    T("child_trade", ("Weird Egg", "Item_WeirdEgg"), ("Chicken", "Item_AlarmCucco"),
      ("Zelda's Letter", "Item_ZeldaLetter"), ("Keaton Mask", "Armor_Child_Mask_Keaton"),
      ("Skull Mask", "Armor_Child_Mask_Skull"), ("Spooky Mask", "Armor_Child_Mask_Spooky"),
      ("Bunny Hood", "Armor_Child_Mask_Bunny"), ("Mask of Truth", "Armor_Child_Mask_Truth")),
    T("goron_mask", ("Goron Mask", "Armor_Child_Mask_Goron")),
    T("zora_mask", ("Zora Mask", "Armor_Child_Mask_Zora")),
    T("gerudo_mask", ("Gerudo Mask", "Armor_Child_Mask_Gerudo")),
    T("adult_trade", ("Pocket Egg", "Item_PocketEgg"), ("Pocket Cucco", "Item_PocketCucco"),
      ("Cojiro", "Item_CojiroCucco"), ("Odd Mushroom", "Item_OddMushroom"), ("Odd Potion", "Item_OddPowder"),
      ("Poacher's Saw", "Item_PoacherSaw"), ("Broken Goron's Sword", "Item_BrokenSword"),
      ("Prescription", "Item_Prescription"), ("Eyeball Frog", "Item_EyeballFrog"),
      ("World's Finest Eye Drops", "Item_EyeDrop"), ("Claim Check", "Item_ClaimCheck")),

    # ---- Equipment ----
    T("kokiri_sword", ("Kokiri Sword", "Weapon_Sword_Kokiri")),
    T("master_sword", ("Master Sword", "Weapon_Sword_Master")),
    T("biggoron_sword", ("Giant's Knife", "Weapon_Sword_Giant"), ("Broken Giant's Knife", "Weapon_Sword_BrokenGiant"),
      ("Biggoron's Sword", "Weapon_Sword_Biggoron")),
    T("shield", ("Deku Shield", "Weapon_Shield_Deku"), ("Hylian Shield", "Weapon_Shield_Hylian"),
      ("Mirror Shield", "Weapon_Shield_Mirror")),
    T("kokiri_tunic", ("Kokiri Tunic", "Armor_Adult_Normal")),
    T("goron_tunic", ("Goron Tunic", "Armor_Adult_Goron")),
    T("zora_tunic", ("Zora Tunic", "Armor_Adult_Zora")),
    T("iron_boots", ("Iron Boots", "Armor_Adult_HeavyBoot")),
    T("hover_boots", ("Hover Boots", "Armor_Adult_HoverBoot")),

    # ---- Upgrades ----
    T("strength", ("Goron's Bracelet", "Armor_Child_Gauntlet_Goron"), ("Silver Gauntlets", "Armor_Adult_Gauntlet_Silver"),
      ("Golden Gauntlets", "Armor_Adult_Gauntlet_Gold")),
    T("scale", ("Silver Scale", "Item_Scale_Silver"), ("Golden Scale", "Item_Scale_Gold")),
    T("magic", ("Magic Meter", "Item_FairyBless_MP"), ("Double Magic", "Item_FairyBless_MPDouble")),
    T("double_defense", ("Double Defense", "Item_FairyBless_DefenseDouble")),
    T("echo_gem", ("Echo Gem", "Item_AgonyStone")),
    T("gerudo_card", ("Gerudo's Card", "Item_Token_Gerudo")),
    C("skulltulas", "Gold Skulltula Tokens", "Item_Token_Gold", 100),
    C("heart_pieces", "Pieces of Heart", "extras/CollectHeartPiece_00", 36),
    C("heart_containers", "Heart Containers", "extras/CollectHeartBase_00", 8),

    # ---- Quest status ----
    T("kokiri_emerald", ("Kokiri's Emerald", "extras/DataFileImportantIcon_00")),
    T("goron_ruby", ("Goron's Ruby", "extras/DataFileImportantIcon_01")),
    T("zora_sapphire", ("Zora's Sapphire", "extras/DataFileImportantIcon_02")),
    T("light_medallion", ("Light Medallion", "extras/DataFileImportantIcon_03")),
    T("forest_medallion", ("Forest Medallion", "extras/DataFileImportantIcon_04")),
    T("fire_medallion", ("Fire Medallion", "extras/DataFileImportantIcon_05")),
    T("water_medallion", ("Water Medallion", "extras/DataFileImportantIcon_06")),
    T("spirit_medallion", ("Spirit Medallion", "extras/DataFileImportantIcon_07")),
    T("shadow_medallion", ("Shadow Medallion", "extras/DataFileImportantIcon_08")),

    T("zeldas_lullaby", ("Zelda's Lullaby", "extras/OcarinaMelodyIcon_00")),
    T("eponas_song", ("Epona's Song", "extras/OcarinaMelodyIcon_01")),
    T("sarias_song", ("Saria's Song", "extras/OcarinaMelodyIcon_02")),
    T("suns_song", ("Sun's Song", "extras/OcarinaMelodyIcon_03")),
    T("song_of_time", ("Song of Time", "extras/OcarinaMelodyIcon_04")),
    T("song_of_storms", ("Song of Storms", "extras/OcarinaMelodyIcon_05")),
    T("scarecrows_song", ("Scarecrow's Song", "extras/OcarinaMelodyIcon_06")),
    T("minuet", ("Minuet of Forest", "extras/OcarinaMelodyIcon_07")),
    T("bolero", ("Bolero of Fire", "extras/OcarinaMelodyIcon_08")),
    T("serenade", ("Serenade of Water", "extras/OcarinaMelodyIcon_09")),
    T("requiem", ("Requiem of Spirit", "extras/OcarinaMelodyIcon_10")),
    T("nocturne", ("Nocturne of Shadow", "extras/OcarinaMelodyIcon_11")),
    T("prelude", ("Prelude of Light", "extras/OcarinaMelodyIcon_12")),
]

# ---- Dungeon items: (id prefix, name, map+compass, small keys, boss key) ----
DUNGEONS = [
    ("deku", "Deku Tree", True, 0, False),
    ("dodongo", "Dodongo's Cavern", True, 0, False),
    ("jabu", "Jabu-Jabu's Belly", True, 0, False),
    ("forest", "Forest Temple", True, 5, True),
    ("fire", "Fire Temple", True, 8, True),
    ("water", "Water Temple", True, 6, True),
    ("shadow", "Shadow Temple", True, 5, True),
    ("spirit", "Spirit Temple", True, 5, True),
    ("well", "Bottom of the Well", True, 3, False),
    ("ice", "Ice Cavern", True, 0, False),
    ("hideout", "Thieves' Hideout", False, 4, False),
    ("gtg", "Gerudo Training Ground", False, 9, False),
    ("ganon", "Ganon's Castle", False, 2, True),
]

for _id, _name, _mc, _keys, _bk in DUNGEONS:
    if _mc:
        CELLS.append(T(f"{_id}_map", (f"{_name} Map", "Item_Dungeon_Map")))
        CELLS.append(T(f"{_id}_compass", (f"{_name} Compass", "Item_Dungeon_Compass")))
    if _keys:
        CELLS.append(C(f"{_id}_keys", f"{_name} Small Keys", "Item_Dungeon_SmallKey", _keys))
    if _bk:
        CELLS.append(T(f"{_id}_bk", (f"{_name} Boss Key", "Item_Dungeon_BossKey")))

CELLS_BY_ID = {c.id: c for c in CELLS}

# Getting the first cell for the first time also gives the second its base tier.
STARTS_WITH = {"sticks": "stick_bag", "nuts": "nut_bag", "bombs": "bomb_bag",
               "bow": "quiver", "slingshot": "bullet_bag"}
assert len(CELLS_BY_ID) == len(CELLS), "duplicate cell id"


def all_icons():
    """Every icon name the cells use (to check the extraction is complete)."""
    names = set()
    for c in CELLS:
        names.add(c.icon) if c.counter else names.update(t[1] for t in c.tiers)
    return names
