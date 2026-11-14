from collections.abc import Callable
from importlib import import_module

from ..config import (
    ALPHA_BETA_AGENT,
    DEFAULT_SEARCH_DEPTH,
    HEURISTIC_AGENT,
    HEURISTIC_ALPHA_BETA_AGENT,
    MINIMAX_AGENT,
)
from ..game.rules import GameRules
from .search import (
    Agent,
    create_alpha_beta_agent,
    create_heuristic_minimax_agent,
    create_heuristic_minimax_alpha_beta_agent,
    create_minimax_agent,
)


_AgentFactory = Callable[..., object]

BUILT_IN_AGENTS = {
    MINIMAX_AGENT: create_minimax_agent,
    ALPHA_BETA_AGENT: create_alpha_beta_agent,
    HEURISTIC_AGENT: create_heuristic_minimax_agent,
    HEURISTIC_ALPHA_BETA_AGENT: create_heuristic_minimax_alpha_beta_agent,
}


def load_agent(
    spec: str, rules: GameRules, depth_limit: int | None = DEFAULT_SEARCH_DEPTH
) -> Agent:
    factory = _resolve_factory(spec)
    if spec in BUILT_IN_AGENTS:
        agent = factory(rules, depth_limit=depth_limit)
    else:
        agent = factory(rules)
    return _validate_agent(agent, spec)


def _resolve_factory(spec: str) -> _AgentFactory:
    if spec in BUILT_IN_AGENTS:
        return BUILT_IN_AGENTS[spec]

    module_name, separator, factory_name = spec.partition(":")
    if not separator or not module_name or not factory_name:
        raise ValueError(f"Expected a built-in name or module:factory, got {spec!r}")

    module = import_module(module_name)
    factory = getattr(module, factory_name, None)
    if not callable(factory):
        raise TypeError(f"Agent factory {spec!r} must be callable")
    return factory


def _validate_agent(agent: object, spec: str) -> Agent:
    if not isinstance(agent, Agent) or not callable(agent.choose_action):
        raise TypeError(f"Agent {spec!r} must provide choose_action(state)")
    return agent
