"use strict";

// ===========================================================================
//  Pomocné funkcie
// ===========================================================================
const $ = (id) => document.getElementById(id);
const SVGNS = "http://www.w3.org/2000/svg";
const DEG = (r) => (r * 180 / Math.PI);
const RAD = (d) => (d * Math.PI / 180);

function svg(w, h) {
  const s = document.createElementNS(SVGNS, "svg");
  s.setAttribute("viewBox", `0 0 ${w} ${h}`);
  s.setAttribute("width", "100%");
  s.style.maxWidth = w + "px";
  return s;
}
function el(tag, attrs = {}, text) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  return e;
}
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// ===========================================================================
//  Záložky
// ===========================================================================
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.tab).classList.add("active");
  });
});
function goTab(name) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === name));
}

// ===========================================================================
//  Stav servera
// ===========================================================================
let HEALTH = { spinqit_available: false, quantum_bound: 2 * Math.SQRT2, classical_bound: 2 };
async function checkHealth() {
  try {
    const r = await fetch("/api/health");
    HEALTH = await r.json();
    const st = $("status");
    if (HEALTH.spinqit_available) {
      st.textContent = "● server beží · spinqit dostupný · backendy: " + HEALTH.backends.join(", ");
      st.className = "status ok";
    } else {
      st.textContent = "● server beží · spinqit NEdostupný — funguje len ideálny simulátor";
      st.className = "status warn";
    }
  } catch (e) {
    $("status").textContent = "● server neodpovedá — spusti: python3 server.py";
    $("status").className = "status warn";
  }
}

// ===========================================================================
//  Blochova sféra
// ===========================================================================
const blochState = { theta: RAD(60), phi: RAD(40) };

function renderBloch() {
  const host = $("bloch");
  host.innerHTML = "";
  const W = 280, H = 280, cx = W / 2, cy = H / 2, R = 110;
  const s = svg(W, H);

  // sféra (elipsy)
  s.appendChild(el("circle", { cx, cy, r: R, fill: "rgba(78,161,255,0.06)", stroke: css("--line"), "stroke-width": 1 }));
  s.appendChild(el("ellipse", { cx, cy, rx: R, ry: R * 0.34, fill: "none", stroke: css("--line"), "stroke-dasharray": "3 3" }));
  s.appendChild(el("line", { x1: cx, y1: cy - R, x2: cx, y2: cy + R, stroke: css("--line") }));
  s.appendChild(el("line", { x1: cx - R, y1: cy, x2: cx + R, y2: cy, stroke: css("--line") }));
  s.appendChild(el("text", { x: cx + 4, y: cy - R - 4, "font-size": 12 }, "|0⟩"));
  s.appendChild(el("text", { x: cx + 4, y: cy + R + 14, "font-size": 12 }, "|1⟩"));

  // vektor stavu (projekcia 3D -> 2D)
  const { theta, phi } = blochState;
  const x = Math.sin(theta) * Math.cos(phi);
  const y = Math.sin(theta) * Math.sin(phi);
  const z = Math.cos(theta);
  const px = cx + R * x;            // x doprava
  const py = cy - R * z + R * 0.34 * y;  // z hore, y do hĺbky
  s.appendChild(el("line", { x1: cx, y1: cy, x2: px, y2: py, stroke: css("--accent2"), "stroke-width": 3 }));
  s.appendChild(el("circle", { cx: px, cy: py, r: 6, fill: css("--accent2") }));

  host.appendChild(s);

  // amplitúdy
  const a = Math.cos(theta / 2);
  const b = Math.sin(theta / 2);
  const p0 = (a * a).toFixed(3), p1 = (b * b).toFixed(3);
  $("stateReadout").innerHTML =
    `|ψ⟩ = ${a.toFixed(3)}·|0⟩ + e<sup>i·${DEG(phi).toFixed(0)}°</sup>·${b.toFixed(3)}·|1⟩<br>` +
    `P(0) = ${p0} &nbsp;&nbsp; P(1) = ${p1}`;
  $("thetaVal").textContent = DEG(theta).toFixed(0) + "°";
  $("phiVal").textContent = DEG(phi).toFixed(0) + "°";
}

$("theta").addEventListener("input", e => { blochState.theta = RAD(+e.target.value); renderBloch(); });
$("phi").addEventListener("input", e => { blochState.phi = RAD(+e.target.value); renderBloch(); });

