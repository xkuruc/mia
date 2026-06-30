#!/usr/bin/env python3
"""
bell.py — príprava a meranie Bellovho stavu |Phi+> = (|00>+|11>)/sqrt(2)
na zariadení SpinQ Gemini (NMR), upravená verzia pôvodného skriptu.

Spustenie:
    python3 bell.py                 # ideálny simulátor
    python3 bell.py --backend torch # lokálny spinqit simulátor
    python3 bell.py --backend nmr   # reálne zariadenie (údaje z config.json)
"""
import argparse
import json
import os
import sys

import chsh_experiment as ex


def main() -> None:
    ap = argparse.ArgumentParser(description="Bellov stav na SpinQ Gemini / simulátore.")
    ap.add_argument("--backend", default="ideal", choices=["ideal", "torch", "basic", "nmr"])
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--draw", metavar="PNG", help="ulož schému obvodu do PNG (vyžaduje spinqit)")
    args = ap.parse_args()

    device = None
    if args.backend == "nmr":
        if not os.path.exists(args.config):
            sys.exit(f"Chýba {args.config} s údajmi o zariadení (pozri config.example.json).")
        with open(args.config, "r", encoding="utf-8") as f:
            device = json.load(f).get("device", {})

    if args.backend in ex.SPINQIT_BACKENDS and not ex.spinqit_available():
        sys.exit("spinqit nie je nainštalovaný. Použi --backend ideal.")

    # voliteľné vykreslenie schémy obvodu (ako v pôvodnom skripte)
    if args.draw:
        if not ex.spinqit_available():
            sys.exit("--draw vyžaduje nainštalovaný spinqit.")
        import spinqit
        from spinqit import get_compiler
        exe = get_compiler("native").compile(ex.build_bell_circuit(), 0)
        spinqit.view.draw(exe, args.draw)
        print(f"Schéma obvodu uložená do {args.draw}")

    probs, counts = ex.run_bell(args.backend, args.shots, device)
    print("Pravdepodobnosti:", {k: round(v, 4) for k, v in sorted(probs.items())})
    if counts:
        print("Counts:          ", dict(sorted(counts.items())))
    print(f"Korelácia E(ZZ) = {ex.correlation(probs):+.4f}   "
          f"(ideálne +1.0 pre |Phi+>)")


if __name__ == "__main__":
    main()
