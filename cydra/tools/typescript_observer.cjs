"use strict";

const fs = require("fs");

let ts;
try {
  ts = require("typescript");
} catch (error) {
  process.stderr.write(`typescript compiler API unavailable: ${error.message}\n`);
  process.exit(42);
}

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const result = [];

function visit(node, path) {
  const push = (kind, name, line, attributes = {}) => {
    result.push({ kind, name, line, attributes });
  };

  if (ts.isFunctionDeclaration(node) && node.name) {
    push("function", node.name.text, lineOf(node), {
      async: !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword),
      exported: hasExport(node),
    });
  } else if (ts.isMethodDeclaration(node) && node.name) {
    push("function", node.name.getText(), lineOf(node), {
      method: true,
      exported: hasExport(node),
    });
  } else if (ts.isClassDeclaration(node) && node.name) {
    push("class", node.name.text, lineOf(node), { exported: hasExport(node) });
  } else if (ts.isInterfaceDeclaration(node)) {
    push("type", node.name.text, lineOf(node), { declaration: "interface" });
  } else if (ts.isTypeAliasDeclaration(node)) {
    push("type", node.name.text, lineOf(node), { declaration: "type_alias" });
  } else if (ts.isImportDeclaration(node)) {
    push("import", node.moduleSpecifier.getText().replace(/^['\"]|['\"]$/g, ""), lineOf(node), {});
  } else if (ts.isExportDeclaration(node)) {
    const module = node.moduleSpecifier;
    push("export", module ? module.getText().replace(/^['\"]|['\"]$/g, "") : "export", lineOf(node), {});
  } else if (ts.isCallExpression(node)) {
    push("call", node.expression.getText(), lineOf(node), {
      expression: node.expression.getText(),
    });
  }

  ts.forEachChild(node, (child) => visit(child, path));
}

function hasExport(node) {
  return !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
}

function lineOf(node) {
  return node.getSourceFile().getLineAndCharacterOfPosition(node.getStart()).line + 1;
}

for (const item of input.files) {
  const sourceFile = ts.createSourceFile(
    item.path,
    item.source,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );

  result.push({
    kind: "file",
    name: item.path,
    line: 1,
    attributes: { statements: sourceFile.statements.length },
  });

  visit(sourceFile, item.path);
}

process.stdout.write(JSON.stringify({
  compiler: "typescript-compiler-api",
  compiler_version: ts.version,
  observations: result,
}));
