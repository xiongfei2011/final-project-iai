# IAI Final Project

Final project for Introduction to Artificial Intelligence (503043) at Ton Duc Thang University.

## Project structure

| Folder | Description |
| --- | --- |
| `task1_nqueens/` | Solve N-Queens with PySAT (Glucose3) and Min-Conflicts. Compare standard Min-Conflicts with a version that uses a variable-selection heuristic. |
| `task2_tank_battle/` | Build a tank game with Pygame and compare four adversarial search configurations. |
| `task3_kakuro/` | Solve Kakuro with constraint propagation and backtracking. Visualize variable domains and the solving process. |

## Setup

Open a terminal in the repository root, the folder that contains `source/`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r source/requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r source/requirements.txt
```

## Running the tasks

Each task is developed in its own folder. Add the tested Python version and the commands to run each program and its experiments here as the implementations become available.

### T2-03 - Tank Battle Search Benchmark

The benchmark was tested with Python 3.13.7. Run these commands from the repository root.

```powershell
cd source
python -B -m task2_tank_battle.benchmark --runs 5 --depth 3 --timeout-ms 10000 --csv task2_tank_battle/benchmark_results.csv
```

Each run loads a fresh board from `source/task2_tank_battle/maps/benchmark/`.
All four configurations choose an action for A from the same starting
state with no bullets on the board. The benchmark times one search.

| Map | Rows × columns | Starting base HP | What to expect at depth 3 |
| --- | --- | --- | --- |
| `opening_win` | 2 × 3 | 1 each | A can destroy B's base in 1 tick. |
| `opening_draw` | 2 × 4 | 1 each | Both bases are destroyed in the opening tick if both tanks fire. |
| `opening_loss` | 3 × 5 | 1 each | B can destroy A's base in the opening tick. |
| `heuristic_cutoff` | 2 × 4 | Standard HP | The heuristic agents assign a value to unfinished boards at the cutoff. |

Depth 3 also explores alternatives to the opening shots and gives the
heuristic agents more room to distinguish unfinished boards.

### T2-04 - Tank Battle Pygame

Install the dependencies in the setup section, then run these commands from the repository root.

```powershell
cd source
python -B -m task2_tank_battle.main --preview
python -B -m task2_tank_battle.main --demo --agent-a heuristic --agent-b heuristic-alpha-beta --depth 2 --turn-ms 450
```

`--preview` shows the initial board. `--demo` uses the short draw
scenario from the benchmark. In the side panel, choose an algorithm for
each tank and press Play or Space. By default, playback starts once
the agents finish planning the match. Use `--live` to play while the
agents are still choosing.

`--turn-ms` sets the interval between game ticks. Each tank can act once per
tick when its AI has a move ready. A tank can fire once its previous shot
has disappeared. Each shot moves up to three cells in the same tick,
checking for an impact in each cell. It disappears on impact, on leaving
the board, or after reaching its range, so a tank can fire again on the
next tick. Hits in the same movement step are applied together. The
replay animates the shot over the cells it travelled.
If a movement command targets a wall, tank, or base, the tank turns in that
direction and stays in its current cell.
If both tanks try to enter the same cell, both stay put.

The built-in agents test pairs of actions from the same board and use the
opponent's strongest reply when scoring a choice. For all four built-in
agents, `--depth` counts complete ticks, with a default of three.

Opening HP, facing directions, the first player, game rules, search defaults, heuristic weights, and display settings are in `source/task2_tank_battle/config.py`. CLI options override the match defaults for one run.

#### Replay an AI match

From `source/`, run a replay on the example map:

```powershell
python -m task2_tank_battle.main --map task2_tank_battle/maps/example.txt --turn-ms 700
```

At each planning tick the game starts both AI searches from the same board and waits for
both answers. When actions have the same search value, the built-in agents
prefer an action different from the one they used in the previous tick.
When the board also repeats, they prefer actions that lead to fewer
previously seen boards across the opponent's possible replies among the
remaining tied choices.
The replay reads the saved board states and actions. In live play an AI that
is still thinking can miss a tick.
The panel shows tank and base HP for the current step. Press Space to play
or pause, Left or Right to step, R to reset, and Esc to quit. The panel
buttons perform the same actions. Reset returns to the opening board with
the chosen agents. At the end, Play restarts playback. Planning stops at a game result or the
configured `REPLAY_MAX_TURNS` limit of 100 steps. Use `--demo` for a short
completed match. `--replay` explicitly selects the default playback mode.

The selectors offer Minimax (`minimax`), Alpha-Beta (`alpha-beta`),
Heuristic Minimax (`heuristic`), and Heuristic Minimax + Alpha-Beta
(`heuristic-alpha-beta`). Partner agents passed with `--agent-a` or
`--agent-b` also appear in the selectors.

Use `--standard-depth 4` in the game to set a separate limit for Minimax and
Alpha-Beta, or `--standard-depth none` to run them without a search-depth
limit. Use small maps for unlimited search, which can take a long time
and reach Python's recursion limit. The benchmark uses a shared `--depth`.

The agents use game utility at finished states and score a repeated state
on the current search path as a draw. At a depth cutoff, Minimax and
Alpha-Beta score unfinished states as 0, and the heuristic agents use the
evaluation function. Alpha-Beta prunes branches that cannot change the
choice.

#### Play on a text map

The game loads `DEFAULT_MAP_PATH` from `config.py` when you omit `--map`.
The **Map** selector lists the `.txt` files in the bundled `maps/` folder
and includes the starting map selected with `--map` or `--demo`. Choosing
a different map returns to step 0 and keeps both agent selections.

Edit `source/task2_tank_battle/maps/example.txt` or pass another UTF-8 file
to `--map`. Relative paths start at the directory where you run the
command. Use one row per line, with the same number of characters in every
row and one of each tank and base.

| Symbol | Tile |
| --- | --- |
| `.` | Empty tile |
| `#` | Wall |
| `A`, `B` | Tank for player A or B |
| `a`, `b` | Base for player A or B |

