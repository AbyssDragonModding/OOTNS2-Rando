"""Manual test checklist for a seed: checklist.xlsx, laid out for Google Sheets / Excel:

  A-G   Seed info (version, seed, settings string, tester; A-B), setting totals (F-G), then the seed's settings:
        Category | Setting | Value | Expected In-Game | How to Test | Result | Notes
  H-I   empty spacer columns
  J-O   Check totals and then every randomized check, grouped by region:
        Region | Location | Vanilla Item | Randomized Item | Result | Notes

Result is a dropdown: "Pass" (green), "Partial" (orange), "Fail" (red) or empty (untested). Testers export the
filled-in sheet as CSV for bug reports; that CSV keeps this layout, so results can be read by column position.
"""
import os
import re

from . import settings as S
from .world import JUNK

SET_COLS = ["Category", "Setting", "Value", "Expected In-Game", "How to Test", "Result", "Notes"]
CHK_COLS = ["Region", "Location", "Vanilla Item", "Randomized Item", "Result", "Notes"]
GAP = 2                                     # empty columns between the two blocks
CHK_START = len(SET_COLS) + GAP             # 0-based column index of "Region" (column J)
INFO_ROWS = 5                               # rows 1-5: seed info, setting totals and check totals
SET_TOTALS = 5                              # setting totals: labels in column F, numbers in G
HEADER_ROW = INFO_ROWS + 2                  # row 7: column headers (row 6 is empty)
RESULTS = [("Pass", "Passed", "B7E1CD"), ("Partial", "Partial", "F9CB9C"), ("Fail", "Failed", "F4C7C3")]

# setting key -> function(value) -> (expected, how to test) or None when there is nothing to see in-game
SETTING_TESTS = {
    "open_forest": lambda v: {
        "closed": ("Kokiri boy blocks the exit until the Deku Tree is beaten", "Walk to the forest exit bridge before the Deku Tree"),
        "closed_deku": ("Exit open from the start; Mido still asks for sword + shield", "Leave the forest at once; talk to Mido without sword/shield"),
        "open": ("Exit open and Mido gone", "Leave the forest at once; walk straight to the Deku Tree")}[v],
    "open_zora": lambda v: ("King Zora already moved aside; Fountain + Jabu-Jabu reachable without Ruto's Letter",
                            "Go behind King Zora as child without the letter") if v == "open" else None,
    "open_door": lambda v: ("Door of Time starts open (Master Sword may still check story)",
                            "Enter the Temple of Time without stones / Song of Time; try the pedestal") if v == "open" else None,
    "open_dmt": lambda v: ("Kakariko's Death Mountain gate is open for child Link without Zelda's Letter",
                           "As child, walk up the Kakariko path to Death Mountain without the letter") if v else
                          ("The Kakariko gate soldier wants Zelda's Letter", "Show him the letter as child"),
    "skip_child_zelda": lambda v: ("New save already owns Zelda's, Malon's and Impa's items (see their Check rows); Malon and "
                                   "Talon are at Lon Lon Ranch; Hyrule Field has day and night; Zelda isn't in the courtyard",
                                   "Start a new save, check the pause menu, then visit Lon Lon Ranch and Hyrule Castle") if v else None,
    "shuffle_rewards": lambda v: {
        "vanilla": None,
        "reward": ("Bosses give a shuffled Spiritual Stone / Medallion", "Beat a boss; compare with the spoiler"),
        "anywhere": ("Bosses give random items; stones/medallions are found in other checks; the Door of Time "
                     "still opens after the three child dungeons", "Beat a boss; open a check holding a stone or medallion")}[v],
    "skip_epona_race": lambda v: ("Adult Epona comes when you play Epona's Song, without Ingo's race",
                                  "As adult with Epona's Song, play it in Hyrule Field") if v else None,
    "saria_song_ocarina": lambda v: ("Saria teaches her song in Sacred Forest Meadow with just an ocarina",
                                     "With an ocarina and before meeting Zelda, walk up to Saria on the stump") if v else
                                    ("Saria's Song needs meeting Zelda first", "Visit Saria before and after Zelda"),
    "shuffle_kokiri_sword": lambda v: (None if v else ("Kokiri Sword is in its normal chest", "Open the Kokiri Sword chest")),
    "shopsanity": lambda v: (("Some shop shelves sell randomized items (10-99 rupees); names and text match the item",
                              "Visit the Kokiri, Goron, Zora and Bombchu shops") if v != "off" else None),
    "shuffle_ocarinas": lambda v: (("No Saria goodbye / Fairy Ocarina on the forest bridge; ocarinas are found as checks",
                                     "Beat the Deku Tree and cross the forest bridge; check the spoiler for both ocarinas")
                                    if v else None),
    "shuffle_house": lambda v: ("All five Skulltula House rewards (10-50 tokens) are random; the two wallets are in chests "
                                "(the first gives the Adult's Wallet, the second the Giant's Wallet)",
                                "Turn in 10 tokens at the Skulltula House; open a chest holding a wallet") if v else None,
    "tokensanity": lambda v: (("Gold Skulltulas drop randomized items (%s)" % v, "Kill a Gold Skulltula") if v != "off" else None),
    "skip_cutscenes": lambda v: ("Every cutscene can be skipped (opening, credits too)", "Press the skip button in the opening") if v else None,
    "skip_area_intros": lambda v: ("First-arrival intros don't play: Kakariko, Graveyard, Hyrule Castle, Lake Hylia, "
                                   "Gerudo Valley/Fortress, Zora's River/Fountain, Ganon's Castle, Lost Woods (after Saria), "
                                   "Fire Temple / Well / Spirit Temple entrances",
                                   "Arrive in those areas for the first time on a new save") if v else None,
    "refill_needs_item": lambda v: ("Arrow / bomb / Bombchu / seed chests give a blue rupee without the Bow / Bomb Bag / Slingshot",
                                    "Open a refill chest (see Check rows) before owning its item") if v else None,
    "anju_one_cucco": lambda v: ("Anju's minigame finishes after returning 1 cucco", "Kakariko, child: return one cucco to the pen") if v else None,
    "free_bombs": lambda v: ("Bag bombs can be pulled out and thrown without the Goron Bracelet",
                             "Get a Bomb Bag before the bracelet; use a bomb") if v else
                            ("Bombs need the Goron Bracelet (logic gives the bracelet first)", "Check the bracelet is found before bombs are needed"),
    "small_chests": lambda v: ("Big chests (and Boss Key chests) are small chests and open with the short animation",
                               "Open a chest that is normally big, e.g. the Deku Tree Slingshot chest") if v else None,
}


