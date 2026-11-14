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

From the repository root, run:

```powershell
cd source
```

### Tank Battle Search Benchmark

```powershell
python -B -m task2_tank_battle.benchmark
```

To run only Suite C:

```powershell
python -B -m task2_tank_battle.benchmark --suite c
```

### Tank Battle Pygame

```powershell
python -B -m task2_tank_battle.main
```

To select a different map:

```powershell
python -B -m task2_tank_battle.main --map task2_tank_battle/maps/example.txt
```

Press Space to start or pause. When you push start button, you have to wait for searching.