Run from `source/`.

```powershell
python -B -m task2_tank_battle.main --map task2_tank_battle/maps/example.txt --preview
python -B -m task2_tank_battle.main --map task2_tank_battle/maps/example.txt
```

#### Load another group's agent

Place the agent module in `source/` or on `PYTHONPATH`. Each side accepts a
built-in name or `module:factory`. A partner factory takes one argument,
the shared `GameRules` instance, and returns an object with
`choose_action(state)`. It sets its own search depth. The CLI option `--depth`
applies to the built-in agents. Each call to `choose_action` receives a copy of the
current `GameState` and returns an action from `rules.actions(state)`.
On that copy, `state.current_turn` identifies which side the agent controls.

Action names are defined in `task2_tank_battle.game.actions`. An agent can return
either a string such as `"FIRE"` or `Action.FIRE`. Read entity data through
attributes such as `state.tanks[player].hp` and `state.tanks[player].position`.
`state.game_map.wall_at(position)` returns the wall if it still blocks that cell.

For example, save the following as `source/partner_agent.py`.

```python
class PartnerAgent:
    def __init__(self, rules):
        self.rules = rules

    def choose_action(self, state):
        return self.rules.actions(state)[0]


def create_agent(rules):
    return PartnerAgent(rules)
```

Run the match from `source/`.

```powershell
python -B -m task2_tank_battle.main --demo --agent-a heuristic --agent-b partner_agent:create_agent
```

For an agent with a different signature, return an adapter from the factory. For example, an adapter can wrap an existing `select_move(state, player)` method.

```python
class PartnerAdapter:
    def __init__(self, agent):
        self.agent = agent

    def choose_action(self, state):
        return self.agent.select_move(state, state.current_turn)
```

The match checks each action against the board given to the agent. An illegal
action stops the match and displays a message. If the destination becomes
occupied while the agent is searching, the move turns the tank in place.
