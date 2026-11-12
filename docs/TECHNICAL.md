# Technical notes

How the generator works and why each setting is done the way it is. This is for contributors and curious
testers; you don't need any of it to play. Version numbers like "0.2.2" below refer to private builds made
before the public 0.1.0 release.

## Settings

| Classic setting | Here |
|---|---|
| Logic Rules (Glitchless / No Logic) | Same |
| Guarantee Reachable Locations (All / Required Only) | Same |
| Open Forest (Closed / Closed Deku / Open) | Same (explained below) |
| Zora's Fountain (Closed / Open) | Open = King Zora already moved, for both ages |
| Open Door of Time | Closed / Open, experimental |
| Open Death Mountain | New: the Kakariko gate starts open for child Link (off by default) |
| Skip Child Zelda | New save already owns Zelda's, Malon's and Impa's items; castle quest complete; experimental (explained below) |
| Skip Epona Race | Adult Epona as soon as you own Epona's Song, experimental |
| Shuffle Kokiri Sword | Toggle (on by default) |
| Shuffle Songs (Song Locations / Anywhere) | Same; *Anywhere* is experimental |
| Shuffle Spiritual Stones/Medallions | Vanilla / Dungeon Reward Locations / Anywhere; experimental (explained below) |
| Freestanding items, boss Heart Containers | Toggles |
| Shuffle Freestanding Rupees | New: 109 world rupees become checks (off by default) |
| NPC & minigame rewards, Great Fairies, Skulltula House | Toggles |
| Tokensanity (Off / Dungeons / Overworld / All) | Same |
| Shuffle Ocarinas | Toggle, experimental (explained below) |
| Shopsanity (Off / 1-4 per shop) | Kokiri, Goron, Zora and Bombchu shops, experimental (explained below) |
| Maps & Compasses / Small Keys / Boss Keys | Vanilla / Own Dungeon (keys experimental) / Remove (maps) / **Start With** (maps, explained below) |
| Item Pool (Balanced / Scarce / Minimal) | Same (Plentiful not available) |
| Excluded Locations | Same |
| Quality of Life | **Make All Cutscenes Skippable**, **Bombs Usable Without Goron Bracelet**, **Anju Needs Only 1 Cucco**, **Refills Need Their Item** (all on by default); **Bag Bombs Open Dodongo's Cavern** (off); **Skip Area Intro Cutscenes** (experimental, off); **Small Chests Only**, **Big Poe Buyer Needs Only 1 Big Poe**, **Skip Kaepora Gaebora** (experimental, off) |
| Settings string | Same idea (import / copy) |

The **Not Supported** tab lists the classic options that can't be done yet, and why.

## Open settings and story flags

These settings change the **default save data** (`GameData/GameDataList`). A flag's key is the MurmurHash3
(seed 0) of its name, and new values only take effect on a **new save file**.

| Setting | What changes |
|---|---|
| Kokiri Forest: Closed Deku | `KokiriForest_Npc_Kokiri_007_Child_Blocker_00` False: the invisible wall and Kokiri boy at the exit |
| Kokiri Forest: Open | also `KokiriForest_Npc_Kokiri_Mido_Child_Blocker` False: Mido's wall at the Deku Tree. That flag alone left Mido standing guard (0.2.0 report): his AI schedule keeps him on the path until `Meet_DekuTree_IsAfter_Step02_Exp`. So the opening cutscene (`OpeningEvent`, the node that starts the "Meet the Deku Tree" quest at `Step01`) starts it at `Step03`, the state right after Mido steps aside. This also opens the Kokiri Shop shelves that are sold out before Mido's step |
| Zora's Fountain: Open | The Zora quest (`Get_StoneOfWater`) starts at `Step07`, plus `HavePlayedEvent.Dm_Zora_0010` (the Ruto's-letter scene), `Get_StoneOfWater_ReadRutoLetter` and `..._TalkedZoraAboutRutoLetter` True. The flags alone left King Zora in place (0.3.1 report): his pack reads `Get_StoneOfWater_IsAfter_Step06_Exp`, and showing him the letter (`Get_StoneOfWater:StoneOfWater_ShowLetter`) sets `Step07` before `Dm_Zora_0010` plays. The first arrival in Zora's Domain (`Dm_SY_BancChangeArrive:Goto_ZoraDomain`, after `Dm_Zora_0000`) progresses the quest to `Step03`/`Step03_Impa`, and progressing also moves backwards: King Zora was back in front of Jabu-Jabu after the next load (0.4.3 report). Since 0.4.4 both steps are `Step07` (`qol.patch_open_zora_arrival`) |
| Open Death Mountain | `Npc_Hylia_Soldier_003_GateOpen` True: the flag the Kakariko gate soldier sets when shown Zelda's Letter. The gate shutter (`Obj_Kakariko_SwitchShutter_A_01`) is tied to it through `KakarikoVillage_Child_Static`'s `PlgGdTable`. The same flag opens the Happy Mask Shop in the market. Child Death Mountain then needs no letter in the logic |
| Door of Time: Open | `Market_Child_TimeTempleDoor_Opened` True. The Master Sword pedestal scene may still check story progress, hence *experimental* |
| Skip Epona Race | The computed flag `Get_Epona_IsCompleted_Exp` (which makes adult Epona exist) is rewritten to read `IsGet.Item_Melody_EponaSong` |
| Saria's Song With Just an Ocarina | Adds a computed flag `Rando_HasOcarina_Exp` (`IsGet.Item_Ocarina_Fairy` OR `IsGet.Item_Ocarina_Time`) and re-points the two child Sacred Forest Meadow logic modules (`SacredForestMeadow_Child_Prefab_3265` / `_bbc3`) from `DoorOfTime_IsAfter_Step01_Exp` (met Zelda) to it. The quest-log step the scene advances is already guarded by Darunia's progress, so getting the song early is safe |
| Skip Area Intro Cutscenes (experimental) | `HavePlayedEvent.<intro>` True for 13 first-arrival intros (listed in `rando/gamedata.py`, explained below) |

