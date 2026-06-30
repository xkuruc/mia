"""
chsh_experiment.py
==================

Jadro experimentu: príprava Bellovho stavu a CHSH test (porušenie Bellových
nerovností) na desktopovom NMR kvantovom počítači SpinQ Gemini cez SpinQit,
prípadne na lokálnom simulátore.

Backendy (parameter `backend`):
    "ideal" : čistý Python (stdlib) statevector simulátor ideálneho |Phi+>.
              Nepotrebuje spinqit ani žiadne závislosti -> appka funguje vždy.
    "torch" : spinqit get_torch_simulator()   (lokálny PyTorch simulátor)
    "basic" : spinqit get_basic_simulator()   (lokálny klasický simulátor)
    "nmr"   : reálne zariadenie SpinQ Gemini cez get_nmr() + NMRConfig

Fyzika CHSH:
    1) Pripravíme |Phi+> = (|00>+|11>)/sqrt(2):  H na q0, potom CNOT(q0->q1).
    2) Meranie qubitu v báze pod uhlom theta v rovine x-z (pozorovateľná
       cos(theta) Z + sin(theta) X) sa robí cez Z-meranie po rotácii Ry(-theta).
    3) Korelácia pre |Phi+>:  E(a,b) = cos(a - b).
    4) CHSH parameter:  S = E(a,b) - E(a,b') + E(a',b) + E(a',b').
       Klasická (lokálne-realistická) hranica |S| <= 2.
       Kvantová (Tsirelsonova) hranica  |S| <= 2*sqrt(2) ~ 2.828.
    5) Optimálne uhly: Alice {0, pi/2}, Bob {pi/4, 3pi/4} -> S = +2*sqrt(2).

Pozn. ku konvenciám SpinQit (overené proti oficiálnym zdrojom):
    - parametrické hradlo:  circ << (Ry, q[0], theta)   (uhol = 3. prvok)
    - výsledok: result.probabilities a result.counts su dict {'00':..,'11':..}
    - little-endian: ľavý znak reťazca = qubit 0  (q0 = Alice, q1 = Bob)
    - NMR zariadenie vracia iba pravdepodobnostnú distribúciu (probabilities)
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optimálne CHSH uhly (v radiánoch)
# ---------------------------------------------------------------------------
DEFAULT_ALICE: Tuple[float, float] = (0.0, math.pi / 2)          # a, a'
DEFAULT_BOB: Tuple[float, float] = (math.pi / 4, 3 * math.pi / 4)  # b, b'

CLASSICAL_BOUND = 2.0
QUANTUM_BOUND = 2.0 * math.sqrt(2.0)   # ~ 2.8284271247

SPINQIT_BACKENDS = ("torch", "basic", "nmr")


# ===========================================================================
#  1) Stavba kvantových obvodov (SpinQit)
# ===========================================================================
def build_bell_circuit():
    """Obvod pripravujúci Bellov stav |Phi+> = (|00>+|11>)/sqrt(2)."""
    from spinqit import Circuit, H, CNOT  # import až tu, aby modul šiel aj bez spinqit
    circ = Circuit()
    q = circ.allocateQubits(2)
    circ.allocateClbits(2)
    circ << (H, q[0])
    circ << (CNOT, [q[0], q[1]])
    return circ


def build_chsh_circuit(alice_angle: float, bob_angle: float):
    """
    Obvod pre jedno CHSH nastavenie.

    Pripraví |Phi+> a otočí meracie bázy: aby sme zmerali pozorovateľnú
    cos(theta) Z + sin(theta) X, aplikujeme Ry(-theta) pred Z-meraním.
    q0 = Alice, q1 = Bob.
    """
    from spinqit import Circuit, H, CNOT, Ry
    circ = Circuit()
    q = circ.allocateQubits(2)
    circ.allocateClbits(2)
    # príprava previazaného stavu
    circ << (H, q[0])
    circ << (CNOT, [q[0], q[1]])
    # rotácia meracích báz (znamienko -theta je dôležité, dáva E = cos(a-b))
    circ << (Ry, q[0], -alice_angle)
    circ << (Ry, q[1], -bob_angle)
    return circ


# ===========================================================================
#  2) Spúšťanie na backendoch
# ===========================================================================
def _run_spinqit(circ, backend: str, shots: int,
                 device: Optional[dict] = None) -> Tuple[Dict[str, float], Optional[Dict[str, int]]]:
    """Skompiluje a spustí obvod na spinqit simulátore alebo NMR zariadení."""
    from spinqit import get_compiler
    comp = get_compiler("native")
    exe = comp.compile(circ, 0)  # 0 = bez optimalizácie

    if backend == "nmr":
        from spinqit import get_nmr, NMRConfig
        if not device:
            raise ValueError("Pre backend 'nmr' treba zadať pripojenie k zariadeniu (device=...).")
        engine = get_nmr()
        cfg = NMRConfig()
        cfg.configure_ip(str(device["ip"]))
        cfg.configure_port(int(device["port"]))
        cfg.configure_account(str(device["account"]), str(device["password"]))
        cfg.configure_task(str(device.get("task", "CHSH")), str(device.get("desc", "Bell")))
        cfg.configure_shots(int(shots))
        result = engine.execute(exe, cfg)

    elif backend == "torch":
        from spinqit import get_torch_simulator, TorchSimulatorConfig
        engine = get_torch_simulator()
        cfg = TorchSimulatorConfig()
        cfg.configure_shots(int(shots))
        result = engine.execute(exe, cfg)

    elif backend == "basic":
        from spinqit import get_basic_simulator, BasicSimulatorConfig
        engine = get_basic_simulator()
        cfg = BasicSimulatorConfig()
        cfg.configure_shots(int(shots))
        result = engine.execute(exe, cfg)

    else:
        raise ValueError(f"Neznámy spinqit backend: {backend!r}")

    probs = {str(k): float(v) for k, v in dict(result.probabilities).items()}
    try:
        counts = {str(k): int(v) for k, v in dict(result.counts).items()}
    except Exception:
        # NMR zariadenie vracia iba pravdepodobnosti
        counts = None
    return _fill_keys(probs), counts


# ---- ideálny statevector simulátor (čistý Python, bez závislostí) ----------
def _ry(theta: float) -> List[List[float]]:
    """Matica Ry(theta) = exp(-i theta Y/2)."""
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return [[c, -s], [s, c]]


def _kron2(A, B) -> List[List[float]]:
    """Kroneckerov súčin dvoch 2x2 matíc -> 4x4 (qubit 0 = najvyšší bit)."""
    M = [[0.0] * 4 for _ in range(4)]
    for i in range(2):
        for j in range(2):
            for k in range(2):
                for l in range(2):
                    M[2 * i + k][2 * j + l] = A[i][j] * B[k][l]
    return M


def _matvec(M, v):
    return [sum(M[r][c] * v[c] for c in range(len(v))) for r in range(len(M))]


def ideal_probabilities(alice_angle: Optional[float] = None,
                        bob_angle: Optional[float] = None) -> Dict[str, float]:
    """
    Presné pravdepodobnosti pre |Phi+> s voliteľnými rotáciami báz Ry(-uhol).
    Konvencia: ľavý bit kľúča = qubit 0 (Alice) — zhoduje sa so SpinQit.
    """
    a = 0.0 if alice_angle is None else alice_angle
    b = 0.0 if bob_angle is None else bob_angle
    psi = [1 / math.sqrt(2), 0.0, 0.0, 1 / math.sqrt(2)]  # |Phi+>
    U = _kron2(_ry(-a), _ry(-b))
    psi = _matvec(U, psi)
    p = [abs(x) ** 2 for x in psi]
    total = sum(p) or 1.0
    return {format(i, "02b"): p[i] / total for i in range(4)}


def sample_counts(probs: Dict[str, float], shots: int) -> Dict[str, int]:
    """Multinomické vzorkovanie -> simulácia konečného počtu meraní (shot noise)."""
    keys = list(probs.keys())
    weights = [max(0.0, probs[k]) for k in keys]
    draws = random.choices(keys, weights=weights, k=int(shots))
    c = Counter(draws)
    return {k: int(c.get(k, 0)) for k in keys}


def _fill_keys(probs: Dict[str, float], n_bits: int = 2) -> Dict[str, float]:
    """Doplní chýbajúce kľúče (00,01,10,11) s nulou — pre stabilné zobrazenie."""
    out = {format(i, f"0{n_bits}b"): 0.0 for i in range(2 ** n_bits)}
    for k, v in probs.items():
        out[k.zfill(n_bits)] = out.get(k.zfill(n_bits), 0.0) + float(v)
    return out


# ===========================================================================
#  3) Spúšťanie jednotlivých nastavení
# ===========================================================================
def run_bell(backend: str = "ideal", shots: int = 1024,
             device: Optional[dict] = None) -> Tuple[Dict[str, float], Optional[Dict[str, int]]]:
    """Spustí samotný Bellov stav (bez rotácie báz)."""
    if backend == "ideal":
        exact = ideal_probabilities(None, None)
        if shots:
            counts = sample_counts(exact, shots)
            probs = {k: counts[k] / shots for k in exact}
        else:
            counts, probs = None, exact
        return _fill_keys(probs), counts
    return _run_spinqit(build_bell_circuit(), backend, shots, device)


def run_setting(backend: str, alice_angle: float, bob_angle: float,
                shots: int = 1024,
                device: Optional[dict] = None) -> Tuple[Dict[str, float], Optional[Dict[str, int]]]:
    """Spustí jedno CHSH nastavenie (dvojica uhlov Alice/Bob)."""
    if backend == "ideal":
        exact = ideal_probabilities(alice_angle, bob_angle)
        if shots:
            counts = sample_counts(exact, shots)
            probs = {k: counts[k] / shots for k in exact}
        else:
            counts, probs = None, exact
        return _fill_keys(probs), counts
    return _run_spinqit(build_chsh_circuit(alice_angle, bob_angle), backend, shots, device)


# ===========================================================================
#  4) Korelácie a CHSH parameter
# ===========================================================================
def correlation(probs: Dict[str, float]) -> float:
    """
    E = P(00) + P(11) - P(01) - P(10).
    Rovnaké bity (00,11) -> +1, rozdielne (01,10) -> -1. Sčítava cez všetky kľúče,
    je robustné voči endianness aj chýbajúcim kľúčom.
    """
    total = sum(probs.values()) or 1.0
    e = 0.0
    for key, p in probs.items():
        k = key.zfill(2)
        sign = 1.0 if k[0] == k[1] else -1.0
        e += sign * (p / total)
    return e


def chsh_value(e_ab: float, e_ab2: float, e_a2b: float, e_a2b2: float) -> float:
    """S = E(a,b) - E(a,b') + E(a',b) + E(a',b')."""
    return e_ab - e_ab2 + e_a2b + e_a2b2


def theory_correlation(alice_angle: float, bob_angle: float) -> float:
    """Teoretická predpoveď QM pre |Phi+>: E(a,b) = cos(a-b)."""
    return math.cos(alice_angle - bob_angle)


# ===========================================================================
#  5) Celý CHSH experiment (4 obvody) a korelačná krivka
# ===========================================================================
@dataclass
class CHSHResult:
    backend: str
    shots: int
    alice: Tuple[float, float]
    bob: Tuple[float, float]
    settings: List[dict] = field(default_factory=list)  # 4 nastavenia s E, teóriou, probs
    S: float = 0.0
    S_theory: float = 0.0
    classical_bound: float = CLASSICAL_BOUND
    quantum_bound: float = QUANTUM_BOUND

    @property
    def violates_classical(self) -> bool:
        return abs(self.S) > self.classical_bound

    def to_dict(self) -> dict:
        return {
            "backend": self.backend,
            "shots": self.shots,
            "alice": list(self.alice),
            "bob": list(self.bob),
            "settings": self.settings,
            "S": self.S,
            "S_theory": self.S_theory,
            "classical_bound": self.classical_bound,
            "quantum_bound": self.quantum_bound,
            "violates_classical": self.violates_classical,
            "abs_S": abs(self.S),
        }


def run_chsh(backend: str = "ideal", shots: int = 1024,
             alice: Tuple[float, float] = DEFAULT_ALICE,
             bob: Tuple[float, float] = DEFAULT_BOB,
             device: Optional[dict] = None,
             task_prefix: str = "CHSH") -> CHSHResult:
    """
    Spustí celý CHSH test: 4 obvody pre dvojice (a,b), (a,b'), (a',b), (a',b'),
    vypočíta 4 korelácie a CHSH parameter S.
    """
    a, ap = alice
    b, bp = bob
    combos = [
        ("E(a,b)",   a,  b,  +1),
        ("E(a,b')",  a,  bp, -1),
        ("E(a',b)",  ap, b,  +1),
        ("E(a',b')", ap, bp, +1),
    ]

    settings: List[dict] = []
    e_vals: List[float] = []
    for label, ang_a, ang_b, sign in combos:
        dev = None
        if device is not None:
            dev = dict(device)
            # rozlíšiteľný názov úlohy na zariadení pre každý obvod
            dev["task"] = f"{task_prefix}_{label}".replace("(", "").replace(")", "").replace(",", "_").replace("'", "p")
        probs, counts = run_setting(backend, ang_a, ang_b, shots, dev)
        e = correlation(probs)
        e_vals.append(e)
        settings.append({
            "label": label,
            "alice_angle": ang_a,
            "bob_angle": ang_b,
            "sign": sign,
            "E": e,
            "E_theory": theory_correlation(ang_a, ang_b),
            "probabilities": probs,
            "counts": counts,
        })

    S = chsh_value(e_vals[0], e_vals[1], e_vals[2], e_vals[3])
    S_theory = chsh_value(
        theory_correlation(a, b),
        theory_correlation(a, bp),
        theory_correlation(ap, b),
        theory_correlation(ap, bp),
    )
    return CHSHResult(backend=backend, shots=shots, alice=alice, bob=bob,
                      settings=settings, S=S, S_theory=S_theory)


def run_sweep(backend: str = "ideal", shots: int = 1024,
              alice_angle: float = 0.0, n_points: int = 25,
              device: Optional[dict] = None) -> List[dict]:
    """
    Korelačná krivka: fixne Alicin uhol, prejdeme Bobov uhol 0..2pi a meriame E.
    Vracia body {bob, E, E_theory} na porovnanie nameranej krivky s cos(a-b).
    """
    pts: List[dict] = []
    for i in range(n_points):
        beta = 2 * math.pi * i / (n_points - 1)
        dev = None
        if device is not None:
            dev = dict(device)
            dev["task"] = f"sweep_{i}"
        probs, _ = run_setting(backend, alice_angle, beta, shots, dev)
        pts.append({
            "bob": beta,
            "E": correlation(probs),
            "E_theory": theory_correlation(alice_angle, beta),
        })
    return pts


def spinqit_available() -> bool:
    """Je nainštalovaný spinqit (potrebné pre torch/basic/nmr backendy)?"""
    try:
        import spinqit  # noqa: F401
        return True
    except Exception:
        return False
