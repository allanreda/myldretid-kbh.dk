// --- Google Analytics 4 dynamic loader ---
(function() {
  const host = window.location.hostname;
  const PROD_ID = "G-HBEYXDZWL0";   // Prod GA4 ID
  const DEV_ID = "G-9PXSDQWSS1";     // Dev GA4 ID 

  // Decide which Measurement ID to use
  const GA_ID = host.includes("dev") ? DEV_ID : PROD_ID;

  // Dynamically load the GA4 script
  const gtagScript = document.createElement("script");
  gtagScript.async = true;
  gtagScript.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  document.head.appendChild(gtagScript);

  // Initialize GA4
  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('js', new Date());
  gtag('config', GA_ID);
})();


let url;

if (window.location.hostname.includes("dev") || window.location.hostname === "localhost") {
  // Dev environment
  url = "https://storage.googleapis.com/myldretid-kbh-dev-predictions/predictions/json_predictions.json";
} else {
  // Prod environment
  url = "https://storage.googleapis.com/myldretid-kbh-prod-predictions/predictions/json_predictions.json";
}

const weekdays = {
    Monday: "Mandag", Tuesday: "Tirsdag", Wednesday: "Onsdag", Thursday: "Torsdag",
    Friday: "Fredag", Saturday: "Lørdag", Sunday: "Søndag"
  };
  
  const months = {
    January: "Januar", February: "Februar", March: "Marts", April: "April",
    May: "Maj", June: "Juni", July: "Juli", August: "August",
    September: "September", October: "Oktober", November: "November", December: "December"
  };
  
  function formatDateLabel(dateStr, period) {
    const date = new Date(dateStr);
    const day = weekdays[date.toLocaleString('en-US', { weekday: 'long' })];
    const label = period === 'morning' ? 'Morgen' : 'Eftermiddag';
    const icon = period === 'morning' ? '🌅' : '🌇';
  
    const dayNum = String(date.getDate()).padStart(2, '0');
    const monthNum = String(date.getMonth() + 1).padStart(2, '0');
  
    return `${icon} ${day}, ${dayNum}.${monthNum} ${label}`;
  }
  
  
  function getDescription(val) {
    if (val < -15) return "🚀 Meget hurtigere end normalt";
    if (val < -10) return "🚗 Hurtigere end normalt";
    if (val < -5) return "👍 En smule hurtigere end normalt";
    if (val < 5) return "👌 Omtrent som normalt";
    if (val < 10) return "⚠️ En smule langsommere end normalt";
    if (val < 15) return "🛑 Langsommere end normalt";
    return "🪦 Meget langsommere end normalt";
  }
  
  function getColor(val) {
    if (val < -15) return "#05f545";
    if (val < -10) return "#1abc9c";
    if (val < -5) return "#37c477";
    if (val < 5) return "#ffff00";
    if (val < 10) return "#f39c12";
    if (val < 15) return "#e67e22";
    return "#f70525";
  }
  
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
        bar: { color: color },
        bgcolor: "#f9f9f9",
        bordercolor: "#e0e0e0",
        borderwidth: 1,
        threshold: {
          line: { color: "#34495e", width: 2 },
          value: 0
        }
      }
    }];
  
    Plotly.newPlot(id, data, {
      paper_bgcolor: '#f0f6ff',
      plot_bgcolor: '#f0f6ff',
      margin: { t: 60, b: 0, l: 10, r: 10 }
    }, { responsive: true });
  }
  
  
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
  
      const mainGauges = combined.slice(0, 2);
      const secondaryGauges = combined.slice(2, 10);
  
      const heroText = getDescription(mainGauges[0].value);
      document.getElementById("hero-description").innerText = heroText;
  
      const mainDiv = document.getElementById("main-gauges");
      const secondDiv = document.getElementById("secondary-gauges");
  
      let idCounter = 0;
  
      for (const g of mainGauges.concat(secondaryGauges)) {
        const id = `gauge-${idCounter++}`;
        const el = document.createElement("div");
        el.id = id;
        el.className = "gauge";
        (mainGauges.includes(g) ? mainDiv : secondDiv).appendChild(el);
        createGauge(id, g.value, formatDateLabel(g.date, g.period), getDescription(g.value), getColor(g.value), mainGauges.includes(g) ? false : true);
      }
  
    } catch (err) {
      console.error("Failed to load data:", err);
      document.getElementById("hero-description").innerText = "Kunne ikke indlæse trafikdata 😞";
    }
  }
  
  main();