#!/usr/bin/env python3
"""Erzeugt die Beispiele des Profils `league` aus zwei durchgehenden Szenarien.

Alle Dateien in profiles/league/examples/ (außer index.yaml) entstehen hier aus denselben Daten,
damit Snapshot, Einzelobjekte und Benachrichtigungen nie auseinanderlaufen. Die Daten sind erfunden.

Szenario 1 (Modus LEAGUE): Testliga Recurve, Wettkampftag 4, 8 Mannschaften, 7 Matches mit je 4 Begegnungen.
  Match 1 ist beendet, Match 2 läuft (Satz 3 wird geschossen), die übrigen sind gesperrt.
Szenario 2 (Modus KNOCKOUT): Testpokal Recurve, 4 Mannschaften. In Match 1 endet eine Begegnung 5:5 nach Satzpunkten
  und braucht ein Stechen (`shoot_off_pending`), die andere ist entschieden.

Spielwerte wie in der Liga: 5 Sätze, je Satz 3 Schützen mit 2 Pfeilen, Pfeilwerte 0 bis 10, Sieg im Satz = 2 Satzpunkte,
Gleichstand = 1, `points_to_win` = 6; ein Match endet, sobald eine Mannschaft 6 Satzpunkte hat.

Aufruf:  python tools/make_examples.py      (danach: python tools/validate.py)
"""
from __future__ import annotations

import itertools
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "profiles" / "league" / "examples"
SETS, ATHLETES, ARROWS, POINTS_TO_WIN = 5, 3, 2, 6

TEAMS = {  # id: (Name, Schützen)
    "t_1": ("SV Adler Testheim 1", ["Jonas Berger", "Lea Kaiser", "Murat Yildiz", "Sofia Lenz", "Tobias Ebert"]),
    "t_2": ("BSC Blauer Pfeil 2", ["Anja Vogel", "Ben Hahn", "Carla Roth", "Dennis Pohl", "Elif Kaya"]),
    "t_3": ("Schützenverein Eichwald 3", ["Frank Seidel", "Greta Lang", "Hannes Brandt", "Ines Krause", "Jörg Winter"]),
    "t_4": ("SC Goldener Bogen 4", ["Katrin Beck", "Lukas Fischer", "Mia Schulte", "Nils Arnold", "Olga Petrova"]),
    "t_5": ("TSV Haselbach 5", ["Uwe Köhler", "Vera Mayer", "Walter Fuchs", "Xenia Scholz", "Yannick Müller"]),
    "t_6": ("ASV Münzenberg 6", ["Paul Dietrich", "Rita Graf", "Stefan Voss", "Tamara Ott", "Ulrich Sommer"]),
    "t_7": ("SV Schwarzwald-Bogner 7", ["Viktor Haas", "Wiebke Lorenz", "Xaver Moser", "Yvonne Thiel", "Zoran Marić"]),
    "t_8": ("Bogensportclub Weißtal 8", ["Jana Hoffmann", "Klaus Richter", "Lena Schröder", "Michael Zimmermann", "Nina Hartmann"]),
}
LOCATION = {"name": "Schützenhaus Musterstadt", "street": "Schützenweg 1", "postal_code": "12345", "city": "Musterstadt",
            "info": "Parkplatz hinter dem Gebäude"}
# Stand vor dem Wettkampftag: (Matchpunkte gewonnen, verloren, Satzpunkte gewonnen, verloren)
BEFORE = {"t_3": (22, 12, 87, 67), "t_7": (19, 17, 77, 75), "t_2": (18, 16, 69, 65), "t_8": (18, 16, 74, 80),
          "t_5": (17, 17, 76, 66), "t_4": (17, 19, 81, 83), "t_6": (16, 18, 65, 79), "t_1": (11, 23, 69, 83)}


def split(name: str) -> tuple[str, str]:
    first, last = name.split(" ", 1)
    return first, last


def roster(tid: str) -> dict:
    return {"team": {"id": tid, "name": TEAMS[tid][0]}, "members": [
        {"start_number": i, "first_name": split(n)[0], "last_name": split(n)[1]} for i, n in enumerate(TEAMS[tid][1], start=1)]}


