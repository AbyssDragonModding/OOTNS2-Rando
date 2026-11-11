"""Binary formats used by the Switch remake romfs.

Everything here works on files read from the user's own extracted romfs at runtime;
no game data is bundled with this program.

  * zstd with the Nintendo "ZsDic" dictionaries (Pack/ZsDic.pack.zs)
  * SARC archives (read)
  * BYML v7 little-endian (type-preserving read + write)
  * BFEVFL event flows (read + string-parameter patch)
  * RESTBL resource size table (read + write)
  * MSBT message files (read, UTF-8 and UTF-16)
"""
import math
import os
import re
import struct
import zlib
from compression import zstd

# ----------------------------------------------------------------------------- zstd


class ZsContext:
    """Loads the zstd dictionaries from the romfs and (de)compresses with them."""

    def __init__(self, romfs):
        self.romfs = romfs
        raw = open(os.path.join(romfs, "Pack", "ZsDic.pack.zs"), "rb").read()
        files = sarc_files(zstd.decompress(raw))
        self.dicts = {}       # name -> ZstdDict
        self.by_id = {}       # dict id -> name
        for name, data in files.items():
            zd = zstd.ZstdDict(data)
            self.dicts[name] = zd
            self.by_id[zd.dict_id] = name

    def decompress(self, raw):
        """Returns (data, dict_name or None)."""
        info = zstd.get_frame_info(raw)
        did = info.dictionary_id
        if did and did in self.by_id:
            name = self.by_id[did]
            return zstd.decompress(raw, zstd_dict=self.dicts[name]), name
        if did:
            raise ValueError("zstd frame uses unknown dictionary id %d" % did)
        return zstd.decompress(raw), None

    def compress(self, data, dict_name, level=16):
        if dict_name:
            return zstd.compress(data, level=level, zstd_dict=self.dicts[dict_name])
        return zstd.compress(data, level=level)

    def read(self, rel_path):
        """Read + decompress a romfs-relative .zs file. Returns (data, dict_name)."""
        raw = open(os.path.join(self.romfs, rel_path), "rb").read()
        return self.decompress(raw)


# ----------------------------------------------------------------------------- SARC

def sarc_files(data):
    assert data[:4] == b"SARC", "not a SARC archive"
    e = "<" if data[6:8] == b"\xff\xfe" else ">"
    hdr_len, = struct.unpack(e + "H", data[4:6])
    data_off, = struct.unpack(e + "I", data[0xC:0x10])
    sfat = hdr_len
    nh, = struct.unpack(e + "H", data[sfat + 6:sfat + 8])
    nodes = [struct.unpack(e + "IIII", data[sfat + 0xC + i * 16:sfat + 0x1C + i * 16]) for i in range(nh)]
    names_off = sfat + 0xC + nh * 16 + 8
    out = {}
    for _h, attr, s, en in nodes:
        if attr & 0x01000000:
            no = names_off + (attr & 0xFFFF) * 4
            name = data[no:data.index(b"\0", no)].decode()
        else:
            name = "unnamed_%x" % s
        out[name] = data[data_off + s:data_off + en]
    return out


def _sarc_hash(name, mult):
    h = 0
    for c in name.encode("utf-8"):
        h = (h * mult + (c if c < 0x80 else c - 0x100)) & 0xFFFFFFFF
    return h


