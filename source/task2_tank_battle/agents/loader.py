"""Load built-in and partner agents for tank battle matches."""

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


def load_agent(spec: str, rules: GameRules, depth_limit: int = DEFAULT_SEARCH_DEPTH) -> Agent:
    """Load an agent by built-in name or by an external module:factory.

    Built-in factories receive rules and depth_limit. External factories
    receive rules and configure their own search depth.
    """
    factory, built_in = _resolve_factory(spec)
    agent = _build_agent(factory, rules, depth_limit, built_in=built_in)
    return _validate_agent(agent, spec)


def _resolve_factory(spec: str) -> tuple[_AgentFactory, bool]:
    if spec in BUILT_IN_AGENTS:
        return BUILT_IN_AGENTS[spec], True

    module_name, separator, factory_name = spec.partition(":")
    if not separator or not module_name or not factory_name:
        raise ValueError(f"Expected a built-in name or module:factory, got {spec!r}")

    module = import_module(module_name)
    factory = getattr(module, factory_name, None)
    if not callable(factory):
        raise TypeError(f"Agent factory {spec!r} must be callable")
    return factory, False


def _build_agent(
    factory: _AgentFactory, rules: GameRules, depth_limit: int, *, built_in: bool
) -> object:
    if built_in:
        return factory(rules, depth_limit=depth_limit)
    return factory(rules)


def _validate_agent(agent: object, spec: str) -> Agent:
    if not isinstance(agent, Agent) or not callable(agent.choose_action):
        raise TypeError(f"Agent {spec!r} must provide choose_action(state)")
    return agent
