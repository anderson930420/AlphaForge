# Proposal: formalize-candidate-validation-and-evidence-contracts

## Boundary problem

- The repo already has `validate-search` and `walk-forward`, but the post-search evidence contract is still implicit in the validation and aggregation code.
- `ValidationResult` and `WalkForwardResult` expose domain facts and persisted refs, but they do not yet carry a canonical candidate-evidence summary or a verdict/status vocabulary.
- Train/test degradation is currently calculable from the metrics, but the names and stable fields are not frozen as a contract.
- Walk-forward aggregation already computes fold-level metrics and benchmark summaries, but the relationship between fold evidence and aggregate evidence is not explicit.
- CLI output currently serializes validation and walk-forward results directly, so any evidence semantics need to be owned upstream instead of inferred in presentation code.

## Canonical ownership decision

- `src/alphaforge/experiment_runner.py` remains the owner of validation and walk-forward orchestration and becomes the assembler of evidence summaries from authoritative inputs.
- `src/alphaforge/schemas.py` owns the runtime shape of candidate-evidence and walk-forward-evidence summaries.
- `src/alphaforge/storage.py` owns serialization of those summaries into persisted validation and walk-forward JSON artifacts.
- `src/alphaforge.cli.py` remains presentation-only and must not infer verdicts or degradation semantics locally.
- `src/alphaforge.report.py` remains downstream of the evidence contract and must not invent its own validation status rules.

## Scope

- Define a canonical candidate-evidence summary for validation flows and fold-level walk-forward evidence.
- Define explicit degradation field names for train/test comparison:
  - return degradation
  - Sharpe degradation
  - max-drawdown delta
- Define a walk-forward aggregate evidence summary and its relationship to fold-level evidence.
- Define a small verdict/status vocabulary for evidence summaries.
- Update validation and walk-forward output contracts, storage serialization, and CLI-facing JSON output to surface the new evidence summaries.

## Out of scope

- Genetic algorithms
- Random search
- New strategy families
- Multi-asset research
- A general workflow engine or research database

## Acceptance conditions

- Validation results expose a stable candidate-evidence summary with verdict and degradation fields.
- Walk-forward fold results expose fold-level candidate-evidence summaries.
- Walk-forward results expose a stable aggregate evidence summary derived from fold evidence and aggregate metrics.
- Verdict semantics are explicit and deterministic for the current flows.
- Tests lock the serialized validation and walk-forward evidence shape.
