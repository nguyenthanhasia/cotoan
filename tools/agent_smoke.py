"""Exercise an existing OpenSpiel search routine; not a strength benchmark.

Run from the repository root: python -m tools.agent_smoke
"""
import json
from pathlib import Path
import pyspiel
import cotoan.spiel
from cotoan import rules
from open_spiel.python.algorithms import minimax


def material(state):
    """Bounded Red-perspective nonterminal material heuristic."""
    return sum((1 if piece > 0 else -1) * (abs(piece) - 1)
               for piece in state.position.board if piece) / 45


def main():
    game = pyspiel.load_game('python_cotoan(max_plies=12)')
    root = game.new_initial_state()
    value, action = minimax.alpha_beta_search(
        game, root, value_function=material,
        maximum_depth=2, maximizing_player_id=0)
    assert action in root.legal_actions()
    assert root.position == rules.initial()
    result = {
        'status': 'passed', 'algorithm': 'OpenSpiel alpha_beta_search',
        'open_spiel': pyspiel.__version__, 'depth': 2, 'horizon': 12,
        'config': game.config.to_dict(), 'profile': game.config.identifier,
        'evaluation': 'Red-perspective signed material divided by 45',
        'value': value, 'action_id': action,
        'action': root.action_to_string(action),
        'legal': True, 'root_unchanged': True,
        'scope': 'interface diagnostic; not an existing-agent port or strength experiment'
    }
    Path('results/agent-smoke.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
