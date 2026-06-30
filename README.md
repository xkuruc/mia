# SpinQ Gemini — laboratórium kvantového previazania a Bellových nerovností

Lokálna výučbová a experimentálna webová aplikácia k bakalárskej práci: riadenie
experimentov na desktopovom NMR kvantovom počítači **SpinQ Gemini** (cez SpinQit)
a demonštrácia **porušenia Bellových nerovností (CHSH)**.

## Štruktúra

```
chsh_experiment.py   # JADRO: Bellov stav + CHSH na spinqit / simulátore (importovateľný modul)
run_chsh.py          # CLI: spustenie CHSH alebo korelačnej krivky z terminálu
bell.py              # CLI: samotný Bellov stav (upravený pôvodný skript)
server.py            # lokálny HTTP server (stdlib, bez frameworku) — beží appka
web/                 # frontend (HTML/CSS/JS, bez externých knižníc, SVG grafy)
  index.html         #   Teória · Experiment · Analýza · Diskusia
  style.css
  app.js
requirements.txt     # Python závislosti (potrebné LEN pre spinqit backendy)
check_env.py         # diagnostika cieľového zariadenia (stdlib)
config.example.json  # vzor pripojenia k zariadeniu -> skopíruj na config.json
SETUP.md             # podrobný návod na inštaláciu na inom počítači
```

> **Inštalácia na inom zariadení:** pozri **[SETUP.md](SETUP.md)**. V skratke: jadro + web
> + ideálny simulátor potrebujú **iba Python 3** (nič inštalovať). Pre spinqit
> simulátory / reálne zariadenie: `pip install -r requirements.txt`.

## Rýchly štart (bez prístroja, bez inštalácie)

Funguje hneď cez vstavaný **ideálny simulátor** (čistý Python):

```bash
python3 server.py
# otvor http://localhost:8000  ->  záložka Experiment  ->  Spustiť CHSH test
```

Alebo z terminálu:

```bash
python3 run_chsh.py                 # CHSH na ideálnom simulátore -> S ~ 2.83
python3 run_chsh.py --sweep         # korelačná krivka E(a-b)
```

## So spinqit (lokálne simulátory)

```bash
python3 -m pip install -r requirements.txt   # stiahne spinqit + jeho závislosti
python3 check_env.py                          # over, že "spinqit ... ✔ OK"
python3 run_chsh.py --backend torch --shots 2048
```

## Na reálnom zariadení SpinQ Gemini

1. Skopíruj `config.example.json` → `config.json` a uprav IP/port/účet (predvyplnené tvoje hodnoty: `172.22.22.3:8989`, `SpinQ001`).
2. CLI:
   ```bash
   python3 run_chsh.py --backend nmr --config config.json
   python3 bell.py     --backend nmr --config config.json
   ```
3. Web: `python3 server.py --config config.json`, v appke zvoľ backend **„Reálne zariadenie SpinQ Gemini".**

## Fyzika v skratke

- Bellov stav `|Φ+⟩ = (|00⟩+|11⟩)/√2` (H na q0, CNOT q0→q1).
- Meranie v báze pod uhlom θ = rotácia `Ry(-θ)` pred Z-meraním.
- Korelácia `E(a,b) = cos(a-b)`; CHSH `S = E(a,b) - E(a,b') + E(a',b) + E(a',b')`.
- Optimálne uhly: Alice `{0°, 90°}`, Bob `{45°, 135°}` → `S = 2√2 ≈ 2.83 > 2`.
- **Pozn. k NMR:** Gemini pracuje s pseudo-pure stavmi (ε≈10⁻⁵), ktoré sú podľa
  Braunsteina a kol. (PRL 83, 1054, 1999) **separabilné**. Experiment teda
  reprodukuje kvantový formalizmus (krivku cos(a-b), S≈2,83), ale **nie je**
  loophole-free Bellovým testom ako fotónové experimenty (Nobelova cena 2022).
  Podrobnosti v záložke **Diskusia**.

## API servera (pre vlastné rozšírenia)

| Endpoint        | Telo (JSON)                                   | Vráti |
|-----------------|-----------------------------------------------|-------|
| `GET /api/health` | —                                           | dostupné backendy |
| `POST /api/bell`  | `{backend, shots, device?}`                 | pravdepodobnosti, counts, E(ZZ) |
| `POST /api/chsh`  | `{backend, shots, device?}`                 | 4 korelácie, S, S_teória, verdikt |
| `POST /api/sweep` | `{backend, shots, alice_angle, points}`     | body korelačnej krivky |
