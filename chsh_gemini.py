#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chsh_gemini.py
==============
Samostatný skript: spustí CHSH test (porušenie Bellových nerovností)
na REÁLNOM zariadení SpinQ Gemini (NMR) cez SpinQit.

Spustenie:
    python chsh_gemini.py

Čo robí:
    1) pripraví Bellov stav |Phi+> = (|00>+|11>)/sqrt(2)   (H na q0, CNOT q0->q1)
    2) pre 4 dvojice meracích uhlov otočí bázy hradlom Ry(-uhol) a zmeria
    3) z pravdepodobností vypočíta 4 korelácie E a CHSH parameter S
    4) S > 2  =>  porušenie Bellovej nerovnosti (kvantové maximum 2*sqrt(2) ~ 2.828)

Kompatibilné s Pythonom 3.8 (potrebným pre spinqit).
"""
from __future__ import annotations

import math
import sys

# ===========================================================================
#  NASTAVENIE  —  uprav podľa svojho zariadenia
# ===========================================================================
IP       = "172.22.22.3"   # IP adresa SpinQ Gemini
PORT     = 8989            # port
ACCOUNT  = "SpinQ001"      # používateľské meno
PASSWORD = "123456"        # heslo
TASK     = "CHSH"          # názov úlohy na zariadení
SHOTS    = 1024            # počet meraní

# Optimálne CHSH uhly (radiány): Alice {0, 90°}, Bob {45°, 135°}  ->  S = 2*sqrt(2)
ALICE = (0.0, math.pi / 2)          # a,  a'
BOB   = (math.pi / 4, 3 * math.pi / 4)  # b,  b'

CLASSICAL_BOUND = 2.0
QUANTUM_BOUND   = 2.0 * math.sqrt(2.0)   # ~ 2.8284

# ---------------------------------------------------------------------------
try:
    from spinqit import get_nmr, NMRConfig, get_compiler, Circuit, H, CNOT, Ry
except ImportError:
    sys.exit("Chyba: nie je nainštalovaný 'spinqit'. Nainštaluj ho: pip install spinqit")


# ===========================================================================
#  Kvantový obvod pre jedno CHSH nastavenie
# ===========================================================================
def build_chsh_circuit(alice_angle, bob_angle):
    """|Phi+> + rotácia meracích báz Ry(-uhol). q0 = Alice, q1 = Bob."""
    circ = Circuit()
    q = circ.allocateQubits(2)
    circ.allocateClbits(2)
    # príprava previazaného Bellovho stavu
    circ << (H, q[0])
    circ << (CNOT, [q[0], q[1]])
    # otočenie meracích báz (znamienko -uhol dáva E = cos(a-b))
    circ << (Ry, q[0], -alice_angle)
    circ << (Ry, q[1], -bob_angle)
    return circ


# ===========================================================================
#  Spustenie na reálnom zariadení
# ===========================================================================
def run_on_gemini(circ, task_name):
    """Skompiluje obvod a spustí ho na SpinQ Gemini. Vráti pravdepodobnosti."""
    exe = get_compiler("native").compile(circ, 0)   # 0 = bez optimalizácie

    engine = get_nmr()
    cfg = NMRConfig()
    cfg.configure_ip(IP)
    cfg.configure_port(PORT)
    cfg.configure_account(ACCOUNT, PASSWORD)
    cfg.configure_task(task_name, "CHSH Bell test")
    cfg.configure_shots(SHOTS)

    result = engine.execute(exe, cfg)
    return to_probabilities(result)


def to_probabilities(result):
    """Z výsledku vytiahne pravdepodobnosti (NMR vracia probabilities); doplní 00..11."""
    try:
        raw = dict(result.probabilities)
    except Exception:
        counts = dict(result.counts)
        total = sum(counts.values()) or 1
        raw = {k: v / total for k, v in counts.items()}

    probs = {"00": 0.0, "01": 0.0, "10": 0.0, "11": 0.0}
    for key, val in raw.items():
        probs[str(key).zfill(2)] = probs.get(str(key).zfill(2), 0.0) + float(val)
    return probs


def correlation(p):
    """E = P(00) + P(11) - P(01) - P(10)."""
    return p["00"] + p["11"] - p["01"] - p["10"]


# ===========================================================================
#  Hlavný program
# ===========================================================================
def main():
    a, ap = ALICE
    b, bp = BOB
    combos = [
        ("E(a,b)",   a,  b),
        ("E(a,b')",  a,  bp),
        ("E(a',b)",  ap, b),
        ("E(a',b')", ap, bp),
    ]

    print("=" * 64)
    print("  CHSH test na SpinQ Gemini  ({}:{},  ucet {})".format(IP, PORT, ACCOUNT))
    print("  shots = {}".format(SHOTS))
    print("=" * 64)
    print("  Alice:  a  = {:6.1f}°   a' = {:6.1f}°".format(math.degrees(a), math.degrees(ap)))
    print("  Bob:    b  = {:6.1f}°   b' = {:6.1f}°".format(math.degrees(b), math.degrees(bp)))
    print("-" * 64)
    print("  {:<10} {:>11} {:>11}   pravdepodobnosti".format("nastavenie", "E namerane", "E teoria"))

    e_vals = []
    for i, (label, ang_a, ang_b) in enumerate(combos, start=1):
        circ = build_chsh_circuit(ang_a, ang_b)
        probs = run_on_gemini(circ, "{}_{}".format(TASK, i))
        e = correlation(probs)
        e_vals.append(e)
        e_theory = math.cos(ang_a - ang_b)
        ptxt = "  ".join("{}:{:.3f}".format(k, probs[k]) for k in ("00", "01", "10", "11"))
        print("  {:<10} {:>11.4f} {:>11.4f}   {}".format(label, e, e_theory, ptxt))

    # S = E(a,b) - E(a,b') + E(a',b) + E(a',b')
    S = e_vals[0] - e_vals[1] + e_vals[2] + e_vals[3]

    print("-" * 64)
    print("  S (namerane)     = {:+.4f}".format(S))
    print("  klasicka hranica = {:.4f}".format(CLASSICAL_BOUND))
    print("  kvantova hranica = {:.4f}   (2*sqrt(2))".format(QUANTUM_BOUND))
    print("-" * 64)
    if abs(S) > CLASSICAL_BOUND:
        print("  ==> |S| = {:.4f} > 2  ->  PORUSENIE Bellovej nerovnosti".format(abs(S)))
    else:
        print("  ==> |S| = {:.4f} <= 2  ->  bez porusenia".format(abs(S)))
    print("=" * 64)


if __name__ == "__main__":
    main()
