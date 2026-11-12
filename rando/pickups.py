"""World pickups for items that only exist as get-demo actors.

Items lying in the world (freestanding spots, rupee spots, boss Heart Container spots, Gold Skulltula drops)
must be Obj_Item_Base actors: those are the ones the player can walk up to and collect. Most key items only
have an Item_* actor (Item_EventObject_Base), which is what the item-get cutscene shows in Link's hands; placed
in the world it just lies there.

For each such item this builds a new actor "Obj_Rando_<item>" cloned from Obj_Arrow_Fire (Lake Hylia's
freestanding Fire Arrows, an Obj_Item_Base pickup that gives a key item):
- pack: the template pack + the item's own component files, a new ActorParam whose model / name / animation /
  parameter-table / effect refs come from the item, and a new PouchContentParam ("PouchActor" = the item);
- RSDB: ActorInfo and GameActorInfo rows cloned from Obj_Arrow_Fire with the item's model fields and
  ActorName (so the pickup uses the item's own text), and a PouchActorInfo row cloned from the item;
- RESTBL: entries for the new pack and the new files inside it.
"""
import bisect
import copy
import os
import zlib

from . import formats as F

TEMPLATE = "Obj_Arrow_Fire"
PREFIX = "Obj_Rando_"
COPIED_REFS = ("ActorNameRef", "ModelInfoRef", "AnimationRef", "GameParameterTableRef", "ELinkRef", "SLinkRef",
               "CaptureRef")
ROW_FROM_ITEM = ("FmdbName", "ModelProjectName", "AnimationResources", "ModelAabbMax", "ModelAabbMin",
                 "ELinkUserName", "SLinkUserName")
HEAP_KEYS = ("InstanceHeapSize", "PreActorRenderInfoHeapSize")

# Walk-over pickups. Obj_Item_Base (rupees, small keys, the Ocarina of Time, ...) is collected by touching it
# (AttentionSenderParam "AutoPickUpItem"); Obj_Arrow_Fire, and so every Obj_Rando_ clone, overrides that with
# "PickUpItem", which needs A. Every shuffled item lying in the world (freestanding and rupee spots, Gold
# Skulltula drops) gets an "Obj_RandoAuto_" copy of its pickup with the walk-over setting: a Skulltula on a
# wall drops its item in mid-air, where Link climbing the vine can touch it but can't press A. The setting's
# blackboard flag (IsEnableAttention) is raised by the DropItem AI, so only pickups that run that AI can use
# it: Obj_Heart_Piece and Obj_Bottle_Letter have their own AI and still need A, so they are kept off
# Skulltula drops (generator.GS_FORBIDDEN).
AUTO_PREFIX = "Obj_RandoAuto_"
AUTO_SOURCE = "Obj_Rupee_Green"
AUTO_ATTENTION = "Component/AttentionSenderParam/AutoPickUpItem.game__component__AttentionSenderParam.bgyml"
AUTO_FILES = (AUTO_ATTENTION,
              "Attention/ClientParam/Auto_Item_Catch.game__attention__ClientParam.bgyml",
              "Attention/ClientParam/LookOnly_Middle_Small.game__attention__ClientParam.bgyml")


def _pack(name):
    return "Pack/Actor/%s.pack.zs" % name


def _param(name):
    return "Actor/%s.engine__actor__ActorParam.bgyml" % name


def _ref_file(ref):
    """'?Component/X/Y.bgyml' -> 'Component/X/Y.bgyml'."""
    return ref.lstrip("?")


def _work_path(file_path):
    """'Component/X/Y.game__x.bgyml' -> 'Work/Component/X/Y.game__x.gyml' (the form $parent / PouchActor use)."""
    return "Work/" + file_path[:-len(".bgyml")] + ".gyml" if file_path.endswith(".bgyml") else file_path


