"""OoT (Switch 2) item tracker, built with Raven (pip install raven-gui).

On first start it asks for the user's own extracted romfs and runs
extract_item_icons.py on it (colour icons + --grayscale copies) into ./icons.
No game file is shipped with the tracker: the icons only ever come from the
user's game.

Left click a cell: next tier (or +1). Right click: previous tier (or -1);
the first tier goes back to the grayscale "not acquired" icon, and right
clicking that does nothing. Shift steps counters by 5.
File menu: New, Open, Save, Save As (JSON), and re-linking the romfs.
"""
import ctypes
import json
import sys
from pathlib import Path

import raven as r

import items

APP_DIR = Path(__file__).resolve().parent
UI_DIR = APP_DIR / "ui"
ICON_DIR = APP_DIR / "icons"
SETTINGS_FILE = APP_DIR / "settings.json"
SAVE_FORMAT = "ootns2-tracker"
SAVE_VERSION = 1

NOT_ACQUIRED_OPACITY = 0.4
COUNTER_STEP_SHIFT = 5
TRACKER_WIDTH = 475  # the window keeps this width; only its height resizes


# ---------------------------------------------------------------- settings

def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def icon_path(name, gray):
    return ICON_DIR / ("grayscale" if gray else "") / f"{name}.png"


def missing_icons():
    return [n for n in sorted(items.all_icons())
            if not icon_path(n, False).is_file() or not icon_path(n, True).is_file()]


def upgrade_save(saved):
    """Map the cells of older saves onto the current ones."""
    if "ocarina" in saved:  # was one cell: Fairy Ocarina -> Ocarina of Time
        level = saved.pop("ocarina")
        saved.setdefault("fairy_ocarina", 1 if level >= 1 else 0)
        saved.setdefault("ocarina_of_time", 1 if level >= 2 else 0)
    for weapon, bag in items.STARTS_WITH.items():
        # was one cell: item -> 2nd -> 3rd capacity; the item comes with the first bag
        if bag not in saved and isinstance(saved.get(weapon), int) and saved[weapon] > 0:
            saved[bag] = saved[weapon]
            saved[weapon] = 1
    if "stone_of_agony" in saved:
        saved.setdefault("echo_gem", saved.pop("stone_of_agony"))
    return saved


# ---------------------------------------------------------------- file dialogs

_JSON_FILTER = (r.RFileFilter * 1)(r.RFileFilter(b"Tracker save (*.json)", b"*.json"))


def _dialog_desc(window, title, file_name=None):
    return r.RFileDialogDesc(parent=window, title=title.encode(), file_name=file_name.encode() if file_name else None,
                             filters=ctypes.cast(_JSON_FILTER, ctypes.POINTER(r.RFileFilter)), filter_count=1,
                             default_extension=b"json")


# ---------------------------------------------------------------- tracker window

