import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class GenerationMetrics:
    faithfulness: float
    answer_relevance: float
    context_recall: float
    context_precision: float
    factuality: float
    hallucination_rate: float


@dataclass
class GenerationEvaluationResult:
    test_case_id: str
    query: str
    answer: str
    context: list[str]
    metrics: GenerationMetrics
    execution_time_ms: int
    errors: list[str] = field(default_factory=list)


class GenerationEvaluator:
    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    async def evaluate(
        self,
        test_case_id: str,
        query: str,
        answer: str,
        context: list[str],
    ) -> GenerationEvaluationResult:
        start_time = datetime.now(UTC)

        faithfulness = await self._calculate_faithfulness(answer, context)
        answer_relevance = await self._calculate_answer_relevance(answer, query)
        context_recall = await self._calculate_context_recall(query, context)
        context_precision = await self._calculate_context_precision(query, context)
        factuality = await self._calculate_factuality(answer, context)
        hallucination_rate = max(0.0, 1.0 - faithfulness)

        elapsed = datetime.now(UTC) - start_time
        execution_time_ms = int(elapsed.total_seconds() * 1000)

        return GenerationEvaluationResult(
            test_case_id=test_case_id,
            query=query,
            answer=answer,
            context=context,
            metrics=GenerationMetrics(
                faithfulness=faithfulness,
                answer_relevance=answer_relevance,
                context_recall=context_recall,
                context_precision=context_precision,
                factuality=factuality,
                hallucination_rate=hallucination_rate,
            ),
            execution_time_ms=execution_time_ms,
            errors=[],
        )

    async def _calculate_faithfulness(self, answer: str, context: list[str]) -> float:
        context_text = " ".join(context).lower()
        if not context_text:
            return 0.0

        answer_claims = self._extract_claims(answer)
        if not answer_claims:
            return 1.0

        supported = 0
        for claim in answer_claims:
            if claim.lower() in context_text:
                supported += 1

        return supported / len(answer_claims)

    async def _calculate_answer_relevance(self, answer: str, query: str) -> float:
        query_terms = set(query.lower().split())
        answer_terms = set(answer.lower().split())

        if not query_terms:
            return 0.0

        overlap = len(query_terms & answer_terms)
        return overlap / len(query_terms)

    async def _calculate_context_recall(self, query: str, context: list[str]) -> float:
        query_terms = set(query.lower().split())
        context_text = " ".join(context).lower()

        if not query_terms:
            return 1.0

        found = sum(1 for term in query_terms if term in context_text)
        return found / len(query_terms)

    async def _calculate_context_precision(self, query: str, context: list[str]) -> float:
        if not context:
            return 0.0

        query_terms = set(query.lower().split())
        relevant_docs = 0

        for doc in context:
            doc_terms = set(doc.lower().split())
            if query_terms & doc_terms:
                relevant_docs += 1

        return relevant_docs / len(context)

    async def _calculate_factuality(self, answer: str, context: list[str]) -> float:
        context_text = " ".join(context).lower()
        if not answer.strip():
            return 1.0

        answer_claims = self._extract_claims(answer)
        if not answer_claims:
            return 1.0

        supported = 0
        for claim in answer_claims:
            if claim.lower() in context_text:
                supported += 1

        return supported / len(answer_claims)

    def _extract_claims(self, text: str) -> list[str]:
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
