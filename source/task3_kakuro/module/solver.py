from core.csp_core import CSP
from core.variable import Variable
from module.inference import Inference


class CSPSolver:
    def __init__(self, csp: CSP, inference: Inference):
        self.csp = csp
        self.inference = inference

        self.conflict_sets = {}
        for variable in self.csp.variables:
            self.conflict_sets[variable.my_tuple] = set()

        self.history = []

    def solve(self):
        self.inference.enforce_node_consistency()

        initial_domains = {
            coord: domain.copy()
            for coord, domain in self.csp.domains.items()
        }
        self.history.clear()

        result, _ = self.backtrack(initial_domains, [])
        return result

    def backtrack(self, current_domains: dict, assigned_order: list):
        for domain in current_domains.values():
            if len(domain) == 0:
                return None, None

        if all(len(domain) == 1 for domain in current_domains.values()):
            return current_domains, None

        curr_var = self.select_unassigned_variable(current_domains)
        if curr_var is None:
            return None, None

        self.conflict_sets[curr_var] = set()
        ordered_values = self.order_domain_values(curr_var, current_domains)

        if len(ordered_values) == 0:
            self.update_conflict_set(curr_var, assigned_order)
            conflict_set = self.conflict_sets[curr_var]
            jump_target = (
                self.get_most_recent_conflict(curr_var, assigned_order)
                if conflict_set
                else None
            )
            if jump_target is not None:
                self.conflict_sets[jump_target].update(conflict_set)
                self.conflict_sets[jump_target].discard(jump_target)
            return None, jump_target

        for val in ordered_values:
            self.history.append((curr_var, val, "ASSIGN"))
            assigned_order.append(curr_var)

            is_valid, new_domains = self.inference.mac(
                curr_var,
                val,
                current_domains,
            )

            if is_valid:
                inferred_assignments = []
                for coord, domain in new_domains.items():
                    if (
                        coord != curr_var
                        and len(current_domains[coord]) > 1
                        and len(domain) == 1
                    ):
                        inferred_value = next(iter(domain))
                        inferred_assignments.append((coord, inferred_value))
                        self.history.append((coord, inferred_value, "ASSIGN"))

                result, jump_var = self.backtrack(new_domains, assigned_order)

                if result is not None:
                    return result, None

                if jump_var is not None and jump_var != curr_var:
                    for coord, inferred_value in reversed(inferred_assignments):
                        self.history.append((coord, inferred_value, "REMOVE"))
                    self.history.append((curr_var, val, "REMOVE"))
                    assigned_order.pop()
                    return None, jump_var
            else:
                self.update_conflict_set(curr_var, assigned_order)

            if is_valid:
                for coord, inferred_value in reversed(inferred_assignments):
                    self.history.append((coord, inferred_value, "REMOVE"))

            self.history.append((curr_var, val, "REMOVE"))
            assigned_order.pop()

        conflict_set = self.conflict_sets[curr_var]
        jump_target = (
            self.get_most_recent_conflict(curr_var, assigned_order)
            if conflict_set
            else None
        )
        if jump_target is not None:
            self.conflict_sets[jump_target].update(conflict_set)
            self.conflict_sets[jump_target].discard(jump_target)

        return None, jump_target

    def select_unassigned_variable(self, current_domains: dict):
        unassigned_vars = [
            coord
            for coord, domain in current_domains.items()
            if len(domain) > 1
        ]

        if not unassigned_vars:
            return None

        min_len = min(len(current_domains[coord]) for coord in unassigned_vars)
        mrv_candidates = [
            coord
            for coord in unassigned_vars
            if len(current_domains[coord]) == min_len
        ]

        if len(mrv_candidates) == 1:
            return mrv_candidates[0]

        max_degree = -1
        best_var = None

        for coord in mrv_candidates:
            degree = 0
            for constraint in self.csp.constraints:
                if any(var.my_tuple == coord for var in constraint.scope):
                    degree += sum(
                        1
                        for var in constraint.scope
                        if var.my_tuple != coord
                        and len(current_domains[var.my_tuple]) > 1
                    )

            if degree > max_degree:
                max_degree = degree
                best_var = coord

        return best_var

    def order_domain_values(self, curr_var: tuple, current_domains: dict):
        candidates = []

        for val in current_domains[curr_var]:
            is_valid, temp_domains = self.inference.forward_checking(
                curr_var,
                val,
                current_domains,
            )
            if is_valid:
                score = sum(len(domain) for domain in temp_domains.values())
                candidates.append((score, val))

        candidates.sort(reverse=True, key=lambda candidate: candidate[0])
        return [candidate[1] for candidate in candidates]

    def update_conflict_set(self, curr_var: tuple, assigned_order: list):
        for constraint in self.csp.constraints:
            if any(var.my_tuple == curr_var for var in constraint.scope):
                for var in constraint.scope:
                    neighbor = var.my_tuple
                    if neighbor != curr_var and neighbor in assigned_order:
                        self.conflict_sets[curr_var].add(neighbor)

    def get_most_recent_conflict(self, curr_var: tuple, assigned_order: list):
        conflict_set = self.conflict_sets[curr_var]

        if not conflict_set:
            return assigned_order[-1] if assigned_order else None

        for past_var in reversed(assigned_order):
            if past_var in conflict_set:
                return past_var

        return None
