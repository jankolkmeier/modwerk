# The one-cable hardware matrix

One remix, many configurations, on a unit with a single USB cable to a Mac and
nothing else: program change over USB MIDI selects a layout, MIDI START and a
host clock play it, the unit's USB audio stream is the capture, and LOAD METER
(vendor request `0xc0/0x57`) is the load readout. First run 24 Oct 2026
(`octabam-bus`, image A1, 28 layouts, about 10 minutes, no crash or freeze).
A step-by-step session guide is [HARDWARE_TESTING.md](HARDWARE_TESTING.md).
Tools: `tools/hw/ot_matrix.py`, `ot_stimuli.py`, `load_meter.py`,
`usb_transport_probe.py`, `usb_counters.py`. What none of it proves is under
"Limits".

## Once

- A fresh project made on the unit (PROJECT > NEW), copied off the card, and
  `python3 tools/hw/ot_matrix.py audit <dir>` finding nothing. Projects that
  descend from a working project fail the audit and are refused by `--clean`.
- `.venv/bin/python3 -m pip install pyusb libusb-package sounddevice numpy`
  (`brew install portaudio` for `sounddevice`).
- The unit's image: `make image REMIX=<remix> BUILD=<tag>`, the `.bin` on the
  card root, PROJECT > SYSTEM > OS UPGRADE (BUILDING.md section 5). Leave one
  `.bin` on the root: the upgrade took the first by name when there were
  several.

## Per remix

```bash
python3 tools/hw/ot_matrix.py plan <remix>                 # the layouts, and how many projects
python3 tools/hw/ot_matrix.py proj <fresh> <dest-prefix> <remix> --clean \
        --stimuli hits,pink,two_tones,sweep                # <dest-prefix>_01 ... up to 31 layouts each
```

Copy each `<dest-prefix>_NN` to the card (PRESETS/), load it on the unit, then:

```bash
python3 tools/hw/ot_matrix.py run <dest-prefix>_NN <label> [--only 0,5-9]
python3 tools/hw/usb_transport_probe.py      # START / STOP over USB, one layout, before a long run
python3 tools/hw/load_meter.py --for 10      # LOAD METER summary
```

`python3 tools/hw/ot_matrix.py report out/hw/matrix/<label>/report.json ...` prints a Markdown table per run.
`run` adds layout 0 (BASE) when `--only` leaves it out. Reports go to
`out/hw/matrix/<label>/report.json`: per layout the flags, the audio metrics,
LOAD METER's summary and its per-reading series; flagged layouts also leave a
WAV. A run holds the unit on one layout per 12 s of play, 3 s of tail and any
wait for the previous tail to fade (up to 15 s).

Layouts per remix, from `plan` (24 Oct 2026): `octabam-core` 24, `octabam-inserts`
70 (110 with `--pairs`), `octabam-bus` 27, plus BASE in each project. Two
cautions before a run: the `dear` settings can put a constant, up to full-scale
DC on MAIN, CUE and the headphones after STOP (below), so mute or turn down
what is connected; and when the card is mounted on the Mac, unmount it (not
eject) before leaving DISK MODE on the unit, since a read/write mount with
pending Mac writes coincided with two freezes (24 Oct 2026,
`FAILURE_MODES.md`).

## Predicting the combinations

A pair (an FX1 and an FX2 effect on the same track) or a split (one effect on
tracks 1-4, another on 5-8) is not run by default. LOAD METER reports each of
the 16 effect slots' cost, and a core's busy time is its base plus the sum of
its slots' costs: on the first runs (24 Oct 2026, 97 layouts of `octabam-bus`
and `octabam-inserts`) the sum matched the measured per-core busy to 0.14
points at the 95th percentile; the worst misses were layouts with one of 16
slots missing from the window. The same effect costs the same on either core's
slots (within 1.5 %) and on FX1 or FX2 (within 0.1 point).

```bash
python3 tools/hw/ot_matrix.py predict octabam-inserts \
        --reports out/hw/matrix/ins01/report.json out/hw/matrix/ins02/report.json out/hw/matrix/ins03/report.json \
        --select pick.json
python3 tools/hw/ot_matrix.py proj <fresh> <dest-prefix> octabam-inserts --clean --stimuli ... \
        --pairs --split --select pick.json
```

