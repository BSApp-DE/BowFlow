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
  npx --yes @redocly/cli@latest build-docs "$spec" -o "$out/$name/index.html" \
    --openapi.theme.colors.primary.main="#1e73be" \
    --openapi.theme.typography.fontFamily="-apple-system, system-ui, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif" \
    --openapi.theme.typography.headings.fontFamily="-apple-system, system-ui, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"
  cp "$spec" "$out/$name/openapi.yaml"
  items+="<a class=\"card\" href=\"$name/\"><h3>$title</h3><p>Version $version</p></a>"$'\n'
done

# site_dir darf nicht im docs_dir (= Repo) liegen, daher erst außerhalb bauen und dann verschieben
tmp=$(mktemp -d)
mkdocs build -q -f tools/mkdocs.yml -d "$tmp/doku"
mv "$tmp/doku" "$out/doku"

cat > "$out/index.html" <<HTML
<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BowFlow</title>
<style>
:root{--accent:#1e73be;--text:#222;--muted:#575760;--bg:#f7f8f9;--surface:#fff;--border:#e3e5e8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 -apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
header{background:var(--surface);box-shadow:0 1px 0 var(--border)}
header div{max-width:60rem;margin:0 auto;padding:1.1rem 1.5rem;display:flex;gap:2rem;align-items:baseline;flex-wrap:wrap}
header strong{font-size:1.25rem}
header a{color:var(--text);text-decoration:none}header a:hover{color:var(--accent)}
main{max-width:60rem;margin:1.5rem auto;padding:0 1.5rem}
.panel{background:var(--surface);padding:2rem}
h1{font-weight:400;font-size:2.6rem;line-height:1.2;margin:0 0 1rem}
h2{font-weight:400;font-size:1.6rem;margin:2rem 0 .8rem}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(16rem,1fr));gap:1rem}
.card{display:block;background:var(--bg);border:1px solid var(--border);padding:1rem 1.2rem;color:var(--text)}
.card:hover{border-color:var(--accent);text-decoration:none}
.card h3{margin:0 0 .3rem;font-size:1.05rem;color:var(--accent)}.card p{margin:0;color:var(--muted);font-size:.9rem}
footer{max-width:60rem;margin:0 auto 2rem;padding:0 1.5rem;color:var(--muted);font-size:.9rem}
</style>
</head><body>
<header><div><strong>BowFlow</strong><a href="doku/">Dokumentation</a><a href="https://github.com/BSApp-DE/BowFlow">GitHub</a></div></header>
<main><div class="panel">
<h1>Offene Schnittstelle für den Bogensport.</h1>
<p>BowFlow beschreibt, wie Apps bei Wettkämpfen Daten austauschen, zum Beispiel Liga App, Scoring App und Spotter App.</p>
<h2>Dokumentation</h2>
<div class="cards"><a class="card" href="doku/"><h3>Konzept, Abläufe, Begriffe</h3><p>Aufbau, Wettkampftag, Entscheidungen</p></a></div>
<h2>API-Referenz</h2>
<div class="cards">
$items</div>
</div></main>
<footer>Ein Projekt von <a href="https://bsapp.de">BSApp</a></footer>
</body></html>
HTML
