const API_BASE = "http://127.0.0.1:8000";

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

const toast = document.getElementById("toast");
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3200);
}

const birthForm = document.getElementById("birthForm");
const generateBtn = document.getElementById("generateBtn");

birthForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    name: document.getElementById("name").value.trim(),
    gender: document.getElementById("gender").value,
    dob: normalizeDob(document.getElementById("dob").value),
    time: document.getElementById("time").value,
    place: document.getElementById("place").value.trim(),
    latitude: numberOrNull("latitude"),
    longitude: numberOrNull("longitude"),
    timezone_name: valueOrNull("timezone"),
    ayanamsa: "Lahiri",
    node_type: "mean"
  };

  if (!payload.name || !payload.dob || !payload.time || !payload.place) return;

  console.log("AstroSight payload:",payload);
  generateBtn.disabled = true;
  generateBtn.innerHTML = "Calculating chart <span>⟳</span>";
  document.getElementById("chartMessage").innerHTML = "<span class='loading-dot'></span> Calculating planetary positions...";

  try {
    const response = await fetch(`${API_BASE}/api/chart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Chart calculation failed.");

    renderChart(data);
    showToast("Chart calculated successfully with Swiss Ephemeris.");
    document.getElementById("chart-results").classList.remove("hidden");
    document.getElementById("chart-results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    document.getElementById("chartMessage").innerHTML = `<strong>Calculation error</strong><br>${escapeHtml(err.message)}`;
    showToast(err.message);
  } finally {
    generateBtn.disabled = false;
    generateBtn.innerHTML = "Generate My Chart <span>→</span>";
  }
});

function normalizeDob(value) {
  const v = String(value || "").trim();

  if (!v) return "";

  // Already YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    return v;
  }

  // DD-MM-YYYY
  let match = v.match(/^(\d{2})-(\d{2})-(\d{4})$/);

  if (match) {
    const day = match[1];
    const month = match[2];
    const year = match[3];

    return `${year}-${month}-${day}`;
  }

  // DD/MM/YYYY
  match = v.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);

  if (match) {
    const day = match[1];
    const month = match[2];
    const year = match[3];

    return `${year}-${month}-${day}`;
  }

  return v;
}

function renderChart(data) {
  const asc = data.angles.ascendant;
  document.getElementById("chartMessage").innerHTML =
    `<strong>${escapeHtml(data.birth.name)}</strong><br>` +
    `${escapeHtml(asc.sign)} Lagna • ${escapeHtml(asc.degree)}<br>` +
    `<small>${escapeHtml(asc.nakshatra.name)} nakshatra • pada ${asc.nakshatra.pada}</small>`;

  document.getElementById("chartMeta").innerHTML =
    `<span>${escapeHtml(data.engine.zodiac)} zodiac</span>` +
    `<span>${escapeHtml(data.engine.ayanamsa)} ayanamsa</span>` +
    `<span>${escapeHtml(data.engine.house_system)} houses</span>`;

  renderWheel(data);
  document.getElementById("resultTitle").textContent = `${data.birth.name}'s Vedic Birth Chart`;
  document.getElementById("resultSubtitle").textContent =
    `${data.birth.place} • ${formatDateTime(data.birth.local_datetime)} • ${data.birth.timezone}`;

  const summary = [
    ["Lagna", `${asc.sign} ${asc.degree}`, asc.nakshatra.name],
    ["Moon Sign", findPlanet(data, "Moon").sign, `${findPlanet(data, "Moon").nakshatra} • pada ${findPlanet(data, "Moon").nakshatra_pada}`],
    ["Sun Sign", findPlanet(data, "Sun").sign, `House ${findPlanet(data, "Sun").house}`],
    ["Birth Location", `${data.birth.latitude.toFixed(4)}, ${data.birth.longitude.toFixed(4)}`, data.birth.timezone]
  ];
  document.getElementById("summaryGrid").innerHTML = summary.map(([a,b,c]) =>
    `<div class="summary-card"><span>${escapeHtml(a)}</span><strong>${escapeHtml(b)}</strong><small>${escapeHtml(c)}</small></div>`
  ).join("");

  document.getElementById("planetTableBody").innerHTML = data.planets.map(p => `
    <tr>
      <td><strong>${escapeHtml(p.planet)}</strong></td>
      <td>${escapeHtml(p.sign)}</td>
      <td>${escapeHtml(p.degree)}</td>
      <td>${p.house}</td>
      <td>${escapeHtml(p.nakshatra)} <small>(${p.nakshatra_pada})</small></td>
      <td><span class="tag">${escapeHtml(statusText(p))}</span></td>
    </tr>
  `).join("");

  document.getElementById("insightsList").innerHTML = data.insights.map(i =>
    `<div class="insight-item"><span>✦</span><p>${escapeHtml(i)}</p></div>`
  ).join("");
  document.getElementById("calculationNote").textContent = data.disclaimer;
}

function renderWheel(data) {
  const wheel = document.getElementById("chartWheel");
  wheel.querySelectorAll(".house-label, .planet-mark").forEach(el => el.remove());

  // Visual Vedic-style 12-sign ring. Positions are placed by sign, not by an
  // ornamental fake chart: the actual sign assignments come from the backend.
  data.houses.forEach((h, i) => {
    const angle = i * 30 - 90;
    const rad = angle * Math.PI / 180;
    const x = 50 + Math.cos(rad) * 38;
    const y = 50 + Math.sin(rad) * 38;
    const el = document.createElement("div");
    el.className = "house-label";
    el.style.left = `${x}%`;
    el.style.top = `${y}%`;
    el.innerHTML = `<b>${h.house}</b><span>${h.sign}</span>`;
    wheel.appendChild(el);
  });

  const byHouse = data.planets_by_house;
  Object.entries(byHouse).forEach(([house, planets]) => {
    if (!planets.length) return;
    const i = Number(house) - 1;
    const angle = i * 30 - 90 + 14;
    const rad = angle * Math.PI / 180;
    const x = 50 + Math.cos(rad) * 23;
    const y = 50 + Math.sin(rad) * 23;
    const el = document.createElement("div");
    el.className = "planet-mark";
    el.style.left = `${x}%`;
    el.style.top = `${y}%`;
    el.textContent = planets.join(" ");
    wheel.appendChild(el);
  });
}

function findPlanet(data, name) {
  return data.planets.find(p => p.planet === name);
}

function statusText(p) {
  const parts = [];
  if (p.retrograde) parts.push("Retrograde");
  if (p.dignity && p.dignity !== "Neutral") parts.push(p.dignity);
  return parts.join(" • ") || "Direct";
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function valueOrNull(id) {
  const v = document.getElementById(id).value.trim();
  return v || null;
}

function numberOrNull(id) {
  const v = document.getElementById(id).value.trim();
  return v === "" ? null : Number(v);
}

const palmInput = document.getElementById("palmInput");
const imagePreview = document.getElementById("imagePreview");
const dropZone = document.getElementById("dropZone");

palmInput.addEventListener("change", (e) => handleImage(e.target.files[0]));
["dragenter", "dragover"].forEach(evt => dropZone.addEventListener(evt, (e) => {
  e.preventDefault(); dropZone.classList.add("drag");
}));
["dragleave", "drop"].forEach(evt => dropZone.addEventListener(evt, (e) => {
  e.preventDefault(); dropZone.classList.remove("drag");
}));
dropZone.addEventListener("drop", (e) => handleImage(e.dataTransfer.files[0]));

function handleImage(file) {
  if (!file || !file.type.startsWith("image/")) {
    showToast("Please choose a valid image.");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    imagePreview.innerHTML = `<img src="${reader.result}" alt="Palm preview">`;
    showToast("Palm image loaded. ML processing is the next module.");
  };
  reader.readAsDataURL(file);
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[c]));
}