The logic follows the open settings:
- The forest exit no longer needs the Deku Tree.
- Saria's Song (on by default) needs only the Kokiri Sword (for the meadow) and the ocarina, under any
  forest setting; with the option off it also needs meeting Zelda.
- Beating the Deku Tree needs the Kokiri Sword and the Slingshot. With a **Closed** forest the Slingshot is
  always placed in Kokiri Forest, the Lost Woods or Sacred Forest Meadow (never inside the Deku Tree or
  outside the forest), even with logic set to none, so it cannot be locked behind the forest exit. With
  Closed Deku or Open it can be anywhere.
- An open Zora's Fountain no longer needs Ruto's Letter. The letter could never be delivered there, so it
  would be a dead item. **The generator replaces it with an empty Bottle:**
  - **Freestanding items shuffled:** the letter in the item pool becomes a Bottle.
  - **Freestanding items not shuffled:** the letter's spot at Lake Hylia (`Obj_Bottle_Letter`) is patched
    to hold `Item_Bottle`.
- An open Door of Time makes adult reachable without the stones or the Song of Time.

An area intro is started by the entrance actor in the *previous* area's stage data: its `InitEventName` plays
unless its `InitEventFlag` is true. That flag is either `HavePlayedEvent.<intro>` or a computed
`InitDemo_<area>` flag built from those (for example `InitDemo_LakeHylia` = any Lake Hylia intro played). Some
`InitEventName`s are entries in the shared `Dm_SY_BancChangeArrive` flow that do more than play the intro, so
skipping them would skip that work too. The 13 intros skipped (`AREA_INTROS` in `rando/gamedata.py`) are the
ones whose arrival does nothing else: Kakariko, Graveyard, Hyrule Castle, Lake Hylia, Gerudo Valley, Gerudo
Fortress, Zora's River, Zora's Fountain, Ganon's Castle, Lost Woods (after Saria's Song), and the Fire Temple,
Bottom of the Well and Spirit Temple entrances.

**Experimental:** in-game reports say the intros still play with this on, so setting
`HavePlayedEvent.<intro>` in the default save data isn't enough. Not yet known why: possibly the entrance actors
read a different flag, or the default value doesn't reach the save.

These intros still play, because their arrival entry also advances a quest or sets a flag:
- **Deku Tree:** Get_StoneOfForest, MeetBoss.
- **Death Mountain Trail:** Get_StoneOfFire, DeathMtTrailNpc.
- **Zora's Domain:** Get_StoneOfWater, Step03.
- **Desert Colossus:** SageOfSpirit, Step04.
- **Castle Town:** Goto_HyruleCastle.
- **Death Mountain Crater:** SageOfFire.
- **Ice Cavern:** SageOfWater, Step03.
- **Shadow Temple:** SageOfShadow, MeetBoss.
- **Gerudo Training Ground:** SubEvent_GetIceArrow.
- **Sacred Forest Meadow:** a Moblin position flag.
- **Story intros:** Kokiri Forest, Goron City, Lost Woods, Hyrule Field and Zora's River (Kaepora).

Version 0.1 also skipped several of these, which could have stalled those quests. Use the skip button for
them.

## Maps & Compasses: Start With

Each dungeon's map and compass are plain save flags, `DungeonInfo.<dungeon>.IsGetMap` and `.IsGetCompass`
(found in the room logic modules). **Start With** turns all 20 on in the default save data, covering the ten
dungeons that have them.

The 20 map and compass checks stay shuffled. Their items in the pool are replaced by random bonus items,
seeded from the seed, drawn from `START_WITH_BONUS` in `rando/generator.py`:
- Blue, Red, Purple and Gold Rupees
- 10 Bombchus
- 30 Arrows
- Deku Nuts
- occasionally a Piece of Heart

These bonus items are never progression. They go into the general pool, so the old map and compass checks
can hold anything, and the bonuses can land anywhere.

A few rooms use these flags to mark their room hint as cleared, so those hints are simply marked done from the
start. In Water Temple room 3 the compass flag is also one of the inputs to a moving-platform node. Check that
room in-game.

## Dodongo's Cavern boulder

The child boulder (`DodongoCavern_CrackRock`) is controlled by
`Logic/DeathMountainTrail_Child_Prefab_ffa7.logic.module.ainb`:
- **The boulder:** it disappears (node 7, `ActorLogicDeathProcComplete`) once its break event has run.
- **The trigger:** the event is requested by node 14, `OperateAND`. Its two inputs are the special bomb
  flower's own state (node 6) and an OR of three `BombFruit` sensors.
- **Bag bombs:** a bag bomb can't satisfy that AND. Node 20, a sensor for `Item_Bomb`, isn't wired into it.

The game therefore only opens the cavern with that bomb flower, which needs the Goron Bracelet, so **the
logic now requires the Goron Bracelet** to enter Dodongo's Cavern. Version 0.1 also accepted bag bombs.

**Bag Bombs Open Dodongo's Cavern** (off by default, confirmed in-game in 0.2.1) makes two changes:
- node 14 becomes an `OperateOR` (name and MurmurHash3 name hash);
- its flower-state input becomes node 20's hit output.

A bag bomb near the boulder, or a bomb-flower fruit, then triggers the break. With the option on, the logic
accepts bombs or the bracelet. If the file isn't recognised, generation stops with an error rather than
producing an unsafe seed.

## Songs: the teaching flow gave the vanilla song too

Every song event teaches its melody through the shared `Dm_SY_Ocarina` flow:
- `LearningOcarinaPlayAuto` covers Zelda's Lullaby through the Song of Storms.
- `LearningOcarinaPlayAutoForSeek` covers the six warp songs.

