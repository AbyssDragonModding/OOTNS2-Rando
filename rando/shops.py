"""Shopsanity: re-target shop shelf actors to sell randomized items.

A shelf (Shop_*) is a generic Shop_Item_Base actor whose pack says what it sells. To sell a new
item we rewrite, inside the shelf's own pack:
  * PouchContentParam  -> the new item's pouch parameters + PouchActor = the new item actor
  * ModelInfo / AnimationParam -> the new item's model so the shelf shows it
  * PriceParam -> the new price
and update the shelf's row in RSDB/ActorInfo (model + heap sizes) and the shelf's shop text
(Shop_X_Name / _ShopCaption / _GetCaption / _GetMessage) in every language, copying the new
item's own text from the same language file. Everything is read from the user's romfs.
"""
import copy
import os

from . import formats as F


def _work_to_pack_path(work_path):
    """'Work/Component/X/Y.game__x.gyml' -> 'Component/X/Y.game__x.bgyml'."""
    p = work_path[5:] if work_path.startswith("Work/") else work_path
    return p[:-5] + ".bgyml" if p.endswith(".gyml") else p


def _ref_path(ref):
    """'?Component/X/Y.bgyml' -> 'Component/X/Y.bgyml'."""
    return ref[1:] if ref and ref.startswith("?") else ref


def _actor_components(files, actor):
    """Merged Components of an actor's ActorParam, following $parent inside the pack."""
    comps, path, seen = {}, "Actor/%s.engine__actor__ActorParam.bgyml" % actor, set()
    chain = []
    while path and path in files and path not in seen:
        seen.add(path)
        doc = F.byml_load(files[path])
        chain.append(doc.get("Components", {}))
        parent = doc.get("$parent")
        path = _work_to_pack_path(parent) if parent else None
    for c in reversed(chain):
        comps.update(c)
    return comps


def _copy_with_parents(src_files, dst_add, dst_files, path):
    """Copy `path` and its $parent chain from src pack into the destination pack if missing."""
    while path and path in src_files:
        if path not in dst_files and path not in dst_add:
            dst_add[path] = src_files[path]
        parent = F.byml_load(src_files[path]).get("$parent")
        path = _work_to_pack_path(parent) if parent else None


class ShopPatcher:
    def __init__(self, world, emit, progress=print, read=None):
        self.world, self.zs, self.emit, self.progress = world, world.zs, emit, progress
        self.read = read or world.zs.read
        self.actor_rows = {}      # shelf type -> target actor (for ActorInfo)
        self.text_jobs = {}       # shelf type -> target text base name

    def patch_shelf(self, shelf, target, price):
        zs = self.zs
        rel = "Pack/Actor/%s.pack.zs" % shelf
        orig, dname = self.read(rel)
        files = F.sarc_files(orig)
        tfiles = F.sarc_files(zs.read("Pack/Actor/%s.pack.zs" % target)[0])
        scomp = _actor_components(files, shelf)
        tcomp = _actor_components(tfiles, target)
        replace, add = {}, {}

        # what is sold
        pc_path = _ref_path(scomp["PouchContentRef"])
        t_pc_path = _ref_path(tcomp.get("PouchContentRef"))
        if t_pc_path and t_pc_path in tfiles:
            pc = copy.deepcopy(F.byml_load(tfiles[t_pc_path]))
            parent = pc.get("$parent")
            if parent:
                _copy_with_parents(tfiles, add, files, _work_to_pack_path(parent))
        else:
            pc = {"$parent": "Work/Component/PouchContentParam/Default.game__component__PouchContentParam.gyml"}
        for k in ("IsBundle", "BundleActor", "BundleActorNum", "BundleIsUseUniqueName", "SmallBagActor",
                  "MaxNumGameData", "EnableStock"):
            pc.pop(k, None)
        pc["PouchActor"] = "Work/Actor/%s.engine__actor__ActorParam.gyml" % target
        pc["IsNotOpenStockNumDisplay"] = True
        replace[pc_path] = F.byml_dump(pc)

        # how it looks
        for key in ("ModelInfoRef", "AnimationRef"):
            spath, tpath = _ref_path(scomp.get(key)), _ref_path(tcomp.get(key))
            if spath in files and tpath in tfiles:
                doc = copy.deepcopy(F.byml_load(tfiles[tpath]))
                if doc.get("$parent"):
                    _copy_with_parents(tfiles, add, files, _work_to_pack_path(doc["$parent"]))
                replace[spath] = F.byml_dump(doc)

        # what it costs
        gpt = F.byml_load(files[_ref_path(scomp["GameParameterTableRef"])])
        price_path = _ref_path(gpt.get("Components", {}).get("PriceParam"))
        if price_path in files:
            pr = F.byml_load(files[price_path])
            pr["BuyingPrice"] = int(price)
            replace[price_path] = F.byml_dump(pr)

        self.emit(rel, orig, F.sarc_rebuild(orig, replace=replace, add=add), dname)
        self.actor_rows[shelf] = target
        self.text_jobs[shelf] = target

    def finish(self):
        if not self.actor_rows:
            return
        self._patch_actor_info()
        self._patch_text()

    def _patch_actor_info(self):
        rel = self.world._find("RSDB", "ActorInfo")
        orig, dname = self.read(rel)
        rows = F.byml_load(orig)
        by_id = {r["__RowId"]: r for r in rows}
        for shelf, target in self.actor_rows.items():
            s, t = by_id.get(shelf), by_id.get(target)
            if s is None or t is None:
                self.progress("warning: no ActorInfo row for %s / %s" % (shelf, target))
                continue
            for k in ("FmdbName", "ModelProjectName", "AnimationResources", "ModelAabbMax", "ModelAabbMin"):
                if k in t:
                    s[k] = copy.deepcopy(t[k])
            for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):
                if k in t:
                    s[k] = type(s.get(k, t[k]))(max(int(s.get(k, 0)), int(t[k])))
        self.emit(rel, orig, F.byml_dump(rows), dname)

    def _patch_text(self):
        rows = {r["__RowId"]: r for r in F.byml_load(self.zs.read(self.world._find("RSDB", "ActorInfo"))[0])}
        mals = os.path.join(self.world.romfs, "Mals")
        for fn in sorted(os.listdir(mals)):
            if not fn.endswith(".sarc.zs"):
                continue
            rel = "Mals/" + fn
            orig, dname = self.read(rel)
            files = F.sarc_files(orig)
            msbt = files.get("ActorMsg/PouchContent.msbt")
            if msbt is None:
                continue
            labels, texts = F.msbt_raw(msbt)
            new = {}
            for shelf, target in self.text_jobs.items():
                base = rows.get(target, {}).get("ActorName", target)

                def raw(*suffixes):
                    for suf in suffixes:
                        lab = "%s_%s" % (base, suf)
                        if lab in labels:
                            return texts[labels[lab]]
                    return None
                wanted = {"Name": raw("Name"), "ShopCaption": raw("ShopCaption", "Caption", "Name"),
                          "GetCaption": raw("GetCaption", "Caption", "Name"), "GetMessage": raw("GetMessage", "Name")}
                for suf, value in wanted.items():
                    lab = "%s_%s" % (shelf, suf)
                    if value is not None and lab in labels:
                        new[lab] = value
            if new:
                files_new = {"ActorMsg/PouchContent.msbt": F.msbt_set_raw(msbt, new)}
                self.emit(rel, orig, F.sarc_rebuild(orig, replace=files_new), dname)
