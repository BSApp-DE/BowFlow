#!/usr/bin/env python3
"""Prüft die BowFlow-Spezifikation auf innere Konsistenz (Kern und alle Profile).

Geprüft werden:
  1. Alle JSON Schemas (Meta-Schema) und ihre $ref-Auflösung
  2. Alle Beispiele gegen das in examples/index.yaml genannte Schema ("core:" verweist auf ein Kern-Schema)
  3. OpenAPI-Dateien gegen die OpenAPI-3.1-Spezifikation
  4. Je Profil: profile.yaml passt zu Schemas, OpenAPI (Pfade, Methoden) und Doku (Benachrichtigungs-Typen)
  5. Interne Markdown-Links zeigen auf vorhandene Dateien

Aufruf:  python tools/validate.py     (Abhängigkeiten: jsonschema, pyyaml, openapi-spec-validator)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []
units = [ROOT / "core"] + sorted((ROOT / "profiles").glob("*/"))  # Kern und Profile


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"  FEHLER: {msg}")


def section(title: str) -> None:
    print(f"\n== {title}")


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# --- 1. Schemas -----------------------------------------------------------------------------
section("Schemas")
schemas: dict[Path, dict] = {}
resources = []
for unit in units:
    for f in sorted((unit / "schemas").glob("*.schema.json")):
        s = json.loads(f.read_text())
        try:
            Draft202012Validator.check_schema(s)
        except Exception as e:  # noqa: BLE001
            fail(f"{rel(f)}: {e}")
            continue
        schemas[f] = s
        resources.append((s["$id"], Resource.from_contents(s)))
registry = Registry().with_resources(resources)
print(f"  {len(schemas)} Schemas gültig")

# --- 2. Beispiele ---------------------------------------------------------------------------
section("Beispiele")
count = 0
for unit in units:
    idx_path = unit / "examples/index.yaml"
    if not idx_path.exists():
        continue
    listed = set()
    for entry in yaml.safe_load(idx_path.read_text()):
        f, ref = entry["file"], entry["schema"]
        listed.add(f)
        path = unit / "examples" / f
        if not path.exists():
            fail(f"{rel(unit)}: Beispiel fehlt: {f}")
            continue
        fname, _, frag = ref.partition("#")
        sdir = ROOT / "core" if fname.startswith("core:") else unit
        sfile = sdir / "schemas" / fname.removeprefix("core:")
        if sfile not in schemas:
            fail(f"{rel(path)}: unbekanntes Schema {fname}")
            continue
        sch = {"$ref": schemas[sfile]["$id"] + ("#" + frag if frag else "")}
        for err in Draft202012Validator(sch, registry=registry).iter_errors(json.loads(path.read_text())):
            fail(f"{rel(path)}: {'/'.join(map(str, err.absolute_path)) or '<root>'}: {err.message}")
        count += 1
    for p in (unit / "examples").glob("*.json"):
        if p.name not in listed:
            fail(f"{rel(p)}: nicht in index.yaml")
print(f"  {count} Beispiele geprüft")

# --- 3. OpenAPI -----------------------------------------------------------------------------
section("OpenAPI")
openapis: dict[Path, dict] = {}
try:
    from openapi_spec_validator import validate
    from openapi_spec_validator.readers import read_from_filename

    have_validator = True
except ImportError:
    have_validator = False
    print("  übersprungen (openapi-spec-validator nicht installiert)")
for unit in units:
    f = unit / "api/openapi.yaml"
    if not f.exists():
        continue
    openapis[unit] = yaml.safe_load(f.read_text())
    if have_validator:
        try:
            spec, base_uri = read_from_filename(str(f))
            validate(spec, base_uri=base_uri)
            print(f"  {rel(f)} ok")
        except Exception as e:  # noqa: BLE001
            fail(f"{rel(f)}: {str(e)[:300]}")

# --- 4. Profile -----------------------------------------------------------------------------
section("Profile")
for unit in units[1:]:
    mpath = unit / "profile.yaml"
    if not mpath.exists():
        fail(f"{rel(unit)}: profile.yaml fehlt")
        continue
    m = yaml.safe_load(mpath.read_text())
    if m["profile"] != unit.name:
        fail(f"{rel(mpath)}: profile '{m['profile']}' passt nicht zum Ordner {unit.name}")
    paths = openapis.get(unit, {}).get("paths", {})
    docs = "\n".join(p.read_text() for p in (unit / "docs").glob("*.md"))
    types = set()
    for obj in m["objects"]:
        name = obj["name"]
        if unit / "schemas" / obj["schema"] not in schemas:
            fail(f"{m['profile']}/{name}: Schema {obj['schema']} fehlt")
        ops = paths.get("/events/{event_id}" + obj["path"])
        if ops is None:
            fail(f"{m['profile']}/{name}: Pfad {obj['path']} fehlt in der OpenAPI")
            continue
        want = {"get"} | ({"put"} if obj["access"] == "read_write" else set()) | ({"delete"} if obj.get("deletable") else set())
        have = set(ops) - {"parameters"}
        if want != have:
            fail(f"{m['profile']}/{name}: Methoden {sorted(have)} statt {sorted(want)}")
        if obj["access"] not in ("read", "read_write"):
            fail(f"{m['profile']}/{name}: access ungültig")
        if obj["access"] == "read":
            types.add(f"{name}.updated")
        else:
            types.add(f"{name}.updated")
            if obj.get("deletable"):
                types.add(f"{name}.deleted")
    snap = m["snapshot"]
    if "/events/{event_id}" + snap["path"] not in paths:
        fail(f"{m['profile']}: Snapshot-Pfad fehlt in der OpenAPI")
    for t in sorted(types):
        if f"`{t}`" not in docs:
            fail(f"{m['profile']}: Typ {t} fehlt in der Doku")
    # Beispiele für Benachrichtigungen verwenden nur erlaubte Typen
    for ex in (unit / "examples").glob("notification-*.json"):
        t = json.loads(ex.read_text())["type"]
        if t not in types:
            fail(f"{rel(ex)}: Typ {t} ist im Profil nicht definiert")
    # Template-Schlüssel stehen in der Doku
    for key, placeholders in m.get("link_templates", {}).items():
        for ph in placeholders:
            if "{" + ph + "}" not in docs:
                fail(f"{m['profile']}: Platzhalter {{{ph}}} fehlt in der Doku")
    print(f"  {m['profile']}: {len(m['objects'])} Objekte, {len(types)} Typen")

# --- 5. Markdown-Links -----------------------------------------------------------------------
section("Markdown-Links")
checked = 0
for md in ROOT.rglob("*.md"):
    for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", md.read_text()):
        target = m.group(1)
        if re.match(r"[a-z]+:", target):
            continue
        checked += 1
        if not (md.parent / target).resolve().exists():
            fail(f"{rel(md)}: Link ins Leere: {target}")
print(f"  {checked} Links geprüft")

print()
if errors:
    print(f"{len(errors)} Fehler")
    sys.exit(1)
print("Alles in Ordnung.")
