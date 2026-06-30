#!/usr/bin/env python3
"""
check_env.py — overí, či má cieľové zariadenie všetko potrebné.
Používa iba štandardnú knižnicu, takže ho spustíš hneď:

    python3 check_env.py
"""
import importlib.util
import json
import os
import sys


def ok(b):
    return "✔ OK" if b else "✗ CHÝBA"


def main():
    print("=" * 60)
    print("  Kontrola prostredia — SpinQ Gemini Bell/CHSH appka")
    print("=" * 60)

    # 1) Python
    v = sys.version_info
    py_ok = v >= (3, 7)
    print(f"  Python {v.major}.{v.minor}.{v.micro:<5}            {ok(py_ok)} (treba 3.7+)")

    # 2) Jadro appky (stdlib) — malo by ísť vždy
    try:
        import chsh_experiment as ex
        res = ex.run_chsh(backend="ideal", shots=0)
        core_ok = abs(res.S) > 2.0
        print(f"  Jadro (ideálny simulátor)     {ok(core_ok)}  (S = {res.S:.3f} > 2 = porušenie)")
    except Exception as e:
        print(f"  Jadro (ideálny simulátor)     ✗ CHYBA: {e}")

    # 3) spinqit — voliteľné (pre torch/basic/nmr)
    spinqit_ok = importlib.util.find_spec("spinqit") is not None
    print(f"  spinqit (torch/basic/nmr)     {ok(spinqit_ok)}  (voliteľné — pip install -r requirements.txt)")

    # 4) config.json — pre reálne zariadenie
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    cfg_ok = os.path.exists(cfg_path)
    if cfg_ok:
        try:
            with open(cfg_path, encoding="utf-8") as f:
                dev = json.load(f).get("device", {})
            print(f"  config.json                   ✔ OK  (zariadenie {dev.get('ip')}:{dev.get('port')})")
        except Exception as e:
            print(f"  config.json                   ✗ CHYBNÝ JSON: {e}")
    else:
        print(f"  config.json                   – chýba (treba LEN pre backend 'nmr'; vzor: config.example.json)")

    print("-" * 60)
    print("  Spustenie webovej appky:   python3 server.py   ->  http://localhost:8000")
    print("  Spustenie z terminálu:     python3 run_chsh.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
