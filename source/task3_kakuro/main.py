from time import perf_counter

from task3_kakuro import config
from task3_kakuro.module.inference import Inference
from task3_kakuro.module.solver import CSPSolver
from task3_kakuro.utils.parser import Parse


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

        if hasattr(constraint, "target_sum"):
            print(f"    {i + 1}. SumConstraint(Target: {constraint.target_sum}) : {scope_coord}")
        else:
            print(f"    {i + 1}. AllDiffConstraint : {scope_coord}")

        print("\n\n")


def run():
    parser = Parse(config.MAP_3001)
    csp_problem = parser.execute()
    solver = CSPSolver(csp_problem, Inference(csp_problem))
    start_time = perf_counter()
    solution = solver.solve()
    solve_time_ms = (perf_counter() - start_time) * 1000
    assign_count = sum(
        action == "ASSIGN" for _, _, action in solver.history
    )
    remove_count = sum(
        action == "REMOVE" for _, _, action in solver.history
    )

    print(f"History events: {len(solver.history)}")
    print(f"ASSIGN: {assign_count}")
    print(f"REMOVE: {remove_count}")
    if solution is None:
        print(f"The Kakuro puzzle has no solution. Solve time: {solve_time_ms:.2f} ms")
        return

    print(
        f"Solution found in {solve_time_ms:.2f} ms. "
        "Opening solver history viewer."
    )

    from task3_kakuro.gui.app import run_history_viewer

    run_history_viewer(
        parser.grid,
        solver.history,
        solve_time_ms=solve_time_ms,
    )


if __name__ == "__main__":
    run()
