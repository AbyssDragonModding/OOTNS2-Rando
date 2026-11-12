# OoT (Switch 2) Item Tracker

An item tracker for the Ocarina of Time remake, built with the
[Raven](https://github.com/oscar-soirey/Raven) GUI library. The layout is
defined in Raven XML (`ui/`).

**No game files are included.** On first start the tracker asks for the romfs
folder you extracted from your own copy of the game. It then extracts the
icons from it into `icons/` (colour + grayscale) with `extract_item_icons.py`.
`icons/` is git-ignored: never share it.

## Run

Needs Python 3.14+ (stdlib zstd) and a Vulkan-capable GPU driver.

```
pip install -r requirements.txt
python tracker.pyw
```

## Use

- **Left click**: next tier / +1 (e.g. Deku Shield -> Hylian -> Mirror).
- **Right click**: previous tier / -1. From the first tier it goes back to the
  grayscale *not acquired* icon; right clicking that does nothing.
- **Shift + click** on counters (Skulltulas, heart pieces, keys...) steps by 5.
- Hover a cell to see what it is at.
- **File** menu: New, Open, Save, Save As (JSON). The last save reopens on start.
  *Link romfs folder / re-extract icons* runs the extraction again.

## Files

| File | What |
|---|---|
| `tracker.pyw` | the app |
| `items.py` | every cell: its tiers or counter and icons |
| `ui/tracker.xml` | main window layout |
| `ui/setup.xml` | romfs prompt |
| `ui/widgets.xml` | `<ItemCell>` and `<Section>` templates |
| `extract_item_icons.py` | icon extractor (also usable on its own: `--romfs PATH --grayscale`) |

To add or reorder a cell: add it to `items.CELLS`, then put
`<ItemCell Item="its_id"/>` where it should go in `ui/tracker.xml`.
