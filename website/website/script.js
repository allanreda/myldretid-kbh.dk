// --------- ENV URLs ----------
let url;
if (window.location.hostname.includes("dev")) {
  url = "https://storage.googleapis.com/myldretid-kbh-dev-predictions/predictions/json_predictions.json";
} else {
  url = "https://storage.googleapis.com/myldretid-kbh-prod-predictions/predictions/json_predictions.json";
}

// --------- GLOBAL STATE ----------
let currentLang = "da";
let latestCombined = null;      // holds all predictions once fetched
let latestHeroValue = null;     // first (next) rush-hour % value

// --------- STATIC TEXT TRANSLATIONS ----------
const translations = {
  da: {
    title: "Myldretid i København",
    tagline: "ML-baserede trafikprognoser for myldretiden i København - opdateres kl. 10 og 18 hver dag.",
    heroSummary: "Næste myldretid:",
    loading: "Indlæser prognoser...",
    footer: "© 2025 myldretid-kbh · Udviklet af Allan Fattah Reda",
  },
  en: {
    title: "Rush Hour in Copenhagen",
    tagline: "ML-based traffic forecasts for Copenhagen’s rush hour – updated daily at 10 AM and 6 PM.",
    heroSummary: "Next rush hour:",
    loading: "Loading forecasts...",
    footer: "© 2025 myldretid-kbh · Developed by Allan Fattah Reda",
  },
};

// --------- DYNAMIC TEXT (LOCALIZED) ----------
function getDescription(val, lang = currentLang) {
  if (lang === "da") {
    if (val < -15) return "🚀 Meget hurtigere end normalt";
    if (val < -10) return "🚗 Hurtigere end normalt";
    if (val < -5)  return "👍 En smule hurtigere end normalt";
    if (val < 5)   return "👌 Omtrent som normalt";
    if (val < 10)  return "⚠️ En smule langsommere end normalt";
    if (val < 15)  return "🛑 Langsommere end normalt";
    return "🪦 Meget langsommere end normalt";
  } else {
    if (val < -15) return "🚀 Much faster than usual";
    if (val < -10) return "🚗 Faster than usual";
    if (val < -5)  return "👍 Slightly faster than usual";
    if (val < 5)   return "👌 About normal";
    if (val < 10)  return "⚠️ Slightly slower than usual";
    if (val < 15)  return "🛑 Slower than usual";
    return "🪦 Much slower than usual";
  }
}

function formatDateLabel(dateStr, period, lang = currentLang) {
  const date = new Date(dateStr);
  const locale = lang === "da" ? "da-DK" : "en-GB";
  const day = date.toLocaleString(locale, { weekday: "long" });
  const icon = period === "morning" ? "🌅" : "🌇";
  const label = lang === "da" ? (period === "morning" ? "Morgen" : "Eftermiddag")
                              : (period === "morning" ? "Morning" : "Afternoon");
  const dayNum = String(date.getDate()).padStart(2, "0");
  const monthNum = String(date.getMonth() + 1).padStart(2, "0");
  return `${icon} ${day.charAt(0).toUpperCase() + day.slice(1)}, ${dayNum}.${monthNum} ${label}`;
}

// --------- COLOR SCALE ----------
function getColor(val) {
  if (val < -15) return "#05f545";
  if (val < -10) return "#1abc9c";
  if (val < -5)  return "#37c477";
  if (val < 5)   return "#ffff00";
  if (val < 10)  return "#f39c12";
  if (val < 15)  return "#e67e22";
  return "#f70525";
}