# Region order on the sheet: roughly the order a run visits them. Keys are stage folders (display names come from
# the game's own text); the extra keys are for event checks whose area has no stage folder of its own here.
REGION_ORDER = [
    "KokiriForest", "LostWood", "SacredForestMeadow", "InsideTheDekuTree", "HyruleField", "Market", "TimeTemple",
    "HyruleCastle", "LonLonRanch", "KakarikoVillage", "Graveyard", "DeathMountainTrail", "GoronCity",
    "DeathMountainCrater", "DodongoCavern", "ZoraRiver", "ZoraDomain", "ZoraFountain", "InsideJabuJabuBelly",
    "LakeHylia", "BottomOfTheWell", "IceCavern", "ForestTemple", "FireTemple", "WaterTemple", "ShadowTemple",
    "GerudoValley", "GerudoFortress", "GerudoTrainingGround", "HountedWasteland", "DesertColossus", "SpiritTemple",
    "GanonCastle", "InsideGanonCastle",
]
EXTRA_REGION_NAMES = {"TimeTemple": "Temple of Time", "LonLonRanch": "Lon Lon Ranch", "LakeHylia": "Lake Hylia"}

# event checks (no stage of their own) -> region, by exact name first, then by name prefix
EVENT_REGION = {
    "Song from Impa": "HyruleCastle", "Song from Malon": "LonLonRanch", "Song from Saria": "SacredForestMeadow",
    "Song from Royal Familys Tomb": "Graveyard", "Song from Windmill": "KakarikoVillage",
    "Song from Ocarina of Time": "HyruleField", "Sheik in Forest": "SacredForestMeadow",
    "Sheik in Crater": "DeathMountainCrater", "Sheik in Ice Cavern": "IceCavern", "Sheik in Kakariko": "KakarikoVillage",
    "Sheik at Colossus": "DesertColossus", "Sheik at Temple": "TimeTemple",
    "Queen Gohma (Kokiri Emerald)": "InsideTheDekuTree", "King Dodongo (Goron Ruby)": "DodongoCavern",
    "Barinade (Zora Sapphire)": "InsideJabuJabuBelly", "Phantom Ganon (Forest Medallion)": "ForestTemple",
    "Volvagia (Fire Medallion)": "FireTemple", "Morpha (Water Medallion)": "WaterTemple",
    "Bongo Bongo (Shadow Medallion)": "ShadowTemple", "Twinrova (Spirit Medallion)": "SpiritTemple",
    "Rauru (Light Medallion)": "TimeTemple",
}
EVENT_PREFIX = [
    ("HF ", "HyruleField"), ("HC ", "HyruleCastle"), ("GC ", "GoronCity"), ("LW ", "LostWood"),
    ("Market ", "Market"), ("Kak ", "KakarikoVillage"), ("GF ", "GerudoFortress"), ("Hideout ", "GerudoFortress"),
    ("ZD ", "ZoraDomain"), ("ZR ", "ZoraRiver"), ("ZF ", "ZoraFountain"), ("ToT ", "TimeTemple"),
    ("LLR ", "LonLonRanch"), ("LH ", "LakeHylia"), ("Graveyard ", "Graveyard"), ("DMT ", "DeathMountainTrail"),
    ("DMC ", "DeathMountainCrater"), ("OGC ", "GanonCastle"), ("Colossus ", "DesertColossus"),
]


