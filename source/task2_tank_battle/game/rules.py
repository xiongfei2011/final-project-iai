from ..config import BULLET_STEPS_PER_TURN
from .actions import MOVE_ACTIONS, Action
from .entities import Bullet, Damageable, Position
from .state import BulletFlight, GameState


class GameRules:

    def actions(self, state: GameState, player: int | None = None) -> list[str]:
        if self.terminal_test(state):
            return []

        if player is None:
            player = state.current_turn
        board = state.game_map
        position = state.tanks[player].position
        legal_actions = []
        if not any(bullet.owner == player and bullet.steps_left > 0 for bullet in state.bullets):
            legal_actions.append(Action.FIRE.value)
        legal_actions.append(Action.STAY.value)

        for action in MOVE_ACTIONS:
            direction = action.direction
            if direction is not None and board.in_bounds(position.moved(direction)):
                legal_actions.append(action.value)

        return legal_actions

    def terminal_test(self, state: GameState) -> bool:
        return any(entity.is_destroyed for entity in (*state.tanks.values(), *state.bases.values()))

    def utility(self, state: GameState, player: int) -> int:
        opponent = 1 - player
        player_lost = (
            state.tanks[player].is_destroyed or state.bases[player].is_destroyed
        )
        opponent_lost = (
            state.tanks[opponent].is_destroyed or state.bases[opponent].is_destroyed
        )
        if player_lost and opponent_lost:
            return 0
        return -1 if player_lost else 1

    def result(self, state: GameState, action: str) -> GameState:
        next_state = self.result_tick(state, {state.current_turn: action})
        if not self.terminal_test(next_state):
            next_state.current_turn = 1 - state.current_turn
        return next_state

    def result_tick(self, state: GameState, actions: dict[int, str]) -> GameState:
        """Resolve moves and turns on the same board before advancing bullets."""
        commands = {}
        destinations = {}
        board = state.game_map
        occupied = {
            entity.position
            for entity in (*state.tanks.values(), *state.bases.values())
        }

        for player, action in actions.items():
            if player not in state.tanks or action not in self.actions(state, player):
                raise ValueError(f"Invalid action for player {player}: {action}")
            command = Action(action)
            commands[player] = command
            direction = command.direction
            if direction is not None:
                target = state.tanks[player].position.moved(direction)
                if target not in occupied and board.wall_at(target) is None:
                    destinations[player] = target

        next_state = state.clone()
        next_state.bullet_flights = ()
        contested = len(destinations) == 2 and len(set(destinations.values())) == 1

        for player in sorted(commands):
            if not (contested and player in destinations):
                self._apply_action(
                    next_state, player, commands[player], destinations.get(player)
                )

        if not self.terminal_test(next_state) and next_state.bullets:
            self._advance_bullets(next_state)

        return next_state

    def _apply_action(
        self,
        state: GameState,
        player: int,
        action: Action,
        destination: Position | None,
    ) -> None:
        tank = state.tanks[player]
        direction = action.direction

        if direction is not None:
            tank.direction = direction
            if destination is not None:
                tank.position = destination
        elif action is Action.FIRE:
            bullet = Bullet(position=tank.position, direction=tank.direction, owner=player)
            state.bullets.append(bullet)

    def _advance_bullets(self, state: GameState) -> None:
        board = state.game_map
        targets: dict[Position, Damageable] = {
            entity.position: entity
            for entity in (*state.tanks.values(), *state.bases.values())
        }
        active = [(bullet.position, bullet) for bullet in state.bullets if bullet.steps_left > 0]
        flights: list[BulletFlight] = []

        for _ in range(BULLET_STEPS_PER_TURN):
            if not active:
                break
            hits: list[Damageable] = []
            moving = []
            for start, bullet in active:
                target = bullet.next_position()
                if not board.in_bounds(target):
                    flights.append(BulletFlight(start, bullet.position, bullet.owner))
                    continue

                bullet.position = target
                bullet.steps_left -= 1
                hit = board.wall_at(target) or targets.get(target)
                if hit is not None:
                    hits.append(hit)
                elif bullet.steps_left > 0:
                    moving.append((start, bullet))
                    continue
                flights.append(BulletFlight(start, target, bullet.owner))

            # Apply hits at the same distance step together before checking the result.
            for hit in hits:
                hit.take_hit()
            active = moving
            if self.terminal_test(state):
                flights.extend(BulletFlight(start, bullet.position, bullet.owner)
                               for start, bullet in active)
                active = []
                break

        flights.extend(BulletFlight(start, bullet.position, bullet.owner) for start, bullet in active)
        state.bullets = [bullet for _, bullet in active]
        state.bullet_flights = tuple(flights)
