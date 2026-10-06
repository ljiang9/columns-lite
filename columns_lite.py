#!/usr/bin/env python3
"""columns-lite: falling 3-jewel columns, match 3+ horizontally / vertically / diagonally.

Board is WIDTH x HEIGHT (6x13). Pieces are vertical triplets of jewels (colors 0-5).
Gravity pulls cells down; cascade: find all matches, clear, re-apply gravity, repeat.
"""
import argparse
import random
import sys

WIDTH = 6
HEIGHT = 13
COLORS = 6
EMPTY = -1

# match directions: right, down, down-right, down-left (checked per cell)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


class IllegalMove(Exception):
    pass


class Board:
    def __init__(self):
        # grid[y][x]; y=0 is top row
        self.grid = [[EMPTY] * WIDTH for _ in range(HEIGHT)]
        self.score = 0
        self.cleared_total = 0

    def copy(self):
        b = Board()
        b.grid = [row[:] for row in self.grid]
        b.score = self.score
        b.cleared_total = self.cleared_total
        return b

    def cell(self, x, y):
        return self.grid[y][x]

    def column_height(self, x):
        """How many cells are filled in column x (from bottom)."""
        h = 0
        for y in range(HEIGHT - 1, -1, -1):
            if self.grid[y][x] != EMPTY:
                h += 1
            else:
                break
        return h

    def can_place(self, x):
        """A triplet fits if there are at least 3 empty cells above the stack in column x."""
        return self.column_height(x) <= HEIGHT - 3

    def place(self, x, triplet, rot=0):
        """Drop a vertical triplet (3 colors, top to bottom) into column x.
        rot: 0,1,2 rotates the triplet cyclically (which color ends up on top).
        Returns number of jewels cleared in cascade."""
        if not (0 <= x < WIDTH):
            raise IllegalMove("列号越界")
        if not self.can_place(x):
            raise IllegalMove("该列已满，放不下三格方块")
        t = list(triplet)
        rot %= 3
        t = t[-rot:] + t[:-rot] if rot else t
        # find landing: stack sits on top of existing pile
        h = self.column_height(x)
        top = HEIGHT - h - 3  # topmost of the three
        for i, c in enumerate(t):
            self.grid[top + i][x] = c
        cleared = self.cascade()
        return cleared

    def matches(self):
        """Return set of (x,y) cells in any 3+ line."""
        found = set()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                c = self.grid[y][x]
                if c == EMPTY:
                    continue
                for dx, dy in DIRS:
                    line = [(x, y)]
                    nx, ny = x + dx, y + dy
                    while 0 <= nx < WIDTH and 0 <= ny < HEIGHT and self.grid[ny][nx] == c:
                        line.append((nx, ny))
                        nx += dx
                        ny += dy
                    if len(line) >= 3:
                        found.update(line)
        return found

    def apply_gravity(self):
        for x in range(WIDTH):
            col = [self.grid[y][x] for y in range(HEIGHT) if self.grid[y][x] != EMPTY]
            col = [EMPTY] * (HEIGHT - len(col)) + col
            for y in range(HEIGHT):
                self.grid[y][x] = col[y]

    def cascade(self):
        """Clear matches + gravity repeatedly. Returns total jewels cleared."""
        total = 0
        combo = 0
        while True:
            m = self.matches()
            if not m:
                break
            combo += 1
            total += len(m)
            self.cleared_total += len(m)
            self.score += len(m) * 10 * combo
            for (x, y) in m:
                self.grid[y][x] = EMPTY
            self.apply_gravity()
        return total

    def is_full(self):
        return not any(self.can_place(x) for x in range(WIDTH))


def legal_moves(board):
    return [x for x in range(WIDTH) if board.can_place(x)]


def choose_move(board, triplet, rng):
    """Greedy 1-ply: try each column and rotation, pick best by (cleared, then height)."""
    best = None
    best_key = None
    for x in legal_moves(board):
        for rot in range(3):
            sim = board.copy()
            cleared = sim.place(x, triplet, rot)
            # prefer clears; tie-break: lowest stack, then lowest score? use cleared, then -max height
            maxh = max(sim.column_height(c) for c in range(WIDTH))
            key = (cleared, -maxh)
            if best_key is None or key > best_key:
                best_key = key
                best = (x, rot)
    if best is None:
        return None
    return best


GLYPHS = "●◆▲■★✚"


def render(board, triplet=None, rot=0):
    lines = []
    lines.append("┌" + "─" * (WIDTH * 2 - 1) + "┐")
    t = list(triplet) if triplet else []
    if rot:
        t = t[-rot:] + t[:-rot]
    for y in range(HEIGHT):
        row = []
        for x in range(WIDTH):
            c = board.grid[y][x]
            row.append(GLYPHS[c] if c != EMPTY else "·")
        lines.append("│" + " ".join(row) + "│")
    lines.append("└" + "─" * (WIDTH * 2 - 1) + "┘")
    lines.append(" " + " ".join(str(i) for i in range(WIDTH)))
    if triplet:
        lines.append("下一组: " + " ".join(GLYPHS[c] for c in t) + " (旋转0-2)")
    return "\n".join(lines)


def play_auto(games=5, pieces=200, seed=42, verbose=False):
    rng = random.Random(seed)
    results = []
    for g in range(games):
        board = Board()
        for p in range(pieces):
            if board.is_full():
                break
            triplet = [rng.randrange(COLORS) for _ in range(3)]
            mv = choose_move(board, triplet, rng)
            if mv is None:
                break
            board.place(mv[0], triplet, mv[1])
            if verbose and p < 3:
                print(render(board))
        results.append((board.score, board.cleared_total))
        print(f"第 {g+1}/{games} 局: 得分 {board.score}, 消除 {board.cleared_total} 颗")
    scores = [r[0] for r in results]
    print(f"总计: 平均分 {sum(scores)/len(scores):.1f}, 最高 {max(scores)}")
    return results


def play_interactive():
    if not sys.stdin.isatty():
        print("交互模式需要终端；请用 --auto 看自动演示。")
        sys.exit(2)
    rng = random.Random()
    board = Board()
    n = 0
    print("=== columns-lite ===")
    print("命令: 列号 [旋转]，如 '2' 或 '2 1'；q 退出。")
    while not board.is_full():
        triplet = [rng.randrange(COLORS) for _ in range(3)]
        print(render(board, triplet))
        raw = input("落子> ").strip()
        if raw.lower() in ("q", "quit"):
            break
        parts = raw.split()
        try:
            x = int(parts[0])
            rot = int(parts[1]) if len(parts) > 1 else 0
            cleared = board.place(x, triplet, rot)
            n += 1
            if cleared:
                print(f"消除 {cleared} 颗！得分 {board.score}")
        except (ValueError, IllegalMove) as e:
            print("非法:", e)
    print(f"游戏结束！共放 {n} 组，得分 {board.score}")
    print(render(board))


def main(argv=None):
    ap = argparse.ArgumentParser(description="columns-lite: 三色柱消除（match-3）")
    ap.add_argument("--auto", action="store_true", help="AI 自动演示")
    ap.add_argument("--games", type=int, default=5, help="自动演示局数")
    ap.add_argument("--pieces", type=int, default=200, help="每局最多方块数")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    ap.add_argument("--verbose", action="store_true", help="输出棋盘")
    args = ap.parse_args(argv)
    if args.auto:
        play_auto(args.games, args.pieces, args.seed, args.verbose)
    else:
        play_interactive()


if __name__ == "__main__":
    main()
