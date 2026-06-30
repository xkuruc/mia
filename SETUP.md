# Inštalácia na cieľovom zariadení

Návod, ako appku rozbehať na inom počítači (od nuly). Časti so spinqit / reálnym
zariadením sú voliteľné — **na výučbu a UI netreba inštalovať nič okrem Pythonu 3**.

---

## 0) Prenes projekt na cieľové zariadenie

Skopíruj celý priečinok `MIA` (USB, zip, alebo git). Musí obsahovať:
`chsh_experiment.py`, `server.py`, `run_chsh.py`, `bell.py`, `check_env.py`,
`requirements.txt`, `config.example.json` a priečinok `web/`.

---

## 1) Python 3

Over, či je nainštalovaný:

```bash
python3 --version
```

Ak nie:
- **Windows:** stiahni z <https://www.python.org/downloads/> a pri inštalácii zaškrtni *„Add Python to PATH"*.
- **macOS:** `brew install python3` (alebo z python.org).
- **Linux:** `sudo apt install python3` (Debian/Ubuntu).

> Jadro appky beží na **Pythone 3.7+**. Pre `spinqit` over podporovanú verziu v dokumentácii
> SpinQ — ak `pip install spinqit` zlyhá kvôli verzii, použi Python **3.8–3.10**.

---

## 2) Rýchly test (bez akejkoľvek inštalácie)

```bash
cd cesta/k/MIA
python3 check_env.py     # diagnostika prostredia
python3 server.py        # otvor http://localhost:8000
```

Funguje cez vstavaný **ideálny simulátor** — appka, teória aj CHSH test idú hneď.

---

## 3) (Voliteľné) spinqit — lokálne simulátory a reálne zariadenie

Potrebné len pre backendy **torch / basic / nmr**.

**a) Virtuálne prostredie (odporúčané — nezasiahne systémový Python):**

```bash
cd cesta/k/MIA
python3 -m venv .venv
# aktivácia:
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows (PowerShell/CMD)
```

**b) Inštalácia závislostí:**

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

`pip` automaticky stiahne aj závislosti spinqit (numpy, torch, …). Over:

```bash
python3 check_env.py        # riadok "spinqit ... ✔ OK"
python3 run_chsh.py --backend torch --shots 2048
```

---

## 4) (Voliteľné) Pripojenie k reálnemu SpinQ Gemini

```bash
cp config.example.json config.json     # Windows: copy config.example.json config.json
```

Uprav v `config.json` `ip`, `port`, `account`, `password` podľa svojho zariadenia
(predvyplnené sú tvoje hodnoty `172.22.22.3:8989`, `SpinQ001`). Potom:

```bash
python3 server.py --config config.json     # web: zvoľ backend "Reálne zariadenie SpinQ Gemini"
# alebo z terminálu:
python3 run_chsh.py --backend nmr --config config.json
python3 bell.py     --backend nmr --config config.json
```

> Cieľové zariadenie musí byť v rovnakej sieti / dosahu IP adresy Gemini.

---

## Zhrnutie závislostí

| Čo chceš robiť | Treba nainštalovať |
|---|---|
| Teória + UI + ideálny simulátor + web | **nič** (iba Python 3) |
| spinqit simulátory (torch/basic) | `pip install -r requirements.txt` |
| Reálne zariadenie SpinQ Gemini | `requirements.txt` + `config.json` |