After you play the song back, that flow **adds the song being taught to your inventory** (one
`EventTriggerAddOrRemovePouchContent` per song). This happens on top of the location's own give node, so
every song location gave its vanilla song as well as the randomized item.

Whenever songs are shuffled, those 12 adds are set to `Num = 0`, so a song location only gives its randomized
item. The demonstration still shows the location's original melody, which is only cosmetic. The Scarecrow's
Song is left alone.

## Weird Egg

**Shuffle Weird Egg** (experimental, off) makes the egg a shuffled item:
- **Off:** Malon at Hyrule Castle always gives the Weird Egg.
- **On:** her reward is random and the egg is placed somewhere else. This needs NPC rewards shuffled.

Normally, when the Hyrule Castle quest reaches step `Step03_01`, the flow
`Goto_HyruleCastle:Step03_01_Npc_Navi_StepStart` hatches the egg into the Wake-Up Cucco without checking that
you have it. With the option on, that flow is rewired to check first:
- **The check:** an unreachable pouch query in the same flow (event 41, left over from Malon's dialogue)
  is changed to "owns `Item_WeirdEgg`?", and the step-start query (event 129) now leads into it.
- **Egg owned:** the normal hatch plays, then the quest step advances.
- **No egg:** the hatch is skipped but the quest step still advances, so the story doesn't stall. An egg
  found later should hatch on the game's own egg timer. This is untested.

## Shuffle Ocarinas (experimental)

Both ocarinas join the item pool:
- **Fairy Ocarina:** Saria gives it in her goodbye on the forest bridge. That scene is played by the
  `Goto_HyruleCastle` quest flow (entry `KokiriForest_ArriveLostWood`: `Dm_Kokiri_0150`, then `Dm_Kokiri_0155`,
  which holds the give node). The bridge area trigger (`Logic/KokiriForest_Child_Level_All_02_ddcd`) only
  requests it while `Dm_Kokiri_0150` hasn't been played. Since 0.3.1 that check is pointed at `Dm_Kokiri_0045`
  instead, the greeting outside Link's house that always plays first, so the trigger never fires. The setting
  also starts `HyruleField_ChangeENV` as true, the only flag the flow sets on its way to Hyrule Field. The Fairy
  Ocarina then replaces one junk item in the pool.
  - Up to 0.3.0 the setting started `HavePlayedEvent.Dm_Kokiri_0150` / `_0155` as true instead. Saria's forest
    AI schedule (`Npc_Kokiri_Saria_Child`, schedule "HavePlayedEvent.Dm_Kokiri_0150") and two forest logic
    modules (`..._c64d`, `..._Npc_Kokiri_Saria_Child_a766`) also read that flag, so she was treated as gone from
    the start and the opening greeting played without her. That is now only the fallback if the trigger
    isn't recognised. After the Deku Tree, Saria now waits by the bridge for a goodbye that never comes.
- **Ocarina of Time:** Zelda's gift at the castle moat is the new check "HF Ocarina of Time" (both give nodes
  in `Dm_MelodyGet_Time`, the same flow as the Song of Time). She teaches the Song of Time right after, so the
  logic only expects this check once you own an ocarina.

**Logic:** "has an ocarina" means owning either one. With the setting off it's still "Deku Tree done" (Saria's
gift), plus the Ocarina of Time.

## Skip Child Zelda (experimental)

A new save starts as if Hyrule Castle had already been done as a child:

- **Quests.** Quest progress is one Enum per challenge, found through a computed flag that reads it.
  `Goto_HyruleCastle` (read by `Goto_HyruleCastle_IsCompleted_Exp`) starts at `Complete`, as after meeting
  Zelda. `DoorOfTime` starts at `Step02`, and `Get_StoneOfFire` at `KakarikoVillageNpc`: that's what Impa's
  send-off (`DoorOfTime:DoorOfTime_SendOff`, after her song) sets. Malon's and Talon's schedules read these
  steps (`Goto_HyruleCastle_IsAfter_Step03_02_Exp` and later), so they're at Lon Lon Ranch, and Zelda's own
  schedule hides her once the quest is complete. `HyruleField_ChangeENV` is also set, so Hyrule Field has its
  normal day/night lighting.
- **Scenes.** The quest's scenes count as already seen (`HavePlayedEvent.*`): Kaepora's Hyrule Field intro
  (`Dm_HrlField_0000/0005/0010`), the Market intro (`Dm_HrlCastle_0005`, whose arrival runs
  `Goto_HyruleCastle_EntryMarket`), Talon waking up, the courtyard (`Dm_HrlCastle_0030`..`0060`), Impa's song
  and send-off (`Dm_MelodyGet_Zelda`, `Dm_HrlField_0020`). Kaepora's flow also opens the quest menu, marks the
  field entrance as reached and gives the amiibo pouch entry; those are set directly
  (`UI_IsFinishChallengeMenuOpenEvent`, `HyruleField_ArriveEntrance`, `Pouch_Amiibo`).
- **Items.** Owning an item is its `IsGet.<actor>` flag, plus, for pouch items, a count: `PouchData` is a struct
  with one member per pouch actor, each a one-Int struct holding how many you have. Songs only have the IsGet
  flag. The items at **HC Zeldas Letter**, **HC Malon Egg** and **Song from Impa** are granted this way. So
  those three checks only hold items the save can grant: songs and single key items that have a `PouchData`
  entry. Ammo, capacity upgrades, bottles, hearts, magic, rupees and the stones/medallions are kept out. If no
  progression item lands there, they get a grantable minor item, such as a shield, Farore's Wind or the Stone
  of Agony. In the logic, these three checks are reachable from the start, and "met Zelda" is always true.
- **Unknowns.** It hasn't been tested whether a new save picks up these Enum and Int defaults like it does
  the plain Bools. It also hasn't been tested whether a later scene could still move the castle quest back.
  If Kaepora, Zelda or the Market intro shows up anyway, please report it.
