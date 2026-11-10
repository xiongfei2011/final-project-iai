class SearchAgent:

    def __init__(self, rules, depth_limit, use_alpha_beta):
        self.rules = rules
        self.depth_limit = depth_limit
        self.use_alpha_beta = use_alpha_beta

    def _value(self, state, max_player):
        if self.rules.terminal_test(state):
            return self.rules.utility(state, max_player)

        is_max_turn = state.current_turn == max_player # Nếu node gốc là 1 current_turn là 0 thì đang ở MIN và ngược lại
        best_score = float("-inf") if is_max_turn else float("inf")

        for action in self.rules.actions(state):
            child_state = self.rules.result(state, action)
            child_score = self._value(child_state, max_player)

            if is_max_turn:
                best_score = max(best_score, child_score)
            else:
                best_score = min(best_score, child_score)

        return best_score

    def search(self, state):
        max_player = state.current_turn
        best_action = None
        best_score = float("-inf")

        for action in self.rules.actions(state):
            child_state = self.rules.result(state, action)
            score = self._value(child_state, max_player)
            if score > best_score:
                best_action = action
                best_score = score

        return best_action, best_score
    


def create_minimax_agent(rules):
    return SearchAgent(rules=rules, depth_limit=None, use_alpha_beta=False)

def create_alpha_beta_agent(rules):
    return SearchAgent(rules=rules, depth_limit=None, use_alpha_beta=True)

def create_heuristic_minimax_agent(rules, depth_limit = 3):
    return SearchAgent(rules=rules, depth_limit=depth_limit, use_alpha_beta=False)

def create_heuristic_minimax_alpha_beta_agent(rules, depth_limit=3):
    return SearchAgent(rules=rules, depth_limit=depth_limit, use_alpha_beta=True)