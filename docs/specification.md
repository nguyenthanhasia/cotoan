# Executable specification: cotoan-v2

Artifact release candidate 0.3.0. These are the normative rules for the supported configurations of Vietnamese Mathematical Chess. GDL-I is the declarative representation and OpenSpiel the agent interface. This specification does not claim federation certification or cover every tournament variant. Historical citations establish attribution, not the operational equations below.

## 1. Board, identities and initial state

Files are a through i and ranks 1 through 11. The square index is q=9*(rank-1)+(file-a), from 0 to 98. Coordinates do not wrap. Directions are the eight horizontal, vertical and diagonal unit vectors.

Each player has one piece of each value 0 through 9. Red values 1 through 9 start on a1 through i1; Blue values 9 through 1 start on a11 through i11. Red zero is fixed on e2 and Blue zero on e10. Red starts by default; the starting player is configurable. A zero cannot move but can support a capture or be captured. There is no check, checkmate, castling, promotion or compulsory capture.

In Python/JSON, empty is 0, Red value v is +(v+1), and Blue value v is -(v+1). Zero pieces are distinct from empty cells. Dynamic state consists of (board, turn, ply), interpreted under an immutable configuration.

## 2. Movement and arithmetic capture

A nonzero attacker of value a at s may move to s+L*d in one of eight directions for 1 <= L <= a. Every traversed square, including the destination, must be empty. Ordinary movement cannot capture.

An arithmetic capture needs adjacent friendly support of value b at s+d, an enemy target at s+L*d, and empty squares s+k*d for 2 <= k < L. Here L>1. The attacker replaces the target; the support remains. At least one enabled operation must supply the distance:

| Operation | Distance L from attacker | Guard | Mask bit |
| --- | --- | --- | --- |
| add | ((a+b) mod 10)+1 | Always | 1 |
| sub | a-b+1 | a>b | 2 |
| mul | ((a*b) mod 10)+1 | Always | 4 |
| div | floor(a/b)+1 | a>b>0 | 8 |
| mod | (a mod b)+1 | a>b>0 | 16 |

Discard L=1, since the adjacent square contains the support. Division is floored, not restricted to exact divisibility. The target's value is not an operand. Operator identity explains legality but is not a player action: multiple witnesses for the same source/destination pair produce one action.

For example, Red 2 at c4 with Red 1 at d4 can capture an enemy at f4 using multiplication, provided e4 is empty. Red 1 stays on d4. Red zero at e2 can support Red 2 at d2 in capturing g2 using addition or subtraction if f2 is empty.

## 3. Scores and settings

Scores start at zero. Capturing an opposing nonzero value v increases the mover's score by v. Zero capture wins independently of points. Player i's score is C_i = 45 - sum(values of surviving opponent pieces).

This equals cumulative captured value because identities are unique, the initial sum is 45, and there is no promotion, creation or return of captured pieces. Scores are derived from occupancy, not independently stored counters. A synthetic board missing pieces is interpreted as if those values have been captured; this does not certify reachability.

| Setting | Allowed values | Default | Meaning |
| --- | --- | --- | --- |
| max_plies | Integer 1..10000 | 300 | Finite playing limit H, in individual moves |
| score_target | Integer 0..45 | 0 | Positive T enables immediate victory at score >= T; zero disables it |
| horizon_rule | score or draw | score | At H, higher score wins with ties drawn, or unconditional draw |
| ops_mask | Integer 0..31 | 31 | Bitwise OR of enabled operations; 0 means quiet moves only |
| first_player | 0 or 1 | 0 | Red or Blue starts |

| Configuration | Settings differing from defaults | Outcome rules |
| --- | --- | --- |
| Score at 300 | None | Zero capture wins; otherwise compare scores at ply 300 |
| Race to 21, bounded | score_target=21 | First player reaching at least 21 wins; otherwise compare at 300 |
| Draw-capped experiment | horizon_rule=draw | Zero capture wins; otherwise draw at 300 |

Target 21 is illustrative, not a mandatory threshold. Unconditional horizon draw is an experimental alternative, not the default. All implemented tasks have finite H; a threshold-only game of unbounded duration is not modeled. AI difficulty/search depth is an agent setting, not a rule parameter.

## 4. Adjudication and state validity

Evaluate in this order after a move and when importing a snapshot:

1. If a zero is absent, its opponent wins, regardless of score.
2. With both zeros present and T>0, a player at or above T wins immediately.
3. At H, apply horizon_rule: compare scores or draw unconditionally.
4. Before H, a player to move without a geometrical action loses.

