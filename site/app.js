"use strict";

(() => {
  const data = JSON.parse(document.getElementById("benchmark-data").textContent);
  const descriptions = {
    A: {
      kicker: "A / EXECUTED CODE REPAIRS",
      title: "From buggy source to passing checks.",
      description: "Models read the source and returned replacement code. The harness applied each repair and ran independent Python checks.",
      note: "Three isolated repairs per configuration, one attempt per task. Each configuration passed 160 behavior checks. Verification time is recorded separately.",
    },
    B: {
      kicker: "B / RANDOMIZED ACTUAL READS",
      title: "Unknown contents. Verified execution.",
      description: "Each trial used a randomly named file with an unknown synthetic token. Passing required exactly one successful read and the exact token in the final JSON.",
      note: "Ten fresh trials per configuration, with rotating model order. All profiles received the same file within each trial. Earlier read failures remain part of the evidence.",
    },
    C: {
      kicker: "C / LUNA MEDIUM VERSUS HIGH",
      title: "Less effort is not always less time.",
      description: "The original ten tasks, rerun with standardized context and alternating Luna effort levels. Flint was not included in this group.",
      note: "One attempt per task and effort level. Median times were nearly identical. Medium was slower in group B, so this does not establish a universal speed advantage.",
    },
  };
  let suite = "A";
  let metric = "total";
  const chart = document.getElementById("comparison-chart");
  const table = document.getElementById("results-table");
  const tabs = Array.from(document.querySelectorAll("[data-suite]"));
  const seconds = (value) => `${value.toFixed(2)}s`;
  const cost = (value) => (value === 0 ? "$0.000000" : `$${value.toFixed(6)}`);

  function render() {
    const rows = data.suites[suite];
    const description = descriptions[suite];
    document.getElementById("chart-kicker").textContent = description.kicker;
    document.getElementById("chart-title").textContent = description.title;
    document.getElementById("chart-description").textContent = description.description;
    document.getElementById("chart-note").textContent = `${description.note} Wall time includes startup, network, inference and tool turns. Bars start at zero and scale within this group.`;
    document.getElementById("suite-panel").setAttribute("aria-labelledby", `tab-${suite}`);
    const maximum = Math.max(...rows.map((row) => row[metric])) * 1.1;
    chart.replaceChildren();
    table.replaceChildren();
    const accessibleValues = [];

    for (const row of rows) {
      const bar = document.createElement("div");
      bar.className = "bar-row";
      const label = document.createElement("div");
      label.className = "bar-label";
      const dot = document.createElement("span");
      dot.className = `model-dot ${row.id}`;
      label.append(dot, document.createTextNode(row.label));
      const track = document.createElement("div");
      track.className = "bar-track";
      const fill = document.createElement("div");
      fill.className = `bar-fill ${row.id}`;
      fill.style.width = `${(row[metric] / maximum) * 100}%`;
      track.append(fill);
      const value = document.createElement("div");
      value.className = "bar-value";
      value.textContent = seconds(row[metric]);
      bar.append(label, track, value);
      chart.append(bar);
      accessibleValues.push(`${row.label}: ${seconds(row[metric])}`);

      const tr = document.createElement("tr");
      for (const [index, text] of [row.label, `${row.passed}/${row.runs}`, seconds(row.total), seconds(row.median), cost(row.cost)].entries()) {
        const td = document.createElement("td");
        if (index === 1) {
          const pill = document.createElement("span");
          pill.className = "pass-pill";
          pill.textContent = text;
          td.append(pill);
        } else {
          td.textContent = text;
        }
        tr.append(td);
      }
      table.append(tr);
    }
    const metricLabel = metric === "total" ? "total time" : "median time per call";
    chart.setAttribute("aria-label", `Group ${suite}, ${metricLabel}. ${accessibleValues.join(". ")}.`);
    const fastest = rows.reduce((best, row) => (row[metric] < best[metric] ? row : best));
    document.getElementById("metric-summary").textContent = `${fastest.label} had the lowest ${metricLabel} in this group (${seconds(fastest[metric])}). These are observed timings from a small sample.`;
    for (const tab of tabs) {
      const active = tab.dataset.suite === suite;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      tab.classList.toggle("active", active);
    }
    for (const button of document.querySelectorAll("[data-metric]")) {
      button.setAttribute("aria-pressed", String(button.dataset.metric === metric));
    }
  }

  for (const tab of tabs) {
    tab.addEventListener("click", () => { suite = tab.dataset.suite; render(); });
    tab.addEventListener("keydown", (event) => {
      let index = tabs.indexOf(tab);
      if (event.key === "ArrowRight") index = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") index = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") index = 0;
      else if (event.key === "End") index = tabs.length - 1;
      else return;
      event.preventDefault();
      tabs[index].click();
      tabs[index].focus();
    });
  }
  for (const button of document.querySelectorAll("[data-metric]")) {
    button.addEventListener("click", () => { metric = button.dataset.metric; render(); });
  }
  for (const [prefix, model] of [["luna", "openai/gpt-6-luna"], ["flint", "recursive/flint-v1.0:free"]]) {
    const observation = data.cross[model];
    document.getElementById(`history-${prefix}`).textContent = `${observation.passed}/${observation.runs}`;
    const dots = document.getElementById(`${prefix}-dots`);
    for (let index = 0; index < observation.runs; index++) {
      const dot = document.createElement("span");
      dot.className = `trial-dot${index >= observation.passed ? " missed" : ""}`;
      dots.append(dot);
    }
  }
  document.getElementById("copy-command").addEventListener("click", async () => {
    const status = document.getElementById("copy-status");
    try {
      await navigator.clipboard.writeText(document.getElementById("reproduce-command").textContent);
      status.textContent = "Command copied. Run it from the repository root.";
    } catch {
      status.textContent = "Select the command above and copy it manually.";
    }
  });
  render();
})();
