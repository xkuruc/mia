#!/usr/bin/env python3
"""
run_chsh.py — spustenie CHSH testu z príkazového riadku.

Príklady:
    # ideálny simulátor (žiadne závislosti, vždy funguje)
    python3 run_chsh.py

    # lokálny spinqit simulátor
    python3 run_chsh.py --backend torch --shots 2048

    # reálne zariadenie SpinQ Gemini (údaje z config.json alebo z argumentov)
    python3 run_chsh.py --backend nmr --config config.json
    python3 run_chsh.py --backend nmr --ip 172.22.22.3 --port 8989 \
        --account SpinQ001 --password 123456

    # korelačná krivka E(a-b) namiesto CHSH
    python3 run_chsh.py --sweep --points 25
"""

import argparse
import json
import math
import os
import sys

import chsh_experiment as ex


def load_device(args) -> dict | None:
    """Zostaví slovník pripojenia k NMR zariadeniu z configu alebo argumentov."""
    if args.backend != "nmr":
        return None
    device = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            device.update(json.load(f).get("device", {}))
    for key in ("ip", "port", "account", "password", "task"):
        val = getattr(args, key, None)
        if val is not None:
            device[key] = val
    missing = [k for k in ("ip", "port", "account", "password") if k not in device]
    if missing:
        sys.exit(f"Chýbajú údaje o zariadení: {', '.join(missing)} "
                 f"(zadaj cez --config alebo --ip/--port/--account/--password)")
    return device


def fmt_deg(rad: float) -> str:
    return f"{rad:.4f} rad ({math.degrees(rad):.1f}°)"


def print_chsh(res: ex.CHSHResult) -> None:
    print("=" * 64)
    print(f"  CHSH test  |  backend = {res.backend}  |  shots = {res.shots}")
    print("=" * 64)
    print(f"  Alice uhly:  a  = {fmt_deg(res.alice[0])},  a' = {fmt_deg(res.alice[1])}")
    print(f"  Bob   uhly:  b  = {fmt_deg(res.bob[0])},  b' = {fmt_deg(res.bob[1])}")
    print("-" * 64)
    print(f"  {'nastavenie':<10} {'E namerané':>12} {'E teória':>12}   pravdepodobnosti")
    for s in res.settings:
        probs = "  ".join(f"{k}:{v:.3f}" for k, v in sorted(s["probabilities"].items()))
        print(f"  {s['label']:<10} {s['E']:>12.4f} {s['E_theory']:>12.4f}   {probs}")
    print("-" * 64)
    print(f"  S (namerané)     = {res.S:+.4f}")
    print(f"  S (teória QM)    = {res.S_theory:+.4f}")
    print(f"  klasická hranica = {res.classical_bound:.4f}")
    print(f"  kvantová hranica = {res.quantum_bound:.4f}  (2*sqrt(2))")
    print("-" * 64)
    if res.violates_classical:
        print(f"  ==> |S| = {abs(res.S):.4f} > 2  ->  PORUŠENIE Bellovej nerovnosti ✔")
    else:
        print(f"  ==> |S| = {abs(res.S):.4f} <= 2  ->  bez porušenia")
    print("=" * 64)


def print_sweep(points) -> None:
    print(f"  {'b [°]':>8} {'E namerané':>12} {'E teória':>12}")
    for p in points:
        print(f"  {math.degrees(p['bob']):>8.1f} {p['E']:>12.4f} {p['E_theory']:>12.4f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="CHSH test na SpinQ Gemini / simulátore (SpinQit).")
    ap.add_argument("--backend", default="ideal", choices=["ideal", "torch", "basic", "nmr"],
                    help="výpočtový backend (default: ideal)")
    ap.add_argument("--shots", type=int, default=1024, help="počet meraní (default: 1024)")
    ap.add_argument("--sweep", action="store_true", help="namiesto CHSH spusti korelačnú krivku")
    ap.add_argument("--points", type=int, default=25, help="počet bodov krivky (default: 25)")
    ap.add_argument("--alice-sweep", type=float, default=0.0,
                    help="Alicin uhol [rad] pri korelačnej krivke (default: 0)")
    # pripojenie k zariadeniu
    ap.add_argument("--config", default="config.json", help="JSON s údajmi o zariadení")
    ap.add_argument("--ip")
    ap.add_argument("--port", type=int)
    ap.add_argument("--account")
    ap.add_argument("--password")
    ap.add_argument("--task")
    args = ap.parse_args()

    if args.backend in ex.SPINQIT_BACKENDS and not ex.spinqit_available():
        sys.exit("spinqit nie je nainštalovaný. Použi --backend ideal alebo nainštaluj spinqit.")

    device = load_device(args)

    if args.sweep:
        pts = ex.run_sweep(args.backend, args.shots, args.alice_sweep, args.points, device)
        print_sweep(pts)
    else:
        res = ex.run_chsh(args.backend, args.shots, device=device)
        print_chsh(res)


if __name__ == "__main__":
    main()
