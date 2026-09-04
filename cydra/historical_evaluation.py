"""State boundary for blind historical CYDRA evaluations.

Historical findings remain outside reasoning until CYDRA output is frozen. Phase
ordering is explicit rather than dependent on enum-string ordering.
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


_PHASE_ORDER = {
    EvaluationPhase.INTAKE: 0,
    EvaluationPhase.UNDERSTANDING: 1,
    EvaluationPhase.REASONING: 2,
    EvaluationPhase.INVESTIGATION: 3,
    EvaluationPhase.VERIFICATION: 4,
    EvaluationPhase.FROZEN: 5,
    EvaluationPhase.ORACLE_REVEALED: 6,
    EvaluationPhase.COMPARED: 7,
}


@dataclass(frozen=True)
class HistoricalEvaluation:
    evaluation_id: str
    contest: str
    repository: str
    revision: str
    phase: EvaluationPhase = EvaluationPhase.INTAKE

    def advance(self, phase: EvaluationPhase) -> "HistoricalEvaluation":
        current_order = _PHASE_ORDER[self.phase]
        requested_order = _PHASE_ORDER[phase]
        if requested_order != current_order + 1:
            raise RuntimeError(
                f"historical evaluation must advance one phase at a time: "
                f"{self.phase.value} -> {phase.value}"
            )
        if phase == EvaluationPhase.ORACLE_REVEALED and self.phase != EvaluationPhase.FROZEN:
            raise RuntimeError("historical oracle cannot be revealed before CYDRA output is frozen")
        if phase == EvaluationPhase.COMPARED and self.phase != EvaluationPhase.ORACLE_REVEALED:
            raise RuntimeError("historical comparison requires oracle reveal after freeze")
        return HistoricalEvaluation(self.evaluation_id, self.contest, self.repository, self.revision, phase)

    @property
    def blind(self) -> bool:
        return self.phase not in {EvaluationPhase.ORACLE_REVEALED, EvaluationPhase.COMPARED}

    @property
    def oracle_allowed(self) -> bool:
        return self.phase in {EvaluationPhase.ORACLE_REVEALED, EvaluationPhase.COMPARED}
