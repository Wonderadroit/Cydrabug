"""Language-neutral source observation contract for CYDRA.

Providers may use language-native parsers, compiler ASTs, or specialized tools.
They emit observations; CYDRA does not treat a provider's output as a security
conclusion. Provenance and semantic strength stay attached to every observation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Protocol


class SourceObservationKind(str, Enum):
    FILE = "file"
    MODULE = "module"
    FUNCTION = "function"
    CLASS = "class"
    TYPE = "type"
    IMPORT = "import"
    EXPORT = "export"
    ENTRY_POINT = "entry_point"
    STATE = "state"
    CALL = "call"
    DATA_FLOW = "data_flow"
    AUTHORIZATION = "authorization"
    EXTERNAL_BOUNDARY = "external_boundary"


class ObservationStrength(str, Enum):
    COMPILER = "compiler"
    TOOL = "specialized_tool"
    STRUCTURAL = "structural"
    LEXICAL = "lexical"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class SourceObservation:
    """A normalized source fact, not a vulnerability conclusion."""

    observation_id: str
    kind: SourceObservationKind
    path: str
    name: str
    attributes: Mapping[str, object] = field(default_factory=dict)
    provider: str = "unknown"
    tool: str | None = None
    tool_version: str | None = None
    strength: ObservationStrength = ObservationStrength.UNRESOLVED
    provenance: tuple[str, ...] = ()
    scope_state: str = "UNKNOWN"


class SourceProvider(Protocol):
    """Provider interface shared by language/tool-specific ingestion adapters."""

    name: str

    def observe(
        self,
        paths: Iterable[str],
        sources: Mapping[str, str],
    ) -> Iterable[SourceObservation]: ...
