"""Setting definitions (shared by the GUI, the CLI and the settings string)."""
import base64
import json
import zlib

# (key, tab, group, label, type, options or None, default, tooltip)
SETTINGS = [
    # ---- Main Rules
    ("logic_rules", "Main Rules", "Logic", "Logic Rules", "choice",
     [("glitchless", "Glitchless"), ("none", "No Logic")], "glitchless",
     "Glitchless: the seed is guaranteed beatable using the conservative remake logic.\n"
     "No Logic: items are placed completely at random; the seed may be unbeatable."),
    ("reachable_locations", "Main Rules", "Logic", "Guarantee Reachable Locations", "choice",
     [("all", "All"), ("beatable", "Required Only")], "all",
     "All: every shuffled location can be reached.\nRequired Only: only beating the game is guaranteed."),
    ("open_forest", "Main Rules", "Open", "Kokiri Forest", "choice",
     [("closed", "Closed"), ("closed_deku", "Closed Deku (exit open)"), ("open", "Open")], "closed",
     "Closed: the Kokiri boy blocks the exit until the Deku Tree is beaten, Mido blocks the Deku Tree.\n"
     "Closed Deku: the exit is open from the start; Mido still wants a sword and shield.\n"
     "Open: both blockers are gone. Switches off the two blocker flags in the default save data."),
    ("open_zora", "Main Rules", "Open", "Zora's Fountain", "choice",
     [("closed", "Closed"), ("open", "Open")], "closed",
     "Open: King Zora has already moved aside (the Zora quest starts past Ruto's letter), so the Fountain\n"
     "and Jabu-Jabu can be reached without the letter. Ruto's Letter would be a dead item then, so it\n"
     "is replaced by an empty Bottle (wherever it lands, or at Lake Hylia if freestanding items aren't shuffled)."),
    ("open_door", "Main Rules", "Open", "Door of Time (experimental)", "choice",
     [("closed", "Closed"), ("open", "Open")], "closed",
     "Open: the Door of Time starts open, so the Master Sword can be reached without the stones and\n"
     "the Song of Time. Untested: the pedestal scene may still check story progress."),
    ("open_dmt", "Main Rules", "Open", "Open Death Mountain", "bool", None, False,
     "The soldier at Kakariko's Death Mountain gate has already been shown Zelda's Letter, so the gate\n"
     "starts open for child Link. Sets the gate's own story flag (Npc_Hylia_Soldier_003_GateOpen), the one\n"
     "the soldier sets when you show him the letter; that flag also opens the Happy Mask Shop. Zelda's\n"
     "Letter is then only needed for the soldier's mask-shop trade."),
    ("skip_child_zelda", "Main Rules", "Open", "Skip Child Zelda (experimental)", "bool", None, False,
     "A new save starts as if you had already been through Hyrule Castle as a child: you already own\n"
     "whatever Zelda (HC Zelda's Letter), Malon (HC Malon Egg) and Impa (Song from Impa) would have given\n"
     "you. The castle quest counts as complete, so Talon and Malon are back at Lon Lon Ranch and Hyrule\n"
     "Field uses its normal day/night cycle from the start. Those three checks only hold items the save\n"
     "can grant directly (songs and single key items). Untested in-game."),
    ("skip_epona_race", "Main Rules", "Open", "Skip Epona Race", "bool", None, False,
     "Adult Epona is available as soon as you own Epona's Song: the 'Epona obtained' story flag is\n"
     "rewritten to 'has Epona's Song', so Ingo's race isn't needed. Untested in-game."),
    ("saria_song_ocarina", "Main Rules", "Open", "Saria's Song With Just an Ocarina", "bool", None, True,
     "Saria gives her song in Sacred Forest Meadow as soon as you own an ocarina; meeting Zelda\n"
     "isn't needed. Works with any Kokiri Forest setting."),
    ("shuffle_songs", "Main Rules", "Shuffle", "Shuffle Songs", "choice",
     [("vanilla", "Vanilla"), ("song", "Song Locations"), ("anywhere", "Anywhere (experimental)")], "song",
     "Song Locations: songs are shuffled among the 12 song-teaching events.\n"
     "Anywhere: songs can also be found in chests and NPC rewards (untested in the remake)."),
    ("shuffle_rewards", "Main Rules", "Shuffle", "Shuffle Spiritual Stones/Medallions (experimental)", "choice",
     [("vanilla", "Vanilla"), ("reward", "Dungeon Reward Locations"), ("anywhere", "Anywhere")], "vanilla",
     "Dungeon Reward Locations: the Spiritual Stones and Medallions are shuffled among the boss rewards.\n"
     "Anywhere: finishing a dungeon gives a random item, and the stones and medallions can be anywhere.\n"
     "The remake's story checks which dungeons you have beaten, not which stones/medallions you hold, so\n"
     "the Door of Time, the Light Arrows and Ganon's bridge follow the dungeons; the logic does the same.\n"
     "The sage cutscenes still play for the original dungeon. Untested in-game."),
    ("shuffle_kokiri_sword", "Main Rules", "Shuffle", "Shuffle Kokiri Sword", "bool", None, True,
     "The Kokiri Sword chest joins the item pool. Off keeps the sword in its vanilla chest."),
    ("shuffle_freestanding", "Main Rules", "Shuffle", "Shuffle Freestanding Items", "bool", None, True,
     "Freestanding Pieces of Heart, Fire Arrows (Lake Hylia) and Ruto's Letter."),
    ("shuffle_weird_egg", "Main Rules", "Shuffle", "Shuffle Weird Egg (experimental)", "bool", None, False,
     "Off: Malon at Hyrule Castle gives the Weird Egg as usual.\n"
     "On: her reward is random and the Weird Egg is somewhere else. The Cucco only hatches if you\n"
     "actually have the egg (the automatic hatch event checks for it); found later, it should hatch\n"
     "on the game's own timer. Needs NPC rewards shuffled. Untested in-game."),
    ("shuffle_ocarinas", "Main Rules", "Shuffle", "Shuffle Ocarinas (experimental)", "bool", None, False,
     "The Fairy Ocarina and the Ocarina of Time join the item pool.\n"
     "Saria's goodbye on the forest bridge (where she hands over the Fairy Ocarina) is switched off, so\n"
     "you have to find an ocarina. Zelda's Ocarina of Time at the castle moat becomes a check; logic\n"
     "expects you to already own an ocarina there, since she teaches the Song of Time right after.\n"
     "Either ocarina plays every song. Partly tested in-game."),
    ("shuffle_rupees", "Main Rules", "Shuffle", "Shuffle Freestanding Rupees", "bool", None, False,
     "The 112 green, blue, red and purple rupees lying around the world (Kokiri Forest, Hyrule Field,\n"
     "Zora's River/Domain/Fountain, Death Mountain, Graveyard, Deku Tree scrub drops) become checks.\n"
     "Each one is collected once (it has its own save flag). Silver rupee puzzles are not touched."),
    ("shuffle_heart_containers", "Main Rules", "Shuffle", "Shuffle Boss Heart Containers", "bool", None, True,
     "Heart Containers dropped by bosses."),
    ("shuffle_npc", "Main Rules", "Shuffle", "Shuffle NPC & Minigame Rewards", "bool", None, True,
     "Gifts such as the Weird Egg, Zelda's Letter, Goron Bracelet, Silver Scale, Gerudo Pass,\n"
     "Light Arrows, Anju's bottle, fishing, frogs, Dampe, Skull Kid and other minigame prizes."),
    ("shuffle_fairies", "Main Rules", "Shuffle", "Shuffle Great Fairy Rewards", "bool", None, True,
     "Din's Fire, Farore's Wind, Nayru's Love and the three Great Fairy blessings."),
    ("shuffle_house", "Main Rules", "Shuffle", "Shuffle Skulltula House Rewards", "bool", None, True,
     "Rewards for 10/20/30/40/50 Gold Skulltula Tokens. The two wallets become progressive wallets\n"
     "found in chests (the first gives the Adult's Wallet, the second the Giant's Wallet)."),
    ("tokensanity", "Main Rules", "Shuffle", "Tokensanity", "choice",
     [("off", "Off"), ("dungeons", "Dungeons Only"), ("overworld", "Overworld Only"), ("all", "All Tokens")], "off",
     "Gold Skulltulas drop a shuffled item instead of a token. Uses the enemy's drop parameter.\n"
     "Killing a Skulltula is permanent, so pick its item up before leaving the room."),
    ("shopsanity", "Main Rules", "Shuffle", "Shopsanity (experimental)", "choice",
     [("off", "Off"), ("1", "1 Item Per Shop"), ("2", "2 Items Per Shop"), ("3", "3 Items Per Shop"),
      ("4", "4 Items Per Shop")], "off",
     "Shelves in the Kokiri, Goron, Zora and Bombchu shops sell shuffled items (prices 10-99 rupees).\n"
     "Only shelves unique to one shop are used (Kokiri 3, Goron 3, Zora 2, Bombchu up to 4), and the\n"
     "Deku Shield and tunics stay buyable. A shelf that rolls junk keeps its normal goods.\n"
     "Edits the shelf actor packs, the actor table and shop text; untested in-game."),
    # ---- Dungeon items
    ("maps_compasses", "Dungeon Items", "Dungeon Items", "Maps & Compasses", "choice",
     [("vanilla", "Vanilla"), ("own", "Own Dungeon"), ("remove", "Remove (replaced by junk)"),
      ("start_with", "Start With")], "own",
     "Own Dungeon: maps and compasses stay inside their own dungeon. The remake decides a key's dungeon\n"
     "from the dungeon the chest is in, so 'Anywhere' (keysanity) is not possible.\n"
     "Remove: their checks hold a Blue Rupee and you never get them.\n"
     "Start With: a new save already has every dungeon's map and compass; their 20 checks hold a\n"
     "random bonus instead (rupees up to Gold, Bombchus, ammo, sometimes a Piece of Heart)."),
    ("small_keys", "Dungeon Items", "Dungeon Items", "Small Keys", "choice",
     [("vanilla", "Vanilla"), ("own", "Own Dungeon (experimental)")], "vanilla",
     "Own Dungeon shuffles small keys inside their dungeon. The logic has no door-by-door key model,\n"
     "so a key can end up behind its own locked door."),
    ("boss_keys", "Dungeon Items", "Dungeon Items", "Boss Keys", "choice",
     [("vanilla", "Vanilla"), ("own", "Own Dungeon (experimental)")], "vanilla",
     "Own Dungeon shuffles the boss key inside its dungeon (same caveat as small keys)."),
    # ---- Other
    ("item_pool", "Other", "Item Pool", "Item Pool", "choice",
     [("balanced", "Balanced"), ("scarce", "Scarce"), ("minimal", "Minimal")], "balanced",
     "Balanced: the vanilla item counts.\nScarce: half of the Pieces of Heart and Heart Containers become rupees.\n"
     "Minimal: all Pieces of Heart and Heart Containers become rupees."),
    ("skip_cutscenes", "Other", "Quality of Life", "Make All Cutscenes Skippable", "bool", None, True,
     "The remake already lets you skip most cutscenes. This also unlocks skipping for the ones it\n"
     "blocks: the opening cutscene, the staff credits and the title-screen demos.\n"
     "(Removing cutscenes completely is not possible: items and story flags are granted inside them.)"),
    ("skip_area_intros", "Other", "Quality of Life", "Skip Area Intro Cutscenes (experimental)", "bool", None, False,
     "Experimental: early reports say the intros still play.\n"
     "First-arrival camera pans count as already seen: Kakariko, Graveyard, Hyrule Castle, Lake Hylia,\n"
     "Gerudo Valley/Fortress, Zora's River/Fountain, Ganon's Castle, Lost Woods (after Saria), and the\n"
     "Fire Temple / Bottom of the Well / Spirit Temple entrances. Intros that also advance a quest\n"
     "(Deku Tree, Death Mountain, Zora's Domain, Colossus, Castle Town, Crater, Ice Cavern, Shadow Temple,\n"
     "Training Ground, Kokiri Forest, Goron City, Hyrule Field) still play; use the skip button for those."),
    ("dodongo_bag_bombs", "Other", "Quality of Life", "Bag Bombs Open Dodongo's Cavern", "bool", None, False,
     "Normally the boulder in front of Dodongo's Cavern only breaks from the special bomb flower next to it\n"
     "(needs the Goron Bracelet). This lets a Bomb Bag bomb near the boulder break it too, by rewiring the\n"
     "boulder's trigger logic. Off: the logic requires the Goron Bracelet to open the cavern."),
    ("refill_needs_item", "Other", "Quality of Life", "Refills Need Their Item", "bool", None, True,
     "A chest with arrows, bombs, Bombchus or Deku seeds gives a blue rupee instead if you don't have\n"
     "the Bow, a Bomb Bag (Bombchus are held in the Bomb Bag in the remake) or the Slingshot (the game's\n"
     "own conditional-chest check). Other checks can't test for the item, so refills placed there\n"
     "become blue rupees."),
    ("anju_one_cucco", "Other", "Quality of Life", "Anju Needs Only 1 Cucco", "bool", None, True,
     "Return a single cucco to Anju's pen to finish her minigame and get the reward.\n"
     "Changes the fence-count check in the minigame logic and Anju's 'cuccos left' counter."),
    ("free_bombs", "Other", "Quality of Life", "Bombs Usable Without Goron Bracelet", "bool", None, True,
     "In the remake, bombs pulled from the bag are 'lifted' and need the Goron Bracelet's strength.\n"
     "Vanilla always gives the bracelet first; a randomizer may not. This lowers the bag bomb's lift\n"
     "requirement so bombs work as soon as you have a Bomb Bag. Bomb Flowers still need the bracelet.\n"
     "Turned off, the logic requires the Goron Bracelet for bombs instead."),
    ("small_chests", "Other", "Quality of Life", "Small Chests Only (experimental)", "bool", None, False,
     "Every big chest (including Boss Key chests) uses the small chest instead, so opening one\n"
     "skips the long big-chest animation. Only the chest's actor changes: its item, flags and\n"
     "position stay the same. The chest size no longer hints at what's inside."),
    ("excluded_locations", "Other", "Excluded", "Excluded Locations", "list", None, [],
     "Locations that never hold progression or dungeon items (only rupees, ammo, hearts)."),
    ("create_spoiler", "Other", "Output", "Create Spoiler Log", "bool", None, True,
     "Write spoiler.txt / spoiler.json next to the mod."),
]

