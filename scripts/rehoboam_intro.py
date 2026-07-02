#!/usr/bin/env python3
"""REHOBOAM intro — Westworld-style divergence sphere, pure ANSI, no deps.

A dotted sphere with a horizontal waveform ring rotating around its equator.
Animates ~4s on a TTY; prints one static frame when piped. Never raises to
the caller: any failure exits 0 silently.
"""
import math
import os
import sys
import time

W, H = 66, 24            # canvas size (chars)
CX, CY = W // 2, H // 2  # center
R = 10                   # sphere radius (rows); columns doubled for aspect
ASPECT = 2.05            # terminal cell aspect correction

CYAN = "\033[38;5;44m"
DIM = "\033[38;5;24m"
WHITE = "\033[38;5;231m"
GOLD = "\033[38;5;179m"
RESET = "\033[0m"
HIDE, SHOW = "\033[?25l", "\033[?25h"

TITLE = "R E H O B O A M"
SUB = "one head predicts · many arms act · nothing diverges unreviewed"


def frame(t: float, divergence: bool) -> str:
    grid = [[" "] * W for _ in range(H)]
    col = [[DIM] * W for _ in range(H)]

    # --- dotted sphere shell (latitude rings) ---
    for lat_i in range(1, 7):
        lat = -math.pi / 2 + lat_i * math.pi / 7
        ry = R * math.sin(lat)
        rr = R * math.cos(lat)
        for k in range(40):
            lon = k * math.tau / 40 + t * 0.15
            x = rr * math.cos(lon)
            z = rr * math.sin(lon)
            if z < -0.15 * R:          # hide most of the back face
                continue
            px = CX + int(round(x * ASPECT))
            py = CY - int(round(ry))
            if 0 <= px < W and 0 <= py < H:
                grid[py][px] = "·"
                col[py][px] = DIM

    # --- the divergence waveform ring (equator) ---
    for k in range(140):
        lon = k * math.tau / 140
        phase = lon * 6 - t * 4.0
        amp = 0.9 + 0.5 * math.sin(t * 1.3)
        if divergence and abs(((lon - t) % math.tau) - math.pi) < 0.5:
            amp += 2.2 * math.exp(-8 * (((lon - t) % math.tau) - math.pi) ** 2)
        wave = amp * math.sin(phase)
        x = (R + 1.5) * math.cos(lon + t * 0.6)
        z = (R + 1.5) * math.sin(lon + t * 0.6)
        px = CX + int(round(x * ASPECT))
        py = CY - int(round(wave))
        if 0 <= px < W and 0 <= py < H:
            front = z >= 0
            grid[py][px] = "█" if front else "▓"
            if divergence and abs(wave) > 1.6:
                col[py][px] = GOLD
            else:
                col[py][px] = CYAN if front else DIM

    # --- core dot ---
    grid[CY][CX] = "◉"
    col[CY][CX] = WHITE

    out = []
    for y in range(H):
        line, last = [], None
        for x in range(W):
            c = col[y][x]
            if grid[y][x] != " " and c != last:
                line.append(c)
                last = c
            line.append(grid[y][x])
        out.append("".join(line) + RESET)
    return "\n".join(out)


def footer(t: float) -> str:
    msgs = [
        "SYSTEM ONLINE",
        "SCOUTING LOOP",
        "COMPUTING BRIEFS",
        "DIVERGENCE WITHIN TOLERANCE",
    ]
    msg = msgs[int(t * 1.2) % len(msgs)]
    pad_t = (W - len(TITLE)) // 2
    pad_s = (W - len(SUB)) // 2
    pad_m = (W - len(msg) - 4) // 2
    return (
        f"{WHITE}{' ' * pad_t}{TITLE}{RESET}\n"
        f"{DIM}{' ' * pad_s}{SUB}{RESET}\n"
        f"{CYAN}{' ' * pad_m}[ {msg} ]{RESET}"
    )


def main() -> None:
    try:
        if not sys.stdout.isatty() or os.environ.get("REHOBOAM_NO_ANIM"):
            print(frame(1.7, divergence=True))
            print(footer(0))
            return
        sys.stdout.write(HIDE)
        t0 = time.time()
        while (t := time.time() - t0) < 4.2:
            sys.stdout.write("\033[H\033[2J")
            sys.stdout.write(frame(t, divergence=t > 2.0) + "\n")
            sys.stdout.write(footer(t) + "\n")
            sys.stdout.flush()
            time.sleep(0.05)
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
