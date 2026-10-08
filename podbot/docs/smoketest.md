# POD-Bot Smoke Test

Run this on the target setup (listen server, final WON CS 1.6) before and after
changes to shared decision, movement, or engine-hook code. Use the same maps and
waypoint files (`.pwf`, plus `.pxp` experience) each time so runs are comparable.

## Setup

- Install the DLL as the original POD-Bot 2.6 does, with `BotNames.txt`, `BotChat.txt`,
  `Botskill.cfg`, `BotLogos.cfg` and `BotWeapons.cfg` in `cstrike\PODBot\`.
- Delete `podbot.log` and `PODERROR.txt` (game working directory) before the run.
- Console commands below are issued by the listen-server host.
- Record: build (git revision, Release/Debug), map, date, pass/fail per step.

## Checklist

| # | Step | Expected |
|---|------|----------|
| 1 | Start the game with the bot DLL, load a map that has a waypoint file | Loads without crash; no `PODERROR.txt` |
| 2 | `addbot` (no arguments) | A bot joins with a random skill, team and model |
| 3 | `addbot <skill> <team> <name>` for each team | Bot joins the requested team with that name |
| 4 | `podbotmenu` | Menu opens and selections respond |
| 5 | Wait for a new round | Bots buy weapons and equipment in the buy phase |
| 6 | Watch for 2 minutes | Bots follow waypoints, open doors, climb ladders, do not stay stuck |
| 7 | Let bots meet enemies or other bots | Bots aim, shoot, reload, switch weapons, use grenades |
| 8 | `botchat 1`, then speak keywords or get killed | Bots send chat messages and reply to chat |
| 9 | `killbots` | Bots die and respawn next round |
| 10 | `removebots` | All bots leave without crash |
| 11 | `addbot` until the server is full; then, on a small server, join/leave/rejoin as a human | Slot handling stays stable; a bot is evicted for the human |
| 12 | Play a bomb or hostage map through to a full round | Bots plant/defuse or rescue hostages |
| 13 | Change map (several times) | Bots re-add as configured, no crash, waypoints reload |
| 14 | Exit the game | Clean exit |

## Capture on failure

- `podbot.log` and `PODERROR.txt` from the game working directory.
- Map name, bot count, step number and what was on screen.
- Console `listbots` output, if the console is still usable.

## Automated run

`podbot/test/run_test.bat <game_dir> [map] [lan_ip]` purges old logs, then runs
phase 1 (`smoketest.cfg`, criteria 1-13 on one host) and phase 2
(`smoketest_slots.cfg` + `smoketest_client.cfg`, criterion 11 with a second
`hl.exe` joining by LAN IP). `parse_results.py <game_dir>` prints PASS/FAIL/MANUAL
per criterion. Set `SKIP_PHASE2=1` to skip phase 2. Items 5-8 and 12 need an
in-game eyeball on the first baseline run.
