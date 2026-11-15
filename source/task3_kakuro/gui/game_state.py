from task3_kakuro.config import EMPTY_CELL, WHITE


class GameState:
    def __init__(self, original_grid: list, history: list, solve_time_ms: float = 0.0):
        if not original_grid or not original_grid[0]:
            raise ValueError("The Kakuro grid must not be empty.")
        if any(len(row) != len(original_grid[0]) for row in original_grid):
            raise ValueError("The Kakuro grid must be rectangular.")

        self.original_grid = original_grid
        self.history = history
        self.total_steps = len(history)
        self.current_step = 0
        self.is_playing = False
        self.solve_time_ms = solve_time_ms
        self.visual_board = {
            (r, c): {"val": "", "color": WHITE}
            for r, row in enumerate(original_grid)
            for c, cell in enumerate(row)
            if cell == EMPTY_CELL
        }
        self._previous_cells = []

    def toggle_play(self):
        self.is_playing = not self.is_playing

    def forward_step(self):
        if self.current_step >= self.total_steps:
            return False

        coord, val, action = self.history[self.current_step]
        if coord not in self.visual_board:
            raise ValueError(f"History references a non-playable cell: {coord}")
        if action not in {"ASSIGN", "REMOVE"}:
            raise ValueError(f"Unknown history action at step {self.current_step}: {action}")

        previous = self.visual_board[coord].copy()
        self._previous_cells.append((coord, previous))
        self.visual_board[coord] = {
            "val": val,
            "color": (144, 238, 144) if action == "ASSIGN" else (255, 99, 71),
        }
        self.current_step += 1
        return True

    def backward_step(self):
        if self.current_step == 0:
            return False

        self.current_step -= 1
        coord, previous = self._previous_cells.pop()
        self.visual_board[coord] = previous
        return True
