import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "BE"))

from app.board import BoardHistory, NQueensBoard
from app.models import SolverResult
from app.solvers import (
    BaseNQueensSolver,
    HeuristicMinConflictsSolver,
    MinConflictsSolver,
    NQueensSATSolver,
)


class NQueensNativeGame:
    MIN_N, MAX_N = 4, 50

    BG = "#F8FAFC"
    CARD_BG = "#FFFFFF"
    BORDER = "#E2E8F0"
    TEXT_PRIMARY = "#0F172A"
    TEXT_MUTED = "#64748B"

    BTN_PRIMARY = "#2563EB"
    BTN_PRIMARY_HOVER = "#1D4ED8"
    BTN_SECONDARY = "#F1F5F9"
    BTN_SEC_HOVER = "#E2E8F0"
    BTN_WARN_BG = "#FEF3C7"
    BTN_WARN_FG = "#B45309"
    BTN_WARN_HOVER = "#FDE68A"
    BTN_DANGER_BG = "#FEF2F2"
    BTN_DANGER_FG = "#DC2626"
    BTN_DANGER_HOVER = "#FEE2E2"

    CELL_LIGHT = "#FFFFFF"
    CELL_DARK = "#CBD5E1"
    CELL_CONFLICT = "#FEE2E2"
    CELL_SOLVED = "#DCFCE7"
    QUEEN_COLOR = "#1E293B"
    QUEEN_CONFLICT = "#DC2626"
    QUEEN_SOLVED = "#15803D"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.n = 8
        self.history = BoardHistory.empty(self.n)
        self.playing = False
        self.paused = False
        self.play_delay = 150
        self._after_id: Optional[str] = None
        self.algo_btns: Dict[str, tk.Label] = {}
        self._configure_window()
        self._build_ui()
        self._refresh()
        self.root.after(50, self.canvas.focus_set)

    def _configure_window(self) -> None:
        self.root.title("N-Queens Interactive Game & AI Solver")
        self.root.geometry("920x800")
        self.root.minsize(680, 580)
        self.root.configure(bg=self.BG)
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        self.root.bind_all("<Left>", self._on_left_key)
        self.root.bind_all("<Right>", self._on_right_key)
        self.root.bind_all("<space>", self._on_space_key)

    def _is_typing_size(self) -> bool:
        return self.root.focus_get() == self.size_entry

    def _on_left_key(self, event: tk.Event) -> Optional[str]:
        if not self._is_typing_size():
            self._undo()
            return "break"
        return None

    def _on_right_key(self, event: tk.Event) -> Optional[str]:
        if not self._is_typing_size():
            self._redo()
            return "break"
        return None

    def _on_space_key(self, event: tk.Event) -> Optional[str]:
        if not self._is_typing_size():
            self._toggle_pause()
            return "break"
        return None

    def _make_btn(
        self,
        parent: tk.Frame,
        text: str,
        command,
        bg: str = BTN_SECONDARY,
        fg: str = TEXT_PRIMARY,
        hover_bg: str = BTN_SEC_HOVER,
        **pack,
    ) -> tk.Label:
        btn = tk.Label(
            parent,
            text=text,
            font=("Helvetica", 12, "bold"),
            bg=bg,
            fg=fg,
            padx=14,
            pady=7,
            cursor="pointinghand",
            highlightthickness=1,
            highlightbackground=self.BORDER if bg == self.BTN_SECONDARY else bg,
        )
        btn._is_disabled = False
        btn._orig_bg = bg
        btn._orig_fg = fg
        btn._hover_bg = hover_bg

        def on_click(_):
            self.canvas.focus_set()
            if not btn._is_disabled:
                command()

        def on_enter(_):
            if not btn._is_disabled:
                btn.config(bg=btn._hover_bg)

        def on_leave(_):
            if not btn._is_disabled:
                btn.config(bg=btn._orig_bg)

        btn.bind("<Button-1>", on_click)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.pack(side=tk.LEFT, **pack)
        return btn

    def _build_ui(self) -> None:
        header = tk.Frame(
            self.root, bg=self.CARD_BG, padx=24, pady=14,
            highlightthickness=1, highlightbackground=self.BORDER
        )
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text="♛ N-QUEENS PUZZLE & AI SOLVER",
            font=("Helvetica", 18, "bold"),
            bg=self.CARD_BG,
            fg=self.TEXT_PRIMARY,
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="SAT (Glucose3) & Local Search",
            font=("Helvetica", 11, "bold"),
            bg="#EFF6FF",
            fg=self.BTN_PRIMARY,
            padx=10,
            pady=4,
        ).pack(side=tk.RIGHT)

        ctrl_card = tk.Frame(
            self.root, bg=self.CARD_BG, padx=20, pady=14,
            highlightthickness=1, highlightbackground=self.BORDER
        )
        ctrl_card.pack(fill=tk.X, padx=24, pady=(16, 8))

        row1 = tk.Frame(ctrl_card, bg=self.CARD_BG)
        row1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            row1, text="Size:", font=("Helvetica", 12, "bold"),
            bg=self.CARD_BG, fg=self.TEXT_PRIMARY
        ).pack(side=tk.LEFT)

        self.size_var = tk.StringVar(value=str(self.n))
        self.size_entry = tk.Entry(
            row1,
            textvariable=self.size_var,
            width=5,
            font=("Helvetica", 13, "bold"),
            justify="center",
            bg=self.BG,
            fg=self.TEXT_PRIMARY,
            insertbackground=self.TEXT_PRIMARY,
            relief=tk.FLAT,
            takefocus=0,
            highlightthickness=1,
            highlightbackground="#CBD5E1",
        )
        self.size_entry.pack(side=tk.LEFT, padx=8, ipady=4)
        self.size_entry.bind("<Return>", lambda _: (self.canvas.focus_set(), self._apply_size()))

        self._make_btn(row1, "Size", self._apply_size, padx=(0, 14))
        self.btn_undo = self._make_btn(row1, "Undo", self._undo, padx=3)
        self.btn_redo = self._make_btn(row1, "Redo", self._redo, padx=3)
        self.btn_pause = self._make_btn(
            row1,
            "⏸ Pause",
            self._toggle_pause,
            bg=self.BTN_WARN_BG,
            fg=self.BTN_WARN_FG,
            hover_bg=self.BTN_WARN_HOVER,
            padx=(14, 0),
        )
        self._make_btn(
            row1,
            "Reset chess board",
            self._clear_board,
            bg=self.BTN_DANGER_BG,
            fg=self.BTN_DANGER_FG,
            hover_bg=self.BTN_DANGER_HOVER,
            padx=(14, 0),
        )

        row2 = tk.Frame(ctrl_card, bg=self.CARD_BG)
        row2.pack(fill=tk.X)

        tk.Label(
            row2, text="AI Algorithm:", font=("Helvetica", 12, "bold"),
            bg=self.CARD_BG, fg=self.TEXT_MUTED
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.algo_btns = {
            "sat": self._make_btn(row2, "▶ Glucose3 (SAT)", lambda: self._solve("sat"), padx=(0, 6)),
            "mc": self._make_btn(row2, "▶ Min-Conflicts (standard)", lambda: self._solve("mc"), padx=4),
            "mc_h": self._make_btn(row2, "▶ Min-Conflicts heuristic", lambda: self._solve("mc_h"), padx=4),
        }

        status = tk.Frame(
            self.root, bg=self.CARD_BG, padx=20, pady=12,
            highlightthickness=1, highlightbackground=self.BORDER
        )
        status.pack(fill=tk.X, padx=24, pady=6)

        self.stat_main = tk.Label(status, font=("Helvetica", 13, "bold"), bg=self.CARD_BG)
        self.stat_main.pack(anchor=tk.W)
        self.stat_sub = tk.Label(
            status,
            text="Click into the board for self-play, or choose AI mode. Press Space to Pause/Resume, ← → for steps.",
            font=("Helvetica", 11),
            bg=self.CARD_BG,
            fg=self.TEXT_MUTED,
        )
        self.stat_sub.pack(anchor=tk.W, pady=(2, 0))

        self.canvas = tk.Canvas(self.root, bg=self.BG, highlightthickness=0, takefocus=1)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 20))
        self.canvas.bind("<Configure>", lambda _: self._refresh())
        self.canvas.bind("<Button-1>", self._on_click)

    def _highlight_algo(self, active_mode: str) -> None:
        for mode, btn in self.algo_btns.items():
            is_active = (mode == active_mode)
            new_bg = self.BTN_PRIMARY if is_active else self.BTN_SECONDARY
            new_fg = "#FFFFFF" if is_active else self.TEXT_PRIMARY
            new_hover = self.BTN_PRIMARY_HOVER if is_active else self.BTN_SEC_HOVER
            btn._orig_bg = new_bg
            btn._orig_fg = new_fg
            btn._hover_bg = new_hover
            btn.config(
                bg=new_bg,
                fg=new_fg,
                highlightbackground=new_bg if is_active else self.BORDER,
            )

    def _stop_playback(self) -> None:
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.playing = False
        self.paused = False

    def _toggle_pause(self) -> None:
        if not self.playing:
            return
        self.paused = not self.paused
        if self.paused:
            if self._after_id is not None:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            self._refresh()
        else:
            self._autoplay()

    def _apply_size(self) -> bool:
        self.canvas.focus_set()
        raw = self.size_var.get().strip()
        self.size_var.set(raw)
        if not raw.isdigit() or not self.MIN_N <= int(raw) <= self.MAX_N:
            messagebox.showwarning("Warning", f"Enter N from {self.MIN_N} to {self.MAX_N}.")
            self.size_var.set(str(self.n))
            return False
        if int(raw) != self.n:
            self._stop_playback()
            self.n = int(raw)
            self.history = BoardHistory.empty(self.n)
            self._highlight_algo("")
            self.stat_sub.config(text=f"Create new chessboard {self.n} x {self.n}.")
            self._refresh()
        return True

    def _undo(self) -> None:
        if not self.playing or self.paused:
            self.history = self.history.undo()
            self._refresh()

    def _redo(self) -> None:
        if not self.playing or self.paused:
            self.history = self.history.redo()
            self._refresh()

    def _clear_board(self) -> None:
        self._stop_playback()
        self.history = self.history.push(BoardHistory.empty(self.n).current)
        self._highlight_algo("")
        self.stat_sub.config(text="Clear chess board.")
        self._refresh()

    def _on_click(self, event: tk.Event) -> None:
        self.canvas.focus_set()
        geometry = self._geometry()
        if (self.playing and not self.paused) or geometry is None:
            return
        ox, oy, cell = geometry
        col, row = int((event.x - ox) // cell), int((event.y - oy) // cell)
        if 0 <= col < self.n and 0 <= row < self.n:
            self._stop_playback()
            self._highlight_algo("")
            self.history = self.history.push(NQueensBoard.toggle(self.history.current, row, col))
            self._refresh()

    def _make_solver(self, mode: str) -> BaseNQueensSolver:
        max_steps = max(20000, self.n * 60)
        if mode == "sat":
            return NQueensSATSolver(self.n)
        if mode == "mc_h":
            return HeuristicMinConflictsSolver(self.n, max_steps=max_steps, record_history=True)
        return MinConflictsSolver(self.n, max_steps=max_steps, record_history=True)

    @staticmethod
    def _describe(result: SolverResult) -> str:
        detail = f"{result.clauses_count} CNF clauses" if result.clauses_count else f"{result.steps} steps"
        return f"[{result.algorithm}] {detail}  •  Time: {result.elapsed_time_ms} ms"

    def _solve(self, mode: str) -> None:
        if not self._apply_size():
            return
        self._stop_playback()
        self._highlight_algo(mode)
        result = self._make_solver(mode).solve()
        if not result.solved:
            self.stat_sub.config(text=f"[{result.algorithm}] {result.message}")
            self._refresh()
            return
        boards = result.history or [result.queens]
        first_new = self.history.step + 1
        self.history = self.history.push(*boards).go_to(first_new)
        self.stat_sub.config(text=self._describe(result))
        self.playing = True
        self.paused = False
        self.play_delay = max(120, min(250, 4500 // len(boards)))
        self._autoplay()

    def _autoplay(self) -> None:
        if not self.playing or self.paused:
            self._refresh()
            return
        self._refresh()
        if not self.history.can_redo:
            self._stop_playback()
            self._refresh()
            return
        self.history = self.history.redo()
        self._after_id = self.root.after(self.play_delay, self._autoplay)

    def _geometry(self) -> Optional[Tuple[float, float, float]]:
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        side = min(w, h) - 16
        return None if side <= 20 else ((w - side) / 2, (h - side) / 2, side / self.n)

    def _refresh(self) -> None:
        queens = self.history.current
        pairs = NQueensBoard.attacking_pairs(queens)
        bad_cols = {c for pair in pairs for c in pair}
        solved = NQueensBoard.is_solved(queens) and (not self.playing or self.paused)
        self._update_status(queens, len(pairs), solved)

        is_running_actively = self.playing and not self.paused
        can_u = self.history.can_undo and not is_running_actively
        can_r = self.history.can_redo and not is_running_actively
        self.btn_undo._is_disabled = not can_u
        self.btn_redo._is_disabled = not can_r
        self.btn_undo.config(fg=self.TEXT_PRIMARY if can_u else "#94A3B8")
        self.btn_redo.config(fg=self.TEXT_PRIMARY if can_r else "#94A3B8")

        if not self.playing:
            self.btn_pause._is_disabled = True
            self.btn_pause._orig_bg = self.BTN_SECONDARY
            self.btn_pause._hover_bg = self.BTN_SECONDARY
            self.btn_pause.config(
                text="⏸ Pause",
                bg=self.BTN_SECONDARY,
                fg="#94A3B8",
                highlightbackground=self.BORDER,
            )
        elif self.paused:
            self.btn_pause._is_disabled = False
            self.btn_pause._orig_bg = "#DCFCE7"
            self.btn_pause._hover_bg = "#BBF7D0"
            self.btn_pause.config(
                text="▶ Resume",
                bg="#DCFCE7",
                fg="#15803D",
                highlightbackground="#86EFAC",
            )
        else:
            self.btn_pause._is_disabled = False
            self.btn_pause._orig_bg = self.BTN_WARN_BG
            self.btn_pause._hover_bg = self.BTN_WARN_HOVER
            self.btn_pause.config(
                text="⏸ Pause",
                bg=self.BTN_WARN_BG,
                fg=self.BTN_WARN_FG,
                highlightbackground=self.BTN_WARN_BG,
            )

        self._draw_board(queens, bad_cols, solved)

    def _update_status(self, queens: List[int], conflicts: int, solved: bool) -> None:
        placed = sum(1 for r in queens if r != NQueensBoard.EMPTY)
        pause_tag = "  [PAUSED]" if self.paused else ""
        step = f"  |  Step {self.history.step} / {self.history.last_step}{pause_tag}"
        if solved:
            self.stat_main.config(text=f" ★Finished: {placed}/{self.n}  |  Conflicted: 0{step}", fg="#16A34A")
        elif conflicts:
            self.stat_main.config(text=f"Queen: {placed}/{self.n}  |  Conflicted: {conflicts}{step}", fg="#DC2626")
        else:
            self.stat_main.config(text=f"Queen: {placed}/{self.n}  |  Conflicted: 0{step}", fg=self.BTN_PRIMARY)

    def _draw_board(self, queens: List[int], bad_cols: set, solved: bool) -> None:
        self.canvas.delete("all")
        geometry = self._geometry()
        if geometry is None:
            return
        ox, oy, cell = geometry
        size = cell * self.n

        self.canvas.create_rectangle(
            ox - 4, oy - 4, ox + size + 4, oy + size + 4,
            fill=self.CARD_BG, outline="#94A3B8", width=2
        )

        for r in range(self.n):
            for c in range(self.n):
                has_queen = queens[c] == r
                bg_color = self.CELL_LIGHT if (r + c) % 2 == 0 else self.CELL_DARK
                q_color = self.QUEEN_COLOR

                if has_queen and c in bad_cols:
                    bg_color = self.CELL_CONFLICT
                    q_color = self.QUEEN_CONFLICT
                elif has_queen and solved:
                    bg_color = self.CELL_SOLVED
                    q_color = self.QUEEN_SOLVED

                x1, y1 = ox + c * cell, oy + r * cell
                self.canvas.create_rectangle(x1, y1, x1 + cell, y1 + cell, fill=bg_color, outline="")
                if has_queen:
                    self.canvas.create_text(
                        x1 + cell / 2,
                        y1 + cell / 2,
                        text="♛",
                        font=("Helvetica", max(9, int(cell * 0.65))),
                        fill=q_color,
                    )