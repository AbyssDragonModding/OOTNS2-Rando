"""Setting definitions (shared by the GUI, the CLI and the settings string)."""
import base64
import json
import zlib

# (key, tab, group, label, type, options or None, default, tooltip)
SETTINGS = [
    # ---- Main Rules
    ("logic_rules", "Main Rules", "Logic", "Logic Rules", "choice",
     [("glitchless", "Glitchless"), ("none", "No Logic (experimental)")], "glitchless",
     "Glitchless: the seed can always be beaten without glitches. The logic is cautious, so it may expect\n"
     "an item a little earlier than you strictly need it.\n"
     "No Logic: items are placed completely at random; the seed may be unbeatable."),
    ("reachable_locations", "Main Rules", "Logic", "Guarantee Reachable Locations", "choice",
     [("all", "All"), ("beatable", "Required Only (experimental)")], "all",
     "All: every check in the seed can be reached, so you can collect everything.\n"
     "Required Only: only beating the game is guaranteed; some checks may be out of reach."),
    ("open_forest", "Main Rules", "Open", "Kokiri Forest", "choice",
     [("closed", "Closed"), ("closed_deku", "Closed Deku"), ("open", "Open")], "closed",
     "Closed: as in the original. Mido blocks the Deku Tree until you have a sword and shield, and the\n"
     "Kokiri boy blocks the forest exit until the Deku Tree is beaten.\n"
     "Closed Deku: the forest exit is open from the start; Mido still wants a sword and shield.\n"
     "Open: both are out of the way; you can go to the Deku Tree or leave the forest right away."),
    ("open_zora", "Main Rules", "Open", "Zora's Fountain", "choice",
     [("closed", "Closed"), ("open", "Open (needs further testing)")], "closed",
     "Open: King Zora has already moved aside (the Zora quest starts past Ruto's letter), so the Fountain\n"
     "and Jabu-Jabu can be reached without the letter. Ruto's Letter would be a dead item then, so it\n"
     "is replaced by an empty Bottle (wherever it lands, or at Lake Hylia if freestanding items aren't shuffled)."),
    ("open_door", "Main Rules", "Open", "Door of Time", "choice",
     [("closed", "Closed"), ("open", "Open (experimental)")], "closed",
     "Open: the Door of Time starts open, so the Master Sword can be reached without the stones and\n"
     "the Song of Time. Untested: the pedestal scene may still check story progress."),
    ("open_dmt", "Main Rules", "Open", "Open Death Mountain", "bool", None, False,
     "The gate from Kakariko to Death Mountain is open for child Link from the start, so you don't need\n"
     "to show Zelda's Letter to the soldier. The Happy Mask Shop opens too. Zelda's Letter is then only\n"
     "needed for the soldier's mask trade."),
    ("skip_child_zelda", "Main Rules", "Open", "Skip Child Zelda", "bool", None, False,
     "A new save starts as if you had already been through Hyrule Castle as a child. You already own\n"
     "the items from Zelda (HC Zeldas Letter), Malon (HC Malon Egg) and Impa (Song from Impa), Malon and\n"
     "Talon are at Lon Lon Ranch, and Hyrule Field has day and night from the start. Those three checks\n"
     "only hold items a save can start with (songs and single items, no ammo or upgrades)."),
    ("skip_epona_race", "Main Rules", "Open", "Skip Epona Race (experimental)", "bool", None, False,
     "Adult Epona is available as soon as you own Epona's Song: the 'Epona obtained' story flag is\n"
     "rewritten to 'has Epona's Song', so Ingo's race isn't needed. Untested in-game."),
    ("saria_song_ocarina", "Main Rules", "Open", "Saria's Song With Just an Ocarina", "bool", None, True,
     "Saria teaches her song in Sacred Forest Meadow as soon as you own an ocarina (either one);\n"
     "you don't need to meet Zelda first. Works with any Kokiri Forest setting."),
    ("shuffle_songs", "Main Rules", "Shuffle", "Shuffle Songs", "choice",
     [("vanilla", "Vanilla"), ("song", "Song Locations"), ("anywhere", "Anywhere (experimental)")], "song",
     "Song Locations: every place that teaches a song (Impa, Malon, Saria, Sheik, the Royal Tomb, the\n"
     "windmill and the Ocarina of Time scene) teaches a random song instead.\n"
     "Anywhere: songs can also be found in chests and NPC rewards (untested in the remake)."),
    ("shuffle_rewards", "Main Rules", "Shuffle", "Shuffle Spiritual Stones/Medallions", "choice",
     [("vanilla", "Vanilla"), ("reward", "Dungeon Reward Locations"), ("anywhere", "Anywhere")], "vanilla",
     "Dungeon Reward Locations: the Spiritual Stones and Medallions are swapped between the bosses.\n"
     "Anywhere: beating a boss gives a random item, and the stones and medallions can be in any check.\n"
     "The story still follows the dungeons you've beaten: the Door of Time opens after the three child\n"
     "dungeons, and the Light Arrows and Ganon's bridge come after the Shadow and Spirit Temples. With a\n"
     "closed Door of Time, all three Spiritual Stones can be found as child. The sage cutscenes play for\n"
     "the dungeon you beat."),
    ("shuffle_kokiri_sword", "Main Rules", "Shuffle", "Shuffle Kokiri Sword (experimental)", "bool", None, True,
     "The Kokiri Sword chest joins the item pool. Off keeps the sword in its vanilla chest."),
    ("shuffle_freestanding", "Main Rules", "Shuffle", "Shuffle Freestanding Items", "bool", None, True,
     "Items lying in the world become checks: the freestanding Pieces of Heart, the Fire Arrows at\n"
     "Lake Hylia and Ruto's Letter. Walk into a shuffled item to collect it (Pieces of Heart and Ruto's\n"
     "Letter still need A)."),
    ("shuffle_weird_egg", "Main Rules", "Shuffle", "Shuffle Weird Egg", "bool", None, False,
     "Off: Malon at Hyrule Castle gives the Weird Egg as usual.\n"
     "On: her reward is random and the Weird Egg is in another check. It hatches into the Cucco on the\n"
     "game's usual timer once you have it. Needs NPC & Minigame Rewards shuffled."),
    ("shuffle_ocarinas", "Main Rules", "Shuffle", "Shuffle Ocarinas", "bool", None, False,
     "The Fairy Ocarina and the Ocarina of Time are found in random checks. Saria doesn't hand you the\n"
     "Fairy Ocarina on the forest bridge, and Zelda's Ocarina of Time at the castle moat becomes a check.\n"
     "Either ocarina plays every song and opens the Door of Time."),
    ("shuffle_rupees", "Main Rules", "Shuffle", "Shuffle Freestanding Rupees", "bool", None, False,
     "The 109 green, blue, red and purple rupees lying around the world (Kokiri Forest, Hyrule Field,\n"
     "Zora's River/Domain/Fountain, Death Mountain, Graveyard) become checks. Walk into one to collect it,\n"
     "and each can only be collected once. Silver rupee puzzles are not changed."),
    ("shuffle_heart_containers", "Main Rules", "Shuffle", "Shuffle Boss Heart Containers", "bool", None, True,
     "The Heart Container each boss leaves behind becomes a random item."),
    ("shuffle_npc", "Main Rules", "Shuffle", "Shuffle NPC & Minigame Rewards", "bool", None, True,
     "Gifts from people and minigame prizes give random items: Zelda's Letter, the Goron Bracelet, the\n"
     "Silver Scale, the Gerudo Pass, the Light Arrows, Anju's bottle, Talon's first cucco game, the\n"
     "Big Poe buyer's bottle, Biggoron, fishing, the frogs, Dampe, the Skull Kid and others."),
    ("shuffle_fairies", "Main Rules", "Shuffle", "Shuffle Great Fairy Rewards", "bool", None, True,
     "The six Great Fairies give random items instead of Din's Fire, Farore's Wind, Nayru's Love and\n"
     "their three blessings (magic, double magic, halved damage)."),
    ("shuffle_house", "Main Rules", "Shuffle", "Shuffle Skulltula House Rewards", "bool", None, True,
     "The Skulltula House rewards for 10, 20, 30, 40 and 50 Gold Skulltula Tokens are random. Its two\n"
     "wallets are found in chests instead: the first one you open gives the Adult's Wallet, the second\n"
     "the Giant's Wallet."),
    ("tokensanity", "Main Rules", "Shuffle", "Tokensanity", "choice",
     [("off", "Off"), ("dungeons", "Dungeons Only"), ("overworld", "Overworld Only"), ("all", "All Tokens")], "off",
     "Gold Skulltulas drop a random item instead of a token. Touch the item to collect it, so you can\n"
     "grab one dropped on a wall while climbing. A Skulltula stays dead once killed, so pick its item\n"
     "up before leaving the room."),
    ("shopsanity", "Main Rules", "Shuffle", "Shopsanity (experimental)", "choice",
     [("off", "Off"), ("1", "1 Item Per Shop"), ("2", "2 Items Per Shop"), ("3", "3 Items Per Shop"),
      ("4", "4 Items Per Shop")], "off",
     "Shelves in the Kokiri, Goron, Zora and Bombchu shops sell shuffled items (prices 10-99 rupees).\n"
     "Only shelves unique to one shop are used (Kokiri 3, Goron 3, Zora 2, Bombchu up to 4), and the\n"
     "Deku Shield and tunics stay buyable. A shelf that rolls junk keeps its normal goods.\n"
     "Edits the shelf actor packs, the actor table and shop text; untested in-game."),
    # ---- Dungeon items
    ("maps_compasses", "Dungeon Items", "Dungeon Items", "Maps & Compasses", "choice",
     [("vanilla", "Vanilla"), ("own", "Own Dungeon (experimental)"), ("remove", "Remove (replaced by junk, experimental)"),
      ("start_with", "Start With")], "own",
     "Own Dungeon: maps and compasses stay inside their own dungeon. The remake decides a key's dungeon\n"
     "from the dungeon the chest is in, so 'Anywhere' (keysanity) is not possible.\n"
     "Remove: their checks hold a Blue Rupee and you never get them.\n"
     "Start With: a new save already has every dungeon's map and compass, and the chests that held them\n"
     "give a random bonus instead (rupees up to Gold, Bombchus, ammo, sometimes a Piece of Heart)."),
    ("small_keys", "Dungeon Items", "Dungeon Items", "Small Keys", "choice",
     [("vanilla", "Vanilla"), ("own", "Own Dungeon (experimental)")], "vanilla",
     "Own Dungeon shuffles small keys inside their dungeon. The logic has no door-by-door key model,\n"
     "so a key can end up behind its own locked door."),
    ("boss_keys", "Dungeon Items", "Dungeon Items", "Boss Keys", "choice",
     [("vanilla", "Vanilla"), ("own", "Own Dungeon (experimental)")], "vanilla",
     "Own Dungeon shuffles the boss key inside its dungeon (same caveat as small keys)."),
    # ---- Other
    ("item_pool", "Other", "Item Pool", "Item Pool", "choice",
     [("balanced", "Balanced"), ("scarce", "Scarce (experimental)"), ("minimal", "Minimal (experimental)")], "balanced",
     "Balanced: the same items as the original game.\nScarce: half of the Pieces of Heart and Heart Containers become rupees.\n"
     "Minimal: all Pieces of Heart and Heart Containers become rupees."),
    ("skip_cutscenes", "Other", "Quality of Life", "Make All Cutscenes Skippable", "bool", None, True,
     "Every cutscene can be skipped with the skip button, including the opening, the staff credits and\n"
     "the title-screen demos that normally can't be. Cutscenes still start: items and story progress\n"
     "are given inside them."),
    ("skip_area_intros", "Other", "Quality of Life", "Skip Area Intro Cutscenes (experimental)", "bool", None, False,
     "Experimental: early reports say the intros still play.\n"
     "First-arrival camera pans count as already seen: Kakariko, Graveyard, Hyrule Castle, Lake Hylia,\n"
     "Gerudo Valley/Fortress, Zora's River/Fountain, Ganon's Castle, Lost Woods (after Saria), and the\n"
     "Fire Temple / Bottom of the Well / Spirit Temple entrances. Intros that also advance a quest\n"
     "(Deku Tree, Death Mountain, Zora's Domain, Colossus, Castle Town, Crater, Ice Cavern, Shadow Temple,\n"
     "Training Ground, Kokiri Forest, Goron City, Hyrule Field) still play; use the skip button for those."),
    ("dodongo_bag_bombs", "Other", "Quality of Life", "Bag Bombs Open Dodongo's Cavern", "bool", None, False,
     "A bomb from your Bomb Bag breaks the boulder in front of Dodongo's Cavern, so you don't need the\n"
     "Goron Bracelet to open it. Off: only the bomb flower next to it works, which needs the bracelet."),
    ("refill_needs_item", "Other", "Quality of Life", "Refills Need Their Item", "bool", None, True,
     "A chest with arrows, bombs, Bombchus or Deku seeds gives a blue rupee instead until you own the\n"
     "Bow, a Bomb Bag (Bombchus go in the Bomb Bag in the remake) or the Slingshot. Refills placed\n"
     "anywhere other than a chest are always blue rupees."),
    ("anju_one_cucco", "Other", "Quality of Life", "Anju Needs Only 1 Cucco", "bool", None, True,
     "Return a single cucco to Anju's pen in Kakariko to finish her minigame and get the reward."),
    ("big_poe_one", "Other", "Quality of Life", "Big Poe Buyer Needs Only 1 Big Poe (experimental)", "bool", None, False,
     "Sell a single Big Poe to the ghost shop in the adult Market to get his reward (normally ten,\n"
     "1000 points). Changes the 900-point check in his sale flow to 0, so your first sale is the last one."),
    ("skip_kaepora", "Other", "Quality of Life", "Skip Kaepora Gaebora", "bool", None, False,
     "Kaepora Gaebora doesn't stop you to talk when you leave Kokiri Forest, in Hyrule Field or at\n"
     "Zora's River. The quest menu and the amiibo menu item he unlocks are available anyway. His optional\n"
     "rides at Lake Hylia and Death Mountain, and his talk in front of Hyrule Castle, are unchanged."),
    ("free_bombs", "Other", "Quality of Life", "Bombs Usable Without Goron Bracelet", "bool", None, True,
     "Bombs from the bag can be pulled out and thrown as soon as you have a Bomb Bag. In the remake they\n"
     "normally need the Goron Bracelet, which the original always gave you first. Bomb Flowers still\n"
     "need the bracelet. Off: the logic expects the Goron Bracelet before bombs."),
    ("small_chests", "Other", "Quality of Life", "Small Chests Only", "bool", None, False,
     "Big chests (including Boss Key chests) become small chests and open with the short animation, so\n"
     "the chest size no longer hints at what's inside. A few chests that play a story scene when opened\n"
     "stay big, such as the Kokiri Sword chest when the sword isn't shuffled."),
    ("excluded_locations", "Other", "Excluded", "Excluded Locations (experimental)", "list", None, [],
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
