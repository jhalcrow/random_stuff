#!/usr/bin/env python3
"""Generate a robot-shaped maze (plus its answer key) as printable SVG.

The robot is a mask of grid cells; the maze is carved inside it with a
randomized depth-first search, so every open cell is reachable and there is
exactly one path from START (top of the left antenna) to FINISH (the right
foot).  Eyes, mouth and the chest panel are holes in the mask.

    python3 robot_maze.py [seed]   ->  robot_maze.svg, robot_maze_solution.svg
"""

import random
import sys
from collections import deque

# One character per cell: '#' is part of the maze, anything else is empty.
ROBOT = """
......###........###......
......###........###......
.......#..........#.......
.......#..........#.......
....##################....
....##################....
..######....##....######..
..######....##....######..
....##################....
....##################....
....###............###....
....##################....
....##################....
...........####...........
...........####...........
.....################.....
.########################.
.########################.
.##..################..##.
.##..###..........###..##.
.##..###..........###..##.
.##..################..##.
.##..################..##.
####.################.####
#..#.################.#..#
.....################.....
.....################.....
.......####....####.......
.......####....####.......
.......####....####.......
.......####....####.......
.....######....######.....
.....######....######.....
"""

def build_mask():
    rows = [r for r in ROBOT.strip("\n").split("\n")]
    width = max(len(r) for r in rows)
    mask = {(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "#"}
    return mask, width, len(rows)


def largest_component(mask):
    seen, best = set(), set()
    for start in mask:
        if start in seen:
            continue
        comp, todo = {start}, [start]
        while todo:
            x, y = todo.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in mask and n not in comp:
                    comp.add(n)
                    todo.append(n)
        seen |= comp
        if len(comp) > len(best):
            best = comp
    return best


def carve(mask, start, rng):
    """Recursive backtracker; returns the set of open passages."""
    passages = set()
    visited = {start}
    stack = [start]
    while stack:
        x, y = stack[-1]
        nbrs = [n for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                if n in mask and n not in visited]
        if not nbrs:
            stack.pop()
            continue
        n = rng.choice(nbrs)
        passages.add(frozenset(((x, y), n)))
        visited.add(n)
        stack.append(n)
    return passages


def solve(passages, start, goal):
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if c == goal:
            break
        x, y = c
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in prev and frozenset((c, n)) in passages:
                prev[n] = c
                q.append(n)
    path, c = [], goal
    while c is not None:
        path.append(c)
        c = prev[c]
    return path[::-1]


def render(mask, passages, width, height, start, goal, path=None, title=""):
    s = 26                      # cell size in SVG units
    m = 60                      # margin
    top = 120                   # room for the title and START
    W, H = width * s + 2 * m, height * s + m + top + 30
    ox, oy = m, top

    def X(x): return ox + x * s
    def Y(y): return oy + y * s

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" font-family="Comic Sans MS, Chalkboard SE, '
           f'Comic Neue, sans-serif">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{W/2}" y="48" text-anchor="middle" font-size="38" '
           f'font-weight="bold" fill="#1d4e89">{title}</text>']

    # Robot body colour, cell by cell (light so it still prints nicely).
    cell_fill = "#dff1ff"
    for (x, y) in sorted(mask):
        colour = cell_fill
        if y <= 3:
            colour = "#fff2c2"          # antennae
        elif y <= 12:
            colour = "#e3f6e1"          # head
        elif y >= 27:
            colour = "#ffe3ec"          # legs
        out.append(f'<rect x="{X(x)}" y="{Y(y)}" width="{s+0.6}" height="{s+0.6}" '
                   f'fill="{colour}"/>')

    # Decorations in the holes: eyes, mouth, chest panel.
    def hole_rect(x0, y0, x1, y1, fill, rx=6):
        out.append(f'<rect x="{X(x0)+3}" y="{Y(y0)+3}" width="{(x1-x0)*s-6}" '
                   f'height="{(y1-y0)*s-6}" rx="{rx}" fill="{fill}"/>')

    for ex in (8, 14):                                  # eyes
        hole_rect(ex, 6, ex + 4, 8, "#1d4e89", rx=20)
        out.append(f'<circle cx="{X(ex+2.7)}" cy="{Y(6.7)}" r="7" fill="white"/>')
    hole_rect(7, 10, 19, 11, "#f28b30", rx=8)           # mouth
    for i in range(8, 19, 2):                           # teeth
        out.append(f'<line x1="{X(i)}" y1="{Y(10)+4}" x2="{X(i)}" '
                   f'y2="{Y(11)-4}" stroke="white" stroke-width="3"/>')
    hole_rect(8, 19, 18, 21, "#5b6c7d", rx=8)           # chest panel
    for i, col in enumerate(("#ff4d4d", "#ffd23f", "#3ddc84", "#3fa7ff")):
        out.append(f'<circle cx="{X(9.5+i*2.3)}" cy="{Y(20)}" r="9" fill="{col}"/>')

    # Walls: any cell edge without a passage across it.
    openings = {(start, (start[0], start[1] - 1)), (goal, (goal[0], goal[1] + 1))}
    segs = []
    for (x, y) in mask:
        for (dx, dy), (x1, y1, x2, y2) in (
                ((0, -1), (x, y, x + 1, y)),
                ((0, 1), (x, y + 1, x + 1, y + 1)),
                ((-1, 0), (x, y, x, y + 1)),
                ((1, 0), (x + 1, y, x + 1, y + 1))):
            n = (x + dx, y + dy)
            if ((x, y), n) in openings:
                continue
            if n in mask and frozenset(((x, y), n)) in passages:
                continue
            if n in mask and (dx < 0 or dy < 0):
                continue                     # shared inner wall: draw once
            segs.append(f'M{X(x1)} {Y(y1)}L{X(x2)} {Y(y2)}')
    out.append(f'<path d="{"".join(segs)}" stroke="#222" stroke-width="4" '
               f'stroke-linecap="round" fill="none"/>')

    if path:
        pts = [(start[0] + .5, start[1] - .7)] + [(x + .5, y + .5) for x, y in path] \
              + [(goal[0] + .5, goal[1] + 1.7)]
        d = "M" + "L".join(f"{X(x):.1f} {Y(y):.1f}" for x, y in pts)
        out.append(f'<path d="{d}" stroke="#e8343a" stroke-width="9" '
                   f'stroke-linejoin="round" stroke-linecap="round" fill="none" '
                   f'opacity="0.85"/>')

    # START / FINISH labels with arrows.
    sx, gy = X(start[0] + .5), Y(goal[1] + 1)
    out.append(f'<text x="{sx-14}" y="{Y(0)-22}" text-anchor="end" font-size="22" '
               f'font-weight="bold" fill="#2a9d3a">START</text>')
    out.append(f'<path d="M{sx-10} {Y(0)-30}Q{sx} {Y(0)-30} {sx} {Y(0)-6}" '
               f'stroke="#2a9d3a" stroke-width="4" fill="none" stroke-linecap="round"/>'
               f'<path d="M{sx-7} {Y(0)-13}L{sx} {Y(0)-3}L{sx+7} {Y(0)-13}" '
               f'stroke="#2a9d3a" stroke-width="4" fill="none" stroke-linecap="round" '
               f'stroke-linejoin="round"/>')
    gx = X(goal[0] + .5)
    out.append(f'<path d="M{gx} {gy+4}L{gx} {gy+22}M{gx-7} {gy+14}L{gx} {gy+24}'
               f'L{gx+7} {gy+14}" stroke="#d62828" stroke-width="4" fill="none" '
               f'stroke-linecap="round" stroke-linejoin="round"/>')
    out.append(f'<text x="{gx+16}" y="{gy+24}" font-size="22" font-weight="bold" '
               f'fill="#d62828">FINISH!</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rng = random.Random(seed)
    mask, width, height = build_mask()
    mask = largest_component(mask)
    start = (7, 0)              # top of the left antenna
    goal = (19, 32)             # bottom of the right foot
    assert start in mask and goal in mask
    passages = carve(mask, start, rng)
    path = solve(passages, start, goal)
    with open("robot_maze.svg", "w") as f:
        f.write(render(mask, passages, width, height, start, goal,
                       title="Help Robo Find the Way Down!"))
    with open("robot_maze_solution.svg", "w") as f:
        f.write(render(mask, passages, width, height, start, goal, path,
                       title="Robo Maze — Answer Key"))
    print(f"seed {seed}: {len(mask)} cells, solution {len(path)} steps")


if __name__ == "__main__":
    main()
