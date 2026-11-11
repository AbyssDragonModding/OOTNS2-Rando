"""Alternate "glass" GUI built with Raven (https://github.com/oscar-soirey/Raven).

Install the Python bindings first:   pip install raven-gui
Started by ootr_remake.pyw.
"""
import json
import math
import os
import queue
import random
import struct
import subprocess
import sys
import threading
import traceback
import zlib

import raven as r

from . import settings as S
from . import gamecheck
from .generator import VERSION, generate

CONFIG = os.path.join(os.path.expanduser("~"), ".ootr_remake.json")
ACCENT = (0.36, 0.80, 0.56)          # Kokiri green
GOLD = (0.96, 0.80, 0.38)            # Triforce gold for headings
MUTED = (0.78, 0.82, 0.86, 0.85)
OK_GREEN = (0.40, 0.86, 0.52)
BAD_RED = (0.96, 0.46, 0.44)


# --------------------------------------------------------------------------- wallpaper
def _wallpaper_png(w=640, h=420):
    """Procedural night-sky gradient with soft glows, made at runtime (no image files shipped).
    Glass materials blur and refract this, which gives the frosted look."""
    glows = [(0.18, 0.22, 0.42, (34, 168, 116)),   # forest green
             (0.84, 0.18, 0.34, (214, 168, 64)),   # gold
             (0.62, 0.92, 0.46, (58, 92, 210)),    # lake blue
             (0.05, 0.95, 0.30, (120, 60, 170))]   # twilight purple
    rows = bytearray()
    for y in range(h):
        rows.append(0)
        v = y / h
        for x in range(w):
            u = x / w
            c = [10 + 8 * v, 16 + 10 * (1 - v), 30 + 22 * v]
            for gx, gy, rad, col in glows:
                d = math.hypot(u - gx, (v - gy) * h / w) / rad
                k = max(0.0, 1.0 - d) ** 2 * 0.6
                c = [c[i] * (1 - k) + col[i] * k for i in range(3)]
            rows += bytes(int(min(255, max(0, q))) for q in c)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 6)) + chunk(b"IEND", b""))


# --------------------------------------------------------------------------- small layout helpers
def vbox(spacing=8):
    w = r.Rwidget_create(r.R_WIDGET_VBOX)
    r.Rpanel_set_spacing(w, spacing)
    return w


def hbox(spacing=8):
    w = r.Rwidget_create(r.R_WIDGET_HBOX)
    r.Rpanel_set_spacing(w, spacing)
    return w


def add(parent, child, fill=None, pad=None):
    r.Rwidget_add_child(parent, child)
    if fill is not None:
        r.Rslot_set_fill(child, fill)
    else:
        r.Rslot_set_auto(child)
    if pad:
        r.Rslot_set_padding(child, *pad)
    return child


def label(text, size=None, color=None, wrap=False):
    w = r.Rlabel_create(text)
    if size:
        r.Rlabel_set_text_size(w, size)
    if color:
        r.Rlabel_set_color(w, *(color if len(color) == 4 else color + (1.0,)))
    if wrap:
        r.Rlabel_set_wrap(w, 1)
    return w


def card(title=None, material=r.R_MATERIAL_FROSTED_GLASS):
    """A rounded glass panel; returns (border, inner vbox)."""
    b = r.Rwidget_create(r.R_WIDGET_BORDER)
    r.Rborder_set_material(b, material)
    r.Rborder_set_corner_radius(b, 16, 16, 16, 16)
    r.Rborder_set_padding(b, 18, 14, 18, 16)
    r.Rborder_set_shadow(b, 18, 0, 4)
    inner = vbox(10)
    r.Rwidget_add_child(b, inner)
    if title:
        add(inner, label(title, 16, GOLD))
    return b, inner


def text_input(placeholder="", text=""):
    w = r.Rwidget_create(r.R_WIDGET_TEXT_INPUT)
    if placeholder:
        r.Rtext_input_set_placeholder(w, placeholder)
    if text:
        r.Rtext_input_set_text(w, text)
    return w


def button(text, cb, primary=False, flat=False):
    w = r.Rbutton_create(text)
    if primary:
        r.Rbutton_set_style(w, r.R_BUTTON_PRIMARY)
    elif flat:
        r.Rbutton_set_style(w, r.R_BUTTON_FLAT)
    r.Rbutton_set_clicked_callback(w, lambda b, ud: cb())
    return w


