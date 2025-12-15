from collections import deque
from typing import List, Optional
import random

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import events


app = FastAPI(title="Simple Minesweeper")
app.mount("/static", StaticFiles(directory="."), name="static")


class ClickRequest(BaseModel):
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    right_click: bool = False


class NewGameRequest(BaseModel):
    rows: int = Field(ge=2, le=30)
    cols: int = Field(ge=2, le=30)
    mines: int = Field(ge=1)


class Cell(BaseModel):
    is_mine: bool = False
    is_revealed: bool = False
    is_flagged: bool = False
    adjacent_mines: int = 0


class GameState(BaseModel):
    rows: int
    cols: int
    mines: int
    board: List[List[Cell]]
    game_over: bool = False
    won: bool = False
    active_event: Optional[dict] = None

    @property
    def safe_cells_left(self) -> int:
        total_cells = self.rows * self.cols
        safe_cells = total_cells - self.mines
        revealed_safe = sum(
            1
            for row in self.board
            for cell in row
            if cell.is_revealed and not cell.is_mine
        )
        return safe_cells - revealed_safe


current_game: GameState | None = None

DIRECTIONS = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
]


def generate_board(rows: int, cols: int, mines: int) -> List[List[Cell]]:
    total_cells = rows * cols
    if mines >= total_cells:
        raise ValueError("Too many mines")

    board = [[Cell() for _ in range(cols)] for _ in range(rows)]

    positions = [(r, c) for r in range(rows) for c in range(cols)]
    mine_positions = random.sample(positions, mines)

    for r, c in mine_positions:
        board[r][c].is_mine = True

    for r in range(rows):
        for c in range(cols):
            if board[r][c].is_mine:
                continue
            count = 0
            for dr, dc in DIRECTIONS:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc].is_mine:
                    count += 1
            board[r][c].adjacent_mines = count

    return board


def reveal_cell(game: GameState, row: int, col: int) -> None:
    if game.game_over:
        return

    cell = game.board[row][col]
    if cell.is_revealed or cell.is_flagged:
        return

    cell.is_revealed = True

    if cell.is_mine:
        game.game_over = True
        game.won = False
        for r in range(game.rows):
            for c in range(game.cols):
                if game.board[r][c].is_mine:
                    game.board[r][c].is_revealed = True
        return

    # flood-fill: всегда раскрываем область пустых и их границу,
    # даже если кликнули по клетке с числом (если рядом есть пустые)
    q = deque()
    start = game.board[row][col]
    if start.adjacent_mines == 0:
        q.append((row, col))
    else:
        # если кликнули по числу, ищем пустые рядом и запускаем от них
        for dr, dc in DIRECTIONS:
            nr, nc = row + dr, col + dc
            if not (0 <= nr < game.rows and 0 <= nc < game.cols):
                continue
            neighbor = game.board[nr][nc]
            if (
                not neighbor.is_mine
                and not neighbor.is_flagged
                and not neighbor.is_revealed
                and neighbor.adjacent_mines == 0
            ):
                neighbor.is_revealed = True
                q.append((nr, nc))

    while q:
        cr, cc = q.popleft()
        for dr, dc in DIRECTIONS:
            nr, nc = cr + dr, cc + dc
            if not (0 <= nr < game.rows and 0 <= nc < game.cols):
                continue
            neighbor = game.board[nr][nc]
            if neighbor.is_flagged or neighbor.is_revealed:
                continue
            neighbor.is_revealed = True
            if neighbor.adjacent_mines == 0 and not neighbor.is_mine:
                q.append((nr, nc))

    if game.safe_cells_left == 0:
        game.game_over = True
        game.won = True
        return

    # если игра продолжается, запускаем новое событие
    prev_type = game.active_event["type"] if game.active_event else None
    game.active_event = events.random_event(prev_type).to_dict()


def toggle_flag(game: GameState, row: int, col: int) -> None:
    if game.game_over:
        return

    cell = game.board[row][col]
    if cell.is_revealed:
        return
    cell.is_flagged = not cell.is_flagged


def serialize_game(game: GameState) -> dict:
    return {
        "rows": game.rows,
        "cols": game.cols,
        "mines": game.mines,
        "game_over": game.game_over,
        "won": game.won,
        "safe_cells_left": game.safe_cells_left,
        "active_event": game.active_event,
        "board": [
            [
                {
                    "is_mine": cell.is_mine if game.game_over else cell.is_mine and cell.is_revealed,
                    "is_revealed": cell.is_revealed,
                    "is_flagged": cell.is_flagged,
                    "adjacent_mines": cell.adjacent_mines if cell.is_revealed or game.game_over else 0,
                }
                for cell in row
            ]
            for row in game.board
        ],
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("index.html")


@app.post("/new-game")
async def new_game(req: NewGameRequest):
    global current_game

    total_cells = req.rows * req.cols
    if req.mines >= total_cells:
        raise HTTPException(
            status_code=400,
            detail=f"Количество мин должно быть от 1 до {total_cells - 1}.",
        )

    board = generate_board(req.rows, req.cols, req.mines)
    current_game = GameState(
        rows=req.rows,
        cols=req.cols,
        mines=req.mines,
        board=board,
        game_over=False,
        won=False,
        active_event=None,
    )
    return serialize_game(current_game)


@app.post("/click")
async def click_cell_endpoint(req: ClickRequest):
    global current_game

    if current_game is None:
        raise HTTPException(status_code=400, detail="Игра ещё не создана.")

    if not (0 <= req.row < current_game.rows and 0 <= req.col < current_game.cols):
        raise HTTPException(status_code=400, detail="Координаты вне поля.")

    if req.right_click:
        toggle_flag(current_game, req.row, req.col)
    else:
        reveal_cell(current_game, req.row, req.col)

    return serialize_game(current_game)


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)

