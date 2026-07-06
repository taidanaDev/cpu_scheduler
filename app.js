//   CPU Scheduler 98 — app.js

const ALGO_LABELS = {
  fcfs: "FCFS", sjf: "SJF", srtf: "SRTF",
  priority_npp: "Priority (NPP)", priority_pp: "Priority (PP)", round_robin: "Round Robin",
};

let pyodide = null;
let currentResult = null;   // { timeline, log, metrics, averages }
let currentProcesses = [];
let pidColors = {};


// 1. Window manager: open/close, drag, minimize, maximize, dynamic taskbar

const WINDOW_TITLES = {
  "win-input": "Process Input",
  "win-gantt": "Gantt Chart",
  "win-monitor": "System Monitor",
  "win-log": "Decision Log",
  "win-results": "Results",
  "win-compare": "Compare Algorithms",
};

const WINDOW_ICONS = {
  "win-input": "assets/directory_admin_tools-4.png",
  "win-gantt": "assets/cd_drive-3.png",
  "win-monitor": "assets/directory_network_conn-4.png",
  "win-log": "assets/notepad-5.png",
  "win-results": "assets/directory_closed_cool-3.png",
  "win-compare": "assets/directory_folder_options-4.png",
};

const ALL_WINDOW_IDS = Object.keys(WINDOW_TITLES);

const ORGANIZED_LAYOUT = {
  "win-input":   { top: 18,  left: 110, width: 430 },
  "win-log":     { top: 18,  left: 560, width: 560 },
  "win-results": { top: 18,  left: 1140, width: 330 },

  "win-gantt":   { top: 235, left: 560, width: 560 },
  "win-monitor": { top: 455, left: 110, width: 430 },
  "win-compare": { top: 455, left: 560, width: 560 },
};

function setWindowRect(id, rect) {
  const win = document.getElementById(id);
  if (!win || !rect) return;

  win.classList.remove("win-maxed");

  win.style.top = rect.top + "px";
  win.style.left = rect.left + "px";
  win.style.width = rect.width + "px";
  win.style.height = "";
}

function openWindow(id, organized = false) {
  const win = document.getElementById(id);
  if (!win) return;

  if (organized && ORGANIZED_LAYOUT[id]) {
    setWindowRect(id, ORGANIZED_LAYOUT[id]);
  }

  win.classList.remove("closed", "minimized");
  bringToFront(win);
  refreshTaskbar();
}

function openAllWindowsOrganized() {
  ALL_WINDOW_IDS.forEach((id) => {
    setWindowRect(id, ORGANIZED_LAYOUT[id]);
    openWindow(id);
  });
}

function closeWindow(id) {
  const win = document.getElementById(id);
  if (!win) return;

  // This hides the window only. It does not delete or reset your data.
  win.classList.add("closed");
  win.classList.remove("minimized", "win-maxed");

  refreshTaskbar();
}

function minimizeWindow(id) {
  const win = document.getElementById(id);
  if (!win) return;

  // Real Windows 98 style: whole window disappears,
  // then user restores it from the taskbar.
  win.classList.add("minimized");
  refreshTaskbar();
}

function refreshTaskbar() {
  const container = document.getElementById("taskbar-items");
  if (!container) return;

  container.innerHTML = "";

  ALL_WINDOW_IDS.forEach((id) => {
    const win = document.getElementById(id);
    if (!win || win.classList.contains("closed")) return;

    const item = document.createElement("div");
    item.className = "taskbar-item";

    if (!win.classList.contains("minimized")) {
      item.classList.add("active");
    }

    item.dataset.win = id;

    item.innerHTML = `
      <img src="${WINDOW_ICONS[id]}" class="taskbar-icon" alt="">
      <span>${WINDOW_TITLES[id]}</span>
    `;

    item.addEventListener("click", () => {
      win.classList.remove("minimized");
      bringToFront(win);
      refreshTaskbar();
    });

    container.appendChild(item);
  });
}

