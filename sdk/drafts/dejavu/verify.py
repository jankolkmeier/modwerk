#!/usr/bin/env python3
"""DEJA VU's gate: dejavu.c compiled for the host (-DDV_HOST), checked against its contract.

    python3 -B verify.py            # needs a host C compiler (cc); m68k-elf-gcc for the unit check

- every MULT gives a loop of 1 << MULT that repeats exactly when locked (SPD 127)
- the replay chance is SPD / 127 (+-3 %)
- DJQ on PTCH lands on root, fifths and octaves only, through the LFO engine's own arithmetic
  (EMAC fractional: the destination word gains (DEP_word << 8) * out >> 31; a PTCH semitone is 5 knob steps)
- a state that starts as garbage (card builds do not zero it) behaves as a fresh one
- dejavu_core.s is what dejavu.c, hooks.s and icon.py generate (when m68k-elf-gcc is on PATH)
"""
import ctypes
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ONE, NOTES = 3, {-12, -5, 0, 7, 12}
failed = []


def check(name, ok, detail=""):
    print(("[PASS] " if ok else "[FAIL] ") + name + (f": {detail}" if detail and not ok else ""))
    if not ok:
        failed.append(name)


def engine_add(out, depw):
    return (((depw + (0x100 if depw == 0x7F00 else 0)) << 8) * out) >> 31


with tempfile.TemporaryDirectory() as tmp:
    so = pathlib.Path(tmp) / "dejavu.so"
    subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-DDV_HOST", "-o", str(so), str(HERE / "dejavu.c")], check=True)
    lib = ctypes.CDLL(str(so))
    lib.dv_host.restype = ctypes.c_int32
    lib.dv_host.argtypes = [ctypes.c_uint, ctypes.c_int] + [ctypes.c_uint] * 6
    lib.dv_quant_of.restype = ctypes.c_int32
    lib.dv_quant_of.argtypes = [ctypes.c_int32, ctypes.c_uint]

    def one(i, n, deja, mult):
        return [lib.dv_host(i, 1, deja, mult, ONE, 1, 0, 0) for _ in range(n)]

    for mult in range(7):
        n = 1 << mult
        x = one(mult, 40 * n, 127, mult)
        check(f"MULT {mult}: a locked loop of {n} repeats", x[n:] == x[:-n])
    for deja in (16, 64, 100):
        x = one(10 + deja % 7, 64 * 400 + 64, deja, 6)
        same = sum(a == b for a, b in zip(x[128:], x[64:-64])) / len(x[128:])
        check(f"SPD {deja}: replays {deja / 127:.2f}", abs(same - deja / 127) < 0.03, f"measured {same:.3f}")
    for k, want in ((4, {0}), (25, {-5, 0}), (35, {-5, 0, 7}), (60, NOTES), (127, NOTES)):
        adds = [engine_add(lib.dv_quant_of(v << 16, k << 8), k << 8) for v in range(-128, 128)]
        exact = all(a % (5 * 256) == 0 for a in adds)
        notes = {a // (5 * 256) for a in adds}
        check(f"DJQ on PTCH at DEP {k}: root and fifth {sorted(want)}", exact and notes == want, f"{sorted(notes)} exact={exact}")
    base = ctypes.addressof(ctypes.c_char.in_dll(lib, "dv_state"))
    ctypes.memset(base, 0xA5, 116 * 24)
    a = one(20, 64, 127, 3)
    ctypes.memset(base, 0, 116 * 24)
    b = one(20, 64, 127, 3)
    check("a garbage state is set up on first use", a == b)

gen = HERE / "generate.py"
if shutil.which("m68k-elf-gcc"):
    r = subprocess.run([sys.executable, "-B", str(gen), "--check"], capture_output=True, text=True)
    check("dejavu_core.s matches dejavu.c, hooks.s and icon.py", r.returncode == 0, (r.stdout + r.stderr).strip()[-300:])
else:
    print("[SKIP] dejavu_core.s regeneration: m68k-elf-gcc not on PATH")

sys.exit(1 if failed else 0)