# --------------------------------------------------------------------------- app
class GlassApp:
    TABS = ["ROM Options", "Main Rules", "Dungeon Items", "Other", "Exclusions", "Not Supported"]

    def __init__(self):
        if not r.Rinit(r.R_BACKEND_VULKAN):
            raise RuntimeError("Raven could not start (a Vulkan driver is required).")
        r.Rlook_set(r.R_LOOK_RAVEN_GLASS_DARK)
        r.Rtheme_set_dark(1)
        r.Rtheme_set_accent(*ACCENT)
        r.Rtheme_set_material(r.R_MATERIAL_FROSTED_GLASS)
        tex = r.Rtexture_create(_wallpaper_png())
        if tex != r.R_INVALID_ID:
            r.Rtheme_set_wallpaper(tex)

        cfg = self._load_config()
        self.st = S.normalize(cfg.get("settings", {}))
        self.excluded = set(self.st["excluded_locations"])
        self.paths = {"romfs": cfg.get("romfs", ""), "exefs": cfg.get("exefs", ""), "out": cfg.get("out", ""),
                      "name": "", "seed": ""}
        self.game = None             # last gamecheck.GameCheck result
        self.queue = queue.Queue()
        self.busy = False
        self.world = None
        self.world_path = None
        self.locations = []          # all location names (from the scan)
        self.visible = []            # names currently shown in the exclusion list
        self.filter = ""
        self.log_lines = []
        self.controls = {}           # setting key -> widget
        self._phase = 0.0

        self.window = r.Rwindow_create("OoT Remake Randomizer", 1000, 800, r.R_WINDOW_DEFAULT)
        self._build()
        r.Rwindow_set_content(self.window, self.root)
        r.Rwindow_show(self.window)
        self._timer = r.Rtimer_create(0.1, r.R_TRUE, self._poll)

    # ------------------------------------------------------------------ build
    def _build(self):
        self.root = vbox(14)
        head = add(self.root, hbox(12), pad=(24, 18, 24, 0))
        titles = add(head, vbox(2), fill=1.0)
        add(titles, label("Ocarina of Time Randomizer", 28))
        add(titles, label("Switch 2 remake edition  ·  v%s  ·  your romfs, your mod" % VERSION, 13, MUTED))
        folder_btn = add(head, button("  Open Folder  ", self.open_output))
        r.Rslot_set_valign(folder_btn, r.R_VALIGN_CENTER)
        r.Rwidget_set_tooltip(folder_btn, "Open the output folder, where your generated seeds are")
        self.gen_btn = add(head, button("  Generate Mod  ", self.generate, primary=True))
        r.Rslot_set_valign(self.gen_btn, r.R_VALIGN_CENTER)

        tabs = add(self.root, r.Rwidget_create(r.R_WIDGET_TAB_VIEW), fill=1.0, pad=(18, 0, 18, 0))
        self.tabs = tabs
        pages = {}
        for t in self.TABS:
            if t == "Exclusions":
                page = vbox(12)
            else:
                scroll = r.Rwidget_create(r.R_WIDGET_SCROLL_BOX)
                r.Rscroll_box_set_orientation(scroll, r.R_VERTICAL)
                page = vbox(14)
                r.Rwidget_add_child(scroll, page)
                r.Rtab_view_add_tab(tabs, t, scroll)
                pages[t] = page
                continue
            r.Rtab_view_add_tab(tabs, t, page)
            pages[t] = page
        self._build_rom(pages["ROM Options"])
        self._build_settings(pages)
        self._build_exclusions(pages["Exclusions"])
        self._build_unsupported(pages["Not Supported"])
        self._build_footer()
        self._verify_game()

    def _row(self, parent, text, control, tip=None, control_fill=1.0):
        row = add(parent, hbox(12))
        lab = add(row, label(text, 14), fill=1.0)
        r.Rslot_set_valign(lab, r.R_VALIGN_CENTER)
        add(row, control, fill=control_fill)
        if tip:
            r.Rwidget_set_tooltip(lab, tip)
            r.Rwidget_set_tooltip(control, tip)
        return row

    def _build_rom(self, page):
        b, c = card("Game files")
        add(page, b, pad=(6, 10, 6, 0))
        self.romfs_in = text_input("Extracted romfs folder (contains Banc, Event, Pack, RSDB, System...)", self.paths["romfs"])
        self.exefs_in = text_input("blank = the exefs folder next to the romfs folder", self.paths["exefs"])
        self.out_in = text_input("Folder the mod package is written to", self.paths["out"])
        for key, ti, title, text in (("romfs", self.romfs_in, "Select the extracted romfs folder", "romfs folder"),
                                     ("exefs", self.exefs_in, "Select the extracted exefs folder", "exefs folder"),
                                     ("out", self.out_in, "Select the output folder", "Output folder")):
            row = add(c, hbox(10))
            r.Rslot_set_valign(add(row, label(text, 14), fill=0.35), r.R_VALIGN_CENTER)
            add(row, ti, fill=1.0)
            add(row, button("Browse", lambda k=key, t=ti, tt=title: self._browse(k, t, tt)))
            r.Rtext_input_set_changed_callback(ti, lambda w, text, ud, k=key: self._path_changed(k, text))
            if key == "romfs":
                self.hash_lab = add(c, label("exefs/main SHA-256: -", 12, MUTED), pad=(0, 0, 0, 2))
                r.Rlabel_set_selectable(self.hash_lab, 1)
                r.Rwidget_set_tooltip(self.hash_lab, "Hash of your game's executable, used to identify the game "
                                                     "version. Select it to copy it into a bug report.")
            if key == "exefs":
                self.game_lab = add(c, label("Checking game version...", 13, MUTED, wrap=True), pad=(0, 0, 0, 4))
                r.Rwidget_set_tooltip(self.game_lab, "The randomizer only runs on game versions it is known to work "
                                                     "with. It checks the SHA-256 hash of exefs/main.")
        add(c, button("Scan romfs  —  check the folder and load the location list", self.scan, flat=True))

        b, c = card("Seed")
        add(page, b, pad=(6, 0, 6, 0))
        self.name_in = text_input("blank = OoTR_Remake_<seed>")
        self.seed_in = text_input("blank = random")
        row = add(c, hbox(10))
        r.Rslot_set_valign(add(row, label("Mod folder name", 14), fill=0.35), r.R_VALIGN_CENTER)
        add(row, self.name_in, fill=1.0)
        row = add(c, hbox(10))
        r.Rslot_set_valign(add(row, label("Seed", 14), fill=0.35), r.R_VALIGN_CENTER)
        add(row, self.seed_in, fill=1.0)
        add(row, button("Random", self._random_seed))
        r.Rtext_input_set_changed_callback(self.name_in, lambda w, t, ud: self.paths.__setitem__("name", t))
        r.Rtext_input_set_changed_callback(self.seed_in, lambda w, t, ud: self.paths.__setitem__("seed", t))

        b, c = card("How it works")
        add(page, b, pad=(6, 0, 6, 10))
        add(c, label("The generator reads what it needs from your own romfs, changes the item placements and writes "
                     "only the changed files into <output>/<mod name>/romfs. Install that folder as a layered mod "
                     "(emulator: .../mods/contents/<title id>/<mod name>/romfs, console: atmosphere/contents). "
                     "Nothing from the game is bundled with this program — share settings strings, not mod folders.",
                     13, MUTED, wrap=True))

    def _build_settings(self, pages):
        groups = {}
        for key, tab, group, text, typ, opts, default, tip in S.SETTINGS:
            if typ == "list":
                continue
            if (tab, group) not in groups:
                b, c = card(group)
                add(pages[tab], b, pad=(6, 10 if not any(g[0] == tab for g in groups) else 0, 6, 0))
                groups[(tab, group)] = c
            c = groups[(tab, group)]
            if typ == "bool":
                w = r.Rcheckbox_create(text)
                r.Rcheckbox_set_style(w, r.R_CHECKBOX_SWITCH)
                r.Rcheckbox_set_checked(w, 1 if self.st[key] else 0)
                r.Rcheckbox_set_changed_callback(w, lambda cb, checked, ud, k=key: self._set(k, bool(checked)))
                add(c, w)
                r.Rwidget_set_tooltip(w, tip)
            else:
                w = r.Rwidget_create(r.R_WIDGET_COMBO_BOX)
                for _v, t in opts:
                    r.Rcombo_box_add_item(w, t)
                idx = next((i for i, o in enumerate(opts) if o[0] == self.st[key]), 0)
                r.Rcombo_box_set_selected(w, idx)
                r.Rcombo_box_set_changed_callback(
                    w, lambda cb, i, ud, k=key, o=opts: self._set(k, o[i][0]) if 0 <= i < len(o) else None)
                self._row(c, text, w, tip, control_fill=0.9)
            self.controls[key] = w

    def _build_exclusions(self, page):
        b, c = card("Excluded locations")
        add(page, b, fill=1.0, pad=(6, 10, 6, 10))
        add(c, label("Excluded locations never hold progression or dungeon items (only rupees, ammo, hearts). Double-click a location to toggle it. "
                     "Scan the romfs on the ROM Options tab to fill this list.", 13, MUTED, wrap=True))
        row = add(c, hbox(10))
        self.filter_in = add(row, text_input("Filter locations..."), fill=1.0)
        r.Rtext_input_set_changed_callback(self.filter_in, lambda w, t, ud: self._apply_filter(t))
        self.excl_count = add(row, label("", 13, MUTED))
        r.Rslot_set_valign(self.excl_count, r.R_VALIGN_CENTER)
        add(row, button("Clear all", self._clear_excluded, flat=True))
        self.excl_list = add(c, r.Rwidget_create(r.R_WIDGET_LIST_VIEW), fill=1.0)
        r.Rlist_view_set_activated_callback(self.excl_list, lambda lv, i, ud: self._toggle_excluded(i))
        self._update_excl_count()

    def _build_unsupported(self, page):
        b, c = card("Classic options not available for the remake yet")
        add(page, b, pad=(6, 10, 6, 10))
        for name, why in S.UNSUPPORTED:
            add(c, label("•  " + name, 14))
            add(c, label(why, 13, MUTED, wrap=True), pad=(20, 0, 0, 6))

    def _build_footer(self):
        b, c = card(None, r.R_MATERIAL_TINTED_GLASS)
        add(self.root, b, pad=(18, 0, 18, 18))
        row = add(c, hbox(10))
        r.Rslot_set_valign(add(row, label("Settings string", 14), fill=0.25), r.R_VALIGN_CENTER)
        self.sstr_in = add(row, text_input(), fill=1.0)
        add(row, button("Import", self._import_string))
        add(row, button("Copy", self._copy_string))
        add(row, button("Reset", lambda: self._apply_settings(S.normalize({})), flat=True))
        self.progress = add(c, r.Rwidget_create(r.R_WIDGET_PROGRESSBAR))
        r.Rprogress_bar_set_value(self.progress, 0.0)
        self.log = add(c, r.Rwidget_create(r.R_WIDGET_LIST_VIEW), fill=1.0)
        r.Rslot_set_max_size(self.log, 130)
        self._refresh_string()
        self.write("Ready. Pick your romfs and an output folder, then Generate.")

    # ------------------------------------------------------------------ settings
    def _set(self, key, value):
        self.st[key] = value
        self._refresh_string()

    def current_settings(self):
        st = dict(self.st)
        st["excluded_locations"] = sorted(self.excluded)
        return S.normalize(st)

    def _apply_settings(self, st):
        self.st = S.normalize(st)
        self.excluded = set(self.st["excluded_locations"])
        for key, w in self.controls.items():
            spec = S.SPEC[key]
            if spec[4] == "bool":
                r.Rcheckbox_set_checked(w, 1 if self.st[key] else 0)
            else:
                idx = next((i for i, o in enumerate(spec[5]) if o[0] == self.st[key]), 0)
                r.Rcombo_box_set_selected(w, idx)
        self._fill_exclusions()
        self._refresh_string()

    def _refresh_string(self):
        r.Rtext_input_set_text(self.sstr_in, S.to_string(self.current_settings())) if hasattr(self, "sstr_in") else None

    def _import_string(self):
        try:
            self._apply_settings(S.from_string(r.Rtext_input_get_text(self.sstr_in) or ""))
            self.write("Settings imported.")
        except Exception as e:
            r.Rmessage_box(self.window, "Invalid settings string", str(e), r.R_MESSAGE_OK)

    def _copy_string(self):
        self._refresh_string()
        r.Rclipboard_set_text(r.Rtext_input_get_text(self.sstr_in))
        self.write("Settings string copied to clipboard.")

    # ------------------------------------------------------------------ exclusions
    def _apply_filter(self, text):
        self.filter = (text or "").lower()
        self._fill_exclusions()

    def _fill_exclusions(self):
        if not hasattr(self, "excl_list"):
            return
        self.visible = [n for n in self.locations if self.filter in n.lower()]
        r.Rlist_view_clear_items(self.excl_list)
        for n in self.visible:
            r.Rlist_view_add_item(self.excl_list, self._excl_text(n))
        self._update_excl_count()

    def _excl_text(self, name):
        return ("✖  " if name in self.excluded else "      ") + name

    def _toggle_excluded(self, index):
        if not 0 <= index < len(self.visible):
            return
        n = self.visible[index]
        self.excluded.symmetric_difference_update({n})
        r.Rlist_view_set_item_text(self.excl_list, index, self._excl_text(n))
        self._update_excl_count()
        self._refresh_string()

    def _clear_excluded(self):
        self.excluded.clear()
        self._fill_exclusions()
        self._refresh_string()

    def _update_excl_count(self):
        r.Rlabel_set_text(self.excl_count, "%d excluded" % len(self.excluded))

    # ------------------------------------------------------------------ actions
    def _browse(self, key, ti, title):
        desc = r.RFileDialogDesc()
        desc.parent = self.window
        desc.title = title.encode("utf-8")
        cur = self.paths.get(key) or ""
        if os.path.isdir(cur):
            desc.directory = cur.encode("utf-8")
        path = r.Rfile_dialog_select_folder(desc)
        if path:
            r.Rtext_input_set_text(ti, path)
            self._path_changed(key, path)

    def _path_changed(self, key, text):
        self.paths[key] = text
        if key in ("romfs", "exefs"):
            self._verify_game()

    def _verify_game(self):
        """Hash exefs/main and show the result under the exefs row (green = supported)."""
        romfs = (r.Rtext_input_get_text(self.romfs_in) or "").strip()
        exefs = (r.Rtext_input_get_text(self.exefs_in) or "").strip()
        try:
            self.game = gamecheck.check(exefs, romfs)
        except OSError as e:
            self.game = gamecheck.GameCheck(False, "missing", "Couldn't read the exefs: %s" % e)
        g = self.game
        if g.ok:
            where = "" if exefs else "  (found next to the romfs folder)"
            text, color = g.message + where, OK_GREEN
        elif g.status == "missing":
            text, color = g.message, MUTED
        else:
            text, color = g.message.split("\n")[0], BAD_RED
        r.Rlabel_set_text(self.game_lab, text)
        r.Rlabel_set_color(self.game_lab, *(color if len(color) == 4 else color + (1.0,)))
        r.Rlabel_set_text(self.hash_lab, "exefs/main SHA-256: %s" % (g.sha256 or "-"))
        hcolor = color if g.sha256 else MUTED
        r.Rlabel_set_color(self.hash_lab, *(hcolor if len(hcolor) == 4 else hcolor + (1.0,)))
        return g

    def _require_game(self):
        g = self._verify_game()
        if not g.ok:
            r.Rmessage_box(self.window, "Game version not supported" if g.status != "missing" else "exefs not found",
                           g.message, r.R_MESSAGE_OK)
        return g.ok

    def open_output(self):
        out = (r.Rtext_input_get_text(self.out_in) or "").strip()
        if not out or not os.path.isdir(out):
            r.Rmessage_box(self.window, "Output", "The output folder doesn't exist yet.\n"
                                                  "Choose one on the ROM Options tab, or generate a seed first.",
                           r.R_MESSAGE_OK)
            return
        try:
            if sys.platform == "win32":
                os.startfile(out)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", out])
        except OSError as e:
            r.Rmessage_box(self.window, "Output", "Couldn't open the folder:\n%s" % e, r.R_MESSAGE_OK)

    def _random_seed(self):
        s = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(10))
        r.Rtext_input_set_text(self.seed_in, s)
        self.paths["seed"] = s

    def _check_paths(self, need_out=True):
        romfs = (r.Rtext_input_get_text(self.romfs_in) or "").strip()
        out = (r.Rtext_input_get_text(self.out_in) or "").strip()
        if not romfs or not os.path.isfile(os.path.join(romfs, "Pack", "ZsDic.pack.zs")) \
                or not os.path.isdir(os.path.join(romfs, "Banc")):
            r.Rmessage_box(self.window, "romfs", "That folder does not look like the game's extracted romfs\n"
                                                 "(expected Pack/ZsDic.pack.zs and a Banc folder).", r.R_MESSAGE_OK)
            return None
        if need_out:
            if not out:
                r.Rmessage_box(self.window, "Output", "Choose an output folder.", r.R_MESSAGE_OK)
                return None
            ar, ao = os.path.abspath(romfs), os.path.abspath(out)
            if os.path.splitdrive(ar)[0].lower() == os.path.splitdrive(ao)[0].lower() and \
                    os.path.commonpath([ar, ao]) == ar:
                r.Rmessage_box(self.window, "Output", "The output folder must not be inside the romfs folder.",
                               r.R_MESSAGE_OK)
                return None
        return romfs, out

    def scan(self):
        paths = self._check_paths(need_out=False)
        if paths and self._require_game():
            self._run_bg(lambda: self._ensure_world(paths[0]), "Scan complete.")

    def _ensure_world(self, romfs):
        from .world import World
        if self.world is None or self.world_path != romfs:
            self.world = World(romfs, progress=lambda m: self.queue.put(("log", m)))
            self.world_path = romfs
            self.queue.put(("locations", sorted(l.name for l in self.world.locations)))
            self.queue.put(("log", "Found %d item locations." % len(self.world.locations)))

    def generate(self):
        paths = self._check_paths()
        if not paths or not self._require_game():
            return
        exefs = self.game.exefs
        romfs, out = paths
        st = self.current_settings()
        seed = (r.Rtext_input_get_text(self.seed_in) or "").strip() or None
        name = (r.Rtext_input_get_text(self.name_in) or "").strip() or None
        self._save_config(st, romfs, out)

        def job():
            self._ensure_world(romfs)
            res = generate(romfs, out, st, seed=seed, mod_name=name, world=self.world, exefs=exefs,
                           progress=lambda m: self.queue.put(("log", m)))
            self.queue.put(("done", res))
        self._run_bg(job, None)

    def _run_bg(self, fn, done_msg):
        if self.busy:
            return
        self.busy = True
        r.Rwidget_set_enabled(self.gen_btn, 0)

        def wrap():
            try:
                fn()
                if done_msg:
                    self.queue.put(("log", done_msg))
            except Exception as e:
                self.queue.put(("error", "%s\n\n%s" % (e, traceback.format_exc())))
            finally:
                self.queue.put(("idle", None))
        threading.Thread(target=wrap, daemon=True).start()

    # ------------------------------------------------------------------ UI-thread pump
    def _poll(self, timer, ud):
        if self.busy:                                   # gentle back-and-forth "working" bar
            self._phase += 0.08
            r.Rprogress_bar_set_value(self.progress, 0.5 + 0.5 * math.sin(self._phase))
        try:
            while True:
                kind, val = self.queue.get_nowait()
                if kind == "log":
                    self.write(val)
                elif kind == "locations":
                    self.locations = val
                    self._fill_exclusions()
                elif kind == "done":
                    r.Rtext_input_set_text(self.seed_in, val["seed"])
                    r.Rprogress_bar_set_value(self.progress, 1.0)
                    self.write("Seed %s written to %s" % (val["seed"], val["mod_root"]))
                    r.Rmessage_box(self.window, "Mod created", "%s\n\nSettings string:\n%s" % (
                        val["mod_root"], val["settings_string"]), r.R_MESSAGE_OK)
                elif kind == "error":
                    self.write("ERROR: " + val.splitlines()[0])
                    r.Rprogress_bar_set_value(self.progress, 0.0)
                    r.Rmessage_box(self.window, "Generation failed", val[:2000], r.R_MESSAGE_OK)
                elif kind == "idle":
                    self.busy = False
                    r.Rwidget_set_enabled(self.gen_btn, 1)
        except queue.Empty:
            pass

    def write(self, msg):
        self.log_lines.append(msg)
        r.Rlist_view_add_item(self.log, msg)
        n = r.Rlist_view_get_item_count(self.log)
        if n > 400:
            r.Rlist_view_remove_item(self.log, 0)
            n -= 1
        r.Rlist_view_scroll_to_item(self.log, n - 1)

    # ------------------------------------------------------------------ config (shared with the classic GUI)
    def _load_config(self):
        try:
            with open(CONFIG, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save_config(self, st, romfs, out):
        try:
            with open(CONFIG, "w", encoding="utf-8") as fh:
                json.dump({"romfs": romfs, "exefs": self.paths.get("exefs", ""), "out": out, "settings": st}, fh, indent=1)
        except Exception:
            pass

    def run(self):
        while r.Rwait_frame(-1.0):
            pass
        r.Rshutdown()


def run():
    GlassApp().run()
