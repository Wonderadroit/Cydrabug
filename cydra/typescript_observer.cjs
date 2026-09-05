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

function hasExport(node) {
  return !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
}

function lineOf(node) {
  return node.getSourceFile().getLineAndCharacterOfPosition(node.getStart()).line + 1;
}

function visit(node) {
  const push = (kind, name, attributes = {}) => {
    result.push({ path: node.getSourceFile().fileName, kind, name, line: lineOf(node), attributes });
  };

  if (ts.isFunctionDeclaration(node) && node.name) {
    push("function", node.name.text, { async: !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword), exported: hasExport(node) });
  } else if (ts.isMethodDeclaration(node) && node.name) {
    push("function", node.name.getText(), { method: true, exported: hasExport(node) });
  } else if (ts.isClassDeclaration(node) && node.name) {
    push("class", node.name.text, { exported: hasExport(node) });
  } else if (ts.isInterfaceDeclaration(node)) {
    push("type", node.name.text, { declaration: "interface" });
  } else if (ts.isTypeAliasDeclaration(node)) {
    push("type", node.name.text, { declaration: "type_alias" });
  } else if (ts.isImportDeclaration(node)) {
    push("import", node.moduleSpecifier.getText().replace(/^['\"]|['\"]$/g, ""));
  } else if (ts.isExportDeclaration(node)) {
    const module = node.moduleSpecifier;
    push("export", module ? module.getText().replace(/^['\"]|['\"]$/g, "") : "export");
  } else if (ts.isCallExpression(node)) {
    push("call", node.expression.getText(), { expression: node.expression.getText() });
  }

  ts.forEachChild(node, visit);
}

for (const item of input.files) {
  const sourceFile = ts.createSourceFile(item.path, item.source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  result.push({ path: item.path, kind: "file", name: item.path, line: 1, attributes: { statements: sourceFile.statements.length } });
  visit(sourceFile);
}

process.stdout.write(JSON.stringify({ compiler: "typescript-compiler-api", compiler_version: ts.version, observations: result }));