function initWindowManager() {
  document.querySelectorAll(".win").forEach((win) => {
    const titlebar = win.querySelector(".titlebar");
    let offsetX = 0;
    let offsetY = 0;
    let dragging = false;

    if (titlebar) {
      titlebar.addEventListener("mousedown", (e) => {
        if (e.target.classList.contains("tb-btn")) return;

        dragging = true;
        offsetX = e.clientX - win.offsetLeft;
        offsetY = e.clientY - win.offsetTop;
        bringToFront(win);
      });
    }

    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;

      const desktop = document.getElementById("desktop");
      const maxLeft = desktop.clientWidth - 80;
      const maxTop = desktop.clientHeight - 30;

      win.style.left = Math.min(Math.max(0, e.clientX - offsetX), maxLeft) + "px";
      win.style.top = Math.min(Math.max(0, e.clientY - offsetY), maxTop) + "px";
    });

    document.addEventListener("mouseup", () => {
      dragging = false;
    });

    win.addEventListener("mousedown", () => {
      bringToFront(win);
    });

    win.querySelectorAll(".tb-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();

        const action = btn.dataset.action;

        if (action === "min") {
          minimizeWindow(win.id);
        }

        if (action === "max") {
          if (!win.classList.contains("win-maxed")) {
            win.dataset.prevTop = win.style.top;
            win.dataset.prevLeft = win.style.left;
            win.dataset.prevWidth = win.style.width;
            win.dataset.prevHeight = win.style.height;

            win.classList.add("win-maxed");
            win.style.top = "8px";
            win.style.left = "8px";
            win.style.width = "calc(100vw - 16px)";
            win.style.height = "calc(100vh - var(--taskbar-h) - 16px)";
          } else {
            win.classList.remove("win-maxed");
            win.style.top = win.dataset.prevTop || "";
            win.style.left = win.dataset.prevLeft || "";
            win.style.width = win.dataset.prevWidth || "";
            win.style.height = win.dataset.prevHeight || "";
          }

          bringToFront(win);
        }

        if (action === "close") {
          closeWindow(win.id);
        }
      });
    });
  });

  // Desktop icons: one click opens the assigned window.
  document.querySelectorAll(".desktop-icon").forEach((icon) => {
    icon.addEventListener("click", (e) => {
      e.stopPropagation();

      document.querySelectorAll(".desktop-icon").forEach((i) => {
        i.classList.remove("selected");
      });

      icon.classList.add("selected");

      const target = icon.dataset.open;

      if (target === "all") {
        openAllWindowsOrganized();
      } else {
        openWindow(target, true);
      }
    });
  });

  document.getElementById("desktop").addEventListener("click", (e) => {
    if (e.target.id === "desktop") {
      document.querySelectorAll(".desktop-icon").forEach((i) => {
        i.classList.remove("selected");
      });
    }
  });

  // Important: desktop starts with icons only.
  ALL_WINDOW_IDS.forEach((id) => {
    const win = document.getElementById(id);
    if (win) win.classList.add("closed");
  });

  refreshTaskbar();
}

let zTop = 10;
function bringToFront(win) {
  zTop += 1;
  win.style.zIndex = zTop;
}

