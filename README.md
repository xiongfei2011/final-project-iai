# IAI Final Project

Final project for Introduction to Artificial Intelligence (503043) at Ton Duc Thang University.

## Project structure

| Folder                 | Description                                                                                                                                     |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `task1_nqueens/`     | Solve N-Queens with PySAT (Glucose3) and Min-Conflicts. Compare standard Min-Conflicts with a version that uses a variable-selection heuristic. |
| `task2_tank_battle/` | Build a tank game with Pygame and compare four adversarial search configurations.                                                               |
| `task3_kakuro/`      | Solve Kakuro with constraint propagation and backtracking. Visualize variable domains and the solving process.                                  |

## Overview

## Task 1: N-Queens

### Key Feature

1. **Manual Play Mode:** Click directly on board squares to place or remove queens manually, with instant real-time conflict highlights (rows, columns, and diagonals).
2. **Min-Conflicts Solver (Standard):** A local search algorithm that randomly selects a conflicted queen and moves it to the row in its column that minimizes conflicts.
3. **Min-Conflicts Solver (Heuristic):** An enhanced variant applying the **Most-Conflicted Variable** selection heuristic—prioritizing the queen currently involved in the highest number of conflicts—to accelerate convergence.
4. **Interactive Playback Controls:** Supports **Play/Pause**, **Step-by-Step** execution, **Undo/Reset** board states, and speed adjustment to inspect solver moves in detail
* **UI Credit: Pygame interface adapted from [eight-queens-problem-visualizer](https://github.com/singhAmandeep007/eight-queens-problem-visualizer.git).**

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

### N-Queen task

#### 1.Benchmark

```powershell
cd task1_nqueens
python -B -m BE.app.benchmark
```

#### 2. Pygame
#### Require: Tkinter and tk

```powershell
cd task1_nqueens
python main.py
```

### Tank Battle

#### 1. Search Benchmark

```powershell
python -B -m task2_tank_battle.benchmark
```

To run only Suite C:

```powershell
python -B -m task2_tank_battle.benchmark --suite c
```

#### 2. Pygame

```powershell
python -m task2_tank_battle.main
```

To select a different map:

```powershell
python -B -m task2_tank_battle.main --map task2_tank_battle/maps/example.txt
```

Press Space to start or pause. Live play is the default. To plan the match before playback, run:

```powershell
python -m task2_tank_battle.main --replay
```

### Kakuro

```powershell
python -m task3_kakuro.main
```

```bash
#For Linux/MacOS
python3 -m task3_kakuro.main
```