DEFAULTS = {s[0]: s[6] for s in SETTINGS}
SPEC = {s[0]: s for s in SETTINGS}

# Classic options that cannot be done with the current data swaps, shown in the GUI for reference.
UNSUPPORTED = [
    ("Keysanity (small keys / boss keys / Ganon's keys anywhere)",
     "The remake has one generic small key and one generic boss key; the stage you pick a key up in "
     "decides which dungeon it counts for, and no event can add a key to another dungeon. Use "
     "'Own Dungeon' on the Dungeon Items tab instead."),
    ("Bunny Hood speed boost (Majora's Mask style)",
     "Run speed comes from the animations; the only speed value in the data is a global scale. Masks "
     "have no movement parameter and the equipment effect list (e.g. UnderwaterBreathing) has no "
     "speed effect that can be confirmed."),
    ("Fast climbing",
     "Climb speed is computed by the player code and passed to the climb animation at runtime; no "
     "data file holds it."),
    ("Scrubsanity",
     "The remake replaced the classic scrub shops with the Scrub Business Seed trading system: their "
     "goods and prices are fixed per item type inside one shared event flow and can be bought again "
     "and again. The only one-time scrubs sell capacity upgrades (kept vanilla) and Pieces of Heart, "
     "and the Heart Piece scrubs share a single event node."),
    ("Auto-skip all cutscenes",
     "Items, songs and story flags are handed out inside the cutscene flows, so cutscenes can't be "
     "removed wholesale. Every cutscene can be skipped with the button (see 'Make All Cutscenes "
     "Skippable'), and the side-effect-free area intros can be skipped automatically."),
    ("Kakariko Gate / Gerudo Fortress (open)", "Their story flags are not mapped yet."),
    ("Rainbow Bridge / Ganon's Boss Key / Trials requirements", "The remake's bridge and trial checks are not mapped yet."),
    ("Starting inventory / starting age", "Needs save-data or GameData edits."),
    ("Shopsanity in the bazaars and potion shops / Cow Shuffle / Beans",
     "Bazaar and potion shelves are shared between several shops; cows use one shared event."),
    ("Gerudo Card individual toggle", "Part of 'Shuffle NPC & Minigame Rewards'."),
    ("Other capacity upgrades (bomb bag / quiver / seed bag sizes)",
     "Stay vanilla: nothing in the logic requires the smaller size first, so a bigger one found "
     "early could be downgraded by the smaller one later."),
    ("Entrance Randomizer", "Not supported."),
    ("Hints (Gossip Stones)", "Gossip Stone text editing is not implemented; use the spoiler log."),
    ("Ice Traps / Chest Appearance Matches Contents / Cosmetics", "Not implemented."),
    ("Master Quest dungeons", "Not present in the remake."),
]


def normalize(settings):
    out = dict(DEFAULTS)
    for k, v in (settings or {}).items():
        if k in SPEC:
            out[k] = v
    return out


def to_string(settings):
    diff = {k: v for k, v in normalize(settings).items() if v != DEFAULTS[k]}
    raw = zlib.compress(json.dumps(diff, sort_keys=True, separators=(",", ":")).encode(), 9)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def from_string(s):
    s = s.strip()
    raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    return normalize(json.loads(zlib.decompress(raw)))
