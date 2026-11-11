# OoT Remake Randomizer

An item randomizer for the Switch 2 remake of *The Legend of Zelda: Ocarina of Time*. It shuffles chests,
songs, dungeon rewards, NPC rewards, shop items, Gold Skulltulas and more, and checks that every seed can be
beaten. The settings follow the classic [OoT Randomizer](https://ootrandomizer.com), adjusted to what the
remake allows.

**No game files are included.** The randomizer reads your own extracted game files (the `romfs`) and writes
only the files it changes into a new mod folder. Share seeds and settings strings, never mod folders.

><span style="display: flex; justify-content: center; color: red;">[WARNING]</span>
> **This randomizer is extremely early in development.** Expect bugs and broken logic: items that don't
> appear or can't be picked up, seeds that softlock or can't be finished, and settings that don't do what
> they say. Settings marked *experimental* are the least reliable. Don't play a seed you can't afford to
> abandon, and keep the spoiler log handy.
>
> Your test reports are what makes it better; see [Testing and reporting problems](#testing-and-reporting-problems).


[Disclamer] Yes claude was used with the production of this. It accelerates that type of stuff much faster. I know how to program, but something like this would take days or weeks instead of a few hours
=======

## Contents

- [What you need](#what-you-need)
- [Setup (Windows)](#setup-windows)
- [Making a seed](#making-a-seed)
- [Installing the seed in your emulator](#installing-the-seed-in-your-emulator)
- [Testing and reporting problems](#testing-and-reporting-problems)
- [Settings](#settings)
- [Supported game versions](#supported-game-versions)
- [Known issues](#known-issues)
- [Versions](#versions)
- [Credits](#credits)

## What you need

- A PC with a graphics driver that supports **Vulkan** (any recent NVIDIA, AMD or Intel driver).
- **Python 3.14 or newer.** The setup steps below cover installing it.
- **Your own extracted romfs and exefs** of the game. The romfs is the folder that contains `Banc`, `Event`,
  `Pack`, `RSDB`, `System` and so on; the exefs contains `main` and `main.npdm`. Most Switch emulators can
  extract both: right-click the game in the game list and choose the *Extract RomFS* / *Dump RomFS* and
  *Extract ExeFS* / *Dump ExeFS* options. Keeping them side by side (`<game>/romfs` and `<game>/exefs`) lets
  the randomizer find the exefs by itself.
- **A supported game version.** See [Supported game versions](#supported-game-versions).

## Setup (Windows)

You only do this once. Nothing here needs the command line.

### 1. Install Python

1. Go to [python.org/downloads](https://www.python.org/downloads/) and click the **Download Python 3.14**
   button (any newer version works too).
2. Run the installer you downloaded.
3. On the first screen, **tick "Add python.exe to PATH"** at the bottom, then click **Install Now**.
4. When it says "Setup was successful", click **Close**.

Use the installer from python.org rather than the Microsoft Store version. The python.org installer also sets
up double-clicking `.pyw` files, which is how the randomizer is started.

### 2. Download the randomizer

1. On this repository's GitHub page, click the green **Code** button, then **Download ZIP**.
2. Right-click the downloaded ZIP and choose **Extract All...**. Put the folder anywhere you like, but **not
   inside your romfs folder**.

Don't run the randomizer from inside the ZIP; Windows only extracts it to a temporary folder.

### 3. Install the requirements

Open the extracted folder and **double-click `Install Requirements.bat`**. A black window opens and installs
the two packages listed in `requirements.txt`:

| Package | Used for |
|---|---|
| `raven-gui` | The randomizer's window (the GUI) |
| `openpyxl` | Writing `checklist.xlsx`, the formatted test checklist |

Wait for "Done", then press any key to close the window. Run it again whenever you download a new version of
the randomizer.

If Windows shows "Windows protected your PC", click **More info** and then **Run anyway**. The file is a short
text script; you can right-click it and choose **Edit** to read it first.

### 4. Start the randomizer

**Double-click `ootr_remake.pyw`.** The randomizer window opens.

- **It opens in Notepad, or Windows asks which app to use:** right-click `ootr_remake.pyw`, choose **Open with**
  > **Choose another app**, pick **Python** (the icon with the rocket, "pythonw"), tick **Always use this app**
  and click **OK**.
- **A message box says something is missing:** do what it says (usually run `Install Requirements.bat` again).
- **It crashes:** the message box names an `error_log.txt` file in the randomizer folder. Attach it when you
  report the problem.
- **For a desktop shortcut:** right-click `ootr_remake.pyw` > **Show more options** > **Send to** >
  **Desktop (create shortcut)**.

### macOS and Linux

These aren't tested. Install Python 3.14+ and a Vulkan driver, then run these once in a terminal opened in the
randomizer folder:

```bash
python3 -m pip install -r requirements.txt
```

```bash
python3 ootr_remake.pyw
```

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
    checklist.xlsx    <- test checklist with Pass/Fail dropdowns and colours
    checklist.csv     <- the same checklist as plain text
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

Every seed with a spoiler log comes with a test checklist: `checklist.xlsx` (recommended) and
`checklist.csv` (the same data without formatting). It has two blocks side by side.

**Left block (columns A–G): the seed and its settings**

| Rows / column | What it is |
|---|---|
| Version, Seed, Settings String | The seed's identity. Copy these into bug reports. |
| Emulator / Tester | Fill this in yourself: emulator name and version, and your name if you like |
| Settings, Passed, Failed, Untested | Running totals for the settings, next to the seed info; they update as you fill in Result |
| **Category**, **Setting**, **Value** | Every setting this seed uses, grouped by tab |
| **Expected In-Game** | What the setting should do in the game (blank when there's nothing to see) |
| **How to Test** | A quick way to check it |
| **Result** | `Pass`, `Fail`, or empty if you haven't tested it |
| **Notes** | What you saw, especially for anything that failed |

**Right block (columns J–O): the checks**

| Rows / column | What it is |
|---|---|
| Checks, Passed, Failed, Untested | Running totals; they update as you fill in Result |
| **Region** | The area, e.g. Kokiri Forest. Checks are grouped by region in roughly the order you visit them. |
| **Location** | The check's name (the same name as in the spoiler) |
| **Vanilla Item** | What's there in the normal game |
| **Randomized Item** | What should be there in this seed. Shop items show their price. Ammo chests note when they give a Blue Rupee instead because you don't have the matching bag yet. |
| **Result** | `Pass`, `Fail`, or empty |
| **Notes** | What happened |

**Result** uses a Pass/Fail dropdown rather than a checkbox. A checkbox only has two states, so "not tested
yet" would look the same as "failed". In `checklist.xlsx`, picking **Pass** turns the cell green and **Fail**
turns it red.

### Opening the checklist in Google Sheets

**With `checklist.xlsx` (dropdowns and colours included):**

1. Go to [sheets.google.com](https://sheets.google.com) and open a **Blank spreadsheet**.
2. Choose **File** > **Import** > **Upload**, and drop in `checklist.xlsx`.
3. Set **Import location** to **Replace spreadsheet** and click **Import data**.
4. Rename the spreadsheet (top left) to the seed, e.g. `OoTR 0.2.0 U5R6C3SVEJ`.

**With `checklist.csv`:**

1. Import it the same way, with **Replace spreadsheet** and **Separator type: Detect automatically**. Leave
   **Convert text to numbers, dates, and formulas** ticked, so the totals work.
2. Add the dropdown: select the Result cells (`N7` down to the last check, and `F7` down to the last setting),
   choose **Insert** > **Dropdown**, and enter the two options `Pass` and `Fail`.
3. Add the colours: with the same cells selected, choose **Format** > **Conditional formatting**. Set
   **Format cells if...** to **Text is exactly**, type `Pass` and pick a green fill. Click **Add another
   rule** and do the same with `Fail` and a red fill.

Excel and LibreOffice open both files directly as well.

Tips while playing:
- **Data** > **Create a filter** on the checks block lets you show one region, or only failed checks.
- You don't have to test everything. A few checks in each region you visit, and every setting you can see
  in-game, already help a lot.
- For anything that fails, write what happened in **Notes**: the item didn't appear, couldn't be picked up,
  wrong item or text, came back after leaving or reloading, softlock, or crash. Mention what you were doing
  and which items you had, if it seems relevant.

### Exporting your results

When you're done (or when something breaks):

1. In Google Sheets, choose **File** > **Download** > **Comma Separated Values (.csv)**. This downloads the
   checklist with your results and notes. In Excel, use **File** > **Save As** > **CSV UTF-8**.
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
| **Main Rules** | Logic (glitchless or none); open Kokiri Forest, Zora's Fountain and the Door of Time; skip Epona's race; Saria's Song with just an ocarina; what gets shuffled: songs, dungeon rewards, Kokiri Sword, Weird Egg, ocarinas, freestanding items, freestanding rupees, boss Heart Containers, NPC and minigame rewards, Great Fairies, Skulltula House rewards, Gold Skulltula tokens (Tokensanity) and shop items (Shopsanity) |
| **Dungeon Items** | Maps & Compasses (vanilla, own dungeon, removed or start with), small keys and boss keys |
| **Other** | Item pool size; quality of life (skippable cutscenes, no area intros (experimental), bombs without the Goron Bracelet, bag bombs open Dodongo's Cavern, Anju needs 1 cucco, ammo chests need their bag, load saves at the dungeon entrance); spoiler log |
| **Exclusions** | Locations that only ever hold minor items |
| **Not Supported** | Classic randomizer options the remake's data can't support yet, and why |

Settings marked **experimental** work in offline checks but haven't been confirmed in a full playthrough.
These are the ones most worth testing.

How each setting is implemented, and what the remake makes impossible (keysanity, scrubsanity and others), is
described in [docs/TECHNICAL.md](docs/TECHNICAL.md).

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
