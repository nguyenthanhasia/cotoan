# CoToan

Reference implementation and research environment for Vietnamese Mathematical Chess (Cờ toán Việt Nam).

Release candidate 0.3.0. Configuration family: cotoan-v2.

CoToan provides executable rules, a GDL-I description, an OpenSpiel adapter, reusable fixtures and conformance tests. It is a research software artifact, not an officially certified game standard. This repository is independent of the manuscript and contains no paper sources, paper PDFs or manuscript-build scripts.

## Quick start

Use Python 3.10 or later in a fresh virtual environment. From the repository root:

```bash
python -m pip install -r requirements-validation.txt
python -m tools.validate
python -m tools.representation_audit
python -m tools.agent_smoke
python -m tools.settings_audit
```

To use the environment:

```python
import pyspiel
import cotoan.spiel

game = pyspiel.load_game("python_cotoan(max_plies=300)")
state = game.new_initial_state()
print(len(state.legal_actions()))  # 87
state.apply_action(state.legal_actions()[0])

# First to at least 21 points, otherwise compare scores at ply 300.
race = pyspiel.load_game("python_cotoan(max_plies=300,score_target=21,horizon_rule=score)")
```

Regenerate the default GDL description without installing OpenSpiel:

```bash
python -m tools.generate_gdl --max-plies 300 --output gdl/cotoan.kif
```

Optional generation settings are --score-target, --horizon-rule, --ops-mask and --first-player. Match them to the OpenSpiel game configuration when comparing implementations. The off-turn GDL role plays noop; one joint GDL step is one game ply.

## Repository contents

| Path | Purpose |
| --- | --- |
| cotoan/rules.py | Immutable reference rules and scoring |
| cotoan/spiel.py | OpenSpiel game, state and observer |
| gdl/cotoan.kif | Generated standalone GDL description |
| docs/specification.md | Rules, configuration fields and representation contracts |
| docs/ai-integration.md | Search-agent integration and migration checks |
| tests/ | Unit tests |
| tools/validate.py | Baseline conformance tests |
| tools/representation_audit.py | Action-multiplicity and horizon-aliasing diagnostics |
| tools/settings_audit.py | Scoring and cross-configuration checks |
| tools/agent_smoke.py | OpenSpiel alpha-beta interface check |
| tools/generate_gdl.py | GDL generator |
| tools/gdl_check.py | Emitted GDL-subset evaluator through clingo |
| examples/ | Reproducible fixtures |
| results/ | Recorded test results |

## Rules and settings

Capturing the opposing zero wins regardless of points. Other captures add the captured piece's value to the mover's score. A positive score_target enables immediate victory at or above that threshold. The default horizon_rule=score awards the higher score victory at ply 300; equal scores draw. horizon_rule=draw is an optional experimental alternative. No-move loss before the horizon is a declared environment convention.

All five arithmetic operations are enabled by default. A different operator mask, starter, score target, horizon or horizon rule identifies a different task. The full configuration is included in snapshots and observations. Version 2 has 2183 observation entries and is not wire-compatible with version 1.

## Validation

The recorded checks include 41 unit tests, 600 move-set comparisons, 70 GDL state comparisons, 66 GDL successor comparisons, 90 arithmetic pairs and 20 OpenSpiel simulation tests. A separate audit covers nine configurations, 210 valid state comparisons, 158 selected successors, 32 operator masks, 512 material subsets and 45 additional simulations. Six inconsistent dual-threshold snapshots are rejected.

These checks measure conformance, not playing strength, educational effectiveness or complete game-tree coverage. The GDL evaluator handles the emitted subset through clingo; it is not an independent GGP competition runtime. Small MCTS and alpha-beta calls demonstrate interface usability only.

The diagnostics illustrate why action identity, time and configuration matter. Arithmetic witnesses can duplicate a single board transition. Omitting remaining time can merge states with different terminal continuations. Changing score settings can change the outcome of the same board and ply. The time-awareness diagnostic applies the established principle described by [Pardo et al., ICML 2018](https://proceedings.mlr.press/v80/pardo18a.html).
