"""State boundary for blind historical CYDRA evaluations.

The evaluator deliberately stores the target identity and blind/frozen phases without
loading historical findings. Historical reports belong to the post-freeze oracle
boundary and must never become reasoning input.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvaluationPhase(str, Enum):
    INTAKE = "INTAKE"
    UNDERSTANDING = "UNDERSTANDING"
    REASONING = "REASONING"
    INVESTIGATION = "INVESTIGATION"
    VERIFICATION = "VERIFICATION"
    FROZEN = "FROZEN"
    ORACLE_REVEALED = "ORACLE_REVEALED"
    COMPARED = "COMPARED"


@dataclass(frozen=True)
class HistoricalEvaluation:
    evaluation_id: str
    contest: str
    repository: str
    revision: str
    phase: EvaluationPhase = EvaluationPhase.INTAKE

    def advance(self, phase: EvaluationPhase) -> "HistoricalEvaluation":
        if phase == EvaluationPhase.ORACLE_REVEALED and self.phase != EvaluationPhase.FROZEN:
            raise RuntimeError("historical oracle cannot be revealed before CYDRA output is frozen")
        if phase == EvaluationPhase.COMPARED and self.phase != EvaluationPhase.ORACLE_REVEALED:
            raise RuntimeError("historical comparison requires oracle reveal after freeze")
        if self.phase in {EvaluationPhase.FROZEN, EvaluationPhase.ORACLE_REVEALED, EvaluationPhase.COMPARED}:
            if phase.value <= self.phase.value:
                raise RuntimeError("historical evaluation phase cannot move backwards")
        return HistoricalEvaluation(
            self.evaluation_id, self.contest, self.repository, self.revision, phase
        )

    @property
    def blind(self) -> bool:
        return self.phase != EvaluationPhase.ORACLE_REVEALED and self.phase != EvaluationPhase.COMPARED

    @property
    def oracle_allowed(self) -> bool:
        return self.phase in {EvaluationPhase.ORACLE_REVEALED, EvaluationPhase.COMPARED}
