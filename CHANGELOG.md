# Changelog

All notable changes to the randomizer. Versions are `Major.Minor.Patch`: a new setting or feature raises the
minor version, a fix raises the patch version. The same seed and settings string make a different mod in a
different version.

## 0.4.5 - 2026-11-12

### Fixed
- **Shuffle Songs: Anywhere**: a song lying in the world (freestanding, rupee or boss Heart Container spot,
  or dropped by a Gold Skulltula) looked like a green rupee, because songs have no model of their own in the
  remake. Song pickups now show Sheik's harp and keep the song's name. Like every shuffled world item since
  0.4.4, they're collected by walking into them. Not yet tested in-game.

## 0.4.4 - 2026-11-12

### Fixed
- **Skip Child Zelda**: about 1 in 15 setting combinations couldn't be generated ("no item the save can
  grant for HC Malon Egg / HC Zeldas Letter / Song from Impa"). The three checks a new save already owns
  need items the save can simply be given, and with Shopsanity, a Scarce/Minimal pool or Weird Egg shuffle
  the leftover items sometimes had none. The generator now moves a suitable item there from another check
  and puts junk in its place. Found by a 6,810-seed fill simulation.
- **Zora's Fountain: Open**: King Zora was moved aside at first, but after leaving Jabu-Jabu's Belly he sat
  in front of the door again, a softlock. The first arrival in Zora's Domain set the Zora quest back to its
  "first visit" step, and he only showed it after the area reloaded. That arrival now keeps the quest where
  Open starts it. Not yet tested in-game.
- **Tokensanity**: an item dropped by a Gold Skulltula on a vine or wall needed A to pick up, which you can't
  press while climbing, so it could only be collected with the Boomerang or Hookshot.