def _region_key(loc):
    if loc.region:
        return loc.region
    if loc.name in EVENT_REGION:
        return EVENT_REGION[loc.name]
    return next((key for pre, key in EVENT_PREFIX if loc.name.startswith(pre)), "Other")


def _natural(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


def _value_text(spec, value):
    kind, choices = spec[4], spec[5]
    if kind == "bool":
        return "On" if value else "Off"
    if kind == "choice":
        return dict(choices).get(value, str(value))
    if kind == "list":
        return ", ".join(value) if value else "(none)"
    return str(value)


def setting_rows(st):
    rows = []
    for key, value in st.items():
        spec = S.SPEC[key]
        test = SETTING_TESTS.get(key)
        expected, how = (test(value) if test else None) or ("", "")
        rows.append(["%s · %s" % (spec[1], spec[2]), spec[3], _value_text(spec, value), expected, how, "", ""])
    return rows


def check_rows(world, plan, filler):
    from .generator import refill_container
    st = S.normalize(plan.st)
    contents = filler.contents()
    order = {k: i for i, k in enumerate(REGION_ORDER)}
    names = dict(EXTRA_REGION_NAMES)

    def region_name(key):
        return world.region_text.get(key) or names.get(key) or world.region_name(key)

    rows = []
    for loc in plan.shuffled:
        item = contents.get(loc.id)
        if item is None:
            continue
        name = world.item_name(item)
        if loc.kind == "shop":
            name = "(normal shop goods)" if item == loc.vanilla or item in JUNK \
                else "%s (%d rupees)" % (name, plan.shop_prices[loc.id])
        need = refill_container(item) if st["refill_needs_item"] and loc.kind == "chest" else None
        if need:
            name += " (Blue Rupee without the %s)" % world.item_name(need.replace("Item_", ""))
        key = _region_key(loc)
        rows.append(((order.get(key, len(order)), _natural(loc.name)),
                     [region_name(key), loc.name, world.item_name(loc.vanilla), name, "", ""]))
    rows.sort(key=lambda r: r[0])
    return [r for _, r in rows]


def _totals(label, count, label_col, result_col):
    """Rows 1-5 of a block: count, passed, partial, failed, untested (formulas over the block's Result column)."""
    res = "%s%d:%s%d" % (_col(result_col), HEADER_ROW + 1, _col(result_col), HEADER_ROW + max(count, 1))
    val = _col(label_col + 1)
    rows = [[label, count]] + [[name, '=COUNTIF(%s,"%s")' % (res, value)] for value, name, _ in RESULTS]
    rows.append(["Untested", "=" + "-".join("%s%d" % (val, i + 1) for i in range(len(rows)))])
    return rows


def build_grid(world, plan, filler, version, seed, sstr):
    """The sheet as a list of rows (lists of cell values)."""
    srows = setting_rows(S.normalize(plan.st))
    crows = check_rows(world, plan, filler)
    info = [["Version", version], ["Seed", seed], ["Settings String", sstr], ["Emulator / Tester", ""], ["", ""]]
    totals = _totals("Checks", len(crows), CHK_START, CHK_START + 4)
    set_totals = _totals("Settings", len(srows), SET_TOTALS, SET_COLS.index("Result"))
    width = CHK_START + len(CHK_COLS)
    grid = [[""] * width for _ in range(HEADER_ROW + max(len(srows), len(crows)))]

    def put(r, c, values):
        grid[r][c:c + len(values)] = values

    for i in range(INFO_ROWS):
        put(i, 0, info[i])
        put(i, SET_TOTALS, set_totals[i])
        put(i, CHK_START, totals[i])
    put(HEADER_ROW - 1, 0, SET_COLS)
    put(HEADER_ROW - 1, CHK_START, CHK_COLS)
    for i, row in enumerate(srows):
        put(HEADER_ROW + i, 0, row)
    for i, row in enumerate(crows):
        put(HEADER_ROW + i, CHK_START, row)
    return grid, len(srows), len(crows)


def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def write_checklist(world, plan, filler, mod_root, version, seed, sstr):
    os.makedirs(mod_root, exist_ok=True)
    grid, n_set, n_chk = build_grid(world, plan, filler, version, seed, sstr)
    path = os.path.join(mod_root, "checklist.xlsx")
    _write_xlsx(grid, n_set, n_chk, path)      # needs openpyxl (requirements.txt); the caller reports ImportError
    return path


def _write_xlsx(grid, n_set, n_chk, path):
    from openpyxl import Workbook
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Checklist"
    for row in grid:
        ws.append(row)

    bold = Font(bold=True)
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F3A5F")
    label_fill = PatternFill("solid", fgColor="DCE6F1")
    bands = [PatternFill("solid", fgColor="FFFFFF"), PatternFill("solid", fgColor="EEF2F7")]
    wrap = Alignment(wrap_text=True, vertical="top")
    top = Alignment(vertical="top")
    group_line = Border(top=Side(style="thin", color="8DA2BC"))
    set_last, chk_last = HEADER_ROW + n_set, HEADER_ROW + n_chk
    chk = [_col(CHK_START + i) for i in range(len(CHK_COLS))]

    for r in range(1, INFO_ROWS + 1):                     # info / totals labels
        for c in ("A", _col(SET_TOTALS), chk[0]):
            if r == INFO_ROWS and c == "A":
                continue                                  # the seed info has one row fewer than the totals
            ws["%s%d" % (c, r)].font = bold
            ws["%s%d" % (c, r)].fill = label_fill
    ws["B4"].fill = PatternFill("solid", fgColor="FFF8DC")  # Emulator / Tester: for the tester to fill in
    for c in list(range(1, len(SET_COLS) + 1)) + list(range(CHK_START + 1, CHK_START + len(CHK_COLS) + 1)):
        cell = ws.cell(row=HEADER_ROW, column=c)
        cell.font, cell.fill = head_font, head_fill

    prev_cat = None                                       # settings: line between categories
    for r in range(HEADER_ROW + 1, set_last + 1):
        cat = ws["A%d" % r].value
        for c in range(1, len(SET_COLS) + 1):
            cell = ws.cell(row=r, column=c)
            cell.alignment = wrap if c in (4, 5, 7) else top
            if cat != prev_cat:
                cell.border = group_line
        prev_cat = cat

    band, prev = 1, None                                  # checks: alternate shading per region
    for r in range(HEADER_ROW + 1, chk_last + 1):
        region = ws["%s%d" % (chk[0], r)].value
        if region != prev:
            band ^= 1
        for i, c in enumerate(chk):
            cell = ws["%s%d" % (c, r)]
            cell.fill = bands[band]
            cell.alignment = wrap if i == 5 else top
            if region != prev:
                cell.border = group_line
        if region != prev:
            ws["%s%d" % (chk[0], r)].font = bold
        prev = region

    dv = DataValidation(type="list", formula1='"%s"' % ",".join(v for v, _, _ in RESULTS), allow_blank=True,
                        promptTitle="Result", prompt="Pass, Partial, Fail, or leave empty if not tested yet")
    ws.add_data_validation(dv)
    centred = Alignment(horizontal="center", vertical="center")
    for col, last in (("F", set_last), (chk[4], chk_last)):
        for r in range(HEADER_ROW, last + 1):            # header and dropdown cells centred both ways
            ws["%s%d" % (col, r)].alignment = centred
        rng = "%s%d:%s%d" % (col, HEADER_ROW + 1, col, max(last, HEADER_ROW + 1))
        dv.add(rng)
        for value, _, color in RESULTS:
            fill = PatternFill("solid", fgColor=color, bgColor=color)
            ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"%s"' % value], fill=fill))

    widths = {"A": 30, "B": 34, "C": 22, "D": 46, "E": 46, "F": 11, "G": 36, "H": 3, "I": 3}
    widths.update(dict(zip(chk, (24, 44, 26, 40, 11, 40))))
    for c, w in widths.items():
        ws.column_dimensions[c].width = w
    ws.freeze_panes = "A%d" % (HEADER_ROW + 1)
    ws.auto_filter.ref = "%s%d:%s%d" % (chk[0], HEADER_ROW, chk[-1], max(chk_last, HEADER_ROW))
    wb.save(path)