def sarc_rebuild(data, replace=None, add=None):
    """Rebuild a little-endian SARC, replacing and/or adding files.
    Existing files keep their order and alignment; added files are aligned to 8."""
    replace, add = dict(replace or {}), dict(add or {})
    assert data[:4] == b"SARC" and data[6:8] == b"\xff\xfe", "only little-endian SARC is supported"
    hdr_len, = struct.unpack_from("<H", data, 4)
    data_off, = struct.unpack_from("<I", data, 0xC)
    sfat = hdr_len
    nh, = struct.unpack_from("<H", data, sfat + 6)
    mult, = struct.unpack_from("<I", data, sfat + 8)
    names_off = sfat + 0xC + nh * 16 + 8
    def pow2(n, cap):
        a = 1
        while a < cap and n % (a * 2) == 0:
            a *= 2
        return a

    entries, starts = [], []
    for i in range(nh):
        h, attr, s, en = struct.unpack_from("<IIII", data, sfat + 0xC + i * 16)
        no = names_off + (attr & 0xFFFF) * 4
        name = data[no:data.index(b"\0", no)].decode()
        starts.append(s)
        entries.append([name, replace.pop(name, data[data_off + s:data_off + en]), 0])
    if replace:
        raise KeyError("not in archive: %s" % ", ".join(replace))
    g = 0
    for st in starts:
        g = math.gcd(g, st)
    file_align = max(4, pow2(g, 0x80)) if g else 8      # archive-wide file alignment (8 for packs)
    data_align = max(4, pow2(data_off, 0x2000))         # alignment of the data section start
    for e in entries:
        e[2] = file_align
    for name, blob in add.items():
        entries.append([name, blob, file_align])
    entries.sort(key=lambda e: _sarc_hash(e[0], mult))
    # name table
    names = bytearray()
    name_idx = {}
    for e in entries:
        name_idx[e[0]] = len(names) // 4
        names += e[0].encode("utf-8") + b"\0"
        while len(names) % 4:
            names.append(0)
    sfat_size = 0xC + len(entries) * 16
    sfnt_off = 0x14 + sfat_size
    new_data_off = sfnt_off + 8 + len(names)
    new_data_off = (new_data_off + data_align - 1) // data_align * data_align
    body = bytearray()
    nodes = bytearray()
    for name, blob, align in entries:
        while len(body) % align:
            body.append(0)
        start = len(body)
        body += blob
        nodes += struct.pack("<IIII", _sarc_hash(name, mult), 0x01000000 | name_idx[name], start, len(body))
    out = bytearray(data[:0x14])
    out += b"SFAT" + struct.pack("<HHI", 0xC, len(entries), mult) + nodes
    out += b"SFNT" + struct.pack("<HH", 8, 0) + names
    out += b"\0" * (new_data_off - len(out))
    out += body
    struct.pack_into("<I", out, 0x8, len(out))
    struct.pack_into("<I", out, 0xC, new_data_off)
    return bytes(out)


# ----------------------------------------------------------------------------- BYML
# Python types map to BYML node types as follows (so files round-trip exactly):
#   str -> 0xA0 string, bool -> 0xD0, int -> 0xD1 (s32), float -> 0xD2 (f32),
#   U32 -> 0xD3, I64 -> 0xD4, U64 -> 0xD5, F64 -> 0xD6, None -> 0xFF,
#   Binary -> 0xA1, list -> 0xC0 array, dict -> 0xC1 dictionary.

class U32(int):
    pass


class I64(int):
    pass


class U64(int):
    pass


class F64(float):
    pass


class Binary(bytes):
    pass


class BymlReader:
    def __init__(self, data):
        self.d = data
        if data[:2] == b"YB":
            self.e, self.order = "<", "little"
        elif data[:2] == b"BY":
            self.e, self.order = ">", "big"
        else:
            raise ValueError("not a BYML file")
        self.ver, kt, st, self.root_off = struct.unpack_from(self.e + "HIII", data, 2)
        self.keys = self._strtab(kt) if kt else []
        self.strs = self._strtab(st) if st else []

    def _u32(self, o):
        return struct.unpack_from(self.e + "I", self.d, o)[0]

    def _n24(self, o):
        return int.from_bytes(self.d[o + 1:o + 4], self.order)

    def _strtab(self, o):
        n = self._n24(o)
        out = []
        for i in range(n):
            so = o + self._u32(o + 4 + i * 4)
            out.append(self.d[so:self.d.index(b"\0", so)].decode("utf-8"))
        return out

    def root(self):
        if not self.root_off:
            return None
        return self._node(self.d[self.root_off], self.root_off)

    def _val(self, t, o):
        d = self.d
        if t in (0xC0, 0xC1, 0xA1):
            return self._node(t, self._u32(o))
        if t == 0xA0:
            return self.strs[self._u32(o)]
        if t == 0xD0:
            return bool(self._u32(o))
        if t == 0xD1:
            return struct.unpack_from(self.e + "i", d, o)[0]
        if t == 0xD2:
            return struct.unpack_from(self.e + "f", d, o)[0]
        if t == 0xD3:
            return U32(self._u32(o))
        if t == 0xD4:
            return I64(struct.unpack_from(self.e + "q", d, self._u32(o))[0])
        if t == 0xD5:
            return U64(struct.unpack_from(self.e + "Q", d, self._u32(o))[0])
        if t == 0xD6:
            return F64(struct.unpack_from(self.e + "d", d, self._u32(o))[0])
        if t == 0xFF:
            return None
        raise ValueError("unsupported BYML value type 0x%x" % t)

    def _node(self, t, o):
        d = self.d
        if t == 0xA1:
            n = self._u32(o)
            return Binary(d[o + 4:o + 4 + n])
        typ, n = d[o], self._n24(o)
        if typ == 0xC0:
            types = d[o + 4:o + 4 + n]
            vo = o + 4 + ((n + 3) & ~3)
            return [self._val(types[i], vo + i * 4) for i in range(n)]
        if typ == 0xC1:
            out = {}
            for i in range(n):
                eo = o + 4 + i * 8
                ki = int.from_bytes(d[eo:eo + 3], self.order)
                out[self.keys[ki]] = self._val(d[eo + 3], eo + 4)
            return out
        raise ValueError("unsupported BYML container type 0x%x" % typ)


