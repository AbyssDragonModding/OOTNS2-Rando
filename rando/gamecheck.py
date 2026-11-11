"""Game version check: only run on game versions the randomizer is known to work with.

The randomizer edits data files whose layout can change between game updates, so a different version could
produce a broken mod. The check hashes the game's executable (`exefs/main`) with SHA-256 and compares it with
KNOWN_VERSIONS. The exefs folder is normally next to the romfs folder (`<game>/exefs` and `<game>/romfs`).

To add a version: dump its exefs, run `python -m rando.gamecheck <exefs folder>` and add the printed hash.
"""
import hashlib
import os

TITLE_ID = "0400486024dec000"

# SHA-256 of exefs/main -> description shown to the user
KNOWN_VERSIONS = {
    "7db9ddfda088c22d219ef13496decd7077c68cd67d4b37f53f4ac46a082768f2": "build e0f3ccfa",
}

_cache = {}   # (path, size, mtime) -> sha256, so re-checking the same file is instant


class GameCheck:
    """Result of a check. `ok` is True only for a whitelisted version; `message` explains the result."""

    def __init__(self, ok, status, message, exefs=None, sha256=None, version=None):
        self.ok, self.status, self.message = ok, status, message
        self.exefs, self.sha256, self.version = exefs, sha256, version

    def __repr__(self):
        return "GameCheck(%s, %s)" % (self.status, self.message)


def default_exefs(romfs):
    """`<game>/exefs` for a romfs at `<game>/romfs`, or None if there's no such folder."""
    if not romfs:
        return None
    path = os.path.join(os.path.dirname(os.path.abspath(romfs.rstrip("/\\"))), "exefs")
    return path if os.path.isdir(path) else None


def _sha256(path):
    st = os.stat(path)
    key = (os.path.abspath(path), st.st_size, st.st_mtime_ns)
    if key not in _cache:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        _cache[key] = h.hexdigest()
    return _cache[key]


def _title_id(npdm):
    """Program ID from main.npdm's ACI0 section, or None if it can't be read."""
    try:
        with open(npdm, "rb") as fh:
            data = fh.read()
        i = data.find(b"ACI0")
        return data[i + 0x10:i + 0x18][::-1].hex() if i >= 0 else None
    except OSError:
        return None


def check(exefs=None, romfs=None):
    """Check an exefs folder (or the one next to `romfs` when `exefs` is empty)."""
    exefs = (exefs or "").strip() or default_exefs(romfs)
    if not exefs:
        return GameCheck(False, "missing", "exefs folder not found. It is normally next to the romfs folder; "
                                           "extract it from your game the same way as the romfs.")
    main = os.path.join(exefs, "main")
    if not os.path.isfile(main):
        return GameCheck(False, "missing", "No 'main' file in %s. Choose the game's extracted exefs folder." % exefs,
                         exefs)
    tid = _title_id(os.path.join(exefs, "main.npdm"))
    if tid and tid != TITLE_ID:
        return GameCheck(False, "wrong_game", "This exefs belongs to a different game (title ID %s, expected %s)."
                         % (tid.upper(), TITLE_ID.upper()), exefs)
    digest = _sha256(main)
    version = KNOWN_VERSIONS.get(digest)
    if version is None:
        return GameCheck(False, "unsupported",
                         "Sorry, this game version isn't supported. It may be outdated, or newer than this release "
                         "of the randomizer. Please update the game and the randomizer to their latest versions.\n"
                         "(SHA-256 of exefs/main: %s)" % digest, exefs, digest)
    return GameCheck(True, "ok", "Supported game version (%s)." % version, exefs, digest, version)


if __name__ == "__main__":
    import sys
    res = check(sys.argv[1] if len(sys.argv) > 1 else None)
    print(res.message)
    if res.sha256:
        print("sha256:", res.sha256)
    sys.exit(0 if res.ok else 1)
