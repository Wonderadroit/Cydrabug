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
  let options = {};

  if (configPath) {
    const raw = ts.readConfigFile(configPath, ts.sys.readFile);
    if (!raw.error) {
      const parsed = ts.parseJsonConfigFileContent(raw.config, ts.sys, path.dirname(configPath));
      options = parsed.options;
    }
  }

  if (
    input.files.some((item) =>
      [".js", ".jsx", ".mjs", ".cjs"].includes(path.extname(item.path).toLowerCase()),
    )
  ) {
    options.allowJs = true;
  }

  return options;
}

const options = compilerOptions();

function compilerHost() {
  const host = ts.createCompilerHost(options, true);
  const originalGetSourceFile = host.getSourceFile.bind(host);
  host.readFile = (fileName) => {
    const absolute = path.resolve(fileName);
    return supplied.has(absolute) ? supplied.get(absolute) : ts.sys.readFile(fileName);
  };
  host.fileExists = (fileName) => {
    const absolute = path.resolve(fileName);
    return supplied.has(absolute) || ts.sys.fileExists(fileName);
  };
  host.getSourceFile = (fileName, languageVersion, onError, shouldCreateNewSourceFile, scriptKind) => {
    const absolute = path.resolve(fileName);
    if (supplied.has(absolute)) {
      return ts.createSourceFile(
        absolute,
        supplied.get(absolute),
        languageVersion,
        true,
        scriptKind ?? scriptKindFor(absolute),
      );
    }
    return originalGetSourceFile(fileName, languageVersion, onError, shouldCreateNewSourceFile, scriptKind);
  };
  return host;
}

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

function scriptKindFor(filePath) {
  switch (path.extname(filePath).toLowerCase()) {
    case ".tsx":
      return ts.ScriptKind.TSX;
    case ".ts":
      return ts.ScriptKind.TS;
    case ".mts":
      return ts.ScriptKind.MTS;
    case ".cts":
      return ts.ScriptKind.CTS;
    case ".jsx":
      return ts.ScriptKind.JSX;
    case ".js":
    case ".mjs":
    case ".cjs":
      return ts.ScriptKind.JS;
    default:
      return ts.ScriptKind.Unknown;
  }
}

function symbolIdentity(checker, symbol) {
  if (!symbol) return null;
  const declarations = symbol.declarations || [];
  const declaration = declarations[0];
  const declarationFile = declaration?.getSourceFile()?.fileName;
  const qualified = checker.getFullyQualifiedName(symbol);
  return {
    qualified_name: qualified,
    declaration_path: declarationFile ? path.resolve(declarationFile) : null,
  };
}

function symbolForLocation(checker, node) {
  let symbol = checker.getSymbolAtLocation(node);
  if (symbol && symbol.flags & ts.SymbolFlags.Alias) {
    const aliased = checker.getAliasedSymbol(symbol);
    if (aliased && aliased !== symbol) symbol = aliased;
  }
  return symbolIdentity(checker, symbol);
}

function enclosingFunction(node) {
  let current = node.parent;
  while (current) {
    if (
      ts.isFunctionDeclaration(current) ||
      ts.isMethodDeclaration(current) ||
      ts.isFunctionExpression(current) ||
      ts.isArrowFunction(current) ||
      ts.isGetAccessorDeclaration(current) ||
      ts.isSetAccessorDeclaration(current) ||
      ts.isConstructorDeclaration(current)
    ) {
      return current;
    }
    current = current.parent;
  }
  return null;
}

function functionSymbol(checker, node) {
  if (!node) return null;
  const name = node.name;
  if (name) return symbolForLocation(checker, name);
  const symbol = checker.getSymbolAtLocation(node);
  return symbolIdentity(checker, symbol);
}

const programRootNames = input.files.map((item) => path.resolve(targetRoot, item.path));
const program = ts.createProgram(programRootNames, options, compilerHost());
const checker = program.getTypeChecker();

function visit(node) {
  const push = (kind, name, attributes = {}) => {
    result.push({ path: node.getSourceFile().fileName, kind, name, line: lineOf(node), attributes });
  };

  if (ts.isFunctionDeclaration(node) && node.name) {
    const symbol = functionSymbol(checker, node);
    push("function", node.name.text, {
      async: !!node.modifiers?.some((m) => m.kind === ts.SyntaxKind.AsyncKeyword),
      exported: hasExport(node),
      symbol_identity: symbol,
    });
  } else if (ts.isMethodDeclaration(node) && node.name) {
    const symbol = functionSymbol(checker, node);
    push("function", node.name.getText(), {
      method: true,
      exported: hasExport(node),
      symbol_identity: symbol,
    });
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
    const caller = enclosingFunction(node);
    const callerSymbol = functionSymbol(checker, caller);
    const calleeSymbol = symbolForLocation(checker, node.expression);
    push("call", node.expression.getText(), {
      expression: node.expression.getText(),
      caller_symbol_identity: callerSymbol,
      callee_symbol_identity: calleeSymbol,
      caller_resolution_status: callerSymbol ? "RESOLVED" : "UNRESOLVED",
      callee_resolution_status: calleeSymbol ? "RESOLVED" : "UNRESOLVED",
    });
  }

  ts.forEachChild(node, visit);
}

for (const item of input.files) {
  const absolutePath = path.resolve(targetRoot, item.path);
  const sourceFile = program.getSourceFile(absolutePath);
  if (!sourceFile) {
    process.stderr.write(
      `TypeScript compiler did not admit supplied source into Program: ${absolutePath}\n`,
    );
    continue;
  }
  result.push({ path: item.path, kind: "file", name: item.path, line: 1, attributes: { statements: sourceFile.statements.length } });
  visit(sourceFile);
}

process.stdout.write(JSON.stringify({ compiler: "typescript-compiler-api", compiler_version: ts.version, observations: result, compiler_package_root: loaded.package_root }));
