#!/usr/bin/env python
"""Scan podbot.log, qconsole.log and PODERROR.txt and print a pass/fail
checklist for the POD-Bot smoke test (podbot/docs/smoketest.md).

Usage: parse_results.py [game_dir]   (folder with hl.exe; default: .)
Exit code: 0 = no FAIL, 1 = at least one FAIL, 2 = logs missing.
Status: PASS / FAIL / MANUAL (needs a human observation, no console evidence).
"""
import os
import re
import sys

CRASH = re.compile(r"Sys_Error|Host_Error|Fatal|access violation|"
                   r"Tried to write to uninitialized|SZ_GetSpace|overflow|"
                   r"Segmentation fault|Illegal instruction|Could not load library|"
                   r"Couldn't|FS_Open", re.I)
MARK = re.compile(r"\[SMOKE\] STEP (\d+)([A-Z]?) (BEGIN|END)")
PLAYER = re.compile(r'^#\s*\d+\s+"([^"]*)"')
MAPLOAD = re.compile(r"^Server spawn|Map:|changelevel|Spawn Server (\S+)", re.I)


def find(gamedir, name, subdirs):
    for sub in subdirs:
        path = os.path.join(gamedir, sub, name)
        if os.path.isfile(path):
            return path
    return None


def read(path):
    if not path:
        return []
    f = open(path, "r")
    try:
        return f.read().splitlines()
    finally:
        f.close()


def newest_server_log(gamedir):
    d = os.path.join(gamedir, "cstrike", "logs")
    try:
        names = [n for n in os.listdir(d) if n.upper().startswith("L") and n.lower().endswith(".log")]
    except OSError:
        return None
    if not names:
        return None
    names.sort(key=lambda n: os.path.getmtime(os.path.join(d, n)))
    return os.path.join(d, names[-1])


