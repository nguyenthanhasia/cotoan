# Agent integration contract

CoToan specifies configurable research tasks, not a game-playing algorithm. GDL-I describes the rules; OpenSpiel lets an algorithm interact with the same configured game. Search need not evaluate GDL facts at every node.

## Two integration routes

An OpenSpiel-native agent obtains `legal_actions()`, expands `child(action)` or a `clone()` followed by `apply_action(action)`, checks `is_terminal()`, and obtains `returns()`. The public adapter exposes the board through its immutable `position` for domain-specific evaluation. This direct Python attribute is an adapter-specific convenience, not part of the generic OpenSpiel API.

An optimized external engine may retain its own board representation, move generator and search code. To claim conformance, it must map its states and actions to the profile and pass checks for legal action sets, successor states, terminal outcomes and serialization. Merely translating coordinate notation does not establish rule equivalence.

| Component | Contract to preserve |
| --- | --- |
| Board | Nine files, eleven ranks; square index `9*(rank-1)+file`, files zero-based |
| Piece identity | Distinguish side and value; never conflate empty with a zero piece |
| Turn | Player 0 is Red; player 1 is Blue |
| Action | One source/destination pair, ID `99*source+destination` |
| Arithmetic | Same guards, floor-division policy, distance offset and path blocking |
| Witnesses | Multiple valid operators explain one endpoint action; they are not extra actions |
| Score | Sum of captured opposing values; derive as 45 minus opposing remaining material |
| Termination | Zero capture, threshold victory, configured horizon outcome, then no-move loss before the limit |
| Settings | Preserve all five Config fields in task identity, serialized states and pooled observations |
| Evaluation | State whose player perspective the score uses; terminal utility must agree |
| State cache | Retain task identity and time information; a board-and-turn-only key is insufficient |
| Learned policy | Map input features, legal masks and output action IDs; weights do not transfer automatically |

## Existing checks

`tools.validate` exercises OpenSpiel MCTS with eight simulations and a fixed random seed of 7. `tools.agent_smoke` exercises OpenSpiel's existing alpha-beta search to depth two with a simple Red-perspective material heuristic and horizon 12. Both select a legal action without requiring a new game-playing algorithm. The alpha-beta result is recorded in `results/agent-smoke.json`.

These checks demonstrate interface usability. They do not demonstrate playing strength, compatibility with an unspecified engine, equivalence of different rule variants, or preservation of an existing agent's decisions.

## Migration acceptance tests

1. Fix version 2, enabled operations, score target, horizon, horizon rule, starter and adjudication order.
2. Verify board and piece mappings through round trips, including both zeros.
3. Compare full legal action sets on the public fixtures and new edge cases.
4. Compare every selected action's successor and outcome, not just the chosen move.
5. Include the same board and turn at different budgets, and the same board/turn/ply under different scoring settings.
6. For a behavior-preserving port, fix move ordering, tie breaking, random seeds, evaluation perspective and search budget; only then compare decisions.
7. Report runtime and playing strength separately from rule conformance.

Score thresholds and score-based horizon victory are supported settings, not grounds for inventing a separate game. Another division rule, repetition, clocks or an unbounded-duration task still requires an explicit extension. A wrapper cannot silently erase such differences. Version 2 changes the observation length from 2179 to 2183 and rejects version-1 snapshots; a learned policy must be adapted deliberately.

The game horizon is distinct from search depth. At a search cutoff, use a heuristic; at the game limit, use the configured terminal score comparison or draw. A training-only truncation is not interchangeable with either. See [Pardo et al., ICML 2018](https://proceedings.mlr.press/v80/pardo18a.html).

## Search-port pitfalls

- A clone must preserve the observable state and its legal actions. A partial board copy with missing derived data does not satisfy that contract.
- A two-sided mobility or threat heuristic should derive features for both players. The current player's legal-action cache is not a complete two-sided feature representation.
- Count endpoint actions or arithmetic witnesses deliberately. They give different feature values; deduplicating the action list does not automatically deduplicate a separate attack-feature cache.
- Return a legal action even when every searched child has the same worst score. A null best-move sentinel must not be confused with a state that has no legal actions.
- Handle draws explicitly. A binary win/otherwise-loss branch does not implement this profile's three-valued terminal utility.
- Fix move ordering, tie breaking and the lifetime of history heuristics for decision comparisons. A move-ordering history table is not a state-value transposition table.

Changing a heuristic or correcting one of these behaviors creates a revised agent. Rule conformance and behavioral preservation are separate claims.

The generic interface is documented in the [OpenSpiel API reference](https://openspiel.readthedocs.io/en/latest/api_reference.html).
