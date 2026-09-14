from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any


@dataclass
class RetrievalMetrics:
    relevant_docs: int
    retrieved_docs: int
    precision: float
    recall: float
    f1_score: float
    mrr: float
    ndcg: float


@dataclass
class RetrievalEvaluationResult:
    test_case_id: str
    query: str
    retrieved_docs: list[dict[str, Any]]
    ground_truth_docs: list[str]
    metrics: RetrievalMetrics
    execution_time_ms: int
    errors: list[str] = field(default_factory=list)


class RetrievalEvaluator:
    def __init__(self, retriever: Any = None):
        self.retriever = retriever

    async def evaluate(
        self,
        test_case_id: str,
        query: str,
        retrieved_docs: list[dict[str, Any]],
        ground_truth_docs: list[str] | None = None,
    ) -> RetrievalEvaluationResult:
        start_time = datetime.now(timezone.utc)
        gt_docs = ground_truth_docs or []
        retrieved_contents = [d.get("content", "") for d in retrieved_docs]

        relevant_docs = 0
        for doc in retrieved_contents:
            for gt in gt_docs:
                if gt.lower() in doc.lower():
                    relevant_docs += 1
                    break

        retrieved_count = len(retrieved_docs)
        ground_truth_count = len(gt_docs)

        precision = relevant_docs / retrieved_count if retrieved_count > 0 else 0.0
        recall = relevant_docs / ground_truth_count if ground_truth_count > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        mrr = self._calculate_mrr(retrieved_contents, gt_docs)
        ndcg = self._calculate_ndcg(retrieved_contents, gt_docs)

        elapsed = datetime.now(timezone.utc) - start_time
        execution_time_ms = int(elapsed.total_seconds() * 1000)

        return RetrievalEvaluationResult(
            test_case_id=test_case_id,
            query=query,
            retrieved_docs=retrieved_docs,
            ground_truth_docs=gt_docs,
            metrics=RetrievalMetrics(
                relevant_docs=relevant_docs,
                retrieved_docs=retrieved_count,
                precision=precision,
                recall=recall,
                f1_score=f1,
                mrr=mrr,
                ndcg=ndcg,
            ),
            execution_time_ms=execution_time_ms,
            errors=[],
        )

    def _calculate_mrr(self, retrieved: list[str], ground_truth: list[str]) -> float:
        for i, doc in enumerate(retrieved):
            for gt in ground_truth:
                if gt.lower() in doc.lower():
                    return 1.0 / (i + 1)
        return 0.0

    def _calculate_ndcg(self, retrieved: list[str], ground_truth: list[str], k: int = 10) -> float:
        if not ground_truth:
            return 0.0

        dcg = 0.0
        for i, doc in enumerate(retrieved[:k]):
            rel = 1.0 if any(gt.lower() in doc.lower() for gt in ground_truth) else 0.0
            if rel > 0:
                dcg += rel / math.log2(i + 2)

        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(ground_truth), k)))
        return dcg / idcg if idcg > 0 else 0.0