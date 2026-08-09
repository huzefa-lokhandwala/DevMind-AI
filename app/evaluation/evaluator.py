"""Evaluator engine for measuring RAG retrieval accuracy and ranking quality."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from app.evaluation.dataset import EvaluationCase, get_sample_evaluation_dataset
from app.evaluation.metrics import (
    reciprocal_rank_case,
    recall_at_k_case,
    top_1_accuracy_case,
)
from app.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationReport:
    """Aggregated retrieval benchmark evaluation summary."""

    top_1_accuracy: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    total_cases: int


class RAGEvaluator:
    """Evaluates Retriever performance against ground-truth evaluation datasets."""

    def evaluate(
        self,
        retriever: Retriever,
        cases: Sequence[EvaluationCase] | None = None,
    ) -> EvaluationReport:
        """Run benchmark evaluation suite for a given Retriever.

        Args:
            retriever: Configured Retriever instance to test.
            cases: Optional sequence of EvaluationCase objects. Defaults to sample benchmark dataset.

        Returns:
            EvaluationReport containing calculated Top-1, Recall@3, Recall@5, and MRR metrics.
        """
        benchmark_cases = cases or get_sample_evaluation_dataset()
        if not benchmark_cases:
            return EvaluationReport(
                top_1_accuracy=0.0,
                recall_at_3=0.0,
                recall_at_5=0.0,
                mrr=0.0,
                total_cases=0,
            )

        top_1_sum = 0.0
        recall_3_sum = 0.0
        recall_5_sum = 0.0
        mrr_sum = 0.0

        for case in benchmark_cases:
            results = retriever.retrieve(case.query, k=5)
            top_1_sum += top_1_accuracy_case(results, case)
            recall_3_sum += recall_at_k_case(results, case, k=3)
            recall_5_sum += recall_at_k_case(results, case, k=5)
            mrr_sum += reciprocal_rank_case(results, case)

        n = len(benchmark_cases)
        return EvaluationReport(
            top_1_accuracy=round(top_1_sum / n, 4),
            recall_at_3=round(recall_3_sum / n, 4),
            recall_at_5=round(recall_5_sum / n, 4),
            mrr=round(mrr_sum / n, 4),
            total_cases=n,
        )
