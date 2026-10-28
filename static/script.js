(() => {
  // If opened with VS Code Live Server (port 5500), talk to FastAPI on port 8000.
  // If opened from FastAPI itself (http://127.0.0.1:8000), use same origin.
  const API = ["5500", "5501"].includes(location.port) ? "http://127.0.0.1:8000" : "";

  const form = document.getElementById("predictForm");
  const btn = document.getElementById("predictBtn");
  const errBox = document.getElementById("formError");
  const weekend = document.getElementById("weekend");
  const weekendText = document.getElementById("weekendText");

  const body = document.getElementById("resultBody");
  const card = document.querySelector(".result-card");
  const title = document.getElementById("resultTitle");
  const desc = document.getElementById("resultDesc");
  const probValue = document.getElementById("probValue");
  const barFill = document.getElementById("barFill");

  const INT_FIELDS = ["Administrative", "Informational", "ProductRelated",
    "OperatingSystems", "Browser", "Region", "TrafficType"];
  const FLOAT_FIELDS = ["Administrative_Duration", "Informational_Duration",
    "ProductRelated_Duration", "BounceRates", "PageValues", "SpecialDay"];

  const EXAMPLE = {
    Administrative: 5, Administrative_Duration: 120,
    Informational: 2, Informational_Duration: 45,
    ProductRelated: 50, ProductRelated_Duration: 1800,
    BounceRates: 0.002, PageValues: 25, SpecialDay: 0,
    OperatingSystems: 2, Browser: 2, Region: 1, TrafficType: 2,
    Month: "Nov", VisitorType: "Returning_Visitor", Weekend: true
  };

  function fillForm(data) {
    for (const [k, v] of Object.entries(data)) {
      const el = form.elements[k];
      if (!el) continue;
      if (el.type === "checkbox") el.checked = !!v; else el.value = v;
    }
    weekendText.textContent = weekend.checked ? "Yes" : "No";
  }

  document.getElementById("useExample").addEventListener("click", () => {
    fillForm(EXAMPLE);
    form.scrollIntoView({ behavior: "smooth", block: "center" });
  });
  weekend.addEventListener("change", () => {
    weekendText.textContent = weekend.checked ? "Yes" : "No";
  });

  function buildPayload() {
    const payload = {};
    const bad = [];
    form.querySelectorAll("input.invalid").forEach(i => i.classList.remove("invalid"));

    for (const name of [...INT_FIELDS, ...FLOAT_FIELDS]) {
      const el = form.elements[name];
      const raw = el.value.trim();
      const num = Number(raw);
      const min = el.min !== "" ? Number(el.min) : -Infinity;
      const max = el.max !== "" ? Number(el.max) : Infinity;
      const isInt = INT_FIELDS.includes(name);
      if (raw === "" || Number.isNaN(num) || num < min || num > max || (isInt && !Number.isInteger(num))) {
        el.classList.add("invalid");
        bad.push(name);
      } else {
        payload[name] = num;
      }
    }
    payload.Month = form.elements.Month.value;
    payload.VisitorType = form.elements.VisitorType.value;
    payload.Weekend = weekend.checked;
    return { payload, bad };
  }

  function showResult(r) {
    const pct = r.purchase_probability * 100;
    const yes = r.prediction === 1;
    card.classList.toggle("is-no", !yes);
    title.textContent = yes ? "Purchase" : "No Purchase";
    desc.textContent = yes
      ? "The model predicts this shopper will make a purchase."
      : "The model predicts this shopper will not make a purchase.";
    probValue.textContent = pct.toFixed(2) + "%";
    barFill.style.width = pct + "%";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errBox.hidden = true;

    const { payload, bad } = buildPayload();
    if (bad.length) {
      errBox.textContent = "Please check these fields: " + bad.join(", ");
      errBox.hidden = false;
      return;
    }

    btn.disabled = true;
    btn.querySelector("span").textContent = "Predicting…";
    try {
      const res = await fetch(API + "/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        const d = data.detail;
        throw new Error(typeof d === "string" ? d : JSON.stringify(d));
      }
      showResult(data);
    } catch (err) {
      errBox.textContent = "Prediction failed: " + err.message;
      errBox.hidden = false;
    } finally {
      btn.disabled = false;
      btn.querySelector("span").textContent = "Predict Purchase";
    }
  });

  async function checkHealth() {
    const dot = document.getElementById("apiDot");
    const text = document.getElementById("apiText");
    try {
      const res = await fetch(API + "/health");
      const ok = res.ok && (await res.json()).status === "healthy";
      dot.className = "dot " + (ok ? "ok" : "bad");
      text.textContent = ok ? "FastAPI" : "API Error";
    } catch {
      dot.className = "dot bad";
      text.textContent = "Offline";
    }
  }
  checkHealth();
  setInterval(checkHealth, 30000);

  const links = document.querySelectorAll(".nav-link[data-target]");
  links.forEach(l => l.addEventListener("click", () => {
    links.forEach(x => x.classList.remove("active"));
    l.classList.add("active");
  }));
})();