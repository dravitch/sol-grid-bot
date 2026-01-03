{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python312
    python312Packages.pip
    python312Packages.virtualenv
    python312Packages.pytest
    python312Packages.black
    python312Packages.ruff
    git
    pre-commit
  ];
}