class Tracker:
    def __init__(self, app):
        self.app = app
        self.state = {c.id: 0 for c in items.CELLS}
        self.textures = {}
        self.save_path = None
        self.dirty = False

        self.window = r.Rwindow_create_from_xml_file(str(UI_DIR / "tracker.xml"))
        if self.window == r.R_INVALID_ID:
            raise RuntimeError(f"Could not load tracker.xml: {r.Rerror_get_last()}")
        self.status = r.Rwidget_find(self.window, "status")

        self.widgets = {}
        for cell in items.CELLS:
            box = r.Rwidget_find(self.window, f"cell_{cell.id}")
            if box == r.R_INVALID_ID:
                print(f"warning: tracker.xml has no cell for '{cell.id}'", file=sys.stderr)
                continue
            self.widgets[cell.id] = (box, r.Rwidget_find(self.window, f"img_{cell.id}"),
                                     r.Rwidget_find(self.window, f"badge_{cell.id}"),
                                     r.Rwidget_find(self.window, f"cnt_{cell.id}"),
                                     r.Rwidget_find(self.window, f"capbadge_{cell.id}"),
                                     r.Rwidget_find(self.window, f"cap_{cell.id}"))
            r.Rwidget_set_event_callback(box, self._make_click_handler(cell))

        for action, handler in {
            "file_new": self.file_new, "file_open": self.file_open, "file_save": self.file_save,
            "file_save_as": self.file_save_as, "file_relink": self.file_relink, "file_exit": self.file_exit,
        }.items():
            r.Raction_bind(action, lambda sender, name, user, h=handler: h())

        r.Rwindow_set_close_callback(self.window, lambda window, user: self.on_close())
        r.Rwindow_set_resize_callback(self.window, lambda window, w, h, user: self.keep_width())
        self.keep_width()
        self.refresh_all()
        self.update_title()

    def keep_width(self):
        """Raven has a minimum window size but no maximum: put the width back after a resize."""
        width, height = r.Rwindow_get_size(self.window)
        if width != TRACKER_WIDTH:
            r.Rwindow_set_size(self.window, TRACKER_WIDTH, height)

    # ---- drawing

    def texture(self, path):
        tex = self.textures.get(path)
        if tex is None:
            tex = self.textures[path] = r.Rtexture_create_from_file(str(path))
        return tex

    def drop_textures(self):
        for tex in self.textures.values():
            if r.Rtexture_is_valid(tex):
                r.Rtexture_destroy(tex)
        self.textures.clear()

    def refresh(self, cell):
        if cell.id not in self.widgets:
            return
        box, img, badge, count, capbadge, cap = self.widgets[cell.id]
        state = self.state[cell.id]
        r.Rimage_set_texture(img, self.texture(icon_path(cell.icon_for(state), gray=state == 0)))
        r.Rwidget_set_opacity(img, NOT_ACQUIRED_OPACITY if state == 0 else 1.0)
        r.Rwidget_set_tooltip(box, cell.describe(state))
        if cell.counter and state > 0:
            r.Rlabel_set_text(count, str(state))
            full = state == cell.counter
            r.Rlabel_set_color(count, *((0.45, 1.0, 0.45, 1.0) if full else (1.0, 1.0, 1.0, 1.0)))
            r.Rwidget_set_attribute(badge, "Visibility", "Visible")
        else:
            r.Rwidget_set_attribute(badge, "Visibility", "Collapsed")
        capacity = cell.capacity_for(state)
        if capacity is not None:
            r.Rlabel_set_text(cap, str(capacity))
            full = state == cell.max_state
            r.Rlabel_set_color(cap, *((0.45, 1.0, 0.45, 1.0) if full else (1.0, 1.0, 1.0, 1.0)))
            r.Rwidget_set_attribute(capbadge, "Visibility", "Visible")
        else:
            r.Rwidget_set_attribute(capbadge, "Visibility", "Collapsed")

    def refresh_all(self):
        for cell in items.CELLS:
            self.refresh(cell)

    def set_status(self, text):
        r.Rlabel_set_text(self.status, text)

    def update_title(self):
        name = self.save_path.name if self.save_path else "untitled"
        r.Rwindow_set_title(self.window, f"{'*' if self.dirty else ''}{name} - OoT Item Tracker")

    # ---- clicks

    def _make_click_handler(self, cell):
        def handler(widget, event, user):
            if event is None or event.type != r.R_EVENT_MOUSE_DOWN:
                return 0
            step = COUNTER_STEP_SHIFT if cell.counter and event.modifiers & r.R_MOD_SHIFT else 1
            if event.button == r.R_MOUSE_LEFT:
                self.change(cell, +step)
            elif event.button == r.R_MOUSE_RIGHT:
                self.change(cell, -step)
            else:
                return 0
            return 1
        return handler

    def change(self, cell, delta):
        old = self.state[cell.id]
        new = max(0, min(cell.max_state, old + delta))
        if new == old:
            return  # already at the top, or at "not acquired": nothing to do
        self.state[cell.id] = new
        self.refresh(cell)
        status = cell.describe(new)
        base = items.STARTS_WITH.get(cell.id)
        if old == 0 and base and self.state[base] == 0:
            # the bow comes with a quiver, the slingshot with a bullet bag
            self.state[base] = 1
            self.refresh(items.CELLS_BY_ID[base])
            status += f" + {items.CELLS_BY_ID[base].describe(1)}"
        self.set_status(status)
        if not self.dirty:
            self.dirty = True
            self.update_title()

    # ---- save / load

    def to_json(self):
        return {"format": SAVE_FORMAT, "version": SAVE_VERSION, "items": dict(self.state)}

    def load_json(self, data):
        if data.get("format") != SAVE_FORMAT:
            raise ValueError("not an OoT tracker save")
        loaded = upgrade_save(dict(data.get("items", {})))
        for cell in items.CELLS:
            value = loaded.get(cell.id, 0)
            self.state[cell.id] = max(0, min(cell.max_state, int(value))) if isinstance(value, (int, float)) else 0

    def write(self, path):
        try:
            Path(path).write_text(json.dumps(self.to_json(), indent=2), encoding="utf-8")
        except OSError as e:
            self.set_status(f"Could not save: {e}")
            return False
        self.save_path, self.dirty = Path(path), False
        self.app.remember_save(self.save_path)
        self.update_title()
        self.set_status(f"Saved {self.save_path}")
        return True

    def read(self, path):
        try:
            self.load_json(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:
            self.set_status(f"Could not open {path}: {e}")
            return False
        self.save_path, self.dirty = Path(path), False
        self.app.remember_save(self.save_path)
        self.refresh_all()
        self.update_title()
        self.set_status(f"Opened {self.save_path}")
        return True

    def file_new(self):
        self.state = {c.id: 0 for c in items.CELLS}
        self.save_path, self.dirty = None, False
        self.refresh_all()
        self.update_title()
        self.set_status("New tracker: everything reset to not acquired")

    def file_open(self):
        path = r.Rfile_dialog_open(_dialog_desc(self.window, "Open tracker save"))
        if path:
            self.read(path)

    def file_save(self):
        if self.save_path:
            self.write(self.save_path)
        else:
            self.file_save_as()

    def file_save_as(self):
        default = self.save_path.name if self.save_path else "tracker.json"
        path = r.Rfile_dialog_save(_dialog_desc(self.window, "Save tracker", default))
        if path:
            if not path.lower().endswith(".json"):
                path += ".json"
            self.write(path)

    def file_relink(self):
        self.app.open_setup(cancel_allowed=True)

    def file_exit(self):
        r.Rwindow_close(self.window)

    def on_close(self):
        self.drop_textures()
        r.Rquit(0)
        return r.R_TRUE


# ---------------------------------------------------------------- setup window

class Setup:
    """Asks for the romfs folder, then extracts the icons on a worker thread."""

    def __init__(self, app, cancel_allowed):
        self.app = app
        self.busy = False
        self.window = r.Rwindow_create_from_xml_file(str(UI_DIR / "setup.xml"))
        if self.window == r.R_INVALID_ID:
            raise RuntimeError(f"Could not load setup.xml: {r.Rerror_get_last()}")
        self.path_input = r.Rwidget_find(self.window, "romfs_path")
        self.status = r.Rwidget_find(self.window, "setup_status")
        self.go = r.Rwidget_find(self.window, "setup_go")
        self.cancel_allowed = cancel_allowed
        known = app.settings.get("romfs")
        if known:
            r.Rtext_input_set_text(self.path_input, known)
        if missing := missing_icons():
            if ICON_DIR.exists():
                self.say(f"{len(missing)} icons are missing: extract them again.")
        r.Raction_bind("setup_browse", lambda s, a, u: self.browse())
        r.Raction_bind("setup_extract", lambda s, a, u: self.start())
        r.Raction_bind("setup_cancel", lambda s, a, u: self.cancel())
        r.Rwindow_set_close_callback(self.window, lambda w, u: self.on_close())

    def say(self, text):
        r.Rlabel_set_text(self.status, text)

    def browse(self):
        desc = r.RFileDialogDesc(parent=self.window, title=b"Select your extracted romfs folder")
        path = r.Rfile_dialog_select_folder(desc)
        if path:
            r.Rtext_input_set_text(self.path_input, path)

    def start(self):
        if self.busy:
            return
        typed = (r.Rtext_input_get_text(self.path_input) or "").strip().strip('"')
        if not typed:
            self.say("Choose your romfs folder first.")
            return
        try:
            import extract_item_icons
        except ImportError as e:
            self.say(str(e))
            return
        romfs = extract_item_icons.find_romfs(typed)
        if romfs is None:
            self.say("That folder has no UI\\Tex\\Icon inside: pick the romfs folder of your OoT (Switch 2) dump.")
            return
        self.busy = True
        r.Rwidget_set_enabled(self.go, r.R_FALSE)
        self.say("Extracting icons... (a few seconds)")

        def work(user):
            try:
                count = extract_item_icons.extract(romfs, ICON_DIR, grayscale=True, log=lambda m: None)
                error = None if not missing_icons() else f"Extraction finished but icons are missing: {missing_icons()[:5]}"
            except Exception as e:  # report anything to the window instead of dying on a worker thread
                count, error = 0, f"Extraction failed: {e}"
            r.Rtask_post(lambda u: self.finished(romfs, count, error))

        r.Rtask_run_async(work)

    def finished(self, romfs, count, error):
        self.busy = False
        r.Rwidget_set_enabled(self.go, r.R_TRUE)
        if error:
            self.say(error)
            return
        self.app.settings["romfs"] = str(romfs)
        save_settings(self.app.settings)
        self.app.setup_done(count)

    def cancel(self):
        r.Rwindow_close(self.window)

    def on_close(self):
        if self.busy:
            return r.R_FALSE  # let the extraction finish
        self.app.setup_closed()
        return r.R_TRUE


# ---------------------------------------------------------------- app

class App:
    def __init__(self):
        self.settings = load_settings()
        self.tracker = None
        self.setup = None

    def run(self):
        r.Rinit(r.R_BACKEND_VULKAN)
        if r.Rxml_register_widgets_from_file(str(UI_DIR / "widgets.xml")) <= 0:
            raise RuntimeError(f"Could not load widgets.xml: {r.Rerror_get_last()}")
        if missing_icons():
            self.open_setup(cancel_allowed=False)
        else:
            self.open_tracker()
        while r.Rwait_frame(-1.0):
            pass
        code = r.Rget_exit_code()
        r.Rshutdown()
        return code

    def open_tracker(self):
        self.tracker = Tracker(self)
        last = self.settings.get("last_save")
        if last and Path(last).is_file():
            self.tracker.read(last)

    def open_setup(self, cancel_allowed):
        if self.setup is None:
            self.setup = Setup(self, cancel_allowed)

    def setup_done(self, count):
        setup, self.setup = self.setup, None
        r.Rwindow_destroy(setup.window)
        if self.tracker:
            self.tracker.drop_textures()  # pick up the freshly extracted files
            self.tracker.refresh_all()
            self.tracker.set_status(f"Extracted {count} icons from your romfs")
        else:
            self.open_tracker()

    def setup_closed(self):
        self.setup = None
        if self.tracker is None:
            r.Rquit(0)  # no icons, nothing to show

    def remember_save(self, path):
        self.settings["last_save"] = str(path)
        save_settings(self.settings)


if __name__ == "__main__":
    sys.exit(App().run())
