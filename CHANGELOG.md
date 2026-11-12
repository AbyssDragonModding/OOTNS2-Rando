# Changelog

All notable changes to the randomizer. Versions are `Major.Minor.Patch`: a new setting or feature raises the
minor version, a fix raises the patch version. The same seed and settings string make a different mod in a
different version.

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
