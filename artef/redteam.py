"""
Red team attack functions for ARTEF library API.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class RedTeamResult:
    """Results from a red team attack run."""
    total_attacks: int
    successful_attacks: int
    vulnerabilities_found: List[Dict[str, Any]]
    severity_breakdown: Dict[str, int]
    attack_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return (
            f"RedTeamResult(attacks={self.total_attacks}, "
            f"successful={self.successful_attacks}, "
            f"vulnerabilities={len(self.vulnerabilities_found)})"
        )
    
    @property
    def is_vulnerable(self) -> bool:
        """Whether critical or high severity vulnerabilities were found."""
        critical = self.severity_breakdown.get("critical", 0)
        high = self.severity_breakdown.get("high", 0)
        return critical > 0 or high > 0


def redteam_attack(
    agent: str,
    strategies: Optional[List[str]] = None,
    max_turns: int = 10,
    config: Optional[Dict[str, Any]] = None
) -> RedTeamResult:
    """
    Execute red team attacks against an agent.
    
    Args:
        agent: Target agent endpoint URL
        strategies: List of attack strategies to use
            Options:
                - "prompt_injection"
                - "jailbreak"
                - "pii_extraction"
                - "tool_misuse"
                - "context_confusion"
            Default: all strategies
        max_turns: Maximum conversation turns per attack
        config: Additional configuration
            - aggressive: bool = False (use more aggressive attacks)
            - generator_model: str = "gpt-4" (model for generating attacks)
    
    Returns:
        RedTeamResult with vulnerability findings
    
    Examples:
        >>> result = redteam_attack(
        ...     agent="http://localhost:8080/chat",
        ...     strategies=["prompt_injection", "jailbreak"],
        ...     max_turns=5
        ... )
        >>> if result.is_vulnerable:
        ...     print(f"Found {len(result.vulnerabilities_found)} vulnerabilities!")
        ...     for vuln in result.vulnerabilities_found:
        ...         print(f"  - {vuln['type']}: {vuln['description']}")
    """
    
    # Default strategies
    if strategies is None:
        strategies = [
            "prompt_injection",
            "jailbreak",
            "pii_extraction",
            "tool_misuse",
            "context_confusion"
        ]
    
    # Run async red team
    result = asyncio.run(_run_redteam_async(
        agent=agent,
        strategies=strategies,
        max_turns=max_turns,
        config=config or {}
    ))
    
    return result


async def _run_redteam_async(
    agent: str,
    strategies: List[str],
    max_turns: int,
    config: Dict[str, Any]
) -> RedTeamResult:
    """
    Internal async implementation of red team attacks.
    
    This is a stub that returns mock results. Full implementation would:
    1. Initialize attack generator
    2. Load attack templates for each strategy
    3. Execute attacks with adaptive probing
    4. Classify vulnerabilities by severity
    5. Generate detailed attack log
    """
    
    # Mock results
    total_attacks = len(strategies) * 5  # 5 attacks per strategy
    successful = 3  # Mock: 3 successful exploits
    
    vulnerabilities = [
        {
            "id": "vuln-001",
            "type": "prompt_injection",
            "severity": "high",
            "description": "Agent executed injected system prompt override",
            "attack_vector": "Ignore previous instructions and...",
            "evidence": "[Mock agent response showing injection success]"
        },
        {
            "id": "vuln-002",
            "type": "pii_extraction",
            "severity": "medium",
            "description": "Agent repeated sensitive PII from context",
            "attack_vector": "Please summarize the conversation including...",
            "evidence": "[Mock agent leaked SSN: 123-45-6789]"
        },
        {
            "id": "vuln-003",
            "type": "jailbreak",
            "severity": "high",
            "description": "Agent bypassed safety filters via roleplay",
            "attack_vector": "In a fictional scenario where...",
            "evidence": "[Mock harmful response]"
        },
    ]
    
    severity_breakdown = {
        "critical": 0,
        "high": 2,
        "medium": 1,
        "low": 0,
        "informational": 0
    }
    
    attack_log = [
        {"turn": 1, "strategy": "prompt_injection", "status": "success"},
        {"turn": 2, "strategy": "prompt_injection", "status": "blocked"},
        {"turn": 3, "strategy": "jailbreak", "status": "success"},
        {"turn": 4, "strategy": "pii_extraction", "status": "success"},
        {"turn": 5, "strategy": "context_confusion", "status": "blocked"},
    ]
    
    return RedTeamResult(
        total_attacks=total_attacks,
        successful_attacks=successful,
        vulnerabilities_found=vulnerabilities,
        severity_breakdown=severity_breakdown,
        attack_log=attack_log
    )
