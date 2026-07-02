#!/usr/bin/env python3
"""BRIGADE intro — the kitchen pass, pure ANSI, no deps.

Steam drifts over the toque, tickets print on the rail one by one, status
messages rotate, and service is called. ~4s on a TTY; a single static frame
when piped. Never raises to the caller: any failure exits 0 silently.

Formerly known as Rehoboam — the machine learned to cook.
"""
import math
import os
import sys
import time

W = 66

WHITE = "\033[38;5;255m"
STEEL = "\033[38;5;250m"
DIMGR = "\033[38;5;242m"
GOLD = "\033[38;5;179m"
COPPER = "\033[38;5;173m"
CREAM = "\033[38;5;230m"
RESET = "\033[0m"
HIDE, SHOW = "\033[?25l", "\033[?25h"

TICKETS = ["TICKET #1", "TICKET #2", "TICKET #3"]
STATIONS = ["saucier", "grillardin", "patissier"]
MSGS = ["MISE EN PLACE", "FIRING TICKETS", "PLATES AT THE PASS", "SERVICE!"]
SUB = "one chef writes the menu · a brigade cooks it"
SUB2 = "nothing leaves the pass untasted"


def center(s: str, visible_len: int | None = None) -> str:
    n = visible_len if visible_len is not None else len(s)
    return " " * max((W - n) // 2, 0) + s


def steam_line(t: float, row: int) -> str:
    """A wavering line of steam puffs above the toque."""
    puffs = []
    for i in range(5):
        x = math.sin(t * 1.7 + i * 1.9 + row * 0.8)
        ch = "(" if x < -0.33 else (")" if x > 0.33 else "~")
        puffs.append(ch)
    body = "  ".join(puffs)
    drift = int(round(math.sin(t * 0.9 + row) * 2))
    pad = max((W - len(body)) // 2 + drift, 0)
    return " " * pad + DIMGR + body + RESET


def frame(t: float) -> list[str]:
    lines: list[str] = [""]

    # steam (two rows, fading upward)
    lines.append(steam_line(t, 0))
    lines.append(steam_line(t, 1))

    # the toque
    toque = [
        ".-~~~~-~~~~-~~~~-~~~~-.",
        "(   B R I G A D E     )",
        " '-.               .-' ",
        "    |=============|    ",
        "    |_____________|    ",
    ]
    for row in toque:
        lines.append(center(WHITE + row + RESET, len(row)))

    lines.append("")

    # ticket rail — tickets print one by one (typewriter by time)
    shown = min(int(t * 1.4) + 1, len(TICKETS))
    cells = []
    for i, name in enumerate(TICKETS):
        if i < shown:
            chars = int(max(0, (t * 1.4 + 1 - i)) * 12)
            cells.append(f" {name[:chars]:<9} ")
        else:
            cells.append(" " * 11)
    rail_top = "═══╦" + "╦".join("═" * 11 for _ in TICKETS) + "╦═══"
    rail_mid = "   ║" + "║".join(GOLD + c + STEEL for c in cells) + "║   "
    rail_bot = "───╨" + "╨".join("─" * 11 for _ in TICKETS) + "╨───"
    lines.append(center(STEEL + rail_top + RESET, len(rail_top)))
    lines.append(center(STEEL + rail_mid + RESET, len(rail_top)))
    lines.append(center(STEEL + rail_bot + RESET, len(rail_top)))

    # stations
    st = "   ".join(f"[ {s} ]" for s in STATIONS)
    lines.append(center(COPPER + st + RESET, len(st)))
    lines.append("")

    # the pass
    label = " THE PASS "
    side = (W - len(label) - 8) // 2
    passline = "─" * side + label + "─" * side
    lines.append(center(GOLD + passline + RESET, len(passline)))

    # status message + bell
    msg = MSGS[min(int(t * 1.1), len(MSGS) - 1)]
    bell = "🔔 " if msg == "SERVICE!" else "   "
    m = f"{bell}[ {msg} ]"
    lines.append("")
    lines.append(center(CREAM + m + RESET, len(m)))

    # footer
    lines.append("")
    lines.append(center(DIMGR + SUB + RESET, len(SUB)))
    lines.append(center(DIMGR + SUB2 + RESET, len(SUB2)))
    return lines


def main() -> None:
    try:
        if not sys.stdout.isatty() or os.environ.get("BRIGADE_NO_ANIM"):
            print("\n".join(frame(3.4)))
            return
        sys.stdout.write(HIDE)
        t0 = time.time()
        while (t := time.time() - t0) < 4.4:
            sys.stdout.write("\033[H\033[2J")
            sys.stdout.write("\n".join(frame(t)) + "\n")
            sys.stdout.flush()
            time.sleep(0.06)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
    finally:
        try:
            sys.stdout.write(SHOW + RESET + "\n")
            sys.stdout.flush()
        except Exception:
            pass


if __name__ == "__main__":
    main()