def byml_load(data):
    return BymlReader(data).root()


def byml_patch_root_u32(data, key, new_value):
    """Overwrite a top-level U32/S32 value in place (same size). Returns the patched bytes."""
    rd = BymlReader(data)
    o = rd.root_off
    assert data[o] == 0xC1, "root is not a dictionary"
    n = rd._n24(o)
    out = bytearray(data)
    for i in range(n):
        eo = o + 4 + i * 8
        ki = int.from_bytes(data[eo:eo + 3], rd.order)
        if rd.keys[ki] == key:
            if data[eo + 3] not in (0xD1, 0xD3):
                raise ValueError("%s is not a 32-bit integer" % key)
            struct.pack_into(rd.e + "I", out, eo + 4, new_value)
            return bytes(out)
    raise KeyError(key)


def sarc_file_ranges(data):
    """{name: (start, end)} absolute offsets of each file inside a SARC."""
    e = "<" if data[6:8] == b"\xff\xfe" else ">"
    hdr_len, = struct.unpack(e + "H", data[4:6])
    data_off, = struct.unpack(e + "I", data[0xC:0x10])
    nh, = struct.unpack(e + "H", data[hdr_len + 6:hdr_len + 8])
    names_off = hdr_len + 0xC + nh * 16 + 8
    out = {}
    for i in range(nh):
        _h, attr, s, en = struct.unpack(e + "IIII", data[hdr_len + 0xC + i * 16:hdr_len + 0x1C + i * 16])
        if attr & 0x01000000:
            no = names_off + (attr & 0xFFFF) * 4
            out[data[no:data.index(b"\0", no)].decode()] = (data_off + s, data_off + en)
    return out


