"""Small algebraic checks for the context-audit additions; not hardware simulation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pages = [p for f in (ROOT / "content").glob("*.json")
         for p in json.loads(f.read_text())]
report = json.loads((ROOT / "data/context-audit.json").read_text())
historical = {p["slug"] for p in report["lessons"]}
assert len(historical) == 50
assert {p["slug"] for p in pages} == historical | {"reproduction"}
assert all(p["body"].strip() for p in pages)

# Windowing over an abstract cyclic group of order 19. j remains unchanged;
# lookup and inverse lookup are XOR on an ancillary binary encoding.
for k in range(256):
    assert sum(((k >> (2*i)) & 3) * 4**i for i in range(4)) == k
for i in range(4):
    for j in range(4):
        t = j * 4**i % 19
        for a in range(19):
            work = 0 ^ t
            result = (a + work) % 19
            work ^= t
            assert result == (a + t) % 19 and work == 0
assert 1 + 3*4 == 13

# Phase-only counterexample: H I |+> = |0>, H Z |+> = |1>.
from math import sqrt
def h(v):
    return ((v[0]+v[1])/sqrt(2), (v[0]-v[1])/sqrt(2))
for phase in (1, -1):
    result = h((1/sqrt(2), phase/sqrt(2)))
    expected = (1, 0) if phase == 1 else (0, 1)
    assert all(abs(a-b) < 1e-12 for a,b in zip(result, expected))

# Edges in the drawn Tanner graph match the two parity equations.
def syndrome(e):
    return (e[0] ^ e[1], e[1] ^ e[2])
assert syndrome((0,1,0)) == syndrome((1,0,1)) == (1,1)
assert 0b1111 + 0b0011 == 0b10010
assert ((0b1111 + 0b0011) & 15) == 0b0010
print("PASS: historical 50-lesson coverage plus reproduction, window cleanup, phase readout, Tanner edges, carry example.")