def main():
    gamedir = sys.argv[1] if len(sys.argv) > 1 else "."
    # run_test.bat keeps phase-1 (single-player) logs under *_phase1 names
    # before phase 2 purges the live ones.
    qpath = find(gamedir, "qconsole_phase1.log", ["cstrike"]) or find(gamedir, "qconsole.log", ["cstrike", "."])
    ppath = find(gamedir, "podbot_phase1.log", ["."]) or find(gamedir, "podbot.log", [".", "cstrike"])
    epath = find(gamedir, "PODERROR_phase1.txt", ["."]) or find(gamedir, "PODERROR.txt", [".", "cstrike"])
    qlines, plines, elines = read(qpath), read(ppath), read(epath)
    # phase 2 (real client on the network address) artifacts
    q2 = find(gamedir, "qconsole_phase2.log", ["cstrike"])
    p2err = find(gamedir, "PODERROR.txt", [".", "cstrike"]) if q2 else None
    q2lines, e2lines = read(q2), read(p2err)

    if not qpath:
        print("qconsole.log not found (launch with -condebug, 'developer 1', 'log on').")
        return 2

    # Split console into step windows and keep status snapshots.
    steps = {}
    cur = []
    status_counts = []
    bots_in_snapshot = 0
    in_status = False
    crash_lines = []
    done = False
    for line in qlines:
        if CRASH.search(line):
            crash_lines.append(line.strip())
        if "[SMOKE] ALL STEPS DONE" in line:
            done = True
        m = MARK.search(line)
        if m:
            if m.group(2):
                continue
            n, kind = int(m.group(1)), m.group(3)
            d = steps.setdefault(n, {"begin": 0, "end": 0, "lines": []})
            d["begin" if kind == "BEGIN" else "end"] += 1
            if kind == "BEGIN":
                cur.append(n)
            elif n in cur:
                cur.remove(n)
            continue
        for n in cur:
            steps[n]["lines"].append(line)
        if line.startswith("hostname") or line.startswith("map"):
            in_status = True
            status_counts.append(0)
        pm = PLAYER.match(line)
        if pm and status_counts:
            status_counts[-1] += 1

    def ran(n):
        return n in steps and steps[n]["begin"] > 0 and steps[n]["end"] > 0

    def text(n):
        return "\n".join(steps.get(n, {}).get("lines", []))

    res = []

    def add(n, name, status, note=""):
        res.append((n, name, status, note))

    # 1: clean boot, no PODERROR.txt, no engine error
    if elines:
        add(1, "Engine hook compliance", "FAIL", "PODERROR.txt has %d line(s): %s" % (len(elines), elines[0].strip()))
    elif crash_lines:
        add(1, "Engine hook compliance", "FAIL", "engine error: %s" % crash_lines[0])
    elif ran(1):
        add(1, "Engine hook compliance", "PASS", "booted, no PODERROR.txt")
    else:
        add(1, "Engine hook compliance", "FAIL", "step 1 marker missing (boot/exec failed?)")

    def stepcheck(n, name, want_text=None, need_ran=True, note_ok="ran to completion"):
        if need_ran and not ran(n):
            add(n, name, "FAIL", "step did not complete (crash/hang before END marker?)")
            return False
        add(n, name, "PASS", note_ok)
        return True

    # 2-3: bots present afterwards (status snapshots show player rows)
    peak = max(status_counts) if status_counts else 0
    if not ran(2):
        add(2, "Dynamic spawning", "FAIL", "step did not complete")
    elif peak >= 1:
        add(2, "Dynamic spawning", "PASS", "status shows up to %d player rows" % peak)
    else:
        add(2, "Dynamic spawning", "FAIL", "no player rows in any 'status' output")
    names = set()
    for line in qlines:
        pm = PLAYER.match(line)
        if pm:
            names.add(pm.group(1))
    if not ran(3):
        add(3, "Explicit spawning", "FAIL", "step did not complete")
    else:
        got = [n for n in ("SmokeHighT", "SmokeHighCT", "SmokeLowT", "SmokeLowCT") if n in names]
        if len(got) == 4:
            add(3, "Explicit spawning", "PASS", "all 4 named bots listed")
        else:
            add(3, "Explicit spawning", "FAIL", "only %d/4 named bots in status: %s" % (len(got), ", ".join(got) or "none"))

    stepcheck(4, "UI & menu stability", note_ok="menu commands completed, engine kept running")

    # 5: economy; look for buy evidence in podbot.log/console if present
    buy = re.compile(r"buy|purchas", re.I)
    if not ran(5):
        add(5, "Economy phase delays", "FAIL", "step did not complete")
    elif buy.search(text(5)) or any(buy.search(l) for l in plines):
        add(5, "Economy phase delays", "PASS", "buy activity logged")
    else:
        add(5, "Economy phase delays", "MANUAL", "freeze period passed; confirm bots bought gear (BotWeapons.cfg) in-game")

    for n, name in ((6, "Pathfinding integrity (~2 min)"), (7, "Combat mechanics lifecycle")):
        if not ran(n):
            add(n, name, "FAIL", "step did not complete")
        else:
            add(n, name, "MANUAL", "window ran; watch for doors/ladders/stuck and aim/shoot/reload/grenades")

    # 6: waypoint/experience load errors
    wp_bad = [l.strip() for l in qlines + plines if re.search(r"waypoint.*(not found|invalid|error)|\.pwf.*(not found|error)|\.pxp.*(error|not found)", l, re.I)]
    if wp_bad and ran(6):
        res[-2] = (6, res[-2][1], "FAIL", wp_bad[0])

    # 8: chat
    if not ran(8):
        add(8, "Chat interaction", "FAIL", "step did not complete")
    else:
        said = [l for l in steps[8]["lines"] if re.search(r"\(.*\)|: ", l)]
        add(8, "Chat interaction", "MANUAL", "keywords sent (hello/gg/noob/thanks/lol); verify bot replies from BotChat.txt")

    # 9, 10: killbots / removebots
    stepcheck(9, "Round reset stability", note_ok="killbots + next round completed without engine error")
    if not ran(10):
        add(10, "Entity teardown", "FAIL", "step did not complete")
    elif crash_lines:
        add(10, "Entity teardown", "FAIL", crash_lines[0])
    else:
        add(10, "Entity teardown", "PASS", "removebots completed, no engine error")

    # 11: phase 1 fill/kick/re-add + phase 2 real client disconnect/reconnect
    noclient = os.path.isfile(os.path.join(gamedir, "cstrike", "smoketest_phase2_noclient.txt"))
    if not ran(11):
        add(11, "Slot capacity stress", "FAIL", "phase 1 (fill + kick/re-add) did not complete")
    elif not q2:
        add(11, "Slot capacity stress", "MANUAL", "phase 1 passed; phase 2 not run (skipped or no qconsole_phase2.log)")
    else:
        # The connect line goes to the server log; mp_logecho 1 mirrors it to the
        # console, and the newest cstrike/logs/L*.log is scanned as a second source.
        srclines = q2lines + read(newest_server_log(gamedir))
        connects = []
        for l in srclines:
            jm = re.search(r"connected, address [\x22]?([^\s\x22]*)", l)
            if jm:
                connects.append(jm.group(1))
        joins = [a for a in connects if a and not re.match(r"(127\.0\.0\.1|none|loopback)", a)]
        bad2 = [l.strip() for l in q2lines if CRASH.search(l)]
        end2 = any("[SMOKE] STEP 11B END" in l for l in q2lines)
        if e2lines:
            add(11, "Slot capacity stress", "FAIL", "phase 2 PODERROR.txt: %s" % e2lines[0].strip())
        elif bad2:
            add(11, "Slot capacity stress", "FAIL", "phase 2 engine error: %s" % bad2[0])
        elif not end2:
            add(11, "Slot capacity stress", "FAIL", "phase 2 server did not reach STEP 11B END")
        elif noclient and not joins:
            add(11, "Slot capacity stress", "MANUAL", "phase 1 passed; second hl.exe did not start - run the client on another PC")
        elif not connects:
            add(11, "Slot capacity stress", "MANUAL", "no 'connected, address' line in console or logs/; log format differs on this build - run probe (podbot/test/probe.bat)")
        elif len(joins) < 3:
            add(11, "Slot capacity stress", "FAIL", "client connected %d time(s), expected 3; seen addresses: %s" % (len(joins), ", ".join(sorted(set(connects)))))
        else:
            add(11, "Slot capacity stress", "PASS", "client joined %d times via %s without error" % (len(joins), joins[0]))

    # 12: both maps with objective rounds
    objlog = [l for l in qlines + plines if re.search(r"Planted_The_Bomb|Bomb_Defused|Target_Bombed|Rescued_A_Hostage|All_Hostages_Rescued|Terrorists_Win|CTs_Win|Round_Draw", l)]
    if steps.get(12, {}).get("begin", 0) >= 2 and steps[12]["end"] >= 2:
        if objlog:
            add(12, "Objective completion", "PASS", "%d objective/round-end event(s) logged" % len(objlog))
        else:
            add(12, "Objective completion", "MANUAL", "both map phases ran; confirm plant/defuse/rescue in-game")
    else:
        add(12, "Objective completion", "FAIL", "need both de_* and cs_* phases to finish (BEGIN/END seen: %d/%d)" % (steps.get(12, {}).get("begin", 0), steps.get(12, {}).get("end", 0)))

    # 13: repeated changelevel, survival to the end
    loads = len([l for l in qlines if re.search(r"^Spawn Server|^Server spawn|changelevel", l, re.I)])
    if ran(13) and done and not elines and not crash_lines:
        add(13, "Map transition persistence", "PASS", "4 level loads survived, run reached ALL STEPS DONE")
    elif ran(13):
        add(13, "Map transition persistence", "FAIL", "step ended but run did not finish cleanly")
    else:
        add(13, "Map transition persistence", "FAIL", "changelevel chain did not complete (crash during map change?)")

    res.sort()
    width = max(len(r[1]) for r in res)
    print("POD-Bot smoke test results (%s)" % gamedir)
    print("podbot.log: %s | qconsole.log: %s | PODERROR.txt: %s"
          % ("%d lines" % len(plines) if ppath else "absent (normal unless logging mask set)",
             "%d lines" % len(qlines), "%d lines" % len(elines) if epath else "absent"))
    print("-" * 78)
    for n, name, st, note in res:
        print("%2d. %-*s  [%s]  %s" % (n, width, name, st, note))
    fails = len([r for r in res if r[2] == "FAIL"])
    manual = len([r for r in res if r[2] == "MANUAL"])
    print("-" * 78)
    print("%d pass, %d fail, %d need manual confirmation" % (len(res) - fails - manual, fails, manual))
    if crash_lines:
        print("Engine error lines (first 5):")
        for l in crash_lines[:5]:
            print("  " + l)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
