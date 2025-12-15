const API_BASE = "";

let gameActive = false;
let gameOver = false;
let activeEvent = null;
let lastEventType = null;

const rowsInput = document.getElementById("rows");
const colsInput = document.getElementById("cols");
const minesInput = document.getElementById("mines");
const boardEl = document.getElementById("board");
const statusTextEl = document.getElementById("status-text");
const sizeLabelEl = document.getElementById("size-label");
const minesLabelEl = document.getElementById("mines-label");
const safeLeftLabelEl = document.getElementById("safe-left-label");
const errorEl = document.getElementById("error");
const eventNameEl = document.getElementById("event-name");
const eventMessageEl = document.getElementById("event-message");
const santaGifEl = document.getElementById("santa-gif");

const romanMap = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"];

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.style.display = "block";
  setTimeout(() => {
    errorEl.style.display = "none";
  }, 2500);
}

function updateStatus(data) {
  sizeLabelEl.textContent = data ? `${data.rows} x ${data.cols}` : "—";
  minesLabelEl.textContent = data ? data.mines : "—";
  safeLeftLabelEl.textContent =
    data && typeof data.safe_cells_left === "number"
      ? data.safe_cells_left
      : "—";

  if (!data || !gameActive) {
    statusTextEl.textContent = "Игра не запущена.";
    return;
  }

  if (data.game_over && data.won) {
    statusTextEl.textContent = "Победа!";
  } else if (data.game_over) {
    statusTextEl.textContent = "Проигрыш (нажата мина).";
  } else {
    statusTextEl.textContent = "Игра идёт.";
  }
}

function applyEventVisuals(data) {
  activeEvent = data ? data.active_event : null;

  if (activeEvent) {
    eventNameEl.textContent = activeEvent.message || activeEvent.type;
    eventMessageEl.textContent = "";
  } else {
    eventNameEl.textContent = "—";
    eventMessageEl.textContent = "";
  }

  const isFlip = activeEvent && activeEvent.type === "flip_board";
  const isMirror = activeEvent && activeEvent.type === "mirror_board";
  boardEl.classList.toggle("flip", isFlip);
  boardEl.classList.toggle("mirror", isMirror);

  if (activeEvent && activeEvent.type === "ded_gif") {
    santaGifEl.src =
      (activeEvent.payload && activeEvent.payload.gif_url) ||
      "/static/Ded.gif";
    santaGifEl.style.display = "block";
  } else {
    santaGifEl.style.display = "none";
  }

  if (activeEvent && activeEvent.type === "rickroll") {
    if (lastEventType !== "rickroll") {
      const url =
        (activeEvent.payload && activeEvent.payload.url) ||
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
      window.open(url, "_blank");
    }
  }

  lastEventType = activeEvent ? activeEvent.type : null;
}

function renderBoard(data) {
  if (!data) {
    boardEl.innerHTML = "";
    boardEl.style.gridTemplateColumns = "repeat(1, 1fr)";
    return;
  }

  boardEl.style.gridTemplateColumns = `repeat(${data.cols}, 32px)`;
  boardEl.innerHTML = "";

  data.board.forEach((row, r) => {
    row.forEach((cell, c) => {
      const div = document.createElement("div");
      div.className = "cell";
      div.dataset.row = r;
      div.dataset.col = c;

      if (!gameActive || data.game_over) {
        div.classList.add("disabled");
      }

      if (cell.is_revealed) {
        div.classList.add("revealed");
        if (cell.is_mine) {
          div.classList.add("mine");
          div.textContent = "X";
        } else if (cell.adjacent_mines > 0) {
          const value =
            activeEvent && activeEvent.type === "roman_numbers"
              ? romanMap[cell.adjacent_mines] || cell.adjacent_mines
              : cell.adjacent_mines;
          div.textContent = value;
        } else {
          div.textContent = "";
        }
      } else if (cell.is_flagged) {
        div.classList.add("flag");
        div.textContent = "F";
      }

      boardEl.appendChild(div);
    });
  });
}

async function newGame() {
  const rows = parseInt(rowsInput.value, 10);
  const cols = parseInt(colsInput.value, 10);
  const mines = parseInt(minesInput.value, 10);

  if (isNaN(rows) || isNaN(cols) || isNaN(mines) || rows < 2 || cols < 2) {
    showError("Минимальный размер поля — 2x2.");
    return;
  }

  const maxCells = rows * cols;
  if (mines < 1 || mines >= maxCells) {
    showError(`Мины должны быть от 1 до ${maxCells - 1}.`);
    return;
  }

  try {
    const res = await fetch(API_BASE + "/new-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rows, cols, mines }),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.detail || "Ошибка при создании игры.");
      return;
    }

    gameActive = true;
    gameOver = false;
    renderBoard(data);
    updateStatus(data);
    applyEventVisuals(data);
  } catch (e) {
    console.error(e);
    showError("Бэкенд недоступен.");
  }
}

async function clickCell(row, col, rightClick = false) {
  if (!gameActive || gameOver) return;

  try {
    const res = await fetch(API_BASE + "/click", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row, col, right_click: rightClick }),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.detail || "Ошибка хода.");
      return;
    }
    renderBoard(data);
    updateStatus(data);
    applyEventVisuals(data);

    if (data.game_over) {
      gameOver = true;
      gameActive = false;
    }
  } catch (e) {
    console.error(e);
    showError("Не удалось отправить ход.");
  }
}

function endGame() {
  gameActive = false;
  gameOver = true;
  renderBoard(null);
  updateStatus(null);
  applyEventVisuals(null);
}

document.getElementById("new-game").addEventListener("click", newGame);
document.getElementById("end-game").addEventListener("click", endGame);

boardEl.addEventListener("click", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell) return;
  const r = parseInt(cell.dataset.row, 10);
  const c = parseInt(cell.dataset.col, 10);
  clickCell(r, c, false);
});

boardEl.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  const cell = e.target.closest(".cell");
  if (!cell) return;
  const r = parseInt(cell.dataset.row, 10);
  const c = parseInt(cell.dataset.col, 10);
  clickCell(r, c, true);
});

renderBoard(null);
updateStatus(null);
applyEventVisuals(null);

