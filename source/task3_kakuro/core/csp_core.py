
from task3_kakuro.core.constraint import Constraint
from task3_kakuro.core.variable import Variable
class CSP:
    def __init__(self, variables: list[Variable], domains: dict[tuple, set], constraints: list[Constraint]):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints