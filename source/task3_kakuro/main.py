import config
from utils.parser import Parse

def test():

    parser = Parse(config.MAP_3000)

    csp_problem = parser.execute()

    print(f"Variable: {len(csp_problem.variables)}\n\n")

    x_coords = [var.my_tuple for var in csp_problem.variables]
    print(f"\n Location: {x_coords}\n\n")

    # print(f"\n Domains: {csp_problem.domains}\n\n")

    for coord, domain in csp_problem.domains.items():
        print(f" In {coord}: {domain}\n\n")

    for i, constraint in enumerate(csp_problem.constraints):
        scope_coord = [var.my_tuple for var in constraint.scope]

        if hasattr(constraint, 'target_sum'):
            print(f"    {i+1}. SumConstraint(Target: {constraint.target_sum}) : {scope_coord}")
        else:
            print(f"    {i+1}. AllDiffConstraint : {scope_coord}")

        print("\n\n")

if __name__ == "__main__":
    test()