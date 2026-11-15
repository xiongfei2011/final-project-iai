import pygame

from task3_kakuro.gui.game_state import GameState
from task3_kakuro.gui.render import Renderer


def run_history_viewer(
    original_grid,
    history,
    cell_size=60,
    step_interval_ms=180,
    solve_time_ms=0.0,
):
    if step_interval_ms <= 0:
        raise ValueError("step_interval_ms must be greater than zero.")

    game_state = GameState(original_grid, history, solve_time_ms)
    rows = len(original_grid)
    cols = len(original_grid[0])
    footer_height = 55

    pygame.init()
    screen = pygame.display.set_mode(
        (max(cols * cell_size, 520), rows * cell_size + footer_height)
    )
    pygame.display.set_caption("Kakuro CSP Solver")
    renderer = Renderer(screen, cell_size)
    clock = pygame.time.Clock()
    elapsed_ms = 0
    running = True

    try:
        while running:
            elapsed_ms += clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        game_state.toggle_play()
                        elapsed_ms = 0
                    elif event.key == pygame.K_RIGHT:
                        game_state.is_playing = False
                        game_state.forward_step()
                        elapsed_ms = 0
                    elif event.key == pygame.K_LEFT:
                        game_state.is_playing = False
                        game_state.backward_step()
                        elapsed_ms = 0

            if game_state.is_playing and elapsed_ms >= step_interval_ms:
                elapsed_ms %= step_interval_ms
                if not game_state.forward_step():
                    game_state.is_playing = False

            renderer.draw(game_state)
    finally:
        pygame.quit()
