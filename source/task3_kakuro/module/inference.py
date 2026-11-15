
import queue
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
    
    def mac(self, curr_var: tuple, curr_value: int, curr_domain: dict):

        new_domains = {}
        for coord, domain in curr_domain.items():
            new_domains[coord] = domain.copy()

        new_domains[curr_var] = {curr_value}

        queue = [curr_var]

        while len(queue) > 0:
            curr_node = queue.pop(0)
            new_relevant = []

            for constraint in self.csp.constraints:
                for v in constraint.scope:
                    coord = v.my_tuple
                    if coord == curr_node:
                        new_relevant.append(constraint)
                        break

            for constraint in new_relevant:
                is_valid, reduced_vars = self.__revise(constraint, new_domains)

                if is_valid == False:
                    return False, {}

                for neighbor in reduced_vars:
                    is_in_queue = False
                    for q in queue:
                        if q == neighbor:
                            is_in_queue = True
                            break

                    if is_in_queue == False:
                        queue.append(neighbor)

        return True, new_domains

    def __revise(self, constraint: Constraint, new_domains: dict):

        reduced_vars = []
        assigned = []
        un_assigned = []

        for v in constraint.scope:
            my_tuple = v.my_tuple

            if len(new_domains[my_tuple]) > 1:
                un_assigned.append(my_tuple)
            elif len(new_domains[my_tuple]) == 1:
                for val in new_domains[my_tuple]:
                    assigned.append(val)

        # TODO: Diff
        if isinstance(constraint, AllDiffConstraint):
            new_assigned = set()

            for val in assigned:
                new_assigned.add(val)

            if len(new_assigned) != len(assigned):
                return False, []

            for coord in un_assigned:
                original_len = len(new_domains[coord])
                valid_val = set()
                for val in new_domains[coord]:
                    is_duplicate = False

                    for a_val in assigned:
                        if val == a_val:
                            is_duplicate = True
                            break

                    if is_duplicate == False:
                        valid_val.add(val)

                new_domains[coord] = valid_val

                if len(new_domains[coord]) == 0:
                    return False, []

                if len(new_domains[coord]) < original_len:
                    reduced_vars.append(coord)

            if len(un_assigned) > 0:
                is_avaliable = set()

                for coord in un_assigned:
                    for val in new_domains[coord]:
                        is_avaliable.add(val)

                if len(un_assigned) > len(is_avaliable):
                    return False, []

        # TODO: Sum
        if isinstance(constraint, SumConstraint):
            sum_min = 0
            sum_max = 0
            
            for v in constraint.scope:
                coord = v.my_tuple
                c_min = 10 
                c_max = 0
                for val in new_domains[coord]:
                    if val < c_min: c_min = val
                    if val > c_max: c_max = val
                sum_min += c_min
                sum_max += c_max

            for v in constraint.scope:
                coord = v.my_tuple
                original_len = len(new_domains[coord])
                
                c_min = 10
                c_max = 0
                for val in new_domains[coord]:
                    if val < c_min: c_min = val
                    if val > c_max: c_max = val
                    
                min_allowed = constraint.target_sum - (sum_max - c_max)
                max_allowed = constraint.target_sum - (sum_min - c_min)
                
                valid_val = set()
                for val in new_domains[coord]:
                    if min_allowed <= val <= max_allowed:
                        valid_val.add(val)
                        
                new_domains[coord] = valid_val
                
                if len(new_domains[coord]) == 0:
                    return False, []
                    
                if len(new_domains[coord]) < original_len:
                    reduced_vars.append(coord)
                    
                    sum_min = 0
                    sum_max = 0
                    for temp_v in constraint.scope:
                        t_coord = temp_v.my_tuple
                        t_min = 10
                        t_max = 0
                        for t_val in new_domains[t_coord]:
                            if t_val < t_min: t_min = t_val
                            if t_val > t_max: t_max = t_val
                        sum_min += t_min
                        sum_max += t_max

        return True, reduced_vars

# TODO: unused
def forward_checking(self, curr_var: tuple, curr_value: int, curr_domain: dict):

        new_domains = {}
        new_constraint = []

        for coord, domain in curr_domain.items():
            new_domains[coord] = domain.copy()
        new_domains[curr_var] = {curr_value}

        for constraint in self.csp.constraints:
            for v in constraint.scope:
                coord = v.my_tuple
                if coord == curr_var:
                    new_constraint.append(constraint)
                    break

        for constraint in new_constraint:
            assigned = []
            un_assigned = []

            for v in constraint.scope:
                tuple = v.my_tuple

                if len(new_domains[tuple]) > 1:
                    un_assigned.append(tuple)
                elif len(new_domains[tuple]) == 1:
                    for val in new_domains[tuple]:
                        assigned.append(val)


            # TODO: Alldiff
            if isinstance(constraint, AllDiffConstraint):
                new_assigned = set()
                for v in assigned:
                    new_assigned.add(v)

                if len(new_assigned) != len(assigned):
                    return False, {}

                for coord in un_assigned:
                    if curr_value in new_domains[coord]:
                        new_domains[coord].remove(curr_value)

                    if len(new_domains[coord]) == 0:
                        return False, {}
            # TODO: Sum
            if isinstance(constraint, SumConstraint):
                curr_sum = 0
                for v in assigned:
                    curr_sum += v

                if curr_sum > constraint.target_sum:
                    return False, {}

                if len(un_assigned) == 0 and curr_sum != constraint.target_sum:
                    return False, {}

                if len(un_assigned) > 0:
                    remain_sum = constraint.target_sum - curr_sum
                    n = len(un_assigned)
                    min_sum = int((n * (n - 1)) / 2)
                    max_bound = remain_sum - min_sum

                    if max_bound <= 0:
                        return False, {}

                    for v in un_assigned:
                        valid = set()
                        for val in new_domains[v]:
                            if (val <= max_bound):
                                valid.add(val)

                        new_domains[v] = valid

                        if len(new_domains[v]) == 0:
                            return False, {}
        return True, new_domains