document.querySelectorAll(".mini").forEach(b => b.addEventListener("click", () => {
  const g = b.dataset.gate;
  let { theta, phi } = blochState;
  // jednoduché pôsobenie hradiel na uhly (pre názornosť)
  if (g === "reset") { theta = 0; phi = 0; }
  else if (g === "X") { theta = Math.PI - theta; phi = -phi; }
  else if (g === "Z") { phi = (phi + Math.PI); }
  else if (g === "Y") { theta = Math.PI - theta; phi = Math.PI - phi; }
  else if (g === "H") {
    // H: |0>->|+> (theta=90,phi=0), |1>->|-> ; aproximácia cez výmenu osí x<->z
    const x = Math.sin(theta) * Math.cos(phi), z = Math.cos(theta);
    theta = Math.acos(Math.min(1, Math.max(-1, x)));
    phi = z >= 0 ? 0 : Math.PI;
  }
  phi = ((phi % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  blochState.theta = Math.min(Math.PI, Math.max(0, theta));
  blochState.phi = phi;
  $("theta").value = DEG(blochState.theta).toFixed(0);
  $("phi").value = DEG(blochState.phi).toFixed(0);
  renderBloch();
}));

// ===========================================================================
//  Experiment — ovládanie
// ===========================================================================
function updateCircuitText() {
  $("circuitText").textContent =
`# Bellov stav |Phi+>
circ << (H, q[0])
circ << (CNOT, [q[0], q[1]])

# CHSH nastavenie (uhly a = Alice, b = Bob), 4 obvody:
circ << (Ry, q[0], -a)   # rotácia meracej bázy Alice
circ << (Ry, q[1], -b)   # rotácia meracej bázy Bob
# E(a,b) = P00 + P11 - P01 - P10  ->  S = E(a,b)-E(a,b')+E(a',b)+E(a',b')`;
}
$("backend").addEventListener("change", e => {
  $("deviceBox").hidden = e.target.value !== "nmr";
});

function payload(extra = {}) {
  const backend = $("backend").value;
  const p = { backend, shots: +$("shots").value, ...extra };
  if (backend === "nmr") {
    p.device = {
      ip: $("dev_ip").value.trim(),
      port: $("dev_port").value ? +$("dev_port").value : undefined,
      account: $("dev_account").value.trim(),
      password: $("dev_password").value,
    };
  }
  return p;
}

function setBusy(on) {
  $("busy").hidden = !on;
  document.querySelectorAll(".run-buttons button").forEach(b => b.disabled = on);
}
function log(msg) {
  $("runLog").textContent = msg;
}

async function api(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!data.ok) throw new Error(data.error || "neznáma chyba");
  return data;
}

$("runBell").addEventListener("click", async () => {
  setBusy(true); log("Spúšťam Bellov stav…");
  try {
    const d = await api("/api/bell", payload());
    renderBell(d);
    log(`Hotovo (${d.backend}). E(ZZ) = ${d.E_zz.toFixed(3)}`);
    goTab("analyza");
  } catch (e) { log("Chyba: " + e.message); }
  finally { setBusy(false); }
});

$("runChsh").addEventListener("click", async () => {
  setBusy(true); log("Spúšťam CHSH test (4 obvody)…");
  try {
    const d = await api("/api/chsh", payload());
    renderChsh(d);
    log(`Hotovo (${d.backend}). S = ${d.S.toFixed(3)} (|S|=${d.abs_S.toFixed(3)})`);
    goTab("analyza");
  } catch (e) { log("Chyba: " + e.message); }
  finally { setBusy(false); }
});

$("runSweep").addEventListener("click", async () => {
  setBusy(true); log("Meriam korelačnú krivku…");
  try {
    const d = await api("/api/sweep", payload({ alice_angle: 0, points: 25 }));
    renderSweep(d);
    log(`Hotovo (${d.backend}). ${d.points.length} bodov.`);
    goTab("analyza");
  } catch (e) { log("Chyba: " + e.message); }
  finally { setBusy(false); }
});

// ===========================================================================
//  Vizualizácie (SVG)
// ===========================================================================
function showResultBlocks() { $("noData").hidden = true; }

function renderBell(d) {
  showResultBlocks();
  $("bellResult").hidden = false;
  const host = $("bellChart"); host.innerHTML = "";
  const keys = ["00", "01", "10", "11"];
  const vals = keys.map(k => d.probabilities[k] || 0);
  host.appendChild(barChart(keys, vals, "pravdepodobnosť"));
  const eq = ((d.probabilities["00"] || 0) + (d.probabilities["11"] || 0)) * 100;
  $("bellNote").innerHTML =
    `Zhodné výsledky (00 alebo 11): <b>${eq.toFixed(1)}%</b>. ` +
    `Pre dokonalý |Φ⁺⟩ je to 100 % — qubity sú dokonale skorelované. ` +
    `E(ZZ) = <b>${d.E_zz.toFixed(3)}</b>.`;
}

function barChart(labels, values, ylabel) {
  const W = 560, H = 280, pad = 46, bw = (W - 2 * pad) / labels.length;
  const s = svg(W, H);
  const maxV = Math.max(1, ...values);
  // os
  s.appendChild(el("line", { x1: pad, y1: H - pad, x2: W - pad, y2: H - pad, stroke: css("--line") }));
  s.appendChild(el("line", { x1: pad, y1: pad, x2: pad, y2: H - pad, stroke: css("--line") }));
  for (let t = 0; t <= 1.0001; t += 0.25) {
    const y = H - pad - t * (H - 2 * pad);
    s.appendChild(el("line", { x1: pad, y1: y, x2: W - pad, y2: y, stroke: css("--line"), "stroke-dasharray": "2 4", opacity: .5 }));
    s.appendChild(el("text", { x: pad - 8, y: y + 4, "text-anchor": "end", "font-size": 11 }, t.toFixed(2)));
  }
  values.forEach((v, i) => {
    const h = (v / maxV) * (H - 2 * pad);
    const x = pad + i * bw + bw * 0.18;
    const w = bw * 0.64;
    s.appendChild(el("rect", { x, y: H - pad - h, width: w, height: h, rx: 4,
      fill: i === 0 || i === 3 ? css("--accent") : css("--muted") }));
    s.appendChild(el("text", { x: x + w / 2, y: H - pad - h - 6, "text-anchor": "middle", "font-size": 12 }, v.toFixed(3)));
    s.appendChild(el("text", { x: x + w / 2, y: H - pad + 16, "text-anchor": "middle", "font-size": 12 }, "|" + labels[i] + "⟩"));
  });
  s.appendChild(el("text", { x: 14, y: H / 2, "font-size": 11, transform: `rotate(-90 14 ${H / 2})`, "text-anchor": "middle", fill: css("--muted") }, ylabel));
  return s;
}

function renderChsh(d) {
  showResultBlocks();
  $("chshResult").hidden = false;
  // gauge
  $("chshGauge").innerHTML = "";
  $("chshGauge").appendChild(chshGauge(d.abs_S, d.classical_bound, d.quantum_bound));
  // tabuľka
  const t = $("chshTable");
  t.innerHTML = "<tr><th>Nastavenie</th><th>a [°]</th><th>b [°]</th><th>E namerané</th><th>E teória cos(a−b)</th></tr>";
  d.settings.forEach(s => {
    const row = t.insertRow();
    row.innerHTML =
      `<td>${s.label}</td><td>${DEG(s.alice_angle).toFixed(0)}</td><td>${DEG(s.bob_angle).toFixed(0)}</td>` +
      `<td><b>${s.E.toFixed(3)}</b></td><td>${s.E_theory.toFixed(3)}</td>`;
  });
  const sum = t.insertRow();
  sum.innerHTML = `<td colspan="3" style="text-align:right">S = E(a,b)−E(a,b′)+E(a′,b)+E(a′,b′) =</td>` +
    `<td><b>${d.S.toFixed(3)}</b></td><td>${d.S_theory.toFixed(3)}</td>`;
  // verdikt
  const v = $("chshVerdict");
  if (d.violates_classical) {
    v.className = "verdict good";
    v.innerHTML = `|S| = <b>${d.abs_S.toFixed(3)}</b> &gt; 2 → <b>PORUŠENIE Bellovej nerovnosti.</b> ` +
      `Korelácie sa nedajú vysvetliť žiadnym lokálnym realistickým modelom (klasická hranica je 2; ` +
      `kvantové maximum 2√2 ≈ 2,828).`;
  } else {
    v.className = "verdict bad";
    v.innerHTML = `|S| = <b>${d.abs_S.toFixed(3)}</b> ≤ 2 → bez porušenia (v rámci klasických hraníc).`;
  }
}

function chshGauge(S, cb, qb) {
  const W = 560, H = 130, pad = 30, maxX = 3.0;
  const s = svg(W, H);
  const X = (val) => pad + (val / maxX) * (W - 2 * pad);
  const y = 70;
  // pás
  s.appendChild(el("rect", { x: X(0), y: y - 12, width: X(cb) - X(0), height: 24, fill: "rgba(255,207,92,.18)" }));
  s.appendChild(el("rect", { x: X(cb), y: y - 12, width: X(qb) - X(cb), height: 24, fill: "rgba(124,92,255,.20)" }));
  s.appendChild(el("line", { x1: X(0), y1: y, x2: X(maxX), y2: y, stroke: css("--line") }));
  // hranice
  [[cb, "klasická = 2", css("--classic")], [qb, "kvantová 2√2", css("--quantum")]].forEach(([val, lab, col]) => {
    s.appendChild(el("line", { x1: X(val), y1: y - 20, x2: X(val), y2: y + 20, stroke: col, "stroke-width": 2 }));
    s.appendChild(el("text", { x: X(val), y: y + 36, "text-anchor": "middle", "font-size": 11, fill: col }, lab));
  });
  // hodnota S
  const col = S > cb ? css("--good") : css("--bad");
  s.appendChild(el("circle", { cx: X(Math.min(S, maxX)), cy: y, r: 9, fill: col, stroke: "#fff", "stroke-width": 1.5 }));
  s.appendChild(el("text", { x: X(Math.min(S, maxX)), y: y - 22, "text-anchor": "middle", "font-size": 14, fill: col, "font-weight": "700" }, "|S| = " + S.toFixed(3)));
  // os
  for (let v = 0; v <= maxX + .001; v += 0.5) {
    s.appendChild(el("text", { x: X(v), y: y + 52, "text-anchor": "middle", "font-size": 10, fill: css("--muted") }, v.toFixed(1)));
  }
  return s;
}

function renderSweep(d) {
  showResultBlocks();
  $("sweepResult").hidden = false;
  const host = $("sweepChart"); host.innerHTML = "";
  host.appendChild(lineChart(d.points));
}

function lineChart(points) {
  const W = 600, H = 320, pad = 46;
  const s = svg(W, H);
  const X = (b) => pad + (b / (2 * Math.PI)) * (W - 2 * pad);
  const Y = (e) => (H / 2) - e * (H / 2 - pad);  // e in [-1,1]
  // mriežka
  s.appendChild(el("line", { x1: pad, y1: Y(0), x2: W - pad, y2: Y(0), stroke: css("--line") }));
  [-1, -0.5, 0.5, 1].forEach(e => {
    s.appendChild(el("line", { x1: pad, y1: Y(e), x2: W - pad, y2: Y(e), stroke: css("--line"), "stroke-dasharray": "2 4", opacity: .5 }));
    s.appendChild(el("text", { x: pad - 8, y: Y(e) + 4, "text-anchor": "end", "font-size": 11 }, e.toFixed(1)));
  });
  [0, 90, 180, 270, 360].forEach(deg => {
    const x = X(RAD(deg));
    s.appendChild(el("text", { x, y: H - 14, "text-anchor": "middle", "font-size": 11, fill: css("--muted") }, deg + "°"));
  });
  s.appendChild(el("text", { x: W / 2, y: H - 2, "text-anchor": "middle", "font-size": 11, fill: css("--muted") }, "uhol Boba b (Alice = 0°)"));
  // teoretická krivka
  let dpath = "";
  points.forEach((p, i) => { dpath += (i ? "L" : "M") + X(p.bob) + " " + Y(p.E_theory) + " "; });
  s.appendChild(el("path", { d: dpath, fill: "none", stroke: css("--quantum"), "stroke-width": 2 }));
  // namerané body
  points.forEach(p => {
    s.appendChild(el("circle", { cx: X(p.bob), cy: Y(p.E), r: 3.5, fill: css("--accent") }));
  });
  // legenda
  s.appendChild(el("circle", { cx: W - 150, cy: 22, r: 4, fill: css("--accent") }));
  s.appendChild(el("text", { x: W - 142, y: 26, "font-size": 11 }, "namerané E"));
  s.appendChild(el("line", { x1: W - 150 - 6, y1: 40, x2: W - 150 + 6, y2: 40, stroke: css("--quantum"), "stroke-width": 2 }));
  s.appendChild(el("text", { x: W - 142, y: 44, "font-size": 11 }, "teória cos(a−b)"));
  return s;
}

// ===========================================================================
//  Štart
// ===========================================================================
renderBloch();
updateCircuitText();
checkHealth();