def byml_dump(root, version=7, big_endian=False):
    E, ORD = (">", "big") if big_endian else ("<", "little")
    keys, strs = set(), set()

    def collect(v):
        if isinstance(v, dict):
            for k, x in v.items():
                keys.add(k)
                collect(x)
        elif isinstance(v, list):
            for x in v:
                collect(x)
        elif isinstance(v, str):
            strs.add(v)

    collect(root)
    keys = sorted(keys, key=lambda s: s.encode())
    strs = sorted(strs, key=lambda s: s.encode())
    kidx = {k: i for i, k in enumerate(keys)}
    sidx = {s: i for i, s in enumerate(strs)}

    out = bytearray(b"\0" * 16)

    def align(n):
        while len(out) % n:
            out.append(0)

    def strtab(lst):
        if not lst:
            return 0
        align(4)
        start = len(out)
        enc = [s.encode("utf-8") + b"\0" for s in lst]
        out.extend(bytes([0xC2]) + len(lst).to_bytes(3, ORD))
        off = 4 + 4 * (len(lst) + 1)
        offs = []
        for e in enc:
            offs.append(off)
            off += len(e)
        offs.append(off)
        for x in offs:
            out.extend(struct.pack(E + "I", x))
        for e in enc:
            out.extend(e)
        return start

    kt = strtab(keys)
    st = strtab(strs)

    def type_of(v):
        if isinstance(v, bool):
            return 0xD0
        if isinstance(v, U32):
            return 0xD3
        if isinstance(v, I64):
            return 0xD4
        if isinstance(v, U64):
            return 0xD5
        if isinstance(v, int):
            return 0xD1
        if isinstance(v, F64):
            return 0xD6
        if isinstance(v, float):
            return 0xD2
        if isinstance(v, str):
            return 0xA0
        if v is None:
            return 0xFF
        if isinstance(v, Binary):
            return 0xA1
        if isinstance(v, list):
            return 0xC0
        if isinstance(v, dict):
            return 0xC1
        raise TypeError("cannot encode %r" % type(v))

    pending = []  # (offset_of_u32_field, value) for out-of-line data

    def inline(v, t):
        if t == 0xD0:
            return struct.pack(E + "I", 1 if v else 0)
        if t == 0xD1:
            return struct.pack(E + "i", v)
        if t == 0xD2:
            return struct.pack(E + "f", v)
        if t == 0xD3:
            return struct.pack(E + "I", v)
        if t == 0xA0:
            return struct.pack(E + "I", sidx[v])
        if t == 0xFF:
            return b"\0\0\0\0"
        return None  # needs an offset

    def write_container(v):
        align(4)
        start = len(out)
        if isinstance(v, list):
            n = len(v)
            types = [type_of(x) for x in v]
            out.extend(bytes([0xC0]) + n.to_bytes(3, ORD))
            out.extend(bytes(types))
            align(4)
            for x, t in zip(v, types):
                b = inline(x, t)
                if b is None:
                    pending.append((len(out), x, t))
                    b = b"\0\0\0\0"
                out.extend(b)
        else:
            items = sorted(v.items(), key=lambda kv: kidx[kv[0]])
            out.extend(bytes([0xC1]) + len(items).to_bytes(3, ORD))
            for k, x in items:
                t = type_of(x)
                out.extend(kidx[k].to_bytes(3, ORD) + bytes([t]))
                b = inline(x, t)
                if b is None:
                    pending.append((len(out), x, t))
                    b = b"\0\0\0\0"
                out.extend(b)
        return start

    seen = {}
    root_off = write_container(root) if root is not None else 0
    # breadth-first emission of children keeps parents before children (like Nintendo's tools)
    i = 0
    deferred64 = []
    while i < len(pending):
        field, x, t = pending[i]
        i += 1
        if t in (0xC0, 0xC1):
            key = _canon(x)
            off = seen.get(key)
            if off is None:
                off = seen[key] = write_container(x)
        elif t == 0xA1:
            align(4)
            off = len(out)
            out.extend(struct.pack(E + "I", len(x)) + bytes(x))
        else:
            deferred64.append((field, x, t))
            continue
        struct.pack_into(E + "I", out, field, off)
    seen64 = {}
    for field, x, t in deferred64:
        k64 = (t, struct.pack(E + "d", x) if t == 0xD6 else x)
        off = seen64.get(k64)
        if off is None:
            align(8)
            off = seen64[k64] = len(out)
            out.extend(struct.pack(E + {0xD4: "q", 0xD5: "Q", 0xD6: "d"}[t], x))
        struct.pack_into(E + "I", out, field, off)
    align(4)
    out[0:2] = b"BY" if big_endian else b"YB"
    struct.pack_into(E + "HIII", out, 2, version, kt, st, root_off)
    return bytes(out)


def _canon(v):
    """Hashable, type-exact key for de-duplicating identical sub-trees."""
    if isinstance(v, dict):
        return ("d",) + tuple((k, _canon(x)) for k, x in sorted(v.items()))
    if isinstance(v, list):
        return ("l",) + tuple(_canon(x) for x in v)
    if isinstance(v, F64):
        return ("F64", struct.pack("<d", v))
    if isinstance(v, float):
        return ("f", struct.pack("<f", v))
    return (type(v).__name__, v)


# ----------------------------------------------------------------------------- BFEVFL

