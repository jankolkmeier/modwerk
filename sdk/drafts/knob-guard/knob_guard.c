/* SPDX-License-Identifier: MIT
 * Copyright (C) 2026 Jan Kolkmeier
 *
 * KNOB GUARD: clearing a lock by pressing a DATA ENTRY knob no longer writes a
 * new one when the knob turns a detent as it is let go. The press is a lock
 * toggle applied on release, and a turn while pressed is stock's coarse edit
 * (x7) that cancels the toggle. While a TRIG key (a parameter lock) or SCENE
 * A/B (a scene lock) is held, a pressed knob's FIRST single detent is dropped
 * (the slip that would turn a clear into a x7 jump); further turns pass, so a
 * deliberate coarse edit works, one detent short. Every turn is dropped for
 * QUIET ticks after the release (the detent the release turns). Everything else reaches
 * the firmware as before: the press itself (the clear), the other knobs, LEVEL,
 * and press + turn outside lock editing (TEMPO's LEVEL steps x7 while pushed,
 * octabam docs/firmware/MAINMENU.md). It takes no key, patches no stock code.
 *
 *   python3 -B sdk/runtime/loader/build.py sdk/drafts/knob-guard/knob_guard.c --name "KNOB GUARD" -o knob-guard.mwrm
 *
 * MKII panel codes (octabam docs/firmware/PANEL.md): TRIG 1-16 are keys 0x00-0x0f,
 * SCENE A/B 0x19/0x1a, the pushes of knobs A-F 0x38-0x3d; turns are encoders 0-5.
 * DIAG's value counts the turns taken. */
#include "modwerk_module.h"

#define KNOBS 6u
#define PUSH_A 0x38
#define SCENE_A 0x19
#define SCENE_B 0x1a
#define QUIET 9u                 /* UI ticks after a release (60 a second): 150 ms */

static uint32_t now, taken;
static uint16_t trigs;           /* TRIG keys held, one bit each */
static uint8_t scenes;           /* SCENE A / B held */
static uint8_t held;             /* knobs pressed while a lock was being edited */
static uint8_t slipped;          /* of them, those whose first detent was dropped */
static uint32_t quiet_until[KNOBS];

static int editing_locks(void) { return trigs || scenes; }

int module_key(int code, int pressed)
{
    if (code >= 0 && code < 16) {
        if (pressed) trigs |= (uint16_t)(1u << code); else trigs &= (uint16_t)~(1u << code);
    } else if (code == SCENE_A || code == SCENE_B) {
        uint8_t bit = code == SCENE_A ? 1u : 2u;
        if (pressed) scenes |= bit; else scenes &= (uint8_t)~bit;
    } else if (code >= PUSH_A && code < PUSH_A + (int)KNOBS) {
        unsigned knob = (unsigned)(code - PUSH_A);
        if (pressed) {
            if (editing_locks()) held |= (uint8_t)(1u << knob), slipped &= (uint8_t)~(1u << knob);
        } else if (held & (1u << knob)) {
            held &= (uint8_t)~(1u << knob);
            quiet_until[knob] = now + QUIET; /* the detent the release turns */
        }
    }
    return 0;
}

int module_enc(int encoder, int delta)
{
    if (encoder < 0 || encoder >= (int)KNOBS) return 0;
    unsigned knob = (unsigned)encoder, bit = 1u << knob;
    if (held & bit) {
        /* A single first detent is the slip; a coalesced fast turn (|delta| > 1) or any later one is a coarse edit. */
        if (!(slipped & bit) && (delta == 1 || delta == -1)) {
            slipped |= (uint8_t)bit;
            taken++;
            return 1;
        }
        slipped |= (uint8_t)bit;
        return 0;
    }
    if ((int32_t)(quiet_until[knob] - now) > 0) {
        taken++;
        return 1;
    }
    return 0;
}

void module_tick(struct modwerk_runtime_api *api)
{
    now++;
    api->value = taken;
}
