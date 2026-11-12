# OoT Remake Randomizer
## Current Version: 0.4.4 (PUBLIC BETA RELEASE)
An item randomizer for the Switch 2 remake of *The Legend of Zelda: Ocarina of Time*. It shuffles chests,
songs, dungeon rewards, NPC rewards, shop items, Gold Skulltulas and more, and checks that every seed can be
beaten. The settings follow the classic [OoT Randomizer](https://ootrandomizer.com), adjusted to what the
remake allows.

**No game files are included.** The randomizer reads your own extracted game files (the `romfs` and `exefs`) and writes
only the files it changes into a new mod folder. Share seeds and settings strings, never mod folders.

><span style="display: flex; justify-content: center; color: red;">[WARNING]</span>
> **This randomizer is extremely early in development.** Expect bugs and broken logic: items that don't
> appear or can't be picked up, seeds that softlock or can't be finished, and settings that don't do what
> they say. Settings marked *experimental* are the least reliable. Don't play a seed you can't afford to
> abandon, and keep the spoiler log handy.
>
> Your test reports are what makes it better; see [Testing and reporting problems](#testing-and-reporting-problems).


[Disclamer] Yes claude was used with the production of this. It accelerates development a ton. Most settings are manually tested in game manually
=======

## Contents

- [What you need](#what-you-need)
- [Setup](#setup)
- [Making a seed](#making-a-seed)
- [Installing the seed in your emulator](#installing-the-seed-in-your-emulator)
- [Testing and reporting problems](#testing-and-reporting-problems)
- [Settings](#settings)
- [Tools](#tools)
- [Supported game versions](#supported-game-versions)
- [Known issues](#known-issues)
- [Versions](#versions)
- [Credits](#credits)

## What you need

- A PC with a graphics driver that supports **Vulkan** (any recent NVIDIA, AMD or Intel driver).
- **Python 3.14 or newer.** The setup script installs it for you (see [Setup](#setup)).
- **Your own extracted romfs and exefs** of the game. The romfs is the folder that contains `Banc`, `Event`,
  `Pack`, `RSDB`, `System` and so on; the exefs contains `main` and `main.npdm`. Most Switch emulators can
  extract both: right-click the game in the game list and choose the *Extract RomFS* / *Dump RomFS* and
  *Extract ExeFS* / *Dump ExeFS* options. Keeping them side by side (`<game>/romfs` and `<game>/exefs`) lets
  the randomizer find the exefs by itself.
- **A supported game version.** See [Supported game versions](#supported-game-versions).

## Setup

You only do this once, and you don't need to know anything about programming. The randomizer is a Python
program: **Python** is the free program that runs it, and the setup script installs Python and everything
else for you.

**What you'll end up with:** a randomizer folder you double-click to open, plus your own game files
(romfs and exefs) that you choose inside the randomizer.

### Step 1: Get your game files ready

The randomizer reads the game from your own dump; it never comes with any game files.

1. In your Switch emulator, right-click the game in the game list.
2. Choose **Extract RomFS** (some emulators call it **Dump RomFS**) and save it to a folder.
3. Do the same with **Extract ExeFS** / **Dump ExeFS**.
4. Keep both next to each other, for example:
   ```
   D:\Games\OoT Remake\romfs\     <- has folders like Banc, Event, Pack, RSDB, System
   D:\Games\OoT Remake\exefs\     <- has the files main and main.npdm
   ```

### Step 2: Download the randomizer

1. Open this project's GitHub page and click the green **Code** button, then **Download ZIP**.
2. Find the ZIP in your Downloads folder, **right-click it and choose Extract All...** (on Linux: right-click >
   *Extract Here*). Put the extracted folder somewhere easy to find, like your Desktop or Documents.
   - Don't put it inside your romfs folder.
   - Don't run anything straight from inside the ZIP. Always extract it first.

The extracted folder looks like this. These are the files you'll use:

| File | What it's for |
|---|---|
| `Setup (Windows).bat` | **Windows:** installs everything. Run it once. |
| `Start Randomizer (Windows).bat` | **Windows:** opens the randomizer. |
| `setup_linux.sh` | **Linux:** installs everything. Run it once. |
| `run_linux.sh` | **Linux:** opens the randomizer. |
| `ootr_remake.pyw` | The randomizer itself. Double-clicking it also works once setup is done. |

### Step 3 (Windows): Run the setup

1. Open the randomizer folder and **double-click `Setup (Windows).bat`**.
2. If Windows shows a blue box saying **"Windows protected your PC"**, click **More info**, then **Run
   anyway**. This shows up for any script downloaded from the internet. The file is plain text: right-click it
   and choose **Edit** if you want to read what it does first.
3. A black window opens and works through three steps:
   1. **Python:** if you don't have Python 3.14 or newer, it installs Python 3.14 just for your Windows user
      (no administrator password). It uses *winget* (built into Windows 10 and 11) or downloads the
      official installer from python.org. This can take a minute or two, and no installer window appears.
   2. **Packages:** it installs the extra pieces the randomizer needs, listed in `requirements.txt`. These
      are the window (`raven-gui`), the checklist spreadsheet (`openpyxl`) and the item tracker's icons
      (`texture2ddecoder`, `pillow`).
   3. **File association:** it makes `.py` and `.pyw` files open with Python when you double-click them.
      This only changes your own user's settings.
4. When it says **"Setup finished"**, press any key to close the window.

If it says *"Python was installed, but this window can't see it yet"*, close the window and double-click
`Setup (Windows).bat` again. Windows only notices a new program in newly opened windows.

### Step 3 (Linux): Run the setup

1. Open the randomizer folder in your file manager, right-click an empty spot and choose **Open in
   Terminal** (or open a terminal and `cd` into the folder).
2. Type this and press Enter:
   ```bash
   bash setup_linux.sh
   ```
3. If Python 3.14 isn't installed, it asks before installing it. It uses your package manager (apt, dnf,
   pacman or zypper), which asks for your password (`sudo`). If your distribution doesn't have 3.14 yet, it
   offers to use [uv](https://docs.astral.sh/uv/) instead, which installs Python into your home folder
   without a password.
4. It then makes a private Python environment in a `.venv` folder inside the randomizer folder and
   installs the packages there. Nothing goes into your system Python.
5. Finally it adds **OoT Remake Randomizer** to your application menu and makes `.pyw` files open with
   Python. It doesn't do this for `.py` files, so they still open in your text editor.

You also need a **Vulkan graphics driver**. Most distributions already have one; the setup warns you if it
can't find `vulkaninfo`.

### Step 4: Start the randomizer

- **Windows:** double-click **`Start Randomizer (Windows).bat`** (or `ootr_remake.pyw`).
- **Linux:** open **OoT Remake Randomizer** from your application menu, double-click `ootr_remake.pyw`, or run
  `./run_linux.sh` in a terminal.

The start scripts check that everything is still installed and fix it if not, for example after you download
a new version. If Python is missing entirely, they run the setup for you.

**Desktop shortcut (Windows):** right-click `Start Randomizer (Windows).bat` > **Show more options** > **Send
to** > **Desktop (create shortcut)**.

### Updating to a new version

Download and extract the new ZIP the same way. You can delete the old folder, but keep your output folder
with your seeds. Then just start the randomizer. The start script installs any new packages automatically,
and running the setup again is never harmful.

### If something goes wrong

| What you see | What to do |
|---|---|
| "Windows protected your PC" | Click **More info**, then **Run anyway**. |
| `ootr_remake.pyw` opens in Notepad, or Windows asks which app to use | Use `Start Randomizer (Windows).bat` instead, or right-click the file > **Open with** > **Choose another app** > **Python** > tick **Always**. |
| "Python 3.14 or newer is required" | Run the setup again. If you installed Python yourself, make sure it's 3.14 or newer. |
| "The GUI library isn't installed yet" | Run the setup again (it needs an internet connection). |
| The window doesn't open, or closes straight away | Your graphics driver may not support Vulkan. Update it from NVIDIA, AMD or Intel. |
| "The randomizer crashed" | It names an `error_log.txt` file in the randomizer folder. Attach that file when you [open an issue](#opening-an-issue). |
| The setup says the download failed | Check your internet connection. You can also install Python 3.14 yourself from [python.org/downloads](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"**) and run the setup again. |

### Doing it by hand (for those who prefer to)

Install Python 3.14 or newer from [python.org](https://www.python.org/downloads/) (Windows: tick **Add
python.exe to PATH**), then in a terminal in the randomizer folder:

```bash
python -m pip install -r requirements.txt
```

```bash
python ootr_remake.pyw
```

On Linux use `python3.14` (or a virtual environment) in place of `python`. macOS isn't tested, but the same
two commands should work with Python 3.14 from python.org.

## Making a seed

1. **ROM Options** tab: choose your **romfs folder** and an **output folder** for the finished mod. The output
   folder can't be inside the romfs.
   - Leave **exefs folder** empty if your exefs is next to the romfs; otherwise choose it.
   - The line under it turns **green** when your game version is supported. If it's red, the randomizer won't
     generate; see [Supported game versions](#supported-game-versions).
2. Optional: click **Scan romfs** to check the folder. This also fills the **Exclusions** tab, where you can
   double-click a location so it never holds an important item.
3. Pick your settings on the **Main Rules**, **Dungeon Items** and **Other** tabs. Hover over any option to see
   what it does.
4. Click **Generate Mod**. Click **Open Folder** (next to it) to open your output folder. Each seed
   gets its own folder there:

```
<output folder>/OoTR_Remake_<seed>/
    romfs/            <- the mod itself; this is what goes into the emulator
    settings.txt      <- version, seed and settings string
    spoiler.txt       <- where every item is, plus a playthrough
    spoiler.json      <- the same, for tools
    checklist.xlsx    <- test checklist with Pass/Partial/Fail dropdowns and colours
```

The spoiler and checklist files are only written when **Create Spoiler Log** (Other tab) is on, because they
show every item's location.

**Sharing a seed:** the same **version + seed + settings string** always makes exactly the same mod. Copy the
settings string from the GUI (or `settings.txt`) and send it with the seed, so others can make the seed
themselves from their own romfs. Your last folders and settings are remembered between runs.

## Installing the seed in your emulator

1. In your emulator, right-click the game and choose **Open Mod Data Location** (the name varies a little
   between emulators).
2. Copy the whole `OoTR_Remake_<seed>` folder into that location, so the result looks like
   `<mod data location>/OoTR_Remake_<seed>/romfs/...`.
3. Make sure only one randomizer seed is enabled at a time (most emulators list mods in the game's
   **Properties** > **Add-Ons** page).
4. **Start a new save file** for every seed. Old saves keep the previous seed's progress flags.

## Testing and reporting problems

### The checklist

Every seed with a spoiler log comes with a test checklist, `checklist.xlsx`. It has two blocks side by
side.

**Left block (columns A–G): the seed and its settings**

| Rows / column | What it is |
|---|---|
| Version, Seed, Settings String | The seed's identity. Copy these into bug reports. |
| Emulator / Tester | Fill this in yourself: emulator name and version, and your name if you like |
| Settings, Passed, Partial, Failed, Untested | Running totals for the settings, next to the seed info; they update as you fill in Result |
| **Category**, **Setting**, **Value** | Every setting this seed uses, grouped by tab |
| **Expected In-Game** | What the setting should do in the game (blank when there's nothing to see) |
| **How to Test** | A quick way to check it |
| **Result** | `Pass`, `Partial`, `Fail`, or empty if you haven't tested it |
| **Notes** | What you saw, especially for anything that failed |

**Right block (columns J–O): the checks**

| Rows / column | What it is |
|---|---|
| Checks, Passed, Partial, Failed, Untested | Running totals; they update as you fill in Result |
| **Region** | The area, e.g. Kokiri Forest. Checks are grouped by region in roughly the order you visit them. |
| **Location** | The check's name (the same name as in the spoiler) |
| **Vanilla Item** | What's there in the normal game |
| **Randomized Item** | What should be there in this seed. Shop items show their price. Ammo chests note when they give a Blue Rupee instead because you don't have the matching bag yet. |
| **Result** | `Pass`, `Partial`, `Fail`, or empty |
| **Notes** | What happened |

**Result** is a dropdown rather than a checkbox, because a checkbox can't tell "not tested yet" from
"failed":

| Result | Colour | Use it when |
|---|---|---|
| **Pass** | green | It works as described |
| **Partial** | orange | It mostly works, but something is off. Say what in **Notes**. |
| **Fail** | red | It doesn't work |
| *(empty)* | none | You haven't tested it yet |

### Opening the checklist in Google Sheets

1. Go to [sheets.google.com](https://sheets.google.com) and open a **Blank spreadsheet**.
2. Choose **File** > **Import** > **Upload**, and drop in `checklist.xlsx`.
3. Set **Import location** to **Replace spreadsheet** and click **Import data**.
4. Rename the spreadsheet (top left) to the seed, e.g. `OoTR 0.3.1 U5R6C3SVEJ`.

The dropdowns, colours and totals come along with the import. Excel and LibreOffice open the file directly
as well.

Tips while playing:
- **Data** > **Create a filter** on the checks block lets you show one region, or only failed checks.
- You don't have to test everything. A few checks in each region you visit, and every setting you can see
  in-game, already help a lot.
- For anything that fails or partly works, write what happened in **Notes**: the item didn't appear, couldn't be picked up,
  wrong item or text, came back after leaving or reloading, softlock, or crash. Mention what you were doing
  and which items you had, if it seems relevant.

### Exporting your results

When you're done (or when something breaks):

1. In Google Sheets, choose **File** > **Download** > **Comma Separated Values (.csv)**. This downloads the
   checklist with your results and notes as a `.csv` file, which is what bug reports use. In Excel, use
   **File** > **Save As** > **CSV UTF-8**.
2. Keep the layout as it is: don't move columns or delete the top rows. The exported file then lines up with
   the original checklist, so the results can be matched check by check.

### Opening an issue

Open an issue on this repository's **Issues** tab and include:

- **Version, seed and settings string.** They're at the top of the checklist and in `settings.txt`.
- **Your emulator and its version**, and the game's version/update.
- **What went wrong and where**: the check's Location name from the checklist or spoiler, what you expected
  and what happened.
- **Attachments:** your exported checklist `.csv`, and `error_log.txt` if the randomizer itself crashed. Add
  `spoiler.txt` if you have it. You can drag files straight into the issue text box.

Search existing issues first; if your problem is already there, add your details to it.

## Settings

The GUI explains every option when you hover over it. In short:

| Tab | What you can change |
|---|---|
| **Main Rules** | Logic (glitchless or none); open Kokiri Forest, Zora's Fountain, the Door of Time and Death Mountain; skip child Zelda; skip Epona's race (experimental); Saria's Song with just an ocarina; what gets shuffled: songs, Spiritual Stones and Medallions (in boss rewards or anywhere), Kokiri Sword, Weird Egg, ocarinas, freestanding items, freestanding rupees, boss Heart Containers, NPC and minigame rewards, Great Fairies, Skulltula House rewards, Gold Skulltula tokens (Tokensanity) and shop items (Shopsanity) |
| **Dungeon Items** | Maps & Compasses (vanilla, own dungeon, removed or start with), small keys and boss keys |
| **Other** | Item pool size; quality of life (skippable cutscenes, no area intros (experimental), bombs without the Goron Bracelet, bag bombs open Dodongo's Cavern, Anju needs 1 cucco, ammo chests need their bag, small chests only, Big Poe buyer needs 1 Big Poe, skip Kaepora Gaebora); spoiler log |
| **Exclusions** | Locations that only ever hold minor items |
| **Not Supported** | Classic randomizer options the remake's data can't support yet, and why |

Labels in the randomizer show how far each setting has been tested in-game:
- **(experimental):** works in offline checks but hasn't been tried in-game yet.
- **(needs further testing):** partly confirmed in-game; see the **Partly working** table below.
- **No label:** confirmed working (the **Working** table). Vanilla and Off choices leave that part of the
  game unchanged.
These are the ones most worth testing.

### Test results

Results from in-game test runs, taken from the testers' exported checklists. A setting loses its
*experimental* tag once a test confirms it fully works. Settings that aren't listed haven't been confirmed
yet.

**Working**

| Setting | Value tested | Version |
|---|---|---|
| Logic Rules | Glitchless | 0.4.3 |
| Guarantee Reachable Locations | All | 0.4.3 |
| Kokiri Forest | Open, Closed | 0.2.1, 0.4.3 |
| Open Death Mountain | Off, On | 0.3.1, 0.4.0, 0.4.3 |
| Skip Child Zelda | On | 0.4.3, 0.4.4 |
| Saria's Song With Just an Ocarina | On | 0.2.1, 0.4.3 |
| Shuffle Songs | Song Locations | 0.3.1, 0.4.3 |
| Shuffle Spiritual Stones/Medallions | Anywhere | 0.4.3 |
| Shuffle Kokiri Sword (experimental) | Off | 0.2.1, 0.4.3 |
| Shuffle Freestanding Items | On | 0.2.1, 0.4.3 |
| Shuffle Weird Egg | Off, On | 0.3.1, 0.4.3 |
| Shuffle Ocarinas | On | 0.4.3 |
| Shuffle Freestanding Rupees | On, Off | 0.2.1, 0.3.1, 0.4.3 |
| Shuffle Boss Heart Containers | On | 0.3.1, 0.4.3 |
| Shuffle NPC & Minigame Rewards | On | 0.4.2, 0.4.3 |
| Shuffle Great Fairy Rewards | On | 0.4.3 |
| Shuffle Skulltula House Rewards | On | 0.4.3 |
| Tokensanity | All Tokens, Dungeons Only, Overworld Only | 0.2.1, 0.3.1, 0.4.0, 0.4.3 |
| Maps & Compasses | Start With | 0.4.3 |
| Small Keys | Vanilla | 0.4.3 |
| Boss Keys | Vanilla | 0.4.3 |
| Item Pool | Balanced | 0.4.3 |
| Make All Cutscenes Skippable | On | 0.2.1, 0.4.3 |
| Bag Bombs Open Dodongo's Cavern | On | 0.3.1, 0.4.3 |
| Refills Need Their Item | On | 0.2.1, 0.4.3 |
| Anju Needs Only 1 Cucco | On | 0.2.1, 0.4.3 |
| Skip Kaepora Gaebora | On | 0.4.3 |
| Bombs Usable Without Goron Bracelet | On | 0.2.1, 0.4.3 |
| Small Chests Only | On | 0.4.3 |

Shuffle Kokiri Sword and Skip Area Intro Cutscenes were only tested with the setting off, so they stay
*experimental*.

**Partly working**

| Setting | Value tested | Version | Notes |
|---|---|---|---|
| Zora's Fountain (Open needs further testing) | Open | 0.4.3 | King Zora starts moved aside, but after leaving Jabu-Jabu's Belly and coming back he sits in front of the door again, which is a softlock (fix in 0.4.4, needs confirmation). In 0.3.1 he hadn't moved at all (fixed in 0.4.0). |

**Not working**

| Setting | Version | What happened |
|---|---|---|
| Load Saves at Dungeon Entrance | 0.2.1 | Never moved the restart point. Removed in 0.3.0. |
| Skip Area Intro Cutscenes (experimental) | 0.2.0 | The intros still play. Off by default. |

How each setting is implemented, and what the remake makes impossible (keysanity, scrubsanity and others), is
described in [docs/TECHNICAL.md](docs/TECHNICAL.md).

## Tools

### Item tracker

`Tools/OOTNS2-Tracker` is an item tracker for the remake. It shows items, songs, stones and medallions,
upgrades and counters (Gold Skulltulas, Pieces of Heart, keys) as a grid you click through while you play.

- **Left click** steps an item up a tier or adds 1, **right click** steps it back down. **Shift + click**
  on a counter steps by 5.
- **File** menu: New, Open, Save and Save As (JSON). The last save reopens when you start it.
- **No game files are included.** On first start it asks for the romfs folder you extracted from your own
  game and takes the item icons from it. The icons stay on your PC (`icons/` is never committed).

It needs Python 3.14 or newer and a Vulkan-capable graphics driver. To run it:

```
cd Tools/OOTNS2-Tracker
pip install -r requirements.txt
python tracker.pyw
```

More in [Tools/OOTNS2-Tracker/README.md](Tools/OOTNS2-Tracker/README.md).

## Supported game versions

The randomizer edits the game's data files, and their layout can change with a game update. To avoid making a
broken mod, it only runs on game versions it has been checked against. It computes the SHA-256 hash of
`exefs/main` and compares it with a list of known versions (`rando/gamecheck.py`).

| Game version | SHA-256 of `exefs/main` |
|---|---|
| 1.1.1 | `7db9ddfda088c22d219ef13496decd7077c68cd67d4b37f53f4ac46a082768f2` |

If your version isn't supported, the randomizer says so and won't generate. Your game is probably older or
newer than the one this release supports: update the game and the randomizer to their latest versions. If
you're on the latest of both, open an issue with the hash the randomizer shows.

## Known issues

- **Start a new save for every seed.**
- **Cutscene leftovers:** a chest that held a story item in the normal game may still play that item's
  follow-up dialogue, because the story flags are set inside those cutscenes.
- **Text box graphics** sometimes look garbled. The randomizer doesn't change any UI files, so this is most
  likely the emulator, but reports with screenshots are welcome.
- **The logic is cautious:** it may expect an item earlier than you strictly need it, so some items show up
  later than they could.
- Settings marked *experimental* are the least certain.
- **Zelda's Letter and the Cucco share a slot:** the remake keeps the child trade items in one slot, so while
  you're holding Zelda's Letter you can't use the Cucco from the Weird Egg. Show the letter to the Kakariko
  gate soldier first (with Open Death Mountain off). This is how the game works, so it can't be fixed.
- **Bag Bombs Open Dodongo's Cavern:** the cavern still plays its opening cutscene.

## Versions

Versions are `Major.Minor.Patch`, starting at **0.1.0**:

- **Minor** goes up when a new setting or feature is added (0.1.x to 0.2.0).
- **Patch** goes up for fixes to existing features (0.1.0 to 0.1.1).

The version is part of every seed: the same seed and settings string make a different mod in a different
version. Always say which version you used when you report a problem. It's shown in the window's title area,
in `settings.txt` and at the top of the checklist.

## Credits

- Settings and logic modelled on the classic [OoT Randomizer](https://ootrandomizer.com).
- GUI built with [Raven](https://github.com/oscar-soirey/Raven) (Apache-2.0).
- This is a fan project. It isn't affiliated with or endorsed by Nintendo. Use your own copy of the game.
