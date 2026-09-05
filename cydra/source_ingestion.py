"""Projection of normalized source observations into CYDRA's canonical model."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from .source_provider import SourceObservation, SourceProvider
from .system_model import Edge, Node, SystemModel


def project_source_observations(observations: Iterable[SourceObservation], system: SystemModel | None = None) -> SystemModel:
    """Ingest observations and only project relationships explicitly established by providers."""
    system = system or SystemModel()
    materialized = tuple(observations)

    for observation in materialized:
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

    node_ids = {observation.observation_id for observation in materialized}
    for observation in materialized:
        for relationship in observation.relationships:
            if relationship.target_observation_id not in node_ids and relationship.target_observation_id not in system.nodes:
                raise ValueError(
                    "source relationship target is not present in the observation/model set: "
                    f"{relationship.target_observation_id}"
                )
            edge_attributes = dict(relationship.attributes)
            edge_attributes.update(
                provider=observation.provider,
                strength=observation.strength.value,
                provenance=list(observation.provenance),
            )
            system.add_edge(
                Edge(
                    observation.observation_id,
                    relationship.relation,
                    relationship.target_observation_id,
                    edge_attributes,
                )
            )

    return system


def ingest_source_provider(provider: SourceProvider, paths: Iterable[str], sources: Mapping[str, str], system: SystemModel | None = None) -> SystemModel:
    """Run one source provider and project its normalized facts into the model."""
    return project_source_observations(provider.observe(paths, sources), system)
