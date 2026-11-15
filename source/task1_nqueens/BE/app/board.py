from typing import List, Tuple


class NQueensBoard:
    """queens[col] lưu hàng của hậu ở cột đó; -1 nghĩa là cột trống"""
    

    EMPTY = -1

    @staticmethod
    def attacking_pairs(queens: List[int]) -> List[Tuple[int, int]]:
        """Tìm các cặp cột có hậu tấn công nhau (cùng hàng hoặc đường chéo"""
        placed = [(c, r) for c, r in enumerate(queens) if r != NQueensBoard.EMPTY]
        return [
            (c1, c2)
            for i, (c1, r1) in enumerate(placed)
            for c2, r2 in placed[i + 1:]
            if r1 == r2 or abs(r1 - r2) == abs(c1 - c2)
        ]

    @staticmethod
    def is_solved(queens: List[int]) -> bool:
        return NQueensBoard.EMPTY not in queens and not NQueensBoard.attacking_pairs(queens)

    @staticmethod
    def toggle(queens: List[int], row: int, col: int) -> List[int]:
        """Đặt/dời hậu cột col xuống row; bấm lại ô đó thì gỡ hậu."""
        board = list(queens)
        board[col] = NQueensBoard.EMPTY if board[col] == row else row
        return board


class BoardHistory:
    """Lịch sử state của bàn cờ (mỗi thao tác trả về bản mới)"""

    def __init__(self, states: List[List[int]], index: int = 0):
        self._states = states
        self._index = index

    @classmethod
    def empty(cls, n: int) -> "BoardHistory":
        return cls([[NQueensBoard.EMPTY] * n])

    @property
    def current(self) -> List[int]:
        return self._states[self._index]

    @property
    def step(self) -> int:
        return self._index

    @property
    def last_step(self) -> int:
        return len(self._states) - 1

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < self.last_step

    def push(self, *boards: List[int]) -> "BoardHistory":
        """Thêm trạng thái mới sau vị trí hiện tại và nhánh redo cũ bị cắt"""
        states = self._states[: self._index + 1] + [list(b) for b in boards]
        return BoardHistory(states, len(states) - 1)

    def go_to(self, index: int) -> "BoardHistory":
        return BoardHistory(self._states, max(0, min(self.last_step, index)))

    def undo(self) -> "BoardHistory":
        return self.go_to(self._index - 1)

    def redo(self) -> "BoardHistory":
        return self.go_to(self._index + 1)