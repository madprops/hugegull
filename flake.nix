{description="Flake for the Python application";

  inputs={
    nixpkgs.url="github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url="github:numtide/flake-utils";
  };

  outputs={self,nixpkgs,flake-utils}:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs=nixpkgs.legacyPackages.${system};
        pythonPackages=pkgs.python3Packages;

        rubyEnv=pkgs.ruby.withPackages (ps: [
          ps.git
        ]);

        app=pythonPackages.buildPythonApplication {
          pname="your-app-name";
          version="1.0.0";
          src=./.;

          propagatedBuildInputs=with pythonPackages; [
            setuptools
            webrtcvad
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
            cp src/icon.png $out/share/icons/hicolor/256x256/apps/your-app-name.png
          '';

          desktopItems=[
            (pkgs.makeDesktopItem {
              name="your-app-name";
              exec="your-app-name --gui";
              icon="your-app-name";
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
            (pkgs.python3.withPackages (ps: [
              ps.setuptools
              ps.webrtcvad
            ]))
            rubyEnv
          ];
        };
      }
    );
}