function tickClock() {
  const el = document.getElementById("clock");
  const now = new Date();
  el.textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
setInterval(tickClock, 1000);


// 2. Process table (editable input UI)

let rowCounter = 0;

function addProcessRow(arrival = 0, burst = 1, priority = 1) {
  rowCounter += 1;
  const pid = "P" + rowCounter;
  const tbody = document.getElementById("process-tbody");
  const tr = document.createElement("tr");
  tr.dataset.pid = pid;
  tr.innerHTML = `
    <td>${pid}</td>
    <td><input type="number" min="0" value="${arrival}" class="in-arrival"></td>
    <td><input type="number" min="1" value="${burst}" class="in-burst"></td>
    <td class="prio-col"><input type="number" min="1" value="${priority}" class="in-priority"></td>
    <td class="del-row" title="Delete">✕</td>
  `;
  tr.querySelector(".del-row").addEventListener("click", () => tr.remove());
  tbody.appendChild(tr);
}

function readProcessesFromTable() {
  const rows = document.querySelectorAll("#process-tbody tr");
  const procs = [];
  rows.forEach((tr) => {
    procs.push({
      pid: tr.dataset.pid,
      arrival: parseInt(tr.querySelector(".in-arrival").value || "0", 10),
      burst: Math.max(1, parseInt(tr.querySelector(".in-burst").value || "1", 10)),
      priority: parseInt(tr.querySelector(".in-priority").value || "1", 10),
    });
  });
  return procs;
}

function assignColors(processes) {
  const palette = ["#c00000", "#0050c0", "#008000", "#c08000", "#8000c0", "#00808c", "#c04080", "#606060"];
  processes.forEach((p, i) => {
    if (!pidColors[p.pid]) pidColors[p.pid] = palette[i % palette.length];
  });
}

document.getElementById("btn-add-row").addEventListener("click", () => addProcessRow(0, 1, 1));
document.getElementById("btn-random").addEventListener("click", () => {
  document.getElementById("process-tbody").innerHTML = "";
  rowCounter = 0;
  const n = 4 + Math.floor(Math.random() * 2); // 4-5 processes
  let t = 0;
  for (let i = 0; i < n; i++) {
    t += Math.floor(Math.random() * 3);
    addProcessRow(t, 1 + Math.floor(Math.random() * 8), 1 + Math.floor(Math.random() * 5));
  }
});

document.querySelectorAll('input[name="algo"]').forEach((r) => {
  r.addEventListener("change", () => {
    const algo = document.querySelector('input[name="algo"]:checked').value;

    document.getElementById("quantum-row").style.display =
      algo === "round_robin" ? "block" : "none";

    document.getElementById("priority-convention-row").style.display =
      algo.startsWith("priority") ? "block" : "none";

    document.querySelectorAll(".prio-col").forEach((el) => {
      el.style.opacity = algo.startsWith("priority") ? "1" : "0.4";
    });
  });
});


// 3. Pyodide bootstrap
async function initPyodide() {
  pyodide = await loadPyodide();
  const resp = await fetch("schedulers.py?v=" + Date.now());
  const src = await resp.text();
  pyodide.FS.writeFile("schedulers.py", src);
  await pyodide.runPythonAsync(`
import json
import schedulers

def run_scheduler_json(algorithm, processes_json, quantum, priority_convention):
    processes = json.loads(processes_json)
    result = schedulers.run_scheduler(
        algorithm,
        processes,
        quantum=quantum,
        priority_convention=priority_convention
    )
    return json.dumps(result)

def run_all_json(processes_json, quantum, priority_convention):
    processes = json.loads(processes_json)
    result = schedulers.run_all(
        processes,
        quantum=quantum,
        priority_convention=priority_convention
    )
    return json.dumps(result)
`);
  document.getElementById("loading-screen").style.display = "none";
}

function runSchedulerPy(algorithm, processes, quantum, priorityConvention) {
  const fn = pyodide.globals.get("run_scheduler_json");
  const jsonStr = fn(algorithm, JSON.stringify(processes), quantum, priorityConvention);
  return JSON.parse(jsonStr);
}

function runAllPy(processes, quantum, priorityConvention) {
  const fn = pyodide.globals.get("run_all_json");
  const jsonStr = fn(JSON.stringify(processes), quantum, priorityConvention);
  return JSON.parse(jsonStr);
}


// 4. RUN button: execute scheduler, reset animation state

document.getElementById("btn-run").addEventListener("click", () => {
  const processes = readProcessesFromTable();
  if (processes.length === 0) {
    alert("Add at least one process first.");
    return;
  }
  const algo = document.querySelector('input[name="algo"]:checked').value;
  const quantum = parseInt(document.getElementById("quantum-input").value || "2", 10);
  const priorityConvention = document.querySelector('input[name="priorityConvention"]:checked').value;

  assignColors(processes);
  currentProcesses = processes;

  try {
    currentResult = runSchedulerPy(algo, processes, quantum, priorityConvention);
  } catch (err) {
    alert("Error running scheduler: " + err);
    console.error(err);
    return;
  }

  renderResultsTable(currentResult, processes);
  setupGanttAnimation(currentResult);
  resetMonitorAndLog();

  ["win-gantt", "win-monitor", "win-log", "win-results"].forEach((id) => openWindow(id));
});


// 5. Gantt chart drawing + animation (canvas)

const gantt = {
  timeline: [],
  totalTime: 0,
  playhead: 0,      // current time unit revealed
  playing: false,
  timer: null,
};

function setupGanttAnimation(result) {
  gantt.timeline = result.timeline;
  gantt.totalTime = result.timeline.length ? result.timeline[result.timeline.length - 1].end : 0;
  gantt.playhead = 0;
  gantt.playing = false;
  clearInterval(gantt.timer);
  drawGantt(0);
}

function pxPerUnit() {
  const canvas = document.getElementById("gantt-canvas");
  const usable = Math.max(canvas.width - 40, 200);
  return gantt.totalTime > 0 ? usable / gantt.totalTime : 20;
}

function drawGantt(uptoTime) {
  const canvas = document.getElementById("gantt-canvas");
  const startX = 10;

  // Resize canvas BEFORE drawing (setting canvas.width clears its contents).
  const minWidth = 900;
  const desiredWidth = gantt.totalTime > 0 ? startX + gantt.totalTime * 24 + 30 : minWidth;
  canvas.width = Math.max(minWidth, desiredWidth);

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const scale = pxPerUnit();
  const barY = 20, barH = 40;

  gantt.timeline.forEach((slice) => {
    const sliceStart = Math.min(slice.start, uptoTime);
    const sliceEnd = Math.min(slice.end, uptoTime);
    if (sliceEnd <= sliceStart) return;

    const x = startX + sliceStart * scale;
    const w = (sliceEnd - sliceStart) * scale;
    ctx.fillStyle = slice.pid === "IDLE" ? "#d8d8d8" : pidColors[slice.pid] || "#999";
    ctx.fillRect(x, barY, w, barH);
    ctx.strokeStyle = "#000";
    ctx.strokeRect(x, barY, w, barH);

    if (w > 18) {
      ctx.fillStyle = slice.pid === "IDLE" ? "#555" : "#fff";
      ctx.font = "bold 11px Tahoma";
      ctx.textAlign = "center";
      ctx.fillText(slice.pid, x + w / 2, barY + barH / 2 + 4);
    }
  });

  // time ruler
  ctx.strokeStyle = "#000";
  ctx.fillStyle = "#000";
  ctx.font = "9px Tahoma";
  ctx.textAlign = "center";
  for (let t = 0; t <= gantt.totalTime; t++) {
    const x = startX + t * scale;
    ctx.beginPath();
    ctx.moveTo(x, barY + barH);
    ctx.lineTo(x, barY + barH + 5);
    ctx.stroke();
    if (scale > 14 || t % Math.ceil(10 / scale) === 0) {
      ctx.fillText(t, x, barY + barH + 16);
    }
  }
}

function stepGantt(delta) {
  gantt.playhead = Math.min(gantt.totalTime, Math.max(0, gantt.playhead + delta));
  drawGantt(gantt.playhead);
  updateMonitorAndLogAt(gantt.playhead);
}

document.getElementById("btn-play").addEventListener("click", () => {
  if (gantt.playing || gantt.totalTime === 0) return;
  gantt.playing = true;
  const speed = () => 700 / parseInt(document.getElementById("speed-slider").value, 10);
  const tick = () => {
    if (!gantt.playing) return;
    if (gantt.playhead >= gantt.totalTime) {
      gantt.playing = false;
      clearInterval(gantt.timer);
      return;
    }
    stepGantt(1);
    clearInterval(gantt.timer);
    gantt.timer = setInterval(tick, speed());
  };
  gantt.timer = setInterval(tick, speed());
});
document.getElementById("btn-pause").addEventListener("click", () => {
  gantt.playing = false;
  clearInterval(gantt.timer);
});
document.getElementById("btn-step-fwd").addEventListener("click", () => { gantt.playing = false; clearInterval(gantt.timer); stepGantt(1); });
document.getElementById("btn-step-back").addEventListener("click", () => { gantt.playing = false; clearInterval(gantt.timer); stepGantt(-1); });


// 6. System monitor (ready/running/completed) + decision log, synced to playhead

function resetMonitorAndLog() {
  document.getElementById("box-ready").innerHTML = "";
  document.getElementById("box-running").innerHTML = "";
  document.getElementById("box-completed").innerHTML = "";
  document.getElementById("log-body").textContent = "";
  updateMonitorAndLogAt(0);
}

function chipHtml(pid) {
  const color = pidColors[pid] || "#888";
  return `<span class="chip" style="background:${color}">${pid}</span>`;
}

function updateMonitorAndLogAt(time) {
  if (!currentResult) return;

  const running = [];
  const completed = [];
  currentResult.timeline.forEach((s) => {
    if (s.pid === "IDLE") return;
    if (s.end <= time) completed.push(s.pid);
    else if (s.start <= time && time < s.end) running.push(s.pid);
  });
  const uniqueCompleted = [...new Set(completed)].filter((pid) => {
    // only truly done if this pid has no later slice still pending
    const lastSlice = [...currentResult.timeline].reverse().find((s) => s.pid === pid);
    return lastSlice.end <= time;
  });
  const runningNow = [...new Set(running)];
  const arrivedNotDone = currentProcesses
    .filter((p) => p.arrival <= time)
    .map((p) => p.pid)
    .filter((pid) => !uniqueCompleted.includes(pid) && !runningNow.includes(pid));

  document.getElementById("box-ready").innerHTML = arrivedNotDone.map(chipHtml).join("") || '<span class="hint">empty</span>';
  document.getElementById("box-running").innerHTML = runningNow.map(chipHtml).join("") || '<span class="hint">idle</span>';
  document.getElementById("box-completed").innerHTML = uniqueCompleted.map(chipHtml).join("") || '<span class="hint">none yet</span>';

  const logBody = document.getElementById("log-body");
  const visible = currentResult.log.filter((entry) => entry.time <= time);
  logBody.textContent = visible.map((e) => `[t=${e.time}] ${e.message}`).join("\n");
  logBody.scrollTop = logBody.scrollHeight;
}


// 7. Results table

function renderResultsTable(result, processes) {
  const tbody = document.getElementById("results-tbody");
  tbody.innerHTML = "";
  processes.forEach((p) => {
    const m = result.metrics[p.pid];
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.pid}</td>
      <td>${m.arrival}</td>
      <td>${m.burst}</td>
      <td>${m.start}</td>
      <td>${m.end}</td>
      <td>${m.waiting}</td>
      <td>${m.turnaround}</td>
    `;
    tbody.appendChild(tr);
  });
  const a = result.averages;
  document.getElementById("results-summary").innerHTML = `
    Avg Waiting Time: <b>${a.waiting} ms</b> &nbsp;|&nbsp;
    Avg Turnaround Time: <b>${a.turnaround} ms</b>
  `;
}


// 8. Compare Algorithms mode

document.getElementById("btn-compare-all").addEventListener("click", () => {
  const processes = readProcessesFromTable();
  if (processes.length === 0) {
    alert("Add at least one process first.");
    return;
  }
  assignColors(processes);
  const quantum = parseInt(document.getElementById("quantum-input").value || "2", 10);
  const priorityConvention = document.querySelector('input[name="priorityConvention"]:checked').value;
  const all = runAllPy(processes, quantum, priorityConvention);
  drawCompareChart(all);
  openWindow("win-compare");
});

function drawCompareChart(allResults) {
  const canvas = document.getElementById("compare-canvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const names = Object.keys(allResults);
  const waits = names.map((n) => allResults[n].averages.waiting);
  const turns = names.map((n) => allResults[n].averages.turnaround);
  const maxVal = Math.max(...waits, ...turns, 1);

  const chartLeft = 50, chartBottom = 190, chartTop = 15, chartRight = canvas.width - 15;
  const groupWidth = (chartRight - chartLeft) / names.length;
  const barW = groupWidth / 3;

  // axes
  ctx.strokeStyle = "#000";
  ctx.beginPath();
  ctx.moveTo(chartLeft, chartTop);
  ctx.lineTo(chartLeft, chartBottom);
  ctx.lineTo(chartRight, chartBottom);
  ctx.stroke();

  names.forEach((name, i) => {
    const gx = chartLeft + i * groupWidth;
    const waitH = (waits[i] / maxVal) * (chartBottom - chartTop);
    const turnH = (turns[i] / maxVal) * (chartBottom - chartTop);

    ctx.fillStyle = "#0050c0";
    ctx.fillRect(gx + 5, chartBottom - waitH, barW, waitH);

    ctx.fillStyle = "#c00000";
    ctx.fillRect(gx + 5 + barW, chartBottom - turnH, barW, turnH);

    // value labels above bars
    ctx.fillStyle = "#000";
    ctx.font = "bold 10px Tahoma";
    ctx.textAlign = "center";

    ctx.fillText(
      waits[i],
      gx + 5 + barW / 2,
      chartBottom - waitH - 4
    );

    ctx.fillText(
      turns[i],
      gx + 5 + barW + barW / 2,
      chartBottom - turnH - 4
    );

    // algorithm label below chart
    ctx.font = "10px Tahoma";
    ctx.fillText(ALGO_LABELS[name], gx + groupWidth / 2, chartBottom + 14);
  });

  // legend
  ctx.fillStyle = "#0050c0";
  ctx.fillRect(chartLeft, chartTop - 5, 10, 10);
  ctx.fillStyle = "#000";
  ctx.fillText("Avg Wait", chartLeft + 45, chartTop + 4);
  ctx.fillStyle = "#c00000";
  ctx.fillRect(chartLeft + 100, chartTop - 5, 10, 10);
  ctx.fillStyle = "#000";
  ctx.fillText("Avg Turnaround", chartLeft + 160, chartTop + 4);
}


// 9. Boot

window.addEventListener("DOMContentLoaded", () => {
  initWindowManager();
  tickClock();
  addProcessRow(0, 5, 3);
  addProcessRow(1, 3, 1);
  addProcessRow(2, 8, 4);
  addProcessRow(3, 6, 2);
  document.getElementById("priority-convention-row").style.display = "none";
  initPyodide();
});