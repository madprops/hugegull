{description="Flake for Huge Gull";

  inputs={
    nixpkgs.url="github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url="github:numtide/flake-utils";
  };

  outputs={self,nixpkgs,flake-utils}:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs=nixpkgs.legacyPackages.${system};

        # Standard python3 now supports tkinter natively via pythonPackages
        python=pkgs.python3;
        pythonPackages=python.pkgs;

        rubyEnv=pkgs.ruby.withPackages (ps: [
          ps.git
        ]);

        app=pythonPackages.buildPythonApplication {
          pname="hugegull";
          version="38.2.2";
          src=./.;
          pyproject = true;

          build-system = [
            pythonPackages.setuptools
          ];

          propagatedBuildInputs=with pythonPackages; [
            setuptools
            webrtcvad
            tkinter
          ] ++ [
            rubyEnv
          ];

          nativeBuildInputs=[
            pkgs.copyDesktopItems
          ];

          postPatch=''
            # Replace the dependency string specifically in requirements.txt
            # to prevent the wheel from baking it into the final metadata.
            sed -i 's/webrtcvad-wheels/webrtcvad/g' requirements.txt
            sed -i 's/webrtcvad_wheels/webrtcvad/g' requirements.txt
          '';

          postInstall=''
            mkdir -p $out/share/icons/hicolor/256x256/apps
            cp hugegull/icon.png $out/share/icons/hicolor/256x256/apps/hugegull.png
          '';

          desktopItems=[
            (pkgs.makeDesktopItem {
              name="hugegull";
              exec="hugegull --gui";
              icon="hugegull";
              desktopName="Huge Gull";
              categories=["Utility"];
              terminal=false;
            })
          ];
        };
      in {
        packages.default=app;
        apps.default=flake-utils.lib.mkApp {drv=app;};

        devShells.default=pkgs.mkShell {
          packages=[
            (python.withPackages (ps: [
              ps.setuptools
              ps.webrtcvad
              ps.tkinter
            ]))
            rubyEnv
            pkgs.ruff
            pkgs.mypy
          ];
        };
      }
    );
}