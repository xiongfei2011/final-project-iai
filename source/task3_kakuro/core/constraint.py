
from core.variable import Variable

class Constraint:
    def __init__(self, scope: list[Variable]):
        self.scope = scope

class SumConstraint(Constraint):
    def __init__(self, scope: list[Variable], target_sum: int):
        super().__init__(scope)
        self.target_sum = target_sum

    def __repr__(self):
        return f"Sum({self.target_sum}, {self.scope})"

class AllDiffConstraint(Constraint):
    def __init__(self, scope: list[Variable]):
        super().__init__(scope)

    def __repr__(self):
        return f"AllDiff({self.scope})"