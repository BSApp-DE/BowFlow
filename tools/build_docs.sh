#!/usr/bin/env bash
# Baut Redoc-Seiten für den Kern und jedes Profil (profiles/*/api/openapi.yaml),
# die Markdown-Doku (MkDocs, nach _site/doku/) und eine Übersichtsseite. Ausgabe: _site/
# Neue Profile werden automatisch gefunden, sobald sie api/openapi.yaml haben.
set -euo pipefail
cd "$(dirname "$0")/.."

out=_site
rm -rf "$out"
mkdir -p "$out"

specs=(core/api/openapi.yaml profiles/*/api/openapi.yaml)
items=""

for spec in "${specs[@]}"; do
  [ -f "$spec" ] || continue
  if [[ "$spec" == core/* ]]; then name=core; else name=$(basename "$(dirname "$(dirname "$spec")")"); fi
  title=$(yq '.info.title' "$spec")
  version=$(yq '.info.version' "$spec")
  mkdir -p "$out/$name"
  npx --yes @redocly/cli@latest build-docs "$spec" -o "$out/$name/index.html"
  cp "$spec" "$out/$name/openapi.yaml"
  items+="<li><a href=\"$name/\">$title</a> <small>$version · <a href=\"$name/openapi.yaml\">openapi.yaml</a></small></li>"$'\n'
done

# site_dir darf nicht im docs_dir (= Repo) liegen, daher erst außerhalb bauen und dann verschieben
tmp=$(mktemp -d)
mkdocs build -q -f tools/mkdocs.yml -d "$tmp/doku"
mv "$tmp/doku" "$out/doku"

cat > "$out/index.html" <<HTML
<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BowFlow Interop API</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem}li{margin:.5rem 0}small{color:#666}</style>
</head><body>
<h1>BowFlow Interop API</h1>
<p><a href="doku/">Dokumentation</a> (Konzept, Abläufe, Begriffe, Entscheidungen)</p>
<h2>API-Referenz</h2>
<ul>
$items</ul>
<p><a href="https://github.com/BSApp-DE/BowFlow">Quellen auf GitHub</a></p>
</body></html>
HTML
