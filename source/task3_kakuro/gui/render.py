import pygame

from config import (
    BLACK,
    CLUE_TEXT_COLOR,
    GRAY,
    LINE_COLOR,
    TEXT_COLOR,
    WALL_CELL,
    WHITE,
)


class Renderer:
    def __init__(self, screen, cell_size=60):
        self.screen = screen
        self.cell_size = cell_size
        self.font_val = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_clue = pygame.font.SysFont("Arial", 16)

    def draw(self, game_state):
        self.screen.fill(GRAY)

        for r, row in enumerate(game_state.original_grid):
            for c, cell_value in enumerate(row):
                rect = pygame.Rect(
                    c * self.cell_size,
                    r * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                if cell_value == WALL_CELL:
                    pygame.draw.rect(self.screen, BLACK, rect)
                    pygame.draw.rect(self.screen, LINE_COLOR, rect, 1)
                elif "\\" in cell_value:
                    self.draw_clue_cell(rect, cell_value)
                else:
                    self.draw_variable_cell(rect, (r, c), game_state)

        self.draw_ui_info(game_state)
        pygame.display.flip()

    def draw_clue_cell(self, rect, clue_str):
        pygame.draw.rect(self.screen, BLACK, rect)
        pygame.draw.rect(self.screen, LINE_COLOR, rect, 1)
        pygame.draw.line(self.screen, WHITE, rect.topleft, rect.bottomright, 2)

        v_clue, h_clue = clue_str.split("\\", maxsplit=1)
        if v_clue != "X":
            text = self.font_clue.render(v_clue, True, CLUE_TEXT_COLOR)
            self.screen.blit(text, (rect.x + 5, rect.y + self.cell_size // 2 + 5))
        if h_clue != "X":
            text = self.font_clue.render(h_clue, True, CLUE_TEXT_COLOR)
            self.screen.blit(
                text,
                (rect.x + self.cell_size // 2 + 5, rect.y + 5),
            )

    def draw_variable_cell(self, rect, coord, game_state):
        cell_data = game_state.visual_board.get(coord)
        bg_color = cell_data["color"] if cell_data else WHITE
        pygame.draw.rect(self.screen, bg_color, rect)
        pygame.draw.rect(self.screen, LINE_COLOR, rect, 1)

        if cell_data and cell_data["val"] != "":
            text = self.font_val.render(str(cell_data["val"]), True, TEXT_COLOR)
            self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_ui_info(self, game_state):
        status = "Playing" if game_state.is_playing else "Paused"
        info = (
            f"Step: {game_state.current_step} / {game_state.total_steps} | "
            f"Solve: {game_state.solve_time_ms:.2f} ms | {status}"
        )
        controls = "SPACE: play/pause | RIGHT: next | LEFT: previous | ESC: quit"
        self.screen.blit(
            self.font_clue.render(info, True, BLACK),
            (10, self.screen.get_height() - 42),
        )
        self.screen.blit(
            self.font_clue.render(controls, True, BLACK),
            (10, self.screen.get_height() - 22),
        )
