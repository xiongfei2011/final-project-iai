
from task3_kakuro import config
from task3_kakuro.core.constraint import Constraint, SumConstraint, AllDiffConstraint
from task3_kakuro.core.csp_core import CSP
from task3_kakuro.core.variable import Variable

class Parse:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.row = 0
        self.col = 0
        self.grid = []
        self.variables = {}
        
        self.constraints = []

    def execute(self) -> CSP:
        self.__read_init_value()
        self.__read_horizontal_constraint()
        self.__read_vertical_constraint()

        X = list(self.variables.values())

        D = {}
        for my_x in X:
            D[my_x.my_tuple] = my_x.domain.copy()

        C = self.constraints

        return CSP(X, D, C)


    def __read_init_value(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        self.row, self.col = map(int, lines[0].split())

        for r in range(self.row):
            row_data = lines[r + 1].split()
            self.grid.append(row_data)

            for c in range(self.col):
                if row_data[c] == config.EMPTY_CELL:
                    self.variables[(r, c)] = Variable((r,c))

    def __read_horizontal_constraint(self):

        for r in range(self.row):
            for c in range(self.col):
                cell_val = self.grid[r][c]

                if (cell_val == config.EMPTY_CELL) or (cell_val == config.WALL_CELL):
                    continue

                if '\\' in cell_val:
                    v_clue , h_clue = cell_val.split('\\')

                    if h_clue != 'X':
                        target_sum = int(h_clue)
                        scope = []

                        for next_c in range(c + 1, self.col):
                            if self.grid[r][next_c] == config.EMPTY_CELL:
                                scope.append(self.variables[(r, next_c)])
                            else:
                                break

                        if scope:
                            self.constraints.append(SumConstraint(scope, target_sum))
                            self.constraints.append(AllDiffConstraint(scope))

    def __read_vertical_constraint(self):

        for r in range(self.row):
            for c in range(self.col):
                cell_val = self.grid[r][c]

                if (cell_val == config.EMPTY_CELL) or (cell_val == config.WALL_CELL):
                    continue

                if '\\' in cell_val:
                    v_clue, h_clue = cell_val.split('\\')

                    if v_clue != 'X':
                        target_sum = int(v_clue)
                        scope = []

                        for next_r in range(r + 1, self.row):
                            if self.grid[next_r][c] == config.EMPTY_CELL:
                                scope.append(self.variables[(next_r, c)])
                            else:
                                break

                        if scope:
                            self.constraints.append(SumConstraint(scope, target_sum))
                            self.constraints.append(AllDiffConstraint(scope))