`predict` ranks every pair and split layout by predicted core busy and writes
the ones at or above `--threshold` (0.85) plus `--validate` (6) spread over the
rest, to check on the unit that the sum holds. It does not predict the
ColdFire's share (EUCLID's hook adds about 7 points), audio faults that need
the combination, or what the unit does past 100 % busy. A layout predicted
over 100 % overloaded the unit (24 Oct 2026: SPECTRUM FX1 + LOFI2 FX2 `dear`, predicted 105 %; the frame
interrupt fell to half rate and stayed there), so `predict` leaves those out unless `--include-overload`.
No single-slot run has gone past 98.8 %.

## Tests not yet run

1. **The heaviest combinations of the stock effects: slot costs measured, combinations not yet ranked.**
   The test remixes `stock-meter-a` and `-b` (branch `feat/stock-meter-remixes`, not in this tree) carry LOAD METER and 13 of the 14 stock effects each (a lacks
   PHASER, b lacks SPATIALIZER). Runs of 25 Oct 2026 (images S1 and S2, projects MXSTK_a_01 and
   MXSTK_b_01, `def` settings, one effect on all eight tracks in FX1 or FX2, 0 of 23 layouts flagged),
   cost per slot = (layout - BASE) / 4 with BASE 22.5 % on core 0 and 14.9 % on core 1; the same on both
   cores and in FX1 and FX2 to 0.1 point:
   DJ EQ 7.30 %, LO-FI 6.65, SPRING REV 6.38, CHORUS 6.28, DARK REV 5.47, PLATE REV 5.28, PHASER 5.18,
   FILTER 5.10, EQUALIZER 4.10, FLANGER 3.12, COMB FILTER 2.72, COMPRESSOR 2.17, SPATIALIZER 1.28,
   DELAY 0.00. DELAY runs on the ColdFire (Sam, 25 Oct 2026), so its DSP cost is 0; the frame
   interrupt's share did not move (59.7 % against 59.6 %). The ColdFire cost of DELAY is not measured.
   Not run: the combinations (the pair predictor, `predict`, ranks them from these costs), `dear`
   settings (the stock effects have none in the registry).
2. **Part and pattern changes while playing: first results, more to run.** `ot_matrix.py switch` (24 Oct
   2026, MXEUC_01 on `octabam-inserts`): a program change sent during play takes effect at the end of the
   pattern, 8.02 s after START (64 steps at 120 BPM), whether it was sent 1 s or 6 s after START (BASE to
   TRANSIENT FX1 + LOFI2 FX2 `dear`, three times each, load 22 to 98 % at 8.02 s). Around the switch: the
   ColdFire's longest frame-interrupt run was 421 to 432 µs (against 280 µs steady and 366 µs at a plain
   pattern wrap with no part change, and 421 to 434 µs at START), so 116 to 119 % of the 362.8 µs frame, about
   60 µs over a wrap; the DSP busy rose 1.2 points at most above the steady value once and not otherwise;
   LOAD METER's bad records stayed at 0 and no silence reached 40 ms. TRANSIENT + LOFI2 to BASE, three times:
   425, 425 and 433 µs, no gap. TRANSIENT + LOFI2 to EUCLID FX1 + CHARACTER FX2 `dear`: 484 µs (133 % of a frame), the
   largest seen, probably EUCLID's ColdFire setup; back again: 426 µs, DSP busy 99.8 % against 98.3 % steady. Every
   transition ran with 0 bad records and no silence. Not yet run: transitions between more pairs, in both directions,
   and with real material. One earlier run (sw03) did not apply a program change sent during play, and the next start
   came up on the wrong layout, after a control that sent the program change for the layout already playing; use
   `--pairs` with two different layouts, not that control. A 1,080 ms silence flagged on one heavy-to-BASE transition
   in that run did not recur in three repeats.
3. **Where the frame budget ends.** One layout at 98.2 % busy ran clean (three times); one at 105.3 % and one at
   112 % overloaded the unit; EUCLID FX1 + LOFI2 FX2 at 95.8 % dropped frames, four times in four. Seven
   EUCLID FX1 pairs with an FX2 effect at 42 to 81 % ran clean. Layouts between 96 and 105 % would show the edge, and
   whether it moves with the ColdFire share.