Equal points under score adjudication yield a draw. Zero/threshold victory takes priority on the final ply. No-move loss is a declared research-environment convention; it does not override score adjudication at H. Terminal states have no actions and returns are win +1, draw 0, loss -1. There are no clocks or repetition rules.

Require unique identities, correct surviving zero anchors, at least one zero present, turn in {0,1}, and ply in 0..H. With both zeros present and T>0, a snapshot in which both players already meet T is inconsistent with first-threshold termination and is rejected. Zero capture takes priority even in a constructed snapshot. Structural validity is not a reachability proof.

Every task has a canonical identifier such as cotoan-v2-h300-t21-score-o31-f0. Configuration is immutable during a game; changing it creates another task. Imported moves from another configuration must be revalidated.

## 5. GDL/OpenSpiel representation contract

| Concept | GDL-I | OpenSpiel |
| --- | --- | --- |
| Players | role red, role blue | 0, 1 |
| Initial state | init facts | new_initial_state() |
| Board | (true (cell sQ red V)) | Signed 99-cell tuple |
| Controller and ply | control and ply facts | position.turn, position.ply |
| Move | (move sSRC sDST) | 99*SRC+DST |
| Off-turn role | Sole action noop | No off-turn action submitted |
| Rules/settings | Generated static facts and clauses | Immutable Config |
| Score | Derived score facts | scores(position) |
| Legality | legal | legal_actions(), action mask |
| Successor | does joint action and next | child(), apply_action() |
| End/utility | terminal, goals 0/50/100 | is_terminal(), returns -1/0/1 |

One GDL joint action pairs the controller's move with the other role's noop; this is one ply, not two. Utility conversion is u=2*goal/100-1. The ambient policy space has 9801 IDs, with illegal entries masked.

GDL geometry and arithmetic tables are finite ordinary facts. Scores use a nine-stage fold over missing opposing values and a finite addition table. There is no engine-specific arithmetic evaluator. The score fold is positive recursion over a finite stage domain; negation is stratified. Candidate movement is independent of terminal status, avoiding a legal/terminal dependency cycle.

PGN/FEN are chess record formats, not definitions of this game's rules. GDL-I is an established research language, not an ISO standard; OpenSpiel is an API, not an official rulebook. RBG and Ludii are relevant alternatives but not implemented adapters.

## 6. Observation and serialization

The version-2 observation has 2183 float32 entries:

1. Twenty binary 11-by-9 identity planes, Red 0..9 then Blue 0..9.
2. One controller plane and one remaining-budget plane H-ply.
3. Five scalars: H, score_target, int(horizon_rule == 'score'), ops_mask, first_player.

The layout is absolute-color. All supported integers are exactly representable. Scores are recoverable from identity planes. For a fixed-task agent, settings may be implicit. They are explicit here for shared policies, datasets and state caches. The starter is included for complete task identity, even though it is not needed to advance a later state. This representation is sufficient, not necessarily minimal.

Snapshots use format cotoan-spiel-state-v2 and contain exactly format, config and position. Config contains all five setting fields; position contains board, turn and ply. Deserialization rejects configuration mismatches, old-format payloads and inconsistent positions. Snapshots are not complete game records; OpenSpiel game-and-state serialization preserves framework history.

Version 2 changes the default horizon result from unconditional draw to score comparison, changes horizon/no-move precedence, adds thresholds and operation settings, and changes observation size from 2179 to 2183. It is not wire-compatible with version 1. The draw setting alone does not reproduce every v1 adjudication detail. Old results must retain old task identifiers. Passing an integer horizon to the Python rule functions is shorthand for a v2 Config, not a legacy-v1 request.

## 7. Conformance and scope

Transitions preserve bounds, piece uniqueness and surviving zero anchors; they toggle the controller and increment ply once. Quiet movement preserves material and scores. Capture removes one opponent piece and increases the mover's points by its value, including a zero increment for zero capture. Rotation plus color swap preserves local rules and swaps scores and utilities; comparing initial arrangements also requires swapping the starter.

The suite includes unit tests, independent move predicates, cross-representation states and successors, 32 operator masks, 512 material subsets, configuration-conditioned observations and serialization rejection. The evaluator executes the emitted GDL subset through clingo; it is not an independent GGP competition runtime or mechanized proof. Such integration checks remain future work, not prerequisites to defining the rules used here.
