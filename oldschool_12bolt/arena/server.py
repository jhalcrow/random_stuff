#!/usr/bin/env python3
"""Run a series of games. Each side is either a local Bot or a remote agent that
talks to this process over HTTP (long-poll).

  python3 server.py --a "12 Bolt" --b "White Weenie" --games 2 --port 8701 --agents a,b
  python3 server.py --a "12 Bolt" --b "The Deck" --games 50 --bots      # bot vs bot, no HTTP

Agent protocol (plain text):
  GET  /wait/<token>   -> blocks until a decision is needed; returns the state text
                          (first line starts with '=== DECISION:') or 'WAITING' / 'SERIES OVER ...'
  POST /act/<token>    -> body is the action script; returns the outcome of that
                          script and then blocks like /wait for the next decision
"""
import argparse
import json
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import engine
from bot import Bot
from cards import DECKS


DECISION_TIMEOUT = 900  # seconds before a bot takes over a stalled decision


class Remote:
    """Policy that hands decisions to an HTTP client and waits for its answer."""

    def __init__(self, token):
        self.token = token
        self.pending = None      # (state_text)
        self.answer = queue.Queue()
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.last_result = ""
        self.series_over = None
        self.calls = 0
        self.fallbacks = 0
        self.fallback = Bot("fallback")

    def decide(self, game, p, window, error):
        text = game.render(p, window, error)
        text += "\n" + WINDOW_HELP.get(window, "")
        with self.cond:
            self.pending = text
            self.cond.notify_all()
        try:
            ans = self.answer.get(timeout=DECISION_TIMEOUT)
        except queue.Empty:
            # the agent went away: let the bot decide so the series can finish
            self.fallbacks += 1
            game.log_event(f"({p.name}'s agent timed out; bot decided this {window})")
            ans = self.fallback.decide(game, p, window, error)
        with self.cond:
            self.pending = None
        self.calls += 1
        return ans

    def wait_for_decision(self, timeout=25):
        with self.cond:
            end = time.time() + timeout
            while self.pending is None and self.series_over is None:
                remaining = end - time.time()
                if remaining <= 0:
                    return "WAITING (no decision needed yet; call /wait again)"
                self.cond.wait(remaining)
            if self.pending is not None:
                return self.pending
            return self.series_over


WINDOW_HELP = {
    "mulligan": "Reply 'keep' or 'mulligan'.",
    "main1": "Reply with one action per line (see guide): land, cast, activate, lotus, tap, attack, done.",
    "main2": "Reply with one action per line: land, cast, activate, done.",
    "block": "Reply with 'block <attacker> with <blocker>' lines, optional instants ('cast ...', 'activate <Factory>'), or 'pass'.",
    "combat": "Blocks are declared. Reply with instants / 'sac atog <artifact>' / 'activate <Order of Leitbur>' or 'pass'.",
    "respond": "A spell is on the stack. Reply 'cast <counter> target #<spell id>' or another instant, or 'pass'.",
    "eot": "End of opponent's turn. Reply with instants (e.g. 'cast Lightning Bolt target opp') or 'pass'.",
    "tutor": "Reply with the exact name of the card to fetch.",
}


class Handler(BaseHTTPRequestHandler):
    remotes = {}
    log_file = None

    def log_message(self, *a):
        pass

    def _send(self, text, code=200):
        data = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parts = self.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "wait" and parts[1] in self.remotes:
            self._send(self.remotes[parts[1]].wait_for_decision())
        elif parts == ["status"]:
            self._send(json.dumps({k: {"pending": r.pending is not None, "calls": r.calls, "fallbacks": r.fallbacks, "over": r.series_over is not None}
                                   for k, r in self.remotes.items()}))
        else:
            self._send("unknown endpoint", 404)

    def do_POST(self):
        parts = self.path.strip("/").split("/")
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode()
        if len(parts) == 2 and parts[0] == "act" and parts[1] in self.remotes:
            r = self.remotes[parts[1]]
            if r.pending is None:
                self._send("NO DECISION PENDING for you right now.\n" + r.wait_for_decision())
                return
            r.answer.put(body)
            # wait briefly for the engine to consume it, then long-poll the next decision
            time.sleep(0.05)
            self._send(r.wait_for_decision())
        else:
            self._send("unknown endpoint", 404)


def run_series(deck_a, deck_b, pol_a, pol_b, games, seed, out_path, verbose=False):
    results = []
    for i in range(games):
        first = i % 2
        g = engine.Game(deck_a, deck_b, pol_a, pol_b, seed=seed + i, first=first)
        winner = g.run()
        rec = {"game": i + 1, "on_the_play": g.players[first].name, "winner": winner.name if winner else "draw",
               "turns": g.turn, "life": {p.name: p.life for p in g.players}, "log": g.log}
        results.append(rec)
        line = f"Game {i + 1}: {rec['on_the_play']} on the play -> winner {rec['winner']} on turn {g.turn} (life {rec['life']})"
        print(line, flush=True)
        if verbose:
            print("\n".join(g.log))
        for pol in (pol_a, pol_b):
            if isinstance(pol, Remote):
                pol.last_result = line
        with open(out_path, "w") as f:
            json.dump({"a": deck_a, "b": deck_b, "results": results}, f, indent=1)
    summary = f"SERIES OVER: {deck_a} vs {deck_b}: " + ", ".join(
        f"game {r['game']}: {r['winner']} (T{r['turns']})" for r in results)
    for pol in (pol_a, pol_b):
        if isinstance(pol, Remote):
            with pol.cond:
                pol.series_over = summary
                pol.cond.notify_all()
    print(summary, flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--port", type=int, default=8701)
    ap.add_argument("--agents", default="", help="comma list of sides driven by HTTP agents: a, b, or a,b")
    ap.add_argument("--bots", action="store_true", help="both sides local bots")
    ap.add_argument("--out", default="")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    assert args.a in DECKS and args.b in DECKS, list(DECKS)
    agents = set(x.strip() for x in args.agents.split(",") if x.strip()) if not args.bots else set()
    pol_a = Remote("a") if "a" in agents else Bot("a")
    pol_b = Remote("b") if "b" in agents else Bot("b")
    out = args.out or f"results_{args.a}_vs_{args.b}.json".replace(" ", "_").replace("'", "")
    if agents:
        Handler.remotes = {k: v for k, v in (("a", pol_a), ("b", pol_b)) if isinstance(v, Remote)}
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"listening on http://127.0.0.1:{args.port}  tokens: {list(Handler.remotes)}", flush=True)
    run_series(args.a, args.b, pol_a, pol_b, args.games, args.seed, out, args.verbose)
    if agents:
        time.sleep(30)   # let the agents collect the final summary


if __name__ == "__main__":
    main()