4. **KITS, MIDI SCENES and DIRECT_JUMP_KYOTI** (all three are in `octabam-core`, `-inserts` and `-bus`; the last two
   also with LOAD METER in the latter two). The area with the most recent work. What the cable can drive, what
   needs hands, and what has run on a unit:

   | feature | over the cable | needs the panel | hardware record |
   |---|---|---|---|
   | KITS | a pattern change by program change loads the pattern's Kit into the Part slot; the per-slot costs in LOAD METER fingerprint which effects a Kit put on which slot; audio and load around the change (`switch`) | LOAD KIT, SAVE KIT, the list copy / paste / clear / undo, assigning a Kit to a pattern | `modules/kits/README.md` "On the unit": not run unattended with the BCR2000 |
   | MIDI SCENES | scene A / B select and the crossfader are CCs (55 / 56, 48), so the morph can be swept over USB MIDI with the locks stamped in `scenes.work` (MSC, 4,096 B); a MIDI track's output is the observable, if the unit sends it over USB (the USB README records no MIDI transmit measurement) | setting a lock (hold a scene, turn a knob), copy / paste a scene | the MIDISC 2.1 reimplementation has not run on hardware (the original ran on its author's unit, 14 Sep 2026) |
   | DIRECT_JUMP_KYOTI | after the toggle ([PTN] + [YES], OFF at every power-on) a program change cues a jump at the next step; the stimuli (impulse and hit trains of known spacing) make the landing step and the phase checkable, and `switch` gives the load and gaps at the jump | the toggle | the author's MKI, 27-28 Sep and 1 Oct 2026; program change on fast re-cues, MIDI tracks and START SILENT only under the author's emulator |

   Not built. Open: what Sam has seen go wrong (symptoms, patterns, the project), which tracks and Kits are in play,
   and whether the unit transmits MIDI track output over USB. Candidate runs: `switch` with the toggle on, many
   program changes at random times and in bursts; a Kits project with a distinct effect set per Kit and a
   program-change walk over all of them; a scene sweep with a known morph.

## Stress sequences

The audio check reads USB channels 0/1 (MAIN on an image whose TRACKS setting is OFF; TRACKS PRE puts T1 there)
and fails the run when their rms over 3 s is below -80 dB while the transport plays and at least three tracks are
unmuted by the sequence's own mute operations. Before that rule (25 Oct 2026) a 56-minute `mix` run stopped at
719 s, three times at the same place: the sequence had muted T1 to T7, leaving T8 alone through MODULATION
mode2 + dear; the mutes alone reproduce it, unmuting brings the audio back (-42 dB against -66 to -69 dB with only
T8), and LOAD METER read healthy throughout. The check assumes every track starts unmuted: load a fresh project.

`tools/hw/ot_fuzz.py` plays seeded random sequences of the things a person does over MIDI (program changes, START /
STOP, a moving tempo, the crossfader, scene select, mutes, levels, FX knobs) against one of the generated projects,
with the health checks above every 0.5 s, and stops on the first failure with the operation index and the last 40
operations; `run SEQ LABEL --until N` replays up to it. It is meant for the vague instability reports on KITS, MIDI
SCENES and DIRECT_JUMP_KYOTI: a failure comes with a seed. It does not drive the panel, so a Kit, a scene lock or
the direct-jump toggle has to be set up by hand. The generator is tested (`tools/verify/tests/test_fuzz.py`); no sequence has been run on a unit yet.

`ot_fuzz.py port REMIX PROJECT LABEL --seeds 1-8 --seconds 30` replays the program changes and CCs of the same
sequences under the ColdFire port (`--sequencer --internal-clock --midi`, one load forked into one child per seed,
`tools/emu/README.md`; START, STOP and tempo have no counterpart there). A seed passes when its run reaches all its
frames, the firmware takes every MIDI byte, and the final live effect ids are those of the layout the model
predicts: a program change lands at the next pattern end and the last one received before it wins. First batch
(24 Oct 2026, `octabam-inserts`, MXINS_01, profile `pc`, seeds 1-8, 30 s each, 82,687 frames, 20 to 38 operations
each): 8 of 8 clean and on the predicted layout; 895 s of wall time for the batch at 3 jobs.