- **Shuffle Freestanding Items / Freestanding Rupees**: shuffled items lying in the world also needed A
  (for example the rupee spots at Zora's River).

  Shuffled items in the world are now collected by walking into them, like rupees. Pieces of Heart and
  Ruto's Letter still need A, because they use their own pickup logic. For that reason the randomizer no
  longer puts them on Gold Skulltulas. Not yet tested in-game.

- **Door of Time: Closed** logic: going to adult now also expects an ocarina and Zelda met (Impa's send-off
  is a step of the Door of Time quest). The two moat checks (Song from Ocarina of Time, HF Ocarina of Time)
  expect the same. Before, both were only implied by other rules.

### Changed
- **Labels from the 0.4.3 test run (seed W68ETAG92L):** these passed in-game and are no longer tagged:
  Skip Child Zelda, Shuffle Spiritual Stones/Medallions, Shuffle Weird Egg, Shuffle Ocarinas, Shuffle
  Freestanding Rupees, Shuffle Great Fairy Rewards, Shuffle Skulltula House Rewards, Maps & Compasses' Start
  With, Skip Kaepora Gaebora and Small Chests Only. Zora's Fountain's Open stays (needs further testing):
  King Zora is back in front of the door after leaving Jabu-Jabu's Belly. Still (experimental) because
  untested or only tested off: Door of Time's Open (the tag moved from the whole setting to that option),
  Skip Epona Race, Shuffle Kokiri Sword, Shopsanity, Big Poe
  Buyer Needs Only 1 Big Poe, Skip Area Intro Cutscenes, Excluded Locations and the other options already
  marked.
- **Tooltips** of the confirmed settings now describe what happens in-game rather than how it's done,
  and no longer say "untested". This covers Logic Rules, Guarantee Reachable Locations, Kokiri Forest,
  Open Death Mountain, Skip Child Zelda, Saria's Song, Shuffle Songs, Stones/Medallions, Freestanding Items,
  Weird Egg, Ocarinas, Freestanding Rupees, Boss Heart Containers, NPC & Minigame Rewards, Great Fairies,
  Skulltula House, Tokensanity, Start With maps and compasses, Balanced pool, Skippable Cutscenes, Bag
  Bombs Open Dodongo's Cavern, Refills, Anju, Kaepora, Bombs Without Bracelet and Small Chests.
- **Door of Time: Closed**: when the Spiritual Stones are shuffled, all three are now placed where child Link
  can reach them, so you hold them before going to adult as in the original. The game itself still only
  checks the three child dungeons. The medallions are unchanged.

### Added
- **One-click setup** for people who don't code:
  - `Setup (Windows).bat` installs Python 3.14 for your user if needed (winget, or the python.org
    installer), installs `requirements.txt` and makes `.py`/`.pyw` files open with Python.
  - `setup_linux.sh` does the same on Linux. It uses your package manager, or uv as a fallback; asks
    before using sudo; installs the packages into a private `.venv`; and adds a menu entry plus a `.pyw`
    association.
  - `Start Randomizer (Windows).bat` and `run_linux.sh` open the randomizer and install any missing
    packages first.
  - `Install Requirements.bat` is replaced by the setup script.
- **README**: a step-by-step Setup guide (game files, download, setup, start, updating, troubleshooting).

### Checked
- **Skip Child Zelda** confirmed in-game (0.4.4): a new save gets the three start checks (Zelda's Letter,
  Malon's Egg, Impa's song), Malon and Talon are at Lon Lon Ranch, and Hyrule Field has day and night.
- **Door of Time: Closed** accepts either ocarina: the altar only checks the quest step, not which ocarina
  you hold, so no patch is needed. In a simulation of 540 seeds across forest, reward, song, ocarina and
  Skip Child Zelda combinations, the three child dungeons, an ocarina and the Song of Time were always
  reachable as child.

## 0.4.3 - 2026-11-11

### Fixed
- **Shuffle Freestanding Rupees**: an item dropped by a Deku Scrub in the Deku Tree landed inside its flower,
  behind an invisible wall, so it couldn't be picked up. The three Deku Tree scrub drops are no longer rupee
  checks (109 instead of 112). Seeds made with 0.4.2 or older can have an important item stuck there, so
  make a new seed.

- **LLR Talons Chickens**: buying milk from Talon and refilling a bottle on later wins also handed out the
  check's item, so it could be collected again and again. Only his first-win prize is the check now.

### Added
- **DMT Biggoron** (Shuffle NPC & Minigame Rewards): the Biggoron's Sword at the end of the adult trade
  sequence is a check. The trade items themselves stay vanilla.
- **Big Poe Buyer Needs Only 1 Big Poe** (Other > Quality of Life, experimental, off by default).
- **Skip Kaepora Gaebora** (Other > Quality of Life, experimental, off by default): his first talks outside
  Kokiri Forest, in Hyrule Field and at Zora's River count as already seen.

### Changed
- **Shuffle NPC & Minigame Rewards** is no longer experimental: all 28 of its checks were randomized in a
  0.4.2 test seed, alongside earlier in-game checks.
- Partly confirmed settings are now labelled **(needs further testing)** in the randomizer instead of
  (experimental): Zora's Fountain's Open, Skip Child Zelda, Shuffle Spiritual Stones/Medallions, Shuffle
  Ocarinas, Shuffle Freestanding Rupees, Shuffle Skulltula House Rewards and Small Chests Only.
- Checked against the full list of minigames and NPC rewards: every one with an item reward is a check,
  except the Treasure Chest Game (its prize chest needs a minigame-only preview model for each prize) and
  Medigoron's Giant's Knife (bought, like a shop).

### Test results (0.4.2 seed)
- Small Chests Only: every big chest in the Deku Tree was small and opened with the short animation. The
  Kokiri Sword chest stays big when the sword isn't shuffled (its chest plays the sword scene).
- Shuffle Spiritual Stones/Medallions: Anywhere: beating the Deku Tree gave its random item.
- Shuffle Skulltula House Rewards: all five rewards random in the spoiler.

## 0.4.2 - 2026-11-11

### Fixed
- **Small Chests Only**: in 0.4.1 the swapped chests couldn't be opened. The 0.4.1 change (sending the big
  chests' scripts to the small chest's opening) is undone. Instead, chests whose script only adds a Navi line
  or a camera move lose that script and open like normal small chests. The eleven chests whose script runs
  a story event (Nabooru, the Serenade of Water, Ruto in Jabu-Jabu, Dampé's race, Ganon's Castle's Golden
  Gauntlets, the Ice Arrow quest, the vanilla Kokiri Sword) stay big chests.

