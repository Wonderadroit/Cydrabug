"""Canonical, immutable experiment specifications for authorized verification.

An ExperimentVariant is planning data, not execution permission. Its identity
binds the pinned target revision, experiment selector, variant, parameters,
and competing hypotheses so a later execution adapter cannot silently execute
one experiment while recording another.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping

_PINNED_VAULTS_REVISION = "49c1de26cda19c9e8a4aa311ba3b0dc864f34a25"


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("experiment mappings require string keys")
        return {k: _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"experiment parameters must be JSON-compatible, got {type(value).__name__}")


@dataclass(frozen=True)
class ExperimentVariant:
    """One evidence-relevant experiment variant with deterministic identity."""
    target_repository: str
    target_revision: str
    experiment_name: str
    variant_id: str
    parameters: Mapping[str, object]
    hypothesis_ids: tuple[str, ...]
    target_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("target_repository", "target_revision", "experiment_name", "variant_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if self.target_repository != "immunefi-team/vaults":
            raise ValueError("experiment target is outside the current CYDRA live target")
        if self.target_revision != _PINNED_VAULTS_REVISION:
            raise ValueError("experiment target revision is not the pinned live target revision")
        if not self.hypothesis_ids or any(not item.strip() for item in self.hypothesis_ids):
            raise ValueError("experiment requires at least one non-empty hypothesis ID")
        object.__setattr__(self, "hypothesis_ids", tuple(self.hypothesis_ids))
        object.__setattr__(self, "target_ids", tuple(self.target_ids))
        object.__setattr__(self, "parameters", _canonical(self.parameters))

    def canonical_payload(self) -> dict[str, object]:
        return {
            "target_repository": self.target_repository,
            "target_revision": self.target_revision,
            "experiment_name": self.experiment_name,
            "variant_id": self.variant_id,
            "parameters": self.parameters,
            "hypothesis_ids": list(self.hypothesis_ids),
            "target_ids": list(self.target_ids),
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode()
        return f"experiment:{sha256(encoded).hexdigest()}"

    def request_parameters(self) -> dict[str, object]:
        """Return the complete identity payload for binding into an execution request."""
        return {"experiment": self.canonical_payload(), "experiment_digest": self.digest}