KITS were idle in every run before this: the projects carried the template's blank `kits.work`, so the library was
empty. Without a `kits.work` the firmware migrates the stock Parts at the first load (Kit `4 * bank + part` is that
Part, each pattern with content plays its Part's Kit: 32 Kits for the 32 layouts); `ot_kits.py from-card` reads the
file it wrote and `rotate 1` points every pattern at the next Kit. Replays of both (`MXKIT_IDENT`, `MXKIT_ROT1`,
`octabam-inserts`, `pc` profile, seeds 1-8, 30 s): 8 of 8 clean each, and in the rotated project every seed ends on
the layout of the pattern's Kit and not of the bank file's Part, so the assigned Kit loads on each program change.
Not yet: Kit load and save, the list operations, scene locks inside the Kits, and the unit.

A project to start from needs no unit: `ot_fresh.py --remix octabam-inserts` has the port create one (90 files, 30 MB,
`ot_matrix.py audit` finds nothing), `proj --clean` builds the stimuli projects from it, and the replay ran on them
(3 of 3 clean, 20 s each, 24 Oct 2026).

`.github/workflows/fuzz.yml` runs the same chain on runners, by hand (`workflow_dispatch`: remix, Kits none / identity /
rotated, profile, seconds, seeds per shard; 8 shards of `ubuntu-latest`). Each shard fetches the stock OS as the `gates`
job does, has the port make its own fresh project, builds the stimuli project, has the firmware migrate the Kits when
asked (`ot_kits.py migrate`, `--rotate 1` for the rotated assignment), and replays its seeds; it uploads the verdict
text and each seed's sequence and MIDI script and nothing derived from the OS. A red shard reproduces locally with the
same seed. Written and its YAML parsed, its action pins checked against `ci.yml`'s and the upload action's against
GitHub; not yet run: it needs the branch pushed, and nothing here has measured how fast the port runs on a runner.

## Flags

Every flag is against BASE of the same project; thresholds are the constants at
the top of `ot_matrix.py`, first guesses not validated on a unit. A flag means
"differs from BASE past a threshold", not "broken". A program change sent while stopped takes effect 0.26 to
0.77 s after START (48 layouts), one sent during play at the end of the pattern; the audio figures start 1 s into
play and the load statistics 2 s in.

| flag | meaning |
|---|---|
| CRASH | no audio in the first 2 s of play where BASE had some (sequencer stuck); the run stops |
| FREEZE | every channel silent for 1 s where BASE was not |
| CLICKS | isolated discontinuities: more events than BASE, in at most 10 % of the 512-sample blocks |
| ROUGH | the same events in more of the blocks: a rough or heavily modulated signal |
| STATIC | 8-16 kHz power 6 dB or more above BASE's |
| LEVEL | rms 3 dB or more from BASE's |
| CLIP | samples at full scale |
| DC / RINGS | the last half second of the tail is above -70 dBFS and BASE's is not; DC when the level is a held constant |
| DROPS | LOAD METER's DSP record failed its checks more than 20 times in the play window: frames were skipped. 0 in every layout except EUCLID FX1 + LOFI2 FX2 (about 2,950 each of four runs) |
| OVERLOAD | the frame interrupt ran under 80 % of 2,756 a second: the DSP missed its frames; the unit stays degraded and the run stops (power-cycle) |
| LOAD | frame-interrupt share or a DSP core's busy/period at 90 % or more, from 2 s into play |

## Limits

- LOAD METER counts timer ticks; none of its figures has been compared with an
  independent measurement. It is absent from `octabam-core` (the 14 stock effects
  leave no DSP words), so that remix gets audio flags only.
- All eight voices start on step 1, so the ColdFire's longest run (about 93 % of
  a frame) is the start-up spike, and the ColdFire share is the same in every
  layout. DSP figures are the discriminating ones.
- BASE is one baseline per project; a fault BASE has too is invisible.
- The stimuli are synthetic (`ot_stimuli.py`): a fault that needs real material
  to show (a smeared transient in a reverb tail) may not.
- The first run's findings: MODULATION on all eight tracks reaches about 99 % DSP-0
  busy; four `dear` MODULATION layouts hold DC after STOP. The measurements are in
  the run's report, not repeated here.