### Changed
- Every setting or option that isn't confirmed in-game is now marked experimental: Kokiri Forest's Closed
  Deku, Zora's Fountain's Open, No Logic, Required Only, Skip Epona Race, Shuffle Kokiri Sword, Shuffle NPC &
  Minigame Rewards, Shuffle Great Fairy Rewards, Shuffle Skulltula House Rewards, every Maps & Compasses
  option other than Vanilla, the Scarce and Minimal item pools, and Excluded Locations.

### Test results (0.4.1 seed)
- Skip Child Zelda with a Closed forest: Mido now blocks the way without a sword and shield (the 0.4.1 fix).

## 0.4.1 - 2026-11-11

### Fixed
- **Skip Child Zelda** with a Closed forest: Mido was gone but his invisible wall still blocked the Deku
  Tree, even with a sword and shield. The Kokiri schedules read the Hyrule Castle quest, which the setting
  completes, so Mido had moved to where he stands after you've met Zelda. The Kokiri now stay on their
  before-the-castle schedules, and Mido guards the path until you show him a sword and shield.
- **Small Chests Only**: the swapped chests still played the long big-chest sequence. About 30 big chests
  run their own script (a Navi line or story flags) that jumps to the big-chest sequence; those jumps now go
  to the small chest's sequence. Every big chest in the game is now swapped, not only the randomized ones.

### Test results (0.4.0 seed)
- Working: Open Death Mountain (On), Tokensanity (Overworld Only).
- Partly working: Skip Child Zelda (starting items and day/night confirmed; the Mido bug is fixed above),
  Shuffle Spiritual Stones/Medallions: Anywhere (a medallion at a freestanding spot works; dungeon rewards
  not tested yet), Small Chests Only (fixed above).

## 0.4.0 - 2026-11-11

### Added
- **Item tracker** (`Tools/OOTNS2-Tracker`): a clickable tracker for items, songs, stones, medallions and
  counters, with save/load. It takes its icons from your own extracted romfs; no game files are included.
- **Small Chests Only** (Other > Quality of Life, experimental, off by default): big chests and Boss Key
  chests use the small chest, so opening one skips the long big-chest animation.
- **Market Big Poe Bottle**: the bottle the Big Poe buyer gives at 1000 points is now an NPC & Minigame
  check (Shuffle NPC & Minigame Rewards).

### Fixed
- **Zora's Fountain: Open**: King Zora still blocked the Fountain. The setting now also starts the Zora
  quest where showing him Ruto's Letter leaves it, which is what moves him.
- **Shuffle Skulltula House Rewards**: the 10 and 30 token rewards were still the Adult's and Giant's
  Wallet. All five rewards are now random. The two wallets go into chests as progressive wallets: the first
  one gives the Adult's Wallet, the second the Giant's Wallet.

### Test results (0.3.1 seed)
- Working: Open Death Mountain (Off), Shuffle Songs (Song Locations), Shuffle Weird Egg (Off), Shuffle
  Freestanding Rupees (Off), Shuffle Boss Heart Containers, Tokensanity (Dungeons Only), Bag Bombs Open
  Dodongo's Cavern.
- Partly working: Zora's Fountain (Open), Shuffle NPC & Minigame Rewards and Shuffle Skulltula House
  Rewards, all fixed above; Shuffle Ocarinas (the Ocarina of Time check is still untested).
- Known issue, not fixable: while holding Zelda's Letter you can't use the Cucco, because the remake keeps
  the child trade items in one slot.

## 0.3.2 - 2026-11-11

