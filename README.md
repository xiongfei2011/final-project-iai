# IAI Final Project

Final project for Introduction to Artificial Intelligence (503043) at Ton Duc Thang University.

## Project structure

| Folder | Description |
| --- | --- |
| `task1_nqueens/` | Solve N-Queens with PySAT (Glucose3) and Min-Conflicts. Compare standard Min-Conflicts with a version that uses a variable-selection heuristic. |
| `task2_tank_battle/` | Build a turn-based tank game with Pygame and compare four adversarial search configurations. |
| `task3_kakuro/` | Solve Kakuro with constraint propagation and backtracking. Visualize variable domains and the solving process. |

## Setup

Open a terminal in the repository root, the folder that contains `source/`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r source/requirement.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r source/requirement.txt
```

## Running the tasks

Each task is developed in its own folder. Add the tested Python version and the commands to run each program and its experiments here as the implementations become available.

### T2-03 - Tank Battle Search Benchmark

The benchmark was tested with Python 3.13.7. Run these commands from the repository root.

```powershell
cd source
python -B -m task2_tank_battle.benchmark --runs 5 --depth 3 --timeout-ms 10000 --csv task2_tank_battle/benchmark_results.csv
```