- **Kokiri.** Every child Kokiri's AI schedule ends with a condition on `Goto_HyruleCastle_IsCompleted_Exp`
  (where they stand once you've met Zelda). With the quest complete from the start, Mido left his post while
  his invisible wall (`KokiriForest_Npc_Kokiri_Mido_Child_Blocker`, cleared only by his own sword-and-shield
  talk) stayed, so a Closed forest couldn't reach the Deku Tree (0.4.0 report). Since 0.4.1 that condition is
  removed from the 12 child Kokiri schedules (`Component/AIScheduleParam/Npc_Kokiri_*_Child`), so they follow
  their Deku Tree quest schedules as before the castle trip.

## Shuffle Spiritual Stones/Medallions (experimental)

The remake never checks which stones or medallions you hold. No event flow queries them, and no computed flag
or logic module reads their `IsGet` flags. Story progress follows the quests instead. The Door of Time quest
(the Ocarina of Time at the moat, then the altar) counts the three child-dungeon quests
(`Get_StoneOf*_IsCompleted_Exp`, completed by beating the boss). The later story follows the sage quests.

So since 0.3.2 the logic follows the dungeons, not the items. Going to adult needs the Deku Tree, Dodongo's
Cavern and Jabu-Jabu finished. The bridge and the Light Arrows need the Shadow and Spirit Temples finished.
The medallions are not progression items. The stones are, but only for the Closed Door of Time (see below).

### Closed Door of Time, step by step (checked in 0.4.4)

The `DoorOfTime` quest (`Challenge/DoorOfTime`) is what opens the door. The items you hold don't matter.
1. **Step02** is set by Impa's send-off after Zelda (`DoorOfTime:DoorOfTime_SendOff`). Skip Child Zelda
   presets it.
2. **Step03** is set by `DoorOfTime_CheckStoneNum`, which runs when Dodongo's Cavern or Jabu-Jabu is
   cleared (`Dm_SY_BancChange_EscapeDungeon`). It only reads `Get_StoneOfFire_IsCompleted_Exp` and
   `Get_StoneOfWater_IsCompleted_Exp`. The Deku Tree is a given, because a Closed forest can't be left
   without it.
3. **Step04** is set by the moat scene (`HyruleField_DoorOfTime_Escape`, logic module
   `HyruleField_Child_Prefab_32f7`, `Dm_HrlField_0060`). This is the "HF Ocarina of Time" check.
4. **Step05** is set after Zelda's song (`Dm_MelodyGet_Time` → `Dm_MelodyGet_Time_After`). This is the
   "Song from Ocarina of Time" check.
5. **The altar** (`Obj_TimeTemple_SpiritStoneBase_A_01`, an `OcarinaPoint`) plays
   `Market_Child_DoorOfTime_OpenDoor` when the Song of Time is played at it. Its `ReplaceEventParam` is
   gated by `Market_Child_TimeTempleDoor_OcarinaReacts`, which is DoorOfTime == Step05 AND NOT
   `Market_Child_TimeTempleDoor_Opened`. No ocarina item is checked, so the **Fairy Ocarina opens the door
   as well as the Ocarina of Time**, and no patch is needed.

The logic follows this. `moat` = child in Hyrule Field + the three child dungeons + Zelda met + an ocarina.
It gates both moat checks. `adult` = `moat` + the Song of Time (an ocarina and the song) + the three
Spiritual Stone items. The game doesn't read the stones, but since 0.4.4 they are progression items again
(only for Door of Time: Closed), so a shuffled stone always lands within child reach. A simulation
filled 10 seeds for each of 54 Closed-door combinations: forest Closed/Closed Deku/Open, rewards
Vanilla/Reward/Anywhere, songs Vanilla/Song/Anywhere, ocarinas shuffled or not, Skip Child Zelda on or
off. A child-only sweep (adult forced off) reached the three dungeons, the three stone items, Zelda, an
ocarina, the Song of Time and the moat scene in every seed.

- **Dungeon Reward Locations**: the nine rewards are shuffled among the boss rewards, as before.
- **Anywhere**: the boss reward checks hold any item, and the stones and medallions go anywhere: chests
  (`Item_Stone_*` / `Item_Medal_*` as the drop actor), freestanding spots (a cloned pickup actor, see below)
  or events. They are kept out of shop shelves and excluded locations. The sage cutscenes still play for the
  original dungeon. Whether they behave with a different item in their give node is untested.

## Zelda's Letter

Zelda's reward (**HC Zeldas Letter**) is an NPC check like any other, so she can give a random item. The
letter is then elsewhere, and the logic waits for it before Kakariko's gate and Death Mountain. Impa's song is
a song location. It gets Zelda's Lullaby fairly often, about 30% of seeds, because it's one of the earliest
song checks and the logic needs the Lullaby early.

## Upgrade NPCs and minigames

These one-time rewards are checks. Each normally gives the "Bigger" version of an upgrade, or the "Biggest"
if you already own the Bigger one. Both give nodes carry the random item. Each event has its own one-time
flag, and later wins give its usual rupees.

| Check | Flow | Normal reward | One-time flag | Logic |
|---|---|---|---|---|
| GC Rolling Goron | `Npc_Goron_006_Child` | Bomb Bag | `GoronCity_GetBombBag_fromGoron006` | child Death Mountain + bombs |
| LW Target in Woods | `Dm_LostWood_0040` | Deku Seed Bag | `LostWood_HitTargetOfDekuScrub_FirstClear` | Slingshot |
| Market Shooting Gallery Reward | `MiniGame_HitTarget` | Deku Seed Bag | `MiniGame_HitTarget_HrlCity_Get_BulletBag` | child + Slingshot |
| Kak Shooting Gallery Reward | `MiniGame_HitTarget` | Quiver | `MiniGame_HitTarget_Kakariko_Get_Quiver` | adult + Bow |
| Market Bombchu Bowling Bomb Bag | `MiniGame_BombchuBowling` | Bomb Bag (2nd win) | `MiniGame_BombchuBowling_ClearSecondTime` | child + bombs |
| Market Bombchu Bowling Piece of Heart | `MiniGame_BombchuBowling` | Piece of Heart (3rd win) | `MiniGame_BombchuBowling_ClearThirdTime` | child + bombs |
| GF HBA Quiver | `Minigame_HorsebackArchery` | Quiver | `MiniGame_HorseBackArchery_Get_Quiver` | same as the HBA Piece of Heart |

The upgrades go into the pool as the Bigger Bomb Bag, Bigger Seed Bag and Bigger Quiver, two copies of
each:
- **Chests are progressive:** a chest holding one uses the game's conditional-chest check. You get the
  Biggest version if you already own the Bigger one, and the Bigger one otherwise.
- **Fill prefers chests:** capacity upgrades go into chests when possible, and they never go on shop shelves.
- **Bomb Bags:** the Bigger Bomb Bag is progression, so the tier rule only places it after the normal Bomb
  Bag. The rule now ignores other copies of the same item when it checks.

**Skulltula House wallets** (with Shuffle Skulltula House Rewards, since 0.4.0): the 10 and 30 token
rewards (Adult's and Giant's Wallet) used to stay vanilla. Handed out by an event, a Giant's Wallet found
first could be "downgraded" by the Adult's Wallet later. Now both go into the pool as two Adult's Wallets
that only chests can hold, with the same conditional-chest check as the bags: a chest gives the Giant's
Wallet if you already own the Adult's one. The spoiler lists both as "Adult's Wallet". The logic counts two
of them as the Giant's Wallet (the Zora Tunic can be bought with it).

**Market Big Poe Bottle** (since 0.4.0): the ghost shop in the adult Market (`Npc_Hylia_048_BottleShop`)
gives an Empty Bottle once you've sold Big Poes worth 1000 points (ten Big Poes), and Gold Rupees after
that. Its bottle give node (`Sell_AfterCheckingLoseMoney`) is now an NPC check. Logic: Epona, the Bow and a
bottle.

**Still vanilla: the Deku Theater rewards.** The Skull Mask and Mask of Truth rewards in the Lost Woods
(`LostWood_ScrubForestStageElder_*`) give Stick and Nut bag upgrades. They depend on the mask trading
sequence, which the logic doesn't track. Business Scrubs (seed trading) stay vanilla too.

## Refills need their item

A chest can already say "if the player owns X, give Y, otherwise give Z" (`Drop__CheckActor`,
`Drop__DropActor_Substitute`, `Drop__DropActor`). For example, a vanilla chest gives arrows with the Bow and a
red rupee without. With **Refills Need Their Item**, every randomized chest holding arrows, bombs, Bombchus or
Deku Seeds gets that check against the Bow, the Bomb Bag or the Slingshot, with a blue rupee as the fallback.
Other check types (NPCs, freestanding items, heart containers, Gold Skulltulas) can't test for an item. The fill
therefore puts refills in chests, and any refill that doesn't fit in a chest becomes a blue rupee. Nuts and
sticks need no container and are unchanged.

Unlike the original, the remake keeps Bombchus in the Bomb Bag: `Item_Bombchu`'s PouchContentParam has
`MaxNumGameData: "Bomb"` and `SmallBagActor: Item_BombBag_Small`. Bombchus picked up without a bag show the
"Five Bombchus" message but the count stays at 0 (reported in-game from a freestanding rupee spot).

## Time of day before the Deku Tree (open forest)

With Open or Closed Deku forest, time seemed not to pass in Hyrule Field until the Deku Tree was done.

**Cause (found in 0.2.4):** Hyrule Field's `WorldParam` (`ConditionEnvTimePalette`) and two
`EnvPaletteTimeTableChangeArea` actors switch on the flag `HyruleField_ChangeENV`. While it's false, the
field uses `MainField_Bluesky_First`, a light table with `IsForceMainLight: true` that pins the sun at one
angle. Vanilla sets the flag in Saria's bridge goodbye (`Goto_HyruleCastle`, right before the banc change to
Hyrule Field), which you only see after the Deku Tree. Leaving an open forest earlier kept the field on the
fixed sun.

