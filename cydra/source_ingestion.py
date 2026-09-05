"""Projection of normalized source observations into CYDRA's canonical model."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from .source_provider import SourceObservation, SourceProvider
from .system_model import Edge, Node, SystemModel


def project_source_observations(
    observations: Iterable[SourceObservation],
    system: SystemModel | None = None,
) -> SystemModel:
    """Ingest provider observations without upgrading their semantic strength."""
    system = system or SystemModel()

    for observation in observations:
        attributes = dict(observation.attributes)
        attributes.update(
            path=observation.path,
            provider=observation.provider,
            strength=observation.strength.value,
            scope_state=observation.scope_state,
            provenance=list(observation.provenance),
        )
        if observation.tool is not None:
            attributes["tool"] = observation.tool
        if observation.tool_version is not None:
            attributes["tool_version"] = observation.tool_version

        if observation.observation_id not in system.nodes:
            system.add_node(Node(observation.observation_id, observation.kind.value, observation.name, attributes))

    return system


def ingest_source_provider(
    provider: SourceProvider,
    paths: Iterable[str],
    sources: Mapping[str, str],
    system: SystemModel | None = None,
) -> SystemModel:
    """Run one source provider and project its normalized facts into the model.

    Provider capability failures intentionally propagate; an unavailable semantic
    tool must not silently degrade into a weaker parser or empty model.
    """
    observations = provider.observe(paths, sources)
    return project_source_observations(observations, system)