### Added
- **Skip Child Zelda** (Main Rules > Open, experimental, off by default): a new save already owns whatever
  Zelda, Malon and Impa would have given you (the items at HC Zeldas Letter, HC Malon Egg and Song from
  Impa). The Hyrule Castle quest counts as complete, so Talon and Malon are at Lon Lon Ranch and Hyrule
  Field has its normal day/night cycle from the start. Those three checks only hold items the save can
  grant directly (songs and single key items).
- **Shuffle Spiritual Stones/Medallions: Anywhere** (experimental): finishing a dungeon gives a random item,
  and the stones and medallions can be anywhere. The setting (formerly "Shuffle Dungeon Rewards") is now
  marked experimental.

### Changed
- The logic now follows finished dungeons instead of held stones and medallions, because that's what the
  remake checks. The Door of Time needs the three child dungeons, and the bridge and Light Arrows need the
  Shadow and Spirit Temples. This also fixes Dungeon Reward Locations seeds, where the logic could expect the
  bridge after the wrong two dungeons.

### Confirmed
- Shuffle Ocarinas: Saria is there for her opening greeting outside Link's house again (the 0.3.1 fix).

## 0.3.1 - 2026-11-11

### Fixed
- **Shuffle Ocarinas**: Saria's greeting outside Link's house at the start played without Saria there.
  Her bridge goodbye is now switched off at the bridge trigger itself, instead of by marking it as already
  seen, which made Saria act as if she had left the forest from the start. After the Deku Tree she waits
  by the bridge, but the goodbye (and its Fairy Ocarina) still doesn't play.

## 0.3.0 - 2026-11-11

### Added
- **Open Death Mountain** (Main Rules > Open, off by default): the Kakariko gate to Death Mountain starts
  open for child Link, so Zelda's Letter isn't needed to get past the soldier. The logic follows the
  setting. This also opens the Happy Mask Shop from the start.
- `CHANGELOG.md`, and a **Test results** section in the README listing which settings are confirmed working.

### Removed
- **Load Saves at Dungeon Entrance**. It never moved the restart point in testing.

### Changed
- **Tokensanity** and **Bag Bombs Open Dodongo's Cavern** are no longer marked experimental; both were
  confirmed working in-game.

## 0.2.1 - 2026-11-11

### Fixed
- **Bombchus** picked up without a Bomb Bag showed "Five Bombchus" but gave none, because the remake keeps
  Bombchus in the Bomb Bag. With **Refills Need Their Item** on, Bombchus are now placed in chests that
  give a Blue Rupee until you have a Bomb Bag (like arrows, bombs and seeds).
- **Open forest**: Mido still blocked the path to the Deku Tree until you had a sword and shield. The
  "Meet the Deku Tree" quest now starts past his step, so he has already moved aside.
- **Shuffle Kokiri Sword**: the original sword chest still played the sword cutscene and handed Link a
  sword that disappeared after saving and quitting. A randomized sword chest now opens like a normal chest.

### Changed
- Test checklist: a new **Partial** result (orange) next to Pass and Fail, counted in both sets of totals.
  Result cells are centred, and the Category column is wider.
- The checklist is now only written as `checklist.xlsx`. Testers export it to CSV from Google Sheets for
  bug reports.

## 0.2.0 - 2026-11-10

### Added
- **Game version check**: the randomizer hashes the game's `exefs/main` (SHA-256) and only runs on known
  versions (currently game version 1.1.1). The ROM Options tab has an **exefs folder** row (empty = the
  `exefs` folder next to the romfs), a status line that turns green for a supported version, and the
  current hash under the romfs box.

## 0.1.0 - 2026-11-10

First public release.

- README for testers: installing Python, `Install Requirements.bat`, starting the randomizer by
  double-clicking `ootr_remake.pyw`, installing seeds and using the test checklist.
- Test checklist (`checklist.xlsx` / `checklist.csv`) with the seed's settings and every check grouped
  by region, Pass/Fail dropdowns and running totals.
- **Open Folder** button that opens the output folder.
- Crash messages and `error_log.txt` when started without a console.
- **Skip Area Intro Cutscenes** marked experimental and off by default (the intros still play).
