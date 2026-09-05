"""Compiler-backed TypeScript source provider for CYDRA.

The provider deliberately delegates parsing to the TypeScript compiler API.
It emits structural observations only; it does not infer authorization or
security properties from names or text patterns.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
import json
import subprocess

from .source_provider import ObservationStrength, SourceObservation, SourceObservationKind


_NODE_SCRIPT = r'''
const ts = require("typescript");
const fs = require("fs");
const files = JSON.parse(process.argv[1]);
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
  const observations = [];
  const add = (kind, name, node, attrs = {}) => {
    const pos = sf.getLineAndCharacterOfPosition(node.getStart(sf));
    observations.push({kind, name, line: pos.line + 1, column: pos.character + 1, attrs});
  };
  add("file", file, sf);
  sf.statements.forEach((node) => {
    if (ts.isImportDeclaration(node)) add("import", node.moduleSpecifier.getText(sf), node);
    if (ts.isFunctionDeclaration(node) && node.name) add("function", node.name.text, node, {parameters: node.parameters.length});
    if (ts.isClassDeclaration(node) && node.name) add("class", node.name.text, node);
    if (ts.isInterfaceDeclaration(node)) add("type", node.name.text, node, {type_kind: "interface"});
    if (ts.isTypeAliasDeclaration(node)) add("type", node.name.text, node, {type_kind: "type_alias"});
    if (ts.isExportDeclaration(node)) add("export", node.moduleSpecifier ? node.moduleSpecifier.getText(sf) : "export", node);
  });
  console.log(JSON.stringify({file, observations}));
}
'''


class TypeScriptCompilerProvider:
    name = "typescript-compiler"

    def __init__(self, node: str = "node") -> None:
        self.node = node

    def observe(
        self,
        paths: Iterable[str],
        sources: Mapping[str, str],
    ) -> Iterable[SourceObservation]:
        files = [str(Path(path)) for path in paths if Path(path).suffix in {".ts", ".tsx"}]
        if not files:
            return ()

        completed = subprocess.run(
            [self.node, "-e", _NODE_SCRIPT, json.dumps(files)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "TypeScript compiler provider unavailable: "
                + (completed.stderr.strip() or "node execution failed")
            )

        observations: list[SourceObservation] = []
        for raw in completed.stdout.splitlines():
            payload = json.loads(raw)
            path = payload["file"]
            for item in payload["observations"]:
                kind = SourceObservationKind(item["kind"])
                line = item.get("line")
                observation_id = f"{kind.value}:{path}:{line}:{item['name']}"
                observations.append(
                    SourceObservation(
                        observation_id=observation_id,
                        kind=kind,
                        path=path,
                        name=item["name"],
                        attributes={**item.get("attrs", {}), "line": line, "column": item.get("column")},
                        provider=self.name,
                        tool="typescript-compiler-api",
                        tool_version=str(_compiler_version(self.node)),
                        strength=ObservationStrength.COMPILER,
                        provenance=(f"source:{path}",),
                    )
                )
        return tuple(observations)


def _compiler_version(node: str) -> str:
    completed = subprocess.run(
        [node, "-e", "process.stdout.write(require('typescript').version)"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError("TypeScript compiler package is unavailable")
    return completed.stdout.strip()
