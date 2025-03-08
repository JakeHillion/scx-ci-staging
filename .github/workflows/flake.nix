{
  description = "Nix flake for the scx CI environment.";

  inputs = {
    nixpkgs.url = "github:JakeHillion/nixpkgs/virtme-ng";
    flake-utils.url = "github:numtide/flake-utils";

    nix-develop-gha.url = "github:nicknovitski/nix-develop";
    nix-develop-gha.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, nix-develop-gha, ... }:
    flake-utils.lib.eachSystem [ "x86_64-linux" ]
      (system: {
        packages.nix-develop-gha = nix-develop-gha.packages."${system}".default;

        devShells =
          let
            pkgs = import nixpkgs { inherit system; };
            common = with pkgs; [ gnutar zstd ];
          in
          {
            update-kernels = pkgs.mkShell {
              buildInputs = with pkgs; common ++ [
                jq
              ];
            };

            build-kernel = pkgs.mkShell {
              buildInputs = with pkgs; common ++ [
                bc
                bison
                cpio
                elfutils
                flex
                git
                openssl
                pahole
                perl
                virtme-ng
                zlib
              ];
            };
          };
      }) // flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        formatter = pkgs.nixpkgs-fmt;

        apps = {
          update-kernels =
            let
              script = pkgs.python3Packages.buildPythonApplication {
                pname = "update-kernels";
                version = "git";

                pyproject = false;
                dontUnpack = true;

                installPhase = "install -Dm755 ${./update-kernels.py} $out/bin/update-kernels";
              };
            in
            {
              type = "app";
              program = "${script}/bin/update-kernels";
            };
        };
      });
}

