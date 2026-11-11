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

    @staticmethod
    def needs_clone(actor):
        return not actor.startswith("Obj_")

    def world_actor(self, actor):
        """Actor to place in the world for `actor` (a world-context actor name from World.actor_for)."""
        if not self.needs_clone(actor):
            return actor
        if (actor, False) not in self.made:
            self.made[(actor, False)] = self._build(actor)
        return self.made[(actor, False)] or actor

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
        if not self.rows:
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
        for t, (rel, data, dname, rows) in tables.items():
            self.emit(rel, data, F.byml_dump(rows), dname)
