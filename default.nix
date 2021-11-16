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
    mkdir -p $out/bin $out/lib
    cp $src/*.py $src/*.js $out/lib
    makeWrapper ${py3} $out/bin/nontexed --add-flags $out/lib/nontexed.py
    makeWrapper ${py3} $out/bin/nontexedweb --add-flags $out/lib/nontexedweb.py
    makeWrapper ${py3} $out/bin/nontexedbot --add-flags $out/lib/bot.py --prefix PATH : ${lib.makeBinPath [ phantomjs ]}
  '';
}
