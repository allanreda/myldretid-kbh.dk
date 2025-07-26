const url = "https://storage.googleapis.com/myldretid-kbh-predictions-test/predictions/json_predictions.json";
// Weekday and month translations
const weekdays = {
    Monday: "Mandag", Tuesday: "Tirsdag", Wednesday: "Onsdag", Thursday: "Torsdag",
    Friday: "Fredag", Saturday: "Lørdag", Sunday: "Søndag"
  };
  
  const months = {
    January: "Januar", February: "Februar", March: "Marts", April: "April",
    May: "Maj", June: "Juni", July: "Juli", August: "August",
    September: "September", October: "Oktober", November: "November", December: "December"
  };
  
  // Format date into Danish label
  function formatDateLabel(dateStr, period) {
    const date = new Date(dateStr);
    const day = weekdays[date.toLocaleString('en-US', { weekday: 'long' })];
    const month = months[date.toLocaleString('en-US', { month: 'long' })];
    const label = period === 'morning' ? 'Morgen' : 'Eftermiddag';
    const icon = period === 'morning' ? '🌅' : '🌇';
    return `${icon} ${day}, ${date.getDate()}. ${month} ${date.getFullYear()} ${label}`;
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
    if (val < 5) return "#f4f4f4";
    if (val < 10) return "#f39c12";
    if (val < 15) return "#e67e22";
    return "#f70525";
  }
  
  function createGauge(id, val, label, description, color) {
    const data = [{
      type: "indicator",
      mode: "gauge+number",
      value: val,
      title: {
        text: `<b>${label}</b><br><span style="color:gray;font-size:14px">${description}</span>`,
        font: { size: 16 }
      },
      number: { suffix: "%", font: { size: 28, color: "#2c3e50" } },
      gauge: {
        axis: { range: [-30, 30], tickwidth: 1, tickcolor: "#888" },
        bar: { color: color },
        bgcolor: "#f9f9f9",
        bordercolor: "#e0e0e0",
        borderwidth: 1,
        threshold: {
          line: { color: "#34495e", width: 2 },
          thickness: 0.75,
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
  
      // Sort by date, morning first
      combined.sort((a, b) => {
        const da = new Date(a.date), db = new Date(b.date);
        if (da - db !== 0) return da - db;
        return a.period === 'morning' ? -1 : 1;
      });
  
      const mainGauges = combined.slice(0, 2);      // Highlight first 2
      const secondaryGauges = combined.slice(2, 10); // Next 8
  
      const mainDiv = document.getElementById("main-gauges");
      const secondDiv = document.getElementById("secondary-gauges");
  
      let idCounter = 0;
  
      for (const g of mainGauges) {
        const id = `gauge-${idCounter++}`;
        const el = document.createElement("div");
        el.id = id;
        el.className = "gauge";
        mainDiv.appendChild(el);
        createGauge(id, g.value, formatDateLabel(g.date, g.period), getDescription(g.value), getColor(g.value));
      }
  
      for (const g of secondaryGauges) {
        const id = `gauge-${idCounter++}`;
        const el = document.createElement("div");
        el.id = id;
        el.className = "gauge";
        secondDiv.appendChild(el);
        createGauge(id, g.value, formatDateLabel(g.date, g.period), getDescription(g.value), getColor(g.value));
      }
  
    } catch (err) {
      console.error("Failed to load prediction data:", err);
      document.body.innerHTML += `<p style="color:red;">Fejl ved indlæsning af trafikdata</p>`;
    }
  }
  
  main();