class EvflFile:
    """Read-only view of a BFEVFL plus the file offsets of string parameters,
    so individual parameters can be re-pointed to new strings."""

    def __init__(self, data):
        self.d = bytearray(data)
        assert self.d[:6] == b"BFEVFL", "not a BFEVFL file"
        self.flowcharts = []
        nfc = self._u16(0x20)
        fcs = self._u64(0x28)
        for i in range(nfc):
            self.flowcharts.append(self._flowchart(self._u64(fcs + i * 8)))

    def _u8(self, o): return self.d[o]
    def _u16(self, o): return struct.unpack_from("<H", self.d, o)[0]
    def _u32(self, o): return struct.unpack_from("<I", self.d, o)[0]
    def _i32(self, o): return struct.unpack_from("<i", self.d, o)[0]
    def _f32(self, o): return struct.unpack_from("<f", self.d, o)[0]
    def _u64(self, o): return struct.unpack_from("<Q", self.d, o)[0]

    def _s(self, p):
        if not p:
            return None
        n = self._u16(p)
        return bytes(self.d[p + 2:p + 2 + n]).decode("utf-8", "replace")

    def _dic(self, p):
        if not p:
            return []
        n = self._u32(p + 4)
        return [self._s(self._u64(p + 8 + (i + 1) * 0x10 + 8)) for i in range(n)]

    def _container(self, p):
        """Returns (value, string_pointer_offsets) where offsets maps key -> field offset."""
        if not p:
            return None, {}
        t, n = self._u8(p), self._u16(p + 2)
        if t == 1:
            names = self._dic(self._u64(p + 8))
            vals, ptrs = {}, {}
            for i in range(n):
                ip = self._u64(p + 0x10 + i * 8)
                v, _ = self._container(ip)
                vals[names[i]] = v
                if ip and self._u8(ip) in (5, 6):
                    ptrs[names[i]] = ip + 0x10
                elif ip and self._u8(ip) == 2:          # int parameter: "#int:<name>" -> value offset
                    ptrs["#int:" + names[i]] = ip + 0x10
            return vals, ptrs
        v = p + 0x10
        if t == 0:
            return ("arg", self._s(self._u64(v))), {}
        if t == 2:
            return self._i32(v), {}
        if t == 3:
            return bool(self._u32(v)), {}
        if t == 4:
            return self._f32(v), {}
        if t in (5, 6):
            return self._s(self._u64(v)), {}
        if t == 7:
            return [self._i32(v + i * 4) for i in range(n)], {}
        if t == 8:
            return [bool(self._u32(v + i * 4)) for i in range(n)], {}
        if t == 9:
            return [self._f32(v + i * 4) for i in range(n)], {}
        if t in (10, 11):
            return [self._s(self._u64(v + i * 8)) for i in range(n)], {}
        if t == 12:
            return ("actor", self._s(self._u64(v)), self._s(self._u64(v + 8))), {}
        return ("?type%d" % t,), {}

    def _flowchart(self, fp):
        na, nact, nq, ne, nep = (self._u16(fp + 0x10 + k * 2) for k in range(5))
        actors_p, events_p = self._u64(fp + 0x28), self._u64(fp + 0x30)
        ep_dic, ep_p = self._u64(fp + 0x38), self._u64(fp + 0x40)
        actors = []
        for a in range(na):
            ap = actors_p + a * 0x38
            acts, qs = self._u64(ap + 0x18), self._u64(ap + 0x20)
            actors.append({
                "name": self._s(self._u64(ap)),
                "actions": [self._s(self._u64(acts + k * 8)) for k in range(self._u16(ap + 0x30))],
                "queries": [self._s(self._u64(qs + k * 8)) for k in range(self._u16(ap + 0x32))],
            })
        events = []
        for e in range(ne):
            p = events_p + e * 0x30
            et = self._u8(p + 8)
            ev = {"index": e, "name": self._s(self._u64(p)), "type": et, "ptrs": {}, "offset": p}
            if et in (0, 1):
                ai = self._u16(p + 0xC)
                actor = actors[ai] if ai < len(actors) else None
                ev["actor"] = actor["name"] if actor else None
                if et == 0:
                    ev["next"] = self._u16(p + 0xA)
                    ev["action"] = actor["actions"][self._u16(p + 0xE)] if actor else None
                else:
                    ev["query"] = actor["queries"][self._u16(p + 0xE)] if actor else None
                    nc, cp = self._u16(p + 0xA), self._u64(p + 0x18)
                    ev["cases"] = [(self._u32(cp + k * 8), self._u32(cp + k * 8 + 4)) for k in range(nc)]
                ev["params"], ev["ptrs"] = self._container(self._u64(p + 0x10))
            elif et == 2:
                nf, fp2 = self._u16(p + 0xA), self._u64(p + 0x10)
                ev["join"] = self._u16(p + 0xC)
                ev["forks"] = [self._u16(fp2 + k * 2) for k in range(nf)]
            elif et == 3:
                ev["next"] = self._u16(p + 0xA)
            elif et == 4:
                ev["next"] = self._u16(p + 0xA)
                ev["params"], ev["ptrs"] = self._container(self._u64(p + 0x10))
                ev["flowchart"] = self._s(self._u64(p + 0x18))
                ev["entry"] = self._s(self._u64(p + 0x20))
            events.append(ev)
        entry_names = self._dic(ep_dic)
        entry_main = [self._u16(ep_p + k * 0x20 + 0x1C) for k in range(nep)]
        # which entry points reach each event (for readable context)
        for e in events:
            e["entry_points"] = []
        for epn, m in zip(entry_names, entry_main):
            stack, seen = [m], set()
            while stack:
                i = stack.pop()
                if i in seen or i >= len(events):
                    continue
                seen.add(i)
                e = events[i]
                e["entry_points"].append(epn)
                stack += ([e["next"]] if "next" in e else []) + [t for _, t in e.get("cases", [])] \
                    + e.get("forks", []) + ([e["join"]] if "join" in e else [])
        return {"name": self._s(self._u64(fp + 0x20)), "actors": actors, "events": events,
                "entry_points": entry_names}

    def set_int_param(self, field_offset, value):
        """Overwrite an int parameter in place (same size)."""
        struct.pack_into("<i", self.d, field_offset, int(value))

    def set_case_targets(self, event, targets):
        """Rewrite a query event's case targets in place: targets = {case value: event index}."""
        assert event["type"] == 1
        cp = self._u64(event["offset"] + 0x18)
        for k in range(len(event["cases"])):
            value = self._u32(cp + k * 8)
            if value in targets:
                struct.pack_into("<I", self.d, cp + k * 8 + 4, targets[value])

    def set_string_param(self, field_offset, value):
        """Re-point one string parameter to a new string appended at the end of the file.
        The pointer field is already in the relocation table, so only its value changes."""
        while len(self.d) % 8:
            self.d.append(0)
        off = len(self.d)
        enc = value.encode("utf-8")
        self.d.extend(struct.pack("<H", len(enc)) + enc + b"\0")
        struct.pack_into("<Q", self.d, field_offset, off)
        while len(self.d) % 8:
            self.d.append(0)
        struct.pack_into("<I", self.d, 0x1C, len(self.d))  # header: file size

    def get_string_at(self, field_offset):
        return self._s(self._u64(field_offset))

    def data(self):
        return bytes(self.d)


# ----------------------------------------------------------------------------- RESTBL

class Restbl:
    def __init__(self, data):
        assert data[:6] == b"RESTBL"
        self.version, self.sbs, nc, nn = struct.unpack_from("<IIII", data, 6)
        o = 0x16
        self.crc = {}
        for i in range(nc):
            c, s = struct.unpack_from("<II", data, o + i * 8)
            self.crc[c] = s
        o += nc * 8
        self.names = {}
        for i in range(nn):
            p = o + i * (self.sbs + 4)
            nm = data[p:p + self.sbs].split(b"\0")[0].decode()
            self.names[nm] = struct.unpack_from("<I", data, p + self.sbs)[0]

    def get(self, path):
        if path in self.names:
            return self.names[path]
        return self.crc.get(zlib.crc32(path.encode()))

    def set(self, path, size):
        if path in self.names:
            self.names[path] = size
        else:
            self.crc[zlib.crc32(path.encode())] = size

    def data(self):
        out = bytearray(b"RESTBL")
        out += struct.pack("<IIII", self.version, self.sbs, len(self.crc), len(self.names))
        for c in sorted(self.crc):
            out += struct.pack("<II", c, self.crc[c])
        for nm in sorted(self.names):
            out += nm.encode().ljust(self.sbs, b"\0") + struct.pack("<I", self.names[nm])
        return bytes(out)


# ----------------------------------------------------------------------------- MSBT

