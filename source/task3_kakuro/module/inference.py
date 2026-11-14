
from core.csp_core import CSP
from core.constraint import Constraint, SumConstraint, AllDiffConstraint

class Inference:
    def __init__(self, csp: CSP):
        self.csp = csp

    def enforce_node_consistency(self):

        for constraint in (self.csp.constraints):
            if isinstance(constraint, SumConstraint):
                target = constraint.target_sum
                scope_len = len(constraint.scope)

                min_sum = int((scope_len * (scope_len - 1)) / 2)
                max_valid = target - min_sum

                for x in constraint.scope:
                    domain = self.csp.domains[x.my_tuple]

                    valid_value = {v for v in domain if v <= max_valid}
                    self.csp.domains[x.my_tuple] = valid_value
        
    def forward_checking(self):
        pass
    
    def enforce_arc_consistency(self):
        pass
