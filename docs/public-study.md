# Frozen public-source study

## Selection and split

The denominator is a fixed chronological sequence of twelve non-merge commits in
`bobbyyyan/scorch`, beginning with commit `72c55d...`. Each touches production
compiler, format, dispatch, or kernel source. Documentation-only, benchmark-only,
and tests-only commits between the selected commits were excluded by rule, not by
outcome. The first four records are the development segment; the next eight are
the temporal held-out segment. This is a retrospective split chosen after initial
repository scouting, not a preregistration or a genuinely blind test.

Every selected commit remains in `data/public-corpus.csv`. An unsupported commit
is an abstention, never silently discarded or counted as a verified patch. Four
commits have complete production-diff adapters; eight abstain. The held-out result
is two admitted and six abstained. No upstream Scorch checkout, native extension,
or repository test suite is executed.

## What “admitted” means

An admitted record satisfies all of the following:

1. Every production-code change in the commit is assigned either to the adapter
   or to a non-runtime category such as a comment.
2. The adapter states a source invariant and an observable (CIN AST, generated
   C++ text, emitted LLIR statement sequence, or initialized mode-order value).
3. A universal prose proof establishes equality of that observable.
4. A dependency-free executable model compares independent before/after paths on
   a retained bounded domain and exercises synthetic mutants.
5. Equality of the source observable is connected by a congruence argument to
   the paper’s five tensor observations. This implication assumes unchanged
   downstream components and excludes hidden reflection or undefined behavior.

Bounded execution is validation of the adapter, not the universal proof. The
source adapters are written from public diffs and are not independent of the
paper authors’ interpretation.

## Adapter records

- **P01 (`72c55d...`)**: exact equivalence between the generated `exec`/`eval`
  construction and direct overload calls. The proof is induction over operands
  and the reversed schedule. The observable is the complete CIN AST produced by
  the changed region.
- **P04 (`d7a9cd...`)**: case analysis over the finite LLIR node dispatch plus
  structural induction over child nodes. Extracted helpers return exactly the
  strings formerly produced in the monolithic dispatcher.
- **P06 (`210568...`)**: the five helper methods partition the original coordinate
  resolver’s emitted statement subsequences and are concatenated in their former
  order, with the same predicates.
- **P08 (`33532a...`)**: under the established TensorVar invariant—an explicit
  nonempty mode order, a nonempty shape, or a format object—the old truthiness
  cascade and the new `if/elif` cascade select the same sequence. The new behavior
  for a constructor lacking all three is outside that invariant and is reported.

## Negative controls and comparison

Each adapter has five hand-written source-level mutants. They are plausible
mistakes (dropped operands, reversed nesting, changed punctuation/branch order,
omitted emitted blocks, and precedence/off-by-one errors), not historical Scorch
bugs. Three test-selection methods receive exactly 64 adapter executions per
adapter: repeated developer examples, seeded random selection, and deterministic
stratified boundary selection. They detect 16/20, 19/20, and 20/20 retained
mutants, respectively; the random survivor is P04's omitted-call-semicolon mutant.
The universal proof is reported separately and is not misrepresented as an
equal-cost test method.

## Retrieval and licensing boundary

Commit identifiers, changed-file scopes, and source URLs are retained. The
consulted Scorch snapshots did not expose a repository license file through the
retrieval interface, so the artifact does not redistribute full upstream files
or patches. Its executable adapters are original clean-room semantic models;
small source facts are attributed by commit URL. Reproduction is network-free.