def _msbt_sections(d):
    nsec = struct.unpack_from("<H", d, 0xE)[0]
    o, out = 0x20, []
    for _ in range(nsec):
        magic, size = d[o:o + 4], struct.unpack_from("<I", d, o + 4)[0]
        out.append((magic, o, size))
        o = (o + 0x10 + size + 15) & ~15
    return out


def msbt_raw(d):
    """Returns ({label: index}, [raw text bytes incl. terminator])."""
    labels, texts = {}, []
    for magic, o, size in _msbt_sections(d):
        b = o + 0x10
        if magic == b"LBL1":
            n = struct.unpack_from("<I", d, b)[0]
            for i in range(n):
                cnt, off = struct.unpack_from("<II", d, b + 4 + i * 8)
                p = b + off
                for _ in range(cnt):
                    ln = d[p]
                    labels[d[p + 1:p + 1 + ln].decode()] = struct.unpack_from("<I", d, p + 1 + ln)[0]
                    p += 5 + ln
        elif magic == b"TXT2":
            n = struct.unpack_from("<I", d, b)[0]
            offs = [struct.unpack_from("<I", d, b + 4 + i * 4)[0] for i in range(n)] + [size]
            texts = [bytes(d[b + offs[i]:b + offs[i + 1]]) for i in range(n)]
    return labels, texts


def msbt_set_raw(d, new_texts):
    """Replace texts by label ({label: raw bytes incl. terminator}); rebuilds TXT2 only."""
    labels, texts = msbt_raw(d)
    texts = list(texts)
    for label, raw in new_texts.items():
        texts[labels[label]] = raw
    out = bytearray(d[:0x20])
    for magic, o, size in _msbt_sections(d):
        if magic == b"TXT2":
            n = len(texts)
            body = bytearray(struct.pack("<I", n))
            off = 4 + 4 * n
            for t in texts:
                body += struct.pack("<I", off)
                off += len(t)
            for t in texts:
                body += t
        else:
            body = d[o + 0x10:o + 0x10 + size]
        out += magic + struct.pack("<I", len(body)) + d[o + 8:o + 0x10] + body
        while len(out) % 16:
            out.append(0xAB)
    struct.pack_into("<I", out, 0x12, len(out))
    return bytes(out)


def msbt_parse(d):
    assert d[:8] == b"MsgStdBn"
    utf8 = d[0xC] == 0
    nsec = struct.unpack_from("<H", d, 0xE)[0]
    o, labels, texts = 0x20, {}, []
    for _ in range(nsec):
        magic, size = d[o:o + 4], struct.unpack_from("<I", d, o + 4)[0]
        b = o + 0x10
        if magic == b"LBL1":
            n = struct.unpack_from("<I", d, b)[0]
            for i in range(n):
                cnt, off = struct.unpack_from("<II", d, b + 4 + i * 8)
                p = b + off
                for _ in range(cnt):
                    ln = d[p]
                    labels[d[p + 1:p + 1 + ln].decode()] = struct.unpack_from("<I", d, p + 1 + ln)[0]
                    p += 5 + ln
        elif magic == b"TXT2":
            n = struct.unpack_from("<I", d, b)[0]
            offs = [struct.unpack_from("<I", d, b + 4 + i * 4)[0] for i in range(n)] + [size]
            for i in range(n):
                raw = d[b + offs[i]:b + offs[i + 1]]
                texts.append(_msbt_text(raw, utf8))
        o = (b + size + 15) & ~15
    return {k: texts[v] for k, v in labels.items() if v < len(texts)}


def _msbt_text(raw, utf8):
    out, j = [], 0
    if utf8:
        buf = bytearray()
        while j < len(raw):
            c = raw[j]
            if c == 0x0E:
                plen = struct.unpack_from("<H", raw, j + 5)[0]
                j += 7 + plen
                continue
            if c == 0x0F:
                j += 5
                continue
            if c == 0:
                break
            buf.append(c)
            j += 1
        return buf.decode("utf-8", "replace").strip()
    while j + 1 < len(raw):
        c = struct.unpack_from("<H", raw, j)[0]
        if c == 0x0E:
            plen = struct.unpack_from("<H", raw, j + 6)[0]
            j += 8 + plen
            continue
        if c == 0x0F:
            j += 6
            continue
        if c == 0:
            break
        out.append(chr(c))
        j += 2
    return "".join(out).strip()
