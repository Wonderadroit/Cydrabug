"use strict";

const fs = require("fs");
const path = require("path");
const Module = require("module");

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const targetRoot = path.resolve(input.target_root || process.cwd());
const supplied = new Map(input.files.map((item) => [path.resolve(targetRoot, item.path), item.source]));

function packageRootFor(filePath) {
  let current = path.dirname(path.resolve(filePath));
  const root = targetRoot;
  while (true) {
    const packageJson = path.join(current, "package.json");
    if (fs.existsSync(packageJson)) return current;
    if (current === root || current === path.dirname(current)) return root;
    current = path.dirname(current);
  }
}

function loadTypeScript(filePath) {
  const packageRoot = packageRootFor(filePath);
  const packageJson = path.join(packageRoot, "package.json");
  const targetRequire = Module.createRequire(packageJson);
  try {
    return {
      ts: targetRequire("typescript"),
      package_root: packageRoot,
    };
  } catch (error) {
    const detail = `typescript compiler API unavailable from owning workspace package ${packageRoot}: ${error.message}`;
    process.stderr.write(detail + "\n");
    process.exit(42);
  }
}

const firstSourcePath = input.files.length
  ? path.resolve(targetRoot, input.files[0].path)
  : targetRoot;
const loaded = loadTypeScript(firstSourcePath);
const ts = loaded.ts;
const result = [];

function hasExport(node) {
  return !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.ExportKeyword);
}

function lineOf(node) {
  return node.getSourceFile().getLineAndCharacterOfPosition(node.getStart()).line + 1;
}

function compilerOptions() {
  const configPath = ts.findConfigFile(targetRoot, ts.sys.fileExists, "tsconfig.json");
  if (!configPath) return {};
  const raw = ts.readConfigFile(configPath, ts.sys.readFile);
  if (raw.error) return {};
  const parsed = ts.parseJsonConfigFileContent(raw.config, ts.sys, path.dirname(configPath));
  return parsed.options;
}

const options = compilerOptions();

function resolveImport(specifier, containingFile) {
  const resolved = ts.resolveModuleName(specifier, containingFile, options, {
    ...ts.sys,
    readFile(fileName) {
      const absolute = path.resolve(fileName);
      return supplied.has(absolute) ? supplied.get(absolute) : ts.sys.readFile(fileName);
    },
    fileExists(fileName) {
      const absolute = path.resolve(fileName);
      return supplied.has(absolute) || ts.sys.fileExists(fileName);
    },
  });
  return resolved.resolvedModule?.resolvedFileName || null;
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
    const specifier = node.moduleSpecifier.getText().replace(/^['\"]|['\"]$/g, "");
    const resolved = resolveImport(specifier, node.getSourceFile().fileName);
    push("import", specifier, {
      resolved_path: resolved,
      resolution_status: resolved ? "RESOLVED" : "UNRESOLVED",
    });
  } else if (ts.isExportDeclaration(node)) {
    const module = node.moduleSpecifier;
    const specifier = module ? module.getText().replace(/^['\"]|['\"]$/g, "") : "export";
    const resolved = module ? resolveImport(specifier, node.getSourceFile().fileName) : null;
    push("export", specifier, {
      resolved_path: resolved,
      resolution_status: module ? (resolved ? "RESOLVED" : "UNRESOLVED") : "DECLARATION",
    });
  } else if (ts.isCallExpression(node)) {
    push("call", node.expression.getText(), { expression: node.expression.getText() });
  }

  ts.forEachChild(node, visit);
}

for (const item of input.files) {
  const absolutePath = path.resolve(targetRoot, item.path);
  const sourceFile = ts.createSourceFile(absolutePath, item.source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  result.push({ path: item.path, kind: "file", name: item.path, line: 1, attributes: { statements: sourceFile.statements.length } });
  visit(sourceFile);
}

process.stdout.write(JSON.stringify({ compiler: "typescript-compiler-api", compiler_version: ts.version, observations: result, compiler_package_root: loaded.package_root }));