// --------- GAUGE RENDERING ----------
function createGauge(id, val, label, description, color, isSmall = false) {
  const data = [{
    type: "indicator",
    mode: "gauge+number",
    value: val,
    title: {
      text: `<b>${label}</b><br><span style="color:gray;font-size:${isSmall ? 12 : 14}px">${description}</span>`,
      font: { size: isSmall ? 14 : 16 }
    },
    number: { suffix: "%", font: { size: isSmall ? 22 : 28, color: "#2c3e50" } },
    gauge: {
      axis: { range: [-30, 30], tickwidth: 1 },
      bar: { color },
      bgcolor: "#f9f9f9",
      bordercolor: "#e0e0e0",
      borderwidth: 1,
      threshold: { line: { color: "#34495e", width: 2 }, value: 0 }
    }
  }];

  Plotly.newPlot(id, data, {
    paper_bgcolor: '#f0f6ff',
    plot_bgcolor: '#f0f6ff',
    margin: { t: 60, b: 0, l: 10, r: 10 }
  }, { responsive: true });
}

function renderGaugesFromCombined(combined, lang = currentLang) {
  // split lists
  const mainGauges = combined.slice(0, 2);
  const secondaryGauges = combined.slice(2, 10);

  // update hero text based on the very next rush hour
  latestHeroValue = mainGauges[0]?.value ?? null;
  const heroEl = document.getElementById("hero-description");
  if (latestHeroValue == null) {
    heroEl.innerText = translations[lang].loading;
  } else {
    heroEl.innerText = getDescription(latestHeroValue, lang);
  }

  // clear and rebuild containers
  const mainDiv = document.getElementById("main-gauges");
  const secondDiv = document.getElementById("secondary-gauges");
  mainDiv.innerHTML = "";
  secondDiv.innerHTML = "";

  let idCounter = 0;
  const all = mainGauges.concat(secondaryGauges);
  for (const g of all) {
    const id = `gauge-${idCounter++}`;
    const el = document.createElement("div");
    el.id = id;
    el.className = "gauge";
    (mainGauges.includes(g) ? mainDiv : secondDiv).appendChild(el);

    createGauge(
      id,
      g.value,
      formatDateLabel(g.date, g.period, lang),
      getDescription(g.value, lang),
      getColor(g.value),
      !mainGauges.includes(g)
    );
  }
}

// --------- MAIN FETCH FLOW ----------
async function main() {
  try {
    const res = await fetch(`${url}?ts=${Date.now()}`);
    const data = await res.json();

    const combined = [
      ...Object.entries(data.morning_predictions).map(([d, v]) => ({ date: d, period: 'morning', value: v })),
      ...Object.entries(data.afternoon_predictions).map(([d, v]) => ({ date: d, period: 'afternoon', value: v }))
    ];

    combined.sort((a, b) => {
      const da = new Date(a.date), db = new Date(b.date);
      return da - db || (a.period === 'morning' ? -1 : 1);
    });

    latestCombined = combined;
    renderGaugesFromCombined(latestCombined, currentLang);

  } catch (err) {
    console.error("Failed to load data:", err);
    document.getElementById("hero-description").innerText =
      currentLang === "da" ? "Kunne ikke indlæse trafikdata 😞" : "Failed to load traffic data 😞";
  }
}

// --------- LANGUAGE SWITCHER ----------
function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("lang", lang);
  const t = translations[lang];

  // Static text
  document.getElementById("title").innerText = t.title;
  document.getElementById("tagline").innerText = t.tagline;
  document.getElementById("hero-summary").innerText = t.heroSummary;
  document.getElementById("footer-text").innerText = t.footer;
  document.documentElement.lang = lang;

  // Hero text: show loading only if we don't have data yet
  const heroEl = document.getElementById("hero-description");
  if (latestHeroValue == null) {
    heroEl.innerText = t.loading;
  } else {
    heroEl.innerText = getDescription(latestHeroValue, lang);
  }

  // Re-render gauges with localized labels/descriptions if data already loaded
  if (latestCombined) {
    renderGaugesFromCombined(latestCombined, lang);
  }
}

// --------- BOOTSTRAP ----------
document.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem("lang") || "da";
  setLanguage(saved);     // set language FIRST (won't overwrite loaded data anymore)
  main();                 // then fetch & render; hero text will switch from "loading" to the description
});
