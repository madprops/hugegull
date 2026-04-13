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
          version="38.2.0";
          src=./.;
          pyproject = true;

          build-system = [
            python3Packages.setuptools
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
            sed -i '/_post_install()/d' setup.py
          '';

          postInstall=''
            mkdir -p $out/share/icons/hicolor/256x256/apps
            cp src/icon.png $out/share/icons/hicolor/256x256/apps/hugegull.png
          '';

          desktopItems=[
            (pkgs.makeDesktopItem {
              name="hugegull";
              exec="hugegull --gui";
              icon="hugegull";
              desktopName="Your App Name";
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