let url;

if (window.location.hostname.includes("dev")) {
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
  
  // === Language translations ===
  const translations = {
    da: {
      title: "Myldretid i København",
      tagline: "ML-baserede trafikprognoser for myldretiden i København - opdateres kl. 10 og 18 hver dag.",
      heroSummary: "Næste myldretid:",
      loading: "Indlæser prognoser...",
      aboutTitle: "ℹ️ Om denne service",
      aboutText: "Denne side viser <strong>trafikprognoser for myldretiden i København</strong>. ML-modellen beregner <em>procentvis afvigelse i rejsetid</em> i forhold til det gennemsnitlige niveau, så du hurtigt kan vurdere, om trafikken bliver hurtigere eller langsommere end normalt.",
      howItWorksTitle: "Sådan virker det",
      howItWorksList: `
        <li><strong>Dataindsamling (dagligt):</strong> Der indsamles data dagligt fra 20 forskellige knudepunkter i København.</li>
        <li><strong>Modeltræning (søndag):</strong> Machine learning-modellen gentrænes på det nyeste indsamlede data for at holde den relevant.</li>
        <li><strong>Prognoser (dagligt kl. 10 & 18):</strong> To gange dagligt benyttes ML-modellen til at forudsige det samlede trafikniveau for de næste 5 dage (10 myldretider).</li>
      `,
      sourcesTitle: "Datakilder",
      sourcesText: "Modellen bygger bl.a. på data fra <strong>TomTom</strong>, <strong>OpenWeather</strong> samt information fra <strong>Københavns Kommune</strong>.",
      colorsTitle: "Farver og tolkning",
      colorsList: `
        <li><strong>Grøn:</strong> Hurtigere end normalt (negativ afvigelse).</li>
        <li><strong>Gul:</strong> Omtrent normalt niveau.</li>
        <li><strong>Rød:</strong> Langsommere end normalt (positiv afvigelse).</li>
      `,
      limitationsTitle: "Begrænsninger",
      limitationsText: "Prognoser er <em>vejledende</em> og kan afvige fra virkeligheden ved uforudsete hændelser såsom uheld, vejarbejde og events. Benyt servicen som en vejledning og husk, at disse prognoser blot er estimater.",
      footer: "© 2025 myldretid-kbh · Udviklet af Allan Fattah Reda"
    },
  
    en: {
      title: "Rush Hour in Copenhagen",
      tagline: "ML-based traffic forecasts for Copenhagen’s rush hour – updated daily at 10 AM and 6 PM.",
      heroSummary: "Next rush hour:",
      loading: "Loading forecasts...",
      aboutTitle: "ℹ️ About this service",
      aboutText: "This page shows <strong>traffic forecasts for Copenhagen’s rush hour</strong>. The ML model calculates the <em>percentage deviation in travel time</em> compared to the average level, so you can quickly see whether traffic will be faster or slower than usual.",
      howItWorksTitle: "How it works",
      howItWorksList: `
        <li><strong>Data collection (daily):</strong> Data is collected daily from 20 key locations across Copenhagen.</li>
        <li><strong>Model training (Sunday):</strong> The machine learning model is retrained weekly on the latest data to stay relevant.</li>
        <li><strong>Forecasts (daily at 10 AM & 6 PM):</strong> Twice daily, the model predicts overall traffic levels for the next 5 days (10 rush hours).</li>
      `,
      sourcesTitle: "Data sources",
      sourcesText: "The model uses data from <strong>TomTom</strong>, <strong>OpenWeather</strong>, and <strong>Copenhagen Municipality</strong>.",
      colorsTitle: "Colors and interpretation",
      colorsList: `
        <li><strong>Green:</strong> Faster than usual (negative deviation).</li>
        <li><strong>Yellow:</strong> Around normal levels.</li>
        <li><strong>Red:</strong> Slower than usual (positive deviation).</li>
      `,
      limitationsTitle: "Limitations",
      limitationsText: "Forecasts are <em>indicative</em> and may differ from real conditions due to accidents, roadworks, or events. Use them as guidance, keeping in mind that these are estimates.",
      footer: "© 2025 myldretid-kbh · Developed by Allan Fattah Reda"
    }
  };
  

  // === Language switcher ===
  function setLanguage(lang) {
    localStorage.setItem("lang", lang);
    const t = translations[lang];
  
    document.getElementById("title").innerText = t.title;
    document.getElementById("tagline").innerText = t.tagline;
    document.getElementById("hero-summary").innerText = t.heroSummary;
    document.getElementById("hero-description").innerText = t.loading;
    document.getElementById("footer-text").innerText = t.footer;
  
    // Info section
    document.getElementById("about-title").innerHTML = t.aboutTitle;
    document.getElementById("about-text").innerHTML = t.aboutText;
    document.getElementById("how-it-works-title").innerHTML = t.howItWorksTitle;
    document.getElementById("how-it-works-list").innerHTML = t.howItWorksList;
    document.getElementById("sources-title").innerHTML = t.sourcesTitle;
    document.getElementById("sources-text").innerHTML = t.sourcesText;
    document.getElementById("colors-title").innerHTML = t.colorsTitle;
    document.getElementById("colors-list").innerHTML = t.colorsList;
    document.getElementById("limitations-title").innerHTML = t.limitationsTitle;
    document.getElementById("limitations-text").innerHTML = t.limitationsText;
  
    document.documentElement.lang = lang;
  }
  

  document.addEventListener("DOMContentLoaded", () => {
    const savedLang = localStorage.getItem("lang") || "da";
    setLanguage(savedLang);
  });

  main();