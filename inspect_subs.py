#!/usr/bin/env python3
"""Print the substitution, card and HIA events of one match, with player names.

Use it to look into a warning such as "9 replacements on but 10 off".

  python inspect_subs.py --date 2026-10-17 --team "New Zealand"
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import rugby_minutes as rm


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="match date, YYYY-MM-DD")
    ap.add_argument("--team", required=True)
    ap.add_argument("--db", default="rugby.db")
    ap.add_argument("--cache-dir", default="cache")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    rows = conn.execute(
        "SELECT match_id, team_a, team_b FROM matches WHERE substr(match_date,1,10) = ? "
        "AND (lower(team_a) = lower(?) OR lower(team_b) = lower(?))",
        (args.date, args.team, args.team)).fetchall()
    if not rows:
        sys.exit("No such match in the database.")
    cache = Path(args.cache_dir)
    for mid, a, b in rows:
        summary = json.loads((cache / f"{mid}_summary.json").read_text())
        timeline = json.loads((cache / f"{mid}_timeline.json").read_text())
        names, pos = {}, {}
        for ti, team in enumerate(summary["teams"]):
            for e in team["teamList"]["list"]:
                if e.get("number") in (None, ""):
                    continue
                p = e["player"]
                label = f"#{e['number']} {(p.get('name') or {}).get('display')}"
                for key in (p.get("id"), p.get("altId")):
                    if key is not None:
                        names[str(key)] = label
        print(f"\n{a} v {b}  ({args.date})  match id {mid}")
        team_names = [a, b]
        counts = {}
        for ev in sorted(timeline["timeline"], key=lambda e: e["time"]["secs"]):
            kind = rm._classify(ev)
            if kind not in ("on", "off", "red", "yellow"):
                continue
            ti = ev.get("teamIndex")
            counts[(ti, kind)] = counts.get((ti, kind), 0) + 1
            secs = ev["time"]["secs"]
            who = names.get(str(ev.get("playerId")), f"unknown ({ev.get('playerId')})")
            team = team_names[ti] if ti in (0, 1) else "?"
            print(f"  {secs // 60:3d}:{secs % 60:02d}  {team:<14}{(ev.get('typeLabel') or ev.get('type')):<34}{who}")
        for ti in (0, 1):
            print(f"  {team_names[ti]}: {counts.get((ti, 'on'), 0)} on, "
                  f"{counts.get((ti, 'off'), 0)} off")


if __name__ == "__main__":
    main()