**Fix:** with Open or Closed Deku forest (and with Shuffle Ocarinas, which skips that scene), the flag starts
as true, so Hyrule Field uses its normal day/night table from the first visit. The trade-off is that the
special first-visit lighting is gone. This hasn't been tested in-game.

Earlier versions documented this as a game-code limit. Quest rules, area files and cutscene commands really
don't stop the clock; the cause was this lighting flag.

## Using items early: the bomb fix

In the remake, a bomb pulled from the Bomb Bag is a *liftable* object. Lifting it needs the strength the
**Goron Bracelet** grants (lift grade `3655598229`). Without the bracelet, Link starts the pull-out animation
and then nothing happens. Vanilla never hits this, because you always get the bracelet before the Bomb Bag.

**Bombs Usable Without Goron Bracelet** lowers the required lift grade of bag bombs (`Item_Bomb`'s
LiftableParam) to the grade pots, small rocks and Bombchus use (`3069107721`). The change is made in every
pack that carries a copy of that shared resource. Bomb Flowers use their own parameter, so they still need the
bracelet, as in vanilla. With the option off, the logic requires the Goron Bracelet before bombs count.

I checked every other item ability the remake grants on pickup:
- **Magic**: every magic item (Din's, Farore's, Nayru's, the Lens and all magic arrows) unlocks magic by itself.
- **Dive depth** (scales) and **adult gauntlet strength**: covered by the tier rule, which only places the
  Golden Scale or Golden Gauntlets where the Silver version is already required.

No other item depends on a different item being found first.

## Items lying in the world (freestanding, rupee, Heart Container and Gold Skulltula spots)

The game has two kinds of item actors:
- **`Obj_*` pickups** (`Obj_Item_Base`): rupees, Pieces of Heart, Heart Containers, tokens, small keys, shields,
  and Lake Hylia's `Obj_Arrow_Fire`. You walk up to them and collect them.
- **`Item_*` actors** (`Item_EventObject_Base`): the model an item-get cutscene puts in Link's hands. Most key
  items only have one of these.

Placed in the world, an `Item_*` actor just lies there and can't be collected. Examples are a Megaton Hammer
on a rupee spot, or Light Arrows dropped by a Gold Skulltula.

For every item that lands in such a spot without an `Obj_` actor of its own, the generator builds a new pickup
actor, `Obj_Rando_<item>` (`rando/pickups.py`):
- **Pack:** a copy of the `Obj_Arrow_Fire` pickup pack plus the item's own component files. A new ActorParam
  takes its model, name, animation, parameter-table and effect references from the item. A new
  PouchContentParam inherits the item's settings, with `PouchActor` set to the item.
- **RSDB:** `ActorInfo` and `GameActorInfo` rows cloned from `Obj_Arrow_Fire`, using the item's model fields and
  its `ActorName`, so the pickup shows the item's own name and get message. There is also a `PouchActorInfo`
  row cloned from the item. Rows are inserted in sorted order.
- **Size table:** entries for the new pack and the new files inside it.

The spot's own save flag, its actor hash, still records the pickup.

**Walk-over pickup (0.4.4).** Whether a pickup needs A is set by its `AttentionSenderRef`. `Obj_Item_Base`
uses `AutoPickUpItem`: touching the item collects it, like a rupee. `Obj_Arrow_Fire`, and so every
`Obj_Rando_` clone, overrides it with `PickUpItem`, which needs A. That made an item dropped by a Gold
Skulltula on a vine impossible to collect without the Boomerang or Hookshot, because Link can't press A
while climbing. Every shuffled item placed in the world now gets an `Obj_RandoAuto_<item>` copy of its
pickup:
- **Pack:** the same pack, with a new ActorParam whose `AttentionSenderRef` is `AutoPickUpItem`. The
  `AutoPickUpItem`, `Auto_Item_Catch` and `LookOnly_Middle_Small` files are copied from `Obj_Rupee_Green`.
- **RSDB:** `ActorInfo`, `GameActorInfo` and `PouchActorInfo` rows are copied from the pickup it copies.

This covers freestanding spots, rupee spots and Gold Skulltula drops. Pickups that already collect on touch
are used as they are: rupees, small keys, shields, the Ocarina of Time and tokens. So is a spot that keeps
its vanilla item.

The walk-over check reads the `IsEnableAttention` blackboard flag, which the `DropItem` AI raises.
`Obj_Heart_Piece` and `Obj_Bottle_Letter` run their own AI, so they keep needing A. On the ground that's
fine, but in mid-air it isn't, so the fill never puts a Piece of Heart or Ruto's Letter on a Gold Skulltula
(`GS_FORBIDDEN` in `rando/generator.py`).

**Gold Skulltula drops** work differently, because a dropped actor has no save flag of its own. Normally the
token sets the Skulltula's flag: the Skulltula writes its flag into the token's `GoldTokenGmdHash` blackboard
key, the token's AI sets it on pickup, and the Skulltula's own death procedure leaves it alone
(`IsSetGmdRespawnFlagToFalse: False`). A shuffled drop is a plain pickup, so before 0.2.2 the Skulltula and its
item came back whenever the room reloaded.
- **0.2.1** gave the drop the token's AI. In-game the drop then didn't spawn at all, so that was reverted.
- **0.2.2** (with Tokensanity on) sets `IsSetGmdRespawnFlagToFalse: True` in
  `Enemy_Skulltula_Gold`'s death procedures, so killing a Skulltula is permanent. The catch: an item you don't
  pick up before leaving the room is gone. This applies to every Gold Skulltula, including ones that still drop
  a real token.

The earlier attempt at this (giving `Item_Arrow_*` packs the Boomerang's physics) didn't make anything
collectible, and it has been removed.

## Big Poe buyer needs only 1 Big Poe (experimental)

The ghost shop in the adult Market (`Npc_Hylia_048_BottleShop`) gives 100 points per Big Poe. Before each sale
its flow compares `GhostShop_CouponNum` with 900 (`EventQueryIsGameDataInt`): below that it's a normal sale, at
900 or more it's the final sale (`Sell_AfterCheckingLoseMoney_900`), which completes `SubEvent_GhostShop` and
gives his reward (the **Market Big Poe Bottle** check). The option sets that 900 to 0, so the first Big Poe sold
is the final sale. The logic still expects Epona, the Bow and a bottle.

## Skip Kaepora Gaebora (experimental)

His forced first talks count as already seen (`HavePlayedEvent.<scene>` True). Each one is started by stage logic
(`HoldGameDataHavePlayedEvent` in a `*_Prefab` logic module) or by `Dm_SY_BancChangeArrive`, only while that flag
is False:

| Scene | Where |
|---|---|
| `Dm_LostWood_0000` | Outside Kokiri Forest (the Lost Woods bridge) |
| `Dm_HrlField_0010` | First Hyrule Field talk (`Goto_HyruleCastle:Goto_HyruleCastle_Kaepora_00`) |
| `Dm_HrlField_0030`, `Dm_HrlField_0040` | Hyrule Field (0040 after visiting Gerudo Valley) |
| `Dm_ZoraRiver_0000`, `Dm_ZoraRiver_0005` | Zora's River |

The first Hyrule Field talk also opens the quest menu (`UI_IsFinishChallengeMenuOpenEvent`), sets
`HyruleField_ArriveEntrance` and gives the amiibo menu item (`Pouch_Amiibo`); those are set too, as Skip Child
Zelda does. Its quest step (`Goto_HyruleCastle` Step02) is left alone: only two NPCs' dialogue reads it, and
entering the Market moves the quest on to Step02_01. Left alone:
- `Dm_HrlCastle_0000` in front of Hyrule Castle. It's an entrance `InitEvent`, the same mechanism as the area
  intros, which didn't skip in testing.
- `Dm_HrlField_0080` (sets `DreamWorld_Open`).
- His optional rides at Lake Hylia and Death Mountain, which only start when you talk to him.

## Shopsanity

A shop shelf is a generic `Shop_Item_Base` actor whose pack says what it sells. For each randomized shelf the
generator rewrites:
- inside the shelf's pack: the `PouchContentParam` (now a single `PouchActor`: the new item), the model and
  animation, and the price (10-99 rupees, so a child's wallet is enough);
- the shelf's row in `RSDB/ActorInfo`: model fields, and memory sizes raised to the larger of the two;
- the shelf's shop text (name, shop caption, get message) in **all 16 languages**, copied from the new item's
  own text in that language file.

Only shelves that appear in exactly one shop are used, because editing a shelf type changes every placement of
it: Kokiri Shop 3, Goron Shop 3, Zora Shop 2, Bombchu Shop 8. The Deku Shield and the tunics are never touched,
since the logic relies on buying them. Shelves restock, so stackable items never go on a shelf: Pieces of Heart,
Heart Containers, tokens, bottles, the Weird Egg and Zelda's Letter. A shelf that rolls junk keeps its normal
goods.

## Anju needs only 1 cucco

The minigame logic (`Logic/MiniGame_CatchCucco_c69b.logic.module.ainb`) finishes the minigame when a compare
node's constant input `Int_A = 7` equals the live fence count. The option sets that constant to 1. Anju's
event flow also keeps a "cuccos left" counter that starts at 7 and is compared with 7 for her dialogue, so
both of those become 1 too. Her reward stays randomized.

## Small Chests Only (experimental)

Off by default (`rando/qol.py`, `patch_small_chests`). Two changes:

- **Model.** Every stage actor that is a big chest (`Obj_TBox_A_02`) or a Boss Key chest (`Obj_TBox_A_03`),
  or their `_NoBake` versions, becomes the small chest (`Obj_TBox_A_01` / `Obj_TBox_A_01_NoBake`). The big
  chests' packs are built on the small one (they carry its ActorParam), so only the actor's `Gyaml` changes:
  its hash, links, `Dynamic` drop fields and save flag stay the same. That's 51 placements, counting the
  child and adult copies of a stage separately.
- **Opening sequence.** The sequence comes from the chest's `GetEventName` blackboard string:
  `Dm_SY_TreasureboxSmall` for the small chest, `Dm_SY_Treasurebox` (the long one) for the big chest. About
  30 big chests override it per placement (`Dynamic.GetEventName`, a row of `RSDB/EventSetting`) with a script
  that ends in a jump (`EventTransition`) to `Dm_SY_Treasurebox`.
  - 0.4.0 only changed the model, so those chests (the Deku Tree Slingshot chest, for one) still played the
    long sequence.
  - 0.4.1 pointed those jumps at `Dm_SY_TreasureboxSmall`. The chests then couldn't be opened at all.
  - Since 0.4.2, scripts that only add a Navi line or a camera move (the `NaviChat` map/compass/item lines,
    the Forest Temple Bow and Boss Key, the Goron Bomb Bag, Hover Boots, Mirror Shield, Lens of Truth and
    Water Temple Longshot chests) are removed from the chest, so it opens like any small chest. That's how
    the randomized Kokiri Sword chest already works. The Navi line is lost. Chests whose script runs story
    events stay vanilla big chests (`BIG_CHEST_STORY_EVENTS`): Nabooru taken at the Colossus, the Serenade of
    Water, the two Ruto chests in Jabu-Jabu, Dampé's race prize, Ganon's Castle's Golden Gauntlets, the Ice
    Arrow side quest and the vanilla Kokiri Sword. That's 40 small and 11 big placements.
  - Major items still get Link's item-held pose and Navi's reaction in the small sequence; that part follows
    the item, not the chest.

Shop chests (Treasure Chest Game) and the invisible Lens chests are left alone. Untested: whether the big
chests' stage collision or lighting ("Bake") expects the bigger model.

## Requested but not possible from the game data

- **Keysanity (keys anywhere).** The remake has one generic small key and one generic boss key (Ganon's
  included). The stage you pick a key up in decides which dungeon it counts for (`RSDB/DungeonParam` defines
  these per stage), and no event action can add a key to a different dungeon. A Forest Temple key found in
  Kakariko would count for Kakariko. **Own Dungeon** (Dungeon Items tab) is the most that works.
- **Bunny Hood speed boost.** Running speed comes from the animations; the only speed value in the data is a
  global `GroundSpeedScale`. Masks have no movement parameter. Equipment effects are hashed names
  (MurmurHash3), and the one I could decode is the Zora Tunic's `UnderwaterBreathing`. There's no speed effect
  I can confirm the engine supports, and the executable uses a compression format I can't read.
- **Fast climbing.** The climb speed is computed by the player code and handed to the climb animation at
  runtime (`PrevClimbSpeedRate`); no data file holds it.
- **Scrubsanity.** The remake replaced the classic scrub shops with the Scrub Business Seed trading system.
  Their goods and prices are fixed per item type inside one shared event flow, and they restock. The only
  one-time scrubs sell capacity upgrades (kept vanilla) and Pieces of Heart, and those share a single event
  node.
- **Auto-skip all cutscenes.** Items, songs and story flags are handed out inside the cutscene flows, so
  removing cutscenes wholesale would lose them. Every cutscene can be skipped with the button, and the
  side-effect-free area intros are skipped automatically.

## Cutscene skipping

The remake already lets you skip almost every cutscene. Only one shared setting
(`Event/EventSetting/EventSettingComponent/SkipSetting/DisableSkip...bgyml`) blocks skipping, and the opening
cutscene, the staff credits and the title-screen demos use it. **Make All Cutscenes Skippable** writes a copy
of that file with skipping allowed.

Cutscenes aren't removed outright, because the remake grants items and sets story flags inside them.

## What gets randomized (about 200 locations by default, up to about 480)

- **178 chests**, including invisible Lens chests and conditional chests. The conditional "only if you don't
  own X" behaviour is removed when a conditional chest is randomized.
- **18 freestanding items**: Pieces of Heart, Fire Arrows at Lake Hylia and Ruto's Letter. Freestanding small
  keys follow the Small Keys setting.
- **8 boss Heart Containers**, **100 Gold Skulltulas** (Tokensanity only)
- **59 event rewards**: 12 songs, 9 dungeon rewards, 6 Great Fairies, 29 NPC and minigame rewards (including
  the upgrade NPCs and minigames listed below), and 5 Skulltula House rewards
- **Up to 12 shop shelves** (Shopsanity)
- **109 freestanding rupees** (**Shuffle Freestanding Rupees**, off by default):
  - **Where:** green, blue, red and purple rupees in Hyrule Field (26), Zora's River (20), Kokiri Forest
    (17), Zora's Fountain (16), Death Mountain Crater (10), the Graveyard (8), Death Mountain Trail (6) and
    Zora's Domain (6).
  - **Not the Deku Tree scrub drops** (since 0.4.3): the three `ScrubDekuRupee_*` rupees appear inside the
    beaten Deku Scrub's flower (Presence `Enemy_Scrub_Deku_ItemDrop_0N`). A rupee there can be collected,
    but an item placed there sat behind the flower's collision and couldn't be picked up (0.4.2 report).
  - **Collected once:** each rupee placement has its own save flag in `Bool64bitKey`, like a freestanding
    Piece of Heart, so an item placed there doesn't respawn.
  - **Patching:** the actor's `Gyaml` is swapped, and placements shared by the child and adult stages
    count as one check.
  - **Logic:** the six Zora's Domain rupees lie at the bottom of the pool, so they need the Silver Scale
    as child or the Iron Boots as adult. The others follow their area's rules.
  - **Left alone:** silver rupees are puzzle pieces with linked counters, so they aren't touched.

These are always left vanilla: the Ocarinas (unless Shuffle Ocarinas is on), the Master Sword, the adult trade sequence's items (its final reward, the Biggoron's Sword, is the **DMT Biggoron** check), the Treasure Chest Game (its prize chest shows its prize through a minigame-only preview model), the other capacity
upgrades (bags and quivers), the bazaar and potion shops, Business Scrubs, cows and the Treasure Chest Game. The
trap chests and the Hall of Fallen Foes are left untouched.

## How it works

| File | Role |
|---|---|
| `rando/formats.py` | zstd with the game's ZsDic dictionaries; SARC read/rebuild (byte-identical on unchanged archives); a type-exact BYML v7 reader/writer (both byte orders); BFEVFL reader and string-parameter patcher; RESTBL; MSBT read and text replace |
| `rando/world.py` | Scans the stage files, event flows and shops for item locations, reads names, and picks the right actor name for each item in each context |
| `rando/logic.py` | Region/age logic modelled on the classic randomizer |
| `rando/generator.py` | Assumed fill (most constrained items first), playthrough validation, patch writing, spoiler |
| `rando/shops.py` | Shopsanity shelf, actor-table and shop-text patcher |
| `rando/qol.py` | Quality-of-life patches (Anju) |
| `rando/gamedata.py` | Default save-data edits (open settings, Epona, area intros) |
| `rando/gamecheck.py` | Game version check: SHA-256 of `exefs/main` against the supported-version list |
| `rando/gui_glass.py` | The Raven GUI (`ootr_remake.pyw` starts it) |

How each location type is patched:
- **Chests**: `Dynamic.Drop__DropActor` in the stage file.
- **Freestanding items and Heart Containers**: the actor's `Gyaml` is swapped.
- **Gold Skulltulas**: the enemy's `Dynamic.Drop__DropActor`.
- **Event rewards**: the item string parameter of each "give item" node is re-pointed to a new string
  appended to the event flow.
- **Shop shelves**: see Shopsanity above.

Every changed file's entry in the resource size table is grown by the amount the file grew.

### Logic

The logic is **conservative**:
- Every location in a dungeon requires everything needed to finish that dungeon.
- Overworld grottos and hidden spots assume explosives, plus a scale or Hookshot where relevant.
- The higher tier of a two-tier item (Longshot, Golden Gauntlets, Golden Scale) is only placed where the
  logic already requires the lower tier, so it can't be picked up first.

Seeds are therefore beatable even where the remake's exact room layouts aren't modelled. The cost is that some
items always show up later than they strictly need to.

## Status / caveats

- **Testing in-game has started.** The first report found the bomb issue, which is fixed above. Everything
  else is verified offline only: every patched field reads back as the item in the spoiler, and every modified
  file parses again.
- Settings marked *experimental* (Shopsanity, Shuffle Ocarinas, songs Anywhere, own-dungeon keys) are the least
  certain.
- Chest "get" cutscene events are kept, because they carry story flags. The exception is the Kokiri Sword chest's `Get_StoneOfForest_GetSword`: its Dm_Kokiri_0063 scene hands Link an unsaved sword (gone after reloading), so a randomized sword chest opens like a normal chest. A chest that used to hold, say, the Bow
  may still play the Bow's follow-up dialogue.
- If something breaks, the spoiler tells you which location holds which item.

## Tests

```
python tests/vanilla_test.py "D:/path/to/romfs"   # informational: shows which regions the logic reaches with vanilla items
```
