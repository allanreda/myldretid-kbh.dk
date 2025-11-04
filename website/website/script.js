// --- Google Analytics 4 dynamic loader ---
(function() {
  const host = window.location.hostname;
  const PROD_ID = "G-HBEYXDZWL0";
  const DEV_ID = "G-9PXSDQWSS1";
  const GA_ID = host.includes("dev") ? DEV_ID : PROD_ID;

  const s = document.createElement("script");
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('js', new Date());
  gtag('config', GA_ID);
})();

// --- Environment URL ---
let url;
if (window.location.hostname.includes("dev") || window.location.hostname === "localhost") {
  url = "https://storage.googleapis.com/myldretid-kbh-dev-predictions/predictions/json_predictions.json";
} else {
  url = "https://storage.googleapis.com/myldretid-kbh-prod-predictions/predictions/json_predictions.json";
}

// --- Helpers ---
const weekdays = {
  Monday: "Mandag", Tuesday: "Tirsdag", Wednesday: "Onsdag", Thursday: "Torsdag",
  Friday: "Fredag", Saturday: "Lørdag", Sunday: "Søndag"
};

function formatDateLabel(dateStr, period) {
  const date = new Date(dateStr);
  const day = weekdays[date.toLocaleString('en-US', { weekday: 'long' })];
  const dayNum = String(date.getDate()).padStart(2, '0');
  const monthNum = String(date.getMonth() + 1).padStart(2, '0');
  const label = period === 'morning' ? 'Morgen' : 'Eftermiddag';

  // Clean, professional label (no emoji)
  return `${day}, ${dayNum}.${monthNum} ${label}`;
}

function getDescription(val) {
  if (val < 15) return "🚀 Meget hurtigere end normalt";
  if (val < 10) return "🚗 Hurtigere end normalt";
  if (val < 5) return "👍 En smule hurtigere end normalt";
  if (val < -5) return "👌 Omtrent som normalt";
  if (val < -10) return "⚠️ En smule langsommere end normalt";
  if (val < -15) return "🛑 Langsommere end normalt";
  return "🪦 Meget langsommere end normalt";
}

function getColor(val) {
  if (val < 15) return "#05f545";
  if (val < 10) return "#1abc9c";
  if (val < 5) return "#37c477";
  if (val < -5) return "#ffff00";
  if (val < -10) return "#f39c12";
  if (val < -15) return "#e67e22";
  return "#f70525";
}

// --- Gauge Renderer ---
function createGauge(id, val, label, description, color, isSmall = false) {
  const container = document.getElementById(id);
  const width = container.offsetWidth;
  const isMobile = window.innerWidth <= 768;

  // Scale factor for everything (as before)
  const fontScale = Math.max(0.5, Math.min(1, width / (isSmall ? 280 : 400)));

  const titleSize = (isSmall ? 14 : 16) * fontScale;
  const descSize = (isSmall ? 11 : 13) * fontScale;
  const numberSize = (isSmall ? 26 : 32) * fontScale;

  // Tick labels around the gauge get a stronger shrink on mobile
  const tickFontSize = (isSmall ? 14 : 14) * fontScale * (isMobile ? 0.75 : 1);

  const data = [{
    type: "indicator",
    mode: "gauge+number",
    value: val,
    title: {
      text: `<b>${label}</b><br><span style="color:gray;font-size:${descSize}px">${description}</span>`,
      font: { size: titleSize }
    },
    number: { suffix: "%", font: { size: numberSize, color: "#2c3e50" } },
    gauge: {
      axis: { range: [-30, 30], tickwidth: 1, tickfont: { size: tickFontSize } },
      bar: { color: color },
      bgcolor: "#f9f9f9",
      bordercolor: "#e0e0e0",
      borderwidth: 1,
      threshold: { line: { color: "#34495e", width: 2 }, value: 0 }
    }
  }];

  const layout = {
    paper_bgcolor: '#f0f6ff',
    plot_bgcolor: '#f0f6ff',
    margin: { t: 50, b: 0, l: 10, r: 10 }
  };

  Plotly.newPlot(id, data, layout, { responsive: true, displayModeBar: false });
}

// --- Main ---
async function main() {
  try {
    const res = await fetch(`${url}?ts=${Date.now()}`);
    const data = await res.json();

    const combined = [
      ...Object.entries(data.morning_predictions).map(([d, v]) => ({ date: d, period: 'morning', value: v })),
      ...Object.entries(data.afternoon_predictions).map(([d, v]) => ({ date: d, period: 'afternoon', value: v }))
    ];

    combined.sort((a, b) => new Date(a.date) - new Date(b.date) || (a.period === 'morning' ? -1 : 1));

    const mainGauges = combined.slice(0, 2);
    const secondaryGauges = combined.slice(2, 10);

    document.getElementById("hero-description").innerText = getDescription(mainGauges[0].value);

    const mainDiv = document.getElementById("main-gauges");
    const secondDiv = document.getElementById("secondary-gauges");

    let idCounter = 0;
    for (const g of mainGauges.concat(secondaryGauges)) {
      const id = `gauge-${idCounter++}`;
      const el = document.createElement("div");
      el.id = id;
      el.className = "gauge";
      (mainGauges.includes(g) ? mainDiv : secondDiv).appendChild(el);
      createGauge(id, g.value, formatDateLabel(g.date, g.period), getDescription(g.value), getColor(g.value), !mainGauges.includes(g));
    }

    // Re-render gauges responsively on resize
    window.addEventListener('resize', () => {
      document.querySelectorAll('.gauge').forEach(div => Plotly.purge(div.id));

      let i = 0;
      for (const g of mainGauges.concat(secondaryGauges)) {
        const id = `gauge-${i++}`;
        createGauge(id, g.value, formatDateLabel(g.date, g.period), getDescription(g.value), getColor(g.value), !mainGauges.includes(g));
      }
    });

  } catch (err) {
    console.error("Failed to load data:", err);
    document.getElementById("hero-description").innerText = "Kunne ikke indlæse trafikdata 😞";
  }
}

main();
