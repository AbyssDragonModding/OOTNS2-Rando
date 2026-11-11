"""Sanity check: the vanilla item placement must be beatable under the randomizer logic.
Usage: python tests/vanilla_test.py <path to romfs>"""
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rando.world import World
from rando import generator as G, settings as S

w = World(sys.argv[1], progress=lambda m: None)
plan = G.Plan(w, S.normalize({}))
f = G.Filler(plan, random.Random(0))
van = {l.id: l.vanilla for l in w.locations}
state, got, sph = f.sweep([], contents=van)
print("vanilla beatable:", state.win, "spheres", len(sph), "reached", len(got), "/", len(van))
for k in ["adult", "deku_done", "dodongo_done", "jabu_done", "forest_done", "fire_done", "water_done",
          "shadow_done", "spirit_done", "ice_done", "gtg_done", "botw_done", "wasteland", "bridge", "ganon_done"]:
    print("  %-14s %s" % (k, getattr(state, k)))
miss = [l for l in w.locations if l.id not in got]
print("unreached by region/kind:", Counter((l.region or "event", l.kind) for l in miss).most_common(40))
print("unreached events:", [l.name for l in miss if l.kind == "event"])
print("items held:", sorted(i for i in state.items if state.items[i]))
sys.exit(0 if state.win else 1)
