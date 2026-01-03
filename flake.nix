{
  description = "Reproducible Python environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
    python = pkgs.python312;
    py = pkgs.python312Packages;
  in {
    devShells.${system}.default = pkgs.mkShell {
      buildInputs = [
        python
        py.pip
        py.virtualenv
        py.pytest
        py.black
        py.ruff
        pkgs.git
        pkgs.pre-commit
      ];
    };
  };
}