class PickupCloner:
    def __init__(self, world, read, emit, restbl, progress=print):
        self.world, self.read, self.emit, self.restbl, self.progress = world, read, emit, restbl, progress
        self.made = {}          # (source actor, False) -> clone name (or None if it could not be built)
        self.rows = []          # (clone, source) for RSDB
        self.auto_rows = []     # (walk-over copy, pickup it copies) for RSDB

    @staticmethod
    def needs_clone(actor):
        return not actor.startswith("Obj_")

    def world_actor(self, actor, auto=False):
        """Actor to place in the world for `actor` (a world-context actor name from World.actor_for).
        auto: the pickup must be collected by touching it (a Gold Skulltula drop)."""
        base = actor
        if self.needs_clone(actor):
            if (actor, False) not in self.made:
                self.made[(actor, False)] = self._build(actor)
            base = self.made[(actor, False)] or actor
        if not auto or not base.startswith("Obj_"):
            return base
        if (base, True) not in self.made:
            self.made[(base, True)] = self._build_auto(base)
        return self.made[(base, True)] or base

    def _build_auto(self, src):
        """Copy of pickup `src` that is collected by walking into it, or None if it already is."""
        raw, dname = self.read(_pack(src))
        files = F.sarc_files(raw)
        if _param(src) not in files:
            return None
        param = F.byml_load(files[_param(src)])
        comps = param.setdefault("Components", {})
        ref = comps.get("AttentionSenderRef")
        if ref is None or "AutoPickUpItem" in ref:
            return None                        # Obj_Item_Base's walk-over setting (or the token's)
        if "AIInfoRef" in comps:
            return None                        # own AI (heart pieces): keeps needing A, kept off Skulltulas
        clone = AUTO_PREFIX + src[len(PREFIX):] if src.startswith(PREFIX) else AUTO_PREFIX + src[len("Obj_"):]
        comps["AttentionSenderRef"] = "?" + AUTO_ATTENTION
        auto_files = F.sarc_files(self.read(_pack(AUTO_SOURCE))[0])
        add = {k: auto_files[k] for k in AUTO_FILES if k not in files and k in auto_files}
        new_param = F.byml_dump(param, version=F.BymlReader(files[_param(src)]).ver)
        add[_param(clone)] = new_param
        data = F.sarc_rebuild(raw, add=add)
        F.sarc_files(data)                                    # sanity: must parse
        self.emit(_pack(clone), data, data, dname)

        pack_size = self.restbl.get(_pack(src)[:-3])
        entries = {
            _pack(clone)[:-3]: None if pack_size is None else pack_size + max(0, len(data) - len(raw)),
            _param(clone): self._size(_param(clone), _param(src), len(new_param) - len(files[_param(src)])),
        }
        for k in add:
            if k not in entries and self.restbl.get(k) is None:
                entries[k] = self._size(k, AUTO_ATTENTION, len(add[k]))
        if entries[_pack(clone)[:-3]] is None:
            # a clone's own pack size was added this run: work it out the way _build did
            entries[_pack(clone)[:-3]] = self._size(_pack(clone)[:-3], _pack(TEMPLATE)[:-3],
                                                    len(data) - len(self.read(_pack(TEMPLATE))[0]))
        for path, size in entries.items():
            if size is not None and self.restbl.get(path) is None:
                if zlib.crc32(path.encode()) in self.restbl.crc:
                    self.progress("warning: size-table hash collision for %s; skipped" % path)
                    continue
                self.restbl.set(path, size)
        self.auto_rows.append((clone, src))
        return clone

    def _size(self, path, fallback_path, delta):
        old = self.restbl.get(path)
        if old is not None:
            return None
        base = self.restbl.get(fallback_path)
        return None if base is None else base + max(0, delta)

    def _build(self, src):
        world = self.world
        if not os.path.exists(os.path.join(world.romfs, *_pack(src).split("/"))):
            self.progress("warning: no pack for %s; it can't be made into a world pickup" % src)
            return None
        clone = PREFIX + src.split("_", 1)[1]
        tmpl_raw, dname = self.read(_pack(TEMPLATE))
        tmpl = F.sarc_files(tmpl_raw)
        item = F.sarc_files(self.read(_pack(src))[0])
        if _param(src) not in item or _param(TEMPLATE) not in tmpl:
            self.progress("warning: %s has no ActorParam; it can't be made into a world pickup" % src)
            return None
        src_param = F.byml_load(item[_param(src)])
        src_comps = src_param.get("Components", {})
        param = F.byml_load(tmpl[_param(TEMPLATE)])
        comps = param.setdefault("Components", {})
        for key in COPIED_REFS:
            if key in src_comps:
                comps[key] = src_comps[key]

        # pouch content: inherit the item's own settings, but give the item itself
        pouch_tmpl_path = _ref_file(comps["PouchContentRef"])
        pouch = F.byml_load(tmpl[pouch_tmpl_path])
        src_pouch_ref = src_comps.get("PouchContentRef")
        if src_pouch_ref:
            pouch["$parent"] = _work_path(_ref_file(src_pouch_ref))
        pouch_actor = "Work/Actor/%s.engine__actor__ActorParam.gyml" % src
        if not src.startswith("Item_") and src_pouch_ref and _ref_file(src_pouch_ref) in item:
            # an Obj_ source's own pouch param already names the item it gives
            pouch_actor = F.byml_load(item[_ref_file(src_pouch_ref)]).get("PouchActor") or pouch_actor
        pouch["PouchActor"] = pouch_actor
        for k in ("IsPickedUpEmitXlinkKey", "PickedUpEmitXlinkKey"):
            pouch.pop(k, None)
        pouch_path = "Component/PouchContentParam/%s.game__component__PouchContentParam.bgyml" % clone
        comps["PouchContentRef"] = "?" + pouch_path

        add = {k: v for k, v in item.items() if k not in tmpl and not k.startswith(("Actor/", "AI/"))}
        new_param = F.byml_dump(param, version=F.BymlReader(tmpl[_param(TEMPLATE)]).ver)
        new_pouch = F.byml_dump(pouch, version=F.BymlReader(tmpl[pouch_tmpl_path]).ver)
        add[_param(clone)] = new_param
        add[pouch_path] = new_pouch
        data = F.sarc_rebuild(tmpl_raw, add=add)
        F.sarc_files(data)                                    # sanity: must parse
        self.emit(_pack(clone), data, data, dname)          # new file: its size entry is set below

        # resource size table entries for everything new
        entries = {
            _pack(clone)[:-3]: self._size(_pack(clone)[:-3], _pack(TEMPLATE)[:-3], len(data) - len(tmpl_raw)),
            _param(clone): self._size(_param(clone), _param(TEMPLATE), len(new_param) - len(tmpl[_param(TEMPLATE)])),
            pouch_path: self._size(pouch_path, pouch_tmpl_path, len(new_pouch) - len(tmpl[pouch_tmpl_path])),
        }
        for k in add:
            if k not in entries and self.restbl.get(k) is None:
                entries[k] = self._size(k, pouch_tmpl_path, len(add[k]))
        for path, size in entries.items():
            if size is not None:
                if zlib.crc32(path.encode()) in self.restbl.crc:
                    self.progress("warning: size-table hash collision for %s; skipped" % path)
                    continue
                self.restbl.set(path, size)
        self.rows.append((clone, src))
        return clone

    def finish(self):
        if not self.rows and not self.auto_rows:
            return
        tables = {}
        for t in ("ActorInfo", "GameActorInfo", "PouchActorInfo"):
            rel = self.world._find("RSDB", t)
            data, dname = self.read(rel)
            tables[t] = (rel, data, dname, F.byml_load(data))
        for clone, src in self.rows:
            for t, (rel, data, dname, rows) in tables.items():
                by_id = {r["__RowId"]: r for r in rows}
                if clone in by_id:
                    continue
                if t == "PouchActorInfo":
                    base = by_id.get(src)
                    if base is None:
                        continue
                    row = copy.deepcopy(base)
                else:
                    base = by_id.get(TEMPLATE)
                    if base is None:
                        self.progress("warning: no %s row for %s" % (t, TEMPLATE))
                        continue
                    row = copy.deepcopy(base)
                    if t == "ActorInfo":
                        s = by_id.get(src, {})
                        for k in ROW_FROM_ITEM:
                            if k in s:
                                row[k] = copy.deepcopy(s[k])
                        row["ActorName"] = s.get("ActorName", src)
                        for k in HEAP_KEYS:
                            if k in s:
                                row[k] = type(row.get(k, s[k]))(max(int(row.get(k, 0)), int(s[k])))
                row["__RowId"] = clone
                keys = [r["__RowId"] for r in rows]
                rows.insert(bisect.bisect_left(keys, clone), row)
        for clone, src in self.auto_rows:       # after the clones: a walk-over copy may copy a clone's rows
            for t, (rel, data, dname, rows) in tables.items():
                by_id = {r["__RowId"]: r for r in rows}
                if clone in by_id or src not in by_id:
                    continue
                row = copy.deepcopy(by_id[src])
                row["__RowId"] = clone
                keys = [r["__RowId"] for r in rows]
                rows.insert(bisect.bisect_left(keys, clone), row)
        for t, (rel, data, dname, rows) in tables.items():
            self.emit(rel, data, F.byml_dump(rows), dname)
