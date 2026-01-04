#!/usr/bin/env python3
"""
Vérification et correction automatique des imports
Scanne tous les fichiers .py et vérifie les imports
"""

import os
import ast
import argparse
from pathlib import Path
from typing import List, Dict, Set


class ImportChecker:
    """Vérifie et analyse les imports d'un projet Python"""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.issues: List[Dict] = []
        self.all_imports: Set[str] = set()

    def scan_file(self, filepath: Path) -> Dict:
        """Scanne un fichier Python pour ses imports"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(filepath))

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(
                            {
                                "type": "import",
                                "module": alias.name,
                                "line": node.lineno,
                            }
                        )
                        self.all_imports.add(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(
                            {
                                "type": "from",
                                "module": module,
                                "name": alias.name,
                                "line": node.lineno,
                            }
                        )
                        self.all_imports.add(module)

            return {
                "file": str(filepath.relative_to(self.root_dir)),
                "imports": imports,
                "ok": True,
            }

        except SyntaxError as e:
            return {
                "file": str(filepath.relative_to(self.root_dir)),
                "error": f"Syntax error: {e}",
                "ok": False,
            }

        except Exception as e:
            return {
                "file": str(filepath.relative_to(self.root_dir)),
                "error": f"Error: {e}",
                "ok": False,
            }

    def scan_project(self) -> List[Dict]:
        """Scanne tous les fichiers Python du projet"""
        results = []

        python_files = list(self.root_dir.rglob("*.py"))
        python_files = [f for f in python_files if "__pycache__" not in str(f)]

        print(f"🔍 Scanning {len(python_files)} Python files...\n")

        for filepath in sorted(python_files):
            result = self.scan_file(filepath)
            results.append(result)

            if not result["ok"]:
                self.issues.append(result)

        return results

    def check_dependencies(self) -> Dict[str, bool]:
        """Vérifie si les modules importés sont installés"""
        import importlib

        stdlib = {
            "os",
            "sys",
            "pathlib",
            "datetime",
            "logging",
            "argparse",
            "json",
            "csv",
            "typing",
            "dataclasses",
            "abc",
            "enum",
            "asyncio",
            "io",
            "re",
            "math",
            "random",
            "time",
        }

        installed = {}

        for module in self.all_imports:
            # Ignorer stdlib
            base_module = module.split(".")[0]
            if base_module in stdlib:
                continue

            # Ignorer modules locaux (src.*)
            if base_module in ["src", "scripts", "tests"]:
                continue

            # Tester import
            try:
                importlib.import_module(base_module)
                installed[base_module] = True
            except ImportError:
                installed[base_module] = False

        return installed

    def print_report(self, results: List[Dict]):
        """Affiche rapport complet"""
        print("=" * 70)
        print("📊 IMPORT ANALYSIS REPORT")
        print("=" * 70)

        # Fichiers OK
        ok_files = [r for r in results if r["ok"]]
        print(f"\n✅ Files analyzed: {len(ok_files)}/{len(results)}")

        # Erreurs de syntaxe
        if self.issues:
            print(f"\n❌ Files with issues: {len(self.issues)}")
            for issue in self.issues:
                print(f"   {issue['file']}: {issue['error']}")

        # Imports par fichier
        print("\n📦 Imports per file:")
        for result in ok_files:
            if result["imports"]:
                print(f"\n  {result['file']}:")
                for imp in result["imports"][:5]:  # Limiter à 5
                    if imp["type"] == "import":
                        print(f"    Line {imp['line']}: import {imp['module']}")
                    else:
                        print(
                            f"    Line {imp['line']}: from {imp['module']} import {imp['name']}"
                        )
                if len(result["imports"]) > 5:
                    print(f"    ... and {len(result['imports']) - 5} more")

        # Dépendances externes
        print("\n📚 External dependencies:")
        deps = self.check_dependencies()

        installed = {k: v for k, v in deps.items() if v}
        missing = {k: v for k, v in deps.items() if not v}

        if installed:
            print("\n  ✅ Installed:")
            for mod in sorted(installed.keys()):
                print(f"     {mod}")

        if missing:
            print("\n  ❌ Missing:")
            for mod in sorted(missing.keys()):
                print(f"     {mod}")

            print("\n  💡 Install missing dependencies:")
            print(f"     pip install {' '.join(sorted(missing.keys()))}")

        # Résumé
        print("\n" + "=" * 70)
        print("📈 SUMMARY")
        print("=" * 70)
        print(f"Total Python files: {len(results)}")
        print(f"Unique imports: {len(self.all_imports)}")
        print(f"External dependencies: {len(deps)}")
        print(f"Missing dependencies: {len(missing)}")
        print(f"Issues found: {len(self.issues)}")
        print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Check Python imports in project")

    parser.add_argument(
        "--dir", type=str, default=".", help="Root directory to scan (default: current)"
    )

    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix import issues (WIP)"
    )

    args = parser.parse_args()

    checker = ImportChecker(args.dir)
    results = checker.scan_project()
    checker.print_report(results)

    # Exit code
    if checker.issues:
        return 1

    deps = checker.check_dependencies()
    missing = [k for k, v in deps.items() if not v]
    if missing:
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
