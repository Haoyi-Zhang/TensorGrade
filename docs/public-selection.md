# Frozen public-commit selection and split

Recorded final protocol: 2026-09-15.

## Repository and denominator

The public study uses `bobbyyyan/scorch`, the compiler-based sparse tensor
framework connected to the motivating TensorBench line of work. The fixed
denominator is the twelve-row chronological sequence in
`data/public-corpus.csv`, beginning with commit `72c55d36...`. Each selected
record is a non-merge commit that changes production compiler, format, dispatch,
or kernel source.

Intervening commits are excluded only when their changes are documentation-only,
benchmark-only, or test-only. Inclusion is decided from changed production-file
scope, not from whether an adapter succeeds. Every selected unsupported commit
remains in the denominator as an abstention.

The first four rows are the development segment used to establish the adapter
templates. The following eight rows are the later retrospective segment. The CSV
field remains `held-out` for stable result compatibility, but repository scouting
preceded the split; it is not preregistered, blind, or a statistical test sample.
No later record was moved into development after its decision, and no adapter
category was added solely to rescue one later record.

## Admission gates

A record is admitted only when all of the following are documented:

1. immutable commit identifier and complete changed production-file list;
2. runtime/non-runtime disposition of every changed production statement;
3. explicit source-state invariant;
4. before/after denotations and an observable that captures all changed behavior
   reaching the claimed execution;
5. a universal equality proof over the invariant;
6. independently coded bounded before/after models and discriminating mutants;
7. an unchanged-downstream congruence argument to the paper's five tensor
   observations.

A failed gate produces an abstention, not a claim that the upstream commit is
incorrect. Intentional feature fixes are generally not regression-equivalence
questions. Physical sparse storage, object identity/exception timing, allocation
and ownership, heuristic scheduling, floating point, raw memory, threading, and
whole-runtime dispatch are outside the frozen adapter templates.

## Execution and licensing boundary

The study does not clone, build, import, or execute Scorch. It does not run the
original test suite or native extension. Commit metadata and diffs were inspected
through a read-only GitHub connector. The artifact redistributes no upstream
source file or patch. Its adapters are original clean-room semantic models, and
`data/public-corpus.csv` retains the source URL and production-file scope for
each record.

The final denominator contains four admitted complete source adapters and eight
abstentions. Development admits two of four; the later segment admits two of
eight. These are descriptive coverage counts for this fixed corpus, not an
estimate of compiler-patch prevalence.