def round_robin(n: int) -> list[list[tuple[int, int]]]:
    teams = list(range(n))
    rounds = []
    for _ in range(n - 1):
        rounds.append([(teams[i], teams[n - 1 - i]) for i in range(n // 2)])
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return rounds


def make_matches(plan: list[list[tuple[str, str]]]) -> list[dict]:
    """plan: je Match die Begegnungen als (Team-ID, Team-ID); Scheibe 1:2, 3:4, ..."""
    out = []
    for m, pairs in enumerate(plan, start=1):
        sheets = []
        for b, pair in enumerate(pairs):
            for k, tid in enumerate(pair):
                target = 2 * b + k + 1
                sheets.append({"id": f"ss_{m}{target:02d}", "target_number": target, "team": {"id": tid, "name": TEAMS[tid][0]}})
        out.append({"number": m, "scoresheets": sheets})
    return out


def opponent(sid: str) -> str:
    t = int(sid[4:])
    return f"ss_{sid[3]}{(t + 1 if t % 2 else t - 1):02d}"


def lineup(rng: random.Random, sid: str, tid: str) -> dict:
    members = TEAMS[tid][1]
    chosen = rng.sample(range(len(members)), ATHLETES)
    return {"scoresheet_id": sid, "athletes": [
        {"position": pos, "start_number": n + 1, "first_name": split(members[n])[0], "last_name": split(members[n])[1]}
        for pos, n in enumerate(chosen, start=1)]}


def arrows_for_set(rng: random.Random, strength: float) -> list[list[int]]:
    def arrow() -> int:
        return 0 if rng.random() < 0.03 else max(1, min(10, round(rng.gauss(strength, 1.6))))
    return [[arrow() for _ in range(ARROWS)] for _ in range(ATHLETES)]


def sheet_team(matches: list[dict]) -> dict[str, str]:
    return {s["id"]: s["team"]["id"] for m in matches for s in m["scoresheets"]}


def play_pair(rng, a: str, b: str, max_sets: int, teams: dict[str, str], lineups: dict, strength: dict,
              penalties: dict | None = None) -> dict:
    """Spielt die Begegnung a gegen b Satz für Satz, bis eine Mannschaft 6 Satzpunkte hat oder max_sets erreicht sind."""
    official, total = {}, {a: 0, b: 0}
    for n in range(1, max_sets + 1):
        ring = {}
        for sid in (a, b):
            pen = (penalties or {}).get((sid, n), 0)
            athletes = arrows_for_set(rng, strength[teams[sid]])
            official[(sid, n)] = {"scoresheet_id": sid, "set_number": n, "penalty_points": pen, "athletes": [
                {"start_number": lineups[sid]["athletes"][i]["start_number"], "arrows": arr} for i, arr in enumerate(athletes)]}
            ring[sid] = sum(sum(arr) for arr in athletes) - pen
        if ring[a] != ring[b]:
            total[a if ring[a] > ring[b] else b] += 2
        else:
            total[a] += 1
            total[b] += 1
        if max(total.values()) >= POINTS_TO_WIN:
            break
    return official


def ring_sum(official: dict, sid: str, n: int) -> int:
    o = official[(sid, n)]
    return sum(sum(s["arrows"]) for s in o["athletes"]) - o["penalty_points"]


def results(official: dict, sid: str, mode: str, shoot_off: dict[str, bool]) -> dict:
    opp = opponent(sid)
    sets, total, opp_total = [], 0, 0
    for n in range(1, SETS + 1):
        if (sid, n) not in official or (opp, n) not in official:
            break
        mine, theirs = ring_sum(official, sid, n), ring_sum(official, opp, n)
        pts = 2 if mine > theirs else (1 if mine == theirs else 0)
        total += pts
        opp_total += 2 - pts
        sets.append({"set_number": n, "ring_sum": mine, "set_points": pts})
    over = max(total, opp_total) >= POINTS_TO_WIN or len(sets) == SETS
    tied = over and total == opp_total
    pending = tied and mode == "KNOCKOUT" and sid not in shoot_off and opp not in shoot_off
    decided = over and not pending
    mp = None
    if decided:
        if tied and mode == "KNOCKOUT":
            mp = 2 if shoot_off.get(sid, not shoot_off.get(opp)) else 0
        else:
            mp = 2 if total > opp_total else (1 if total == opp_total else 0)
    return {"scoresheet_id": sid, "sets": sets, "set_points_total": total, "match_points": mp, "decided": decided,
            "shoot_off_pending": pending}


def write(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


# --- Szenario 1: Liga ----------------------------------------------------------------------------
def build_league(seed: int) -> dict | None:
    rng = random.Random(seed)
    team_ids = list(TEAMS)
    matches = make_matches([[(team_ids[a], team_ids[c]) for a, c in pairs] for pairs in round_robin(8)])
    teams = sheet_team(matches)
    strength = {tid: 7.6 + 0.2 * (i % 4) for i, tid in enumerate(team_ids)}
    lineups = {sid: lineup(rng, sid, teams[sid]) for sid in teams if sid[3] in "12"}
    official: dict = {}
    for m, max_sets in ((1, SETS), (2, 2)):
        for b in range(1, 9, 2):
            official.update(play_pair(rng, f"ss_{m}{b:02d}", f"ss_{m}{b + 1:02d}", max_sets, teams, lineups, strength,
                                      {("ss_204", 2): 10}))
    res = {sid: results(official, sid, "LEAGUE", {}) for sid in lineups}
    m1 = [r for sid, r in res.items() if sid[3] == "1"]
    lengths = [len(r["sets"]) for r in m1]
    tie_sets = sum(1 for r in res.values() for s in r["sets"] if s["set_points"] == 1)
    if not (any(r["match_points"] == 1 for r in m1) and min(lengths) < 5 and tie_sets >= 3):
        return None  # Szenario nicht abwechslungsreich genug, nächster Zufallswert

    provisional = {}
    for sid in lineups:
        t = int(sid[4:])
        if sid[3] != "2" or t > 4:
            continue
        flat = [a for sh in arrows_for_set(rng, strength[teams[sid]]) for a in sh]
        arrows, closed = (flat, True) if t <= 2 else (flat[:4] + [None, None], False)
        provisional[sid] = {"scoresheet_id": sid, "set_number": 3, "arrows": arrows, "closed": closed}

    now = {tid: list(v) for tid, v in BEFORE.items()}
    for sid, r in res.items():
        if r["decided"]:
            tid = teams[sid]
            now[tid][0] += r["match_points"]
            now[tid][1] += 2 - r["match_points"]
            now[tid][2] += r["set_points_total"]
            now[tid][3] += res[opponent(sid)]["set_points_total"]

    def order(d):
        return sorted(d.items(), key=lambda x: (-x[1][0], -(x[1][2] - x[1][3]), -x[1][2]))
    before_rank = {t: i for i, (t, _) in enumerate(order(BEFORE), 1)}
    standings = {"standings": [
        {"rank": rank, "team": {"id": tid, "name": TEAMS[tid][0]}, "match_points_won": w, "match_points_lost": lo,
         "set_points_won": sw, "set_points_lost": sl, "rank_change": before_rank[tid] - rank}
        for rank, (tid, (w, lo, sw, sl)) in enumerate(order(now), 1)]}

    plan = {"event": {"id": "ev_42", "name": "Testliga Recurve, Wettkampftag 4", "date": "2026-11-29",
                      "league_name": "Testliga Recurve", "season_name": "Runde 2026", "location": LOCATION},
            "rules": {"mode": "LEAGUE", "sets_per_match": SETS, "athletes_per_team": ATHLETES,
                      "arrows_per_athlete_per_set": ARROWS, "points_to_win": POINTS_TO_WIN},
            "matches": matches}
    state = {"state": "RUNNING", "match_states": [{"number": 1, "state": "COMPLETED"}, {"number": 2, "state": "ACTIVE"}] +
             [{"number": m, "state": "LOCKED"} for m in range(3, len(matches) + 1)]}
    snapshot = {"sequence": 119, "competition_plan": plan, "event_state": state,
                "rosters": [roster(t) for t in TEAMS], "lineups": list(lineups.values()),
                "provisional_sets": list(provisional.values()), "official_sets": [official[k] for k in sorted(official)],
                "shoot_offs": [], "results": list(res.values()), "standings": standings}
    return dict(snapshot=snapshot, plan=plan, state=state, lineup=lineups["ss_201"], provisional=provisional["ss_201"],
                official=official[("ss_204", 2)], results=res["ss_101"], standings=standings)


# --- Szenario 2: KO-Runde mit Stechen ----------------------------------------------------------
def build_knockout(seed: int) -> dict | None:
    rng = random.Random(seed)
    ids = ["t_1", "t_2", "t_3", "t_4"]
    matches = make_matches([[("t_1", "t_2"), ("t_3", "t_4")], [("t_1", "t_3"), ("t_2", "t_4")]])
    teams = sheet_team(matches)
    strength = {tid: 8.0 for tid in ids}
    lineups = {sid: lineup(rng, sid, teams[sid]) for sid in teams if sid[3] == "1"}
    official = {}
    official.update(play_pair(rng, "ss_101", "ss_102", SETS, teams, lineups, strength))
    official.update(play_pair(rng, "ss_103", "ss_104", SETS, teams, lineups, strength))
    res = {sid: results(official, sid, "KNOCKOUT", {}) for sid in lineups}
    if not (res["ss_101"]["shoot_off_pending"] and res["ss_103"]["decided"]):
        return None
    winner = {"ss_102": True}  # Das Stechen gewinnt die Mannschaft an Scheibe 2
    final = {sid: results(official, sid, "KNOCKOUT", winner) for sid in ("ss_101", "ss_102")}
    plan = {"event": {"id": "ev_43", "name": "Testpokal Recurve, Runde 1", "date": "2026-11-29", "league_name": "Testpokal Recurve",
                      "location": LOCATION},
            "rules": {"mode": "KNOCKOUT", "sets_per_match": SETS, "athletes_per_team": ATHLETES,
                      "arrows_per_athlete_per_set": ARROWS, "points_to_win": POINTS_TO_WIN},
            "matches": matches}
    state = {"state": "RUNNING", "match_states": [{"number": 1, "state": "ACTIVE"}, {"number": 2, "state": "LOCKED"}]}
    snapshot = {"sequence": 57, "competition_plan": plan, "event_state": state,
                "rosters": [roster(t) for t in ids], "lineups": list(lineups.values()), "provisional_sets": [],
                "official_sets": [official[k] for k in sorted(official)], "shoot_offs": [], "results": list(res.values()),
                "standings": {"standings": []}}
    return dict(snapshot=snapshot, pending=res["ss_101"], decided=final["ss_102"])


def main() -> None:
    league = next(r for r in (build_league(s) for s in itertools.count(1)) if r)
    ko = next(r for r in (build_knockout(s) for s in itertools.count(1)) if r)
    write("snapshot.json", league["snapshot"])
    write("competition-plan.json", league["plan"])
    write("event-state.json", league["state"])
    write("roster.json", roster("t_5"))
    write("lineup.json", league["lineup"])
    write("provisional-set.json", league["provisional"])
    write("official-set.json", league["official"])  # mit 10 Strafpunkten
    write("results.json", league["results"])
    write("standings.json", league["standings"])
    write("snapshot-knockout.json", ko["snapshot"])
    write("results-shoot-off-pending.json", ko["pending"])
    write("results-shoot-off-decided.json", ko["decided"])
    write("shoot-off.json", {"scoresheet_id": "ss_102", "won": True})
    write("notification-official-set.json", {"sequence": 118, "sent_at": "2026-11-29T10:14:07+01:00", "event_id": "ev_42",
                                             "type": "official_set.updated", "object": league["official"]})
    write("notification-lineup-deleted.json", {"sequence": 119, "sent_at": "2026-11-29T10:15:30+01:00", "event_id": "ev_42",
                                               "type": "lineup.deleted", "object": {"scoresheet_id": "ss_301"}})
    write("notification-shoot-off.json", {"sequence": 58, "sent_at": "2026-11-29T10:40:12+01:00", "event_id": "ev_43",
                                          "type": "shoot_off.updated", "object": {"scoresheet_id": "ss_102", "won": True}})
    print(f"Beispiele geschrieben nach {OUT}")


if __name__ == "__main__":
    main()
