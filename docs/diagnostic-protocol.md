# Frozen diagnostic and public-adapter protocols

## Semantic diagnostics

The 64-case diagnostic input set was frozen on 2026-09-14 before its first
campaign execution. The seed is 1729. Every case is admitted, refuted, or
abstained without retry-based tuning. Each admitted case is compared with an
independent all-rational-values coefficient oracle at `n0=1` and `n0=2`.
Every SMT refutation and every reconstructed at-most-two-cell certificate is
replayed. The bounded oracle is not an all-shapes decision.

The equal-kernel diagnostic exhaustively checks all 729 ordered pairs of
three-coordinate rows in `{-1,0,1}^3` on all 27 vectors in the same set. The
19,683 direct integer evaluations test the implementation of the rational
criterion; they are not a proof over arbitrary rational rows.

## Public source adapters

The twelve-row denominator and development/later split were frozen before final
adapter evaluation on 2026-09-15. The executable public study uses seed 20260915
and exactly 64 input executions per adapter for each of three mutant-selection
policies. Five mutants are retained per admitted adapter. Decisions and
abstentions are never altered by rerunning the bounded model.

The development-example policy repeats a short hand-written suite; seeded random
and deterministic boundary-stratified selection receive the same execution
budget. The universal source proofs are reported separately and are not counted
as a zero-cost or equal-budget testing method. Mutants are synthetic negative
controls, not historical Scorch defects.

## Resource and retention rules

Use one worker and no child workers inside a case. Each reproduction child has a
2 GiB address-space limit, 105/110 CPU-second soft/hard limits, and a 115-second
wall timeout. SMT queries use 1,500 ms. Retain exact inputs, rejected controls,
raw decisions, replay outcomes, public abstentions, and per-process measurements.
After any implementation repair, rerun the complete five-phase workflow from a
clean extraction. Do not tune generated inputs or source adapters against the
later public segment.
