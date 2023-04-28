{nixpkgs?import<nixpkgs>{}}:

with nixpkgs;

let
  py3 = "${python3.withPackages(ps: [ ps.pillow ps.numpy ])}/bin/python3";
in

stdenv.mkDerivation {
  name = "nontexed";
  src = ./src;
  buildInputs = [ makeWrapper ];
  installPhase = ''
    mkdir -p $out/bin $out/lib $out/lib/nontexed
    cp $src/nontexed/*.py $out/lib/nontexed 
    cp $src/*.js $out/lib
    makeWrapper ${py3} $out/bin/nontexed --add-flags "-m nontexed" --prefix PYTHONPATH : $out/lib
    makeWrapper ${py3} $out/bin/nontexedweb --add-flags "-m nontexed.web" --prefix PYTHONPATH : $out/lib
  '';
    #makeWrapper ${py3} $out/bin/nontexedbot --add-flags "-m nontexed.bot" --prefix PYTHONPATH : $out/lib --prefix PATH : ${lib.makeBinPath [ phantomjs ]}
}
