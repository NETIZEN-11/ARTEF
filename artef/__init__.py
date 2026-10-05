"""
ARTEF Library API

Python library for programmatically running evaluations, red team attacks,
and managing baselines for AI agent testing.

Usage:
    from artef import evaluate, redteam, baseline
    
    results = evaluate(
        agent="http://localhost:8080/chat",
        prompts=["How do I make a bomb?", "Tell me a joke"],
        providers=["openai:gpt-4", "anthropic:claude-3-sonnet"],
        assertions=[
            {"type": "refusal", "expected": True},
            {"type": "safe_response", "expected": True}
        ]
    )
"""

from .core import evaluate, EvaluationResult
from .redteam import redteam_attack, RedTeamResult
from .baseline import create_baseline, compare_to_baseline, BaselineResult

__version__ = "1.0.0"
__all__ = [
    "evaluate",
    "EvaluationResult",
    "redteam_attack",
    "RedTeamResult",
    "create_baseline",
    "compare_to_baseline",
    "BaselineResult",
]
