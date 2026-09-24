"""Regression tests for the frozen public-source adapters."""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

from semantic_contract.public_adapters import (
    ADAPTERS, EinsumBuildSpec, mutation_study, p01_exhaustive_specs, verify_adapter,
)


ROOT = Path(__file__).resolve().parents[1]


class PublicAdapterStudyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with (ROOT / "data/public-corpus.csv").open() as handle:
            cls.corpus = list(csv.DictReader(handle))
        cls.adapters = [verify_adapter(adapter_id) for adapter_id in ADAPTERS]
        cls.mutation = mutation_study(seed=20260915, budget_per_adapter=64)

    def test_corpus_denominator_and_split_are_frozen(self) -> None:
        self.assertEqual(len(self.corpus), 12)
        self.assertEqual(sum(r["split"] == "development" for r in self.corpus), 4)
        self.assertEqual(sum(r["split"] == "held-out" for r in self.corpus), 8)
        self.assertEqual(sum(r["decision"] == "admitted" for r in self.corpus), 4)
        self.assertEqual(sum(r["decision"] == "abstained" for r in self.corpus), 8)
        self.assertEqual(sum(r["split"] == "development" and r["decision"] == "admitted" for r in self.corpus), 2)
        self.assertEqual(sum(r["split"] == "held-out" and r["decision"] == "admitted" for r in self.corpus), 2)

    def test_all_admitted_adapters_match_on_retained_domain(self) -> None:
        self.assertEqual(sum(r["bounded_case_count"] for r in self.adapters), 29740)
        self.assertTrue(all(r["mismatch_count"] == 0 for r in self.adapters))

    def test_p01_includes_declared_four_operand_boundary(self) -> None:
        specs = p01_exhaustive_specs()
        self.assertEqual(len(specs), 29222)
        self.assertEqual(len(specs), len(set(specs)))
        self.assertTrue(any(len(spec.operands) == 4 for spec in specs))
        self.assertTrue(all(isinstance(spec, EinsumBuildSpec) for spec in specs))

    def test_negative_controls_are_not_silently_accepted(self) -> None:
        self.assertEqual(self.mutation["mutant_count"], 20)
        self.assertEqual(self.mutation["summary"]["developer-examples"]["detected"], 16)
        self.assertEqual(self.mutation["summary"]["random"]["detected"], 19)
        self.assertEqual(self.mutation["summary"]["stratified-boundary"]["detected"], 20)
        missed = [
            row for row in self.mutation["rows"]
            if not row["random"]["detected"]
        ]
        self.assertEqual(
            [(row["adapter"], row["mutant"]) for row in missed],
            [("P04", "omit-call-semicolon")],
        )


if __name__ == "__main__":
    unittest.main()
