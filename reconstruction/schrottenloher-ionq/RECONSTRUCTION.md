# From Schrottenloher's code to an IonQ-style arithmetic circuit

This is an executable reconstruction, starting with the **gate-efficient configuration of Schrottenloher's actual repository**, commit `a9538b3`. Qarton is pinned to `4fdcf6961ad45104a460e5f54d587a6776a73461`, the dependency in that commit's installer. Original source files are preserved; additions are in `ionq_reconstruction/`.

**Result:** 39,902,548 expected Toffolis for 28 window additions with the common lookup allowance, versus 57,739,612 for the baseline. The reduction is 17,837,064 (30.89%). The construction does **not** reproduce IonQ's exact circuit: the remaining difference from the roughly 39.0-million report estimate is about 0.91 million (38,993,024 is the total derived from its rounded 1.196-million per-addition budget). In particular, this reconstruction uses a different modular replay representation and more qubits, and retains the baseline lookup implementation.

Sources: [Schrottenloher repository](https://gitlab.inria.fr/capsule/qarton-projects/ec-point-addition/-/tree/a9538b3), [Schrottenloher paper](https://arxiv.org/html/2606.02235v1), [IonQ report](https://arxiv.org/html/2609.05625v1). This is independent analysis, not code released or endorsed by IonQ.

## 1. Accounting: disjoint modules

All numbers below come from constructing circuits and traversing Qarton's resource tree. `results/counts.json` contains the machine-readable ledger. Parent and child entries in its `nested_class_toffolis` overlap: never sum that whole dictionary. The following rows are disjoint.

| Module per point addition | Baseline | Reconstruction, static | Reconstruction, expected | Expected saving per addition | Saving over 28 |
|---|---:|---:|---:|---:|---:|
| Build and erase GCD records, four traversals | 850,276 | 616,460 | 616,460 | 233,816 | 6,546,848 |
| Replay once for division and once for multiplication | 791,700 | 563,932 | 550,666 | 241,034 | 6,748,952 |
| Subtract a modular square | 207,964 | 58,749 | 58,605 | 149,359 | 4,182,052 |
| Remaining coordinate arithmetic | 15,581 | 2,848 | 2,752 | 12,829 | 359,212 |
| Common lookup allowance | 196,608 | 196,608 | 196,608 | 0 | 0 |
| **Total per addition** | **2,062,129** | **1,438,597** | **1,425,091** | **637,038** | **17,837,064** |
| **28 additions** | **57,739,612** | **40,280,716** | **39,902,548** | | |

Here a Toffoli includes a temporary logical AND; its measurement-based uncompute is free in this convention. Static counts charge every explicitly classically controlled phase-comparison branch. Expected counts charge those branches half their cost, because they are controlled by fresh uniform X-measurement outcomes. Everything else is charged in full. This expectation is not a maximum over sampled measurement trajectories.

The static-to-expected discount over 28 additions is 378,168: replay contributes 371,448, squaring 4,032, and coordinate arithmetic 2,688. These discounts are already inside the main table; they are not additional savings to add to it.

The common lookup allowance is `3*2^16` per addition. It is a comparison convention, not the exact gate count of a newly synthesized 65,536-entry lookup. We construct and test the full composition with an eight-entry table, whose three load/unload pairs cost 42 Toffolis. Subtracting those 42 from the composed count independently reproduces the arithmetic ledger.

IonQ's 40,420,330 compiled injection count has a different accounting boundary. Our 40,280,716 static total must not be presented as reproducing or outperforming that compiled circuit. No Fourier transforms, routing, error correction, distillation, or classical recovery costs are newly reconstructed here.

## 2. What the point-addition circuit does

Let the incoming point be A=(x1,y1), and let the coherent address j select Tj=(x2,y2). The address is retained throughout. For ordinary affine addition, define d=x1-x2 and lambda=(y1-y2)/d. Then x3=lambda^2-x1-x2 and y3=lambda(x1-x3)-y1.

The register schedule, with all arithmetic modulo p, is:

| Step | x register | y register | Main module |
|---|---|---|---|
| Input | x1 | y1 | |
| First lookup, subtract coordinates, unlookup | d=x1-x2 | y1-y2 | Two modular subtractions |
| Divide | d | lambda | Recorded-GCD division |
| Middle lookup and add | d+3x2+R | lambda | One modular addition |
| Subtract square; remove mask R | x2-x3 | lambda | Modular square, subtraction |
| Multiply | x2-x3 | lambda(x2-x3) | Recorded-GCD multiplication |
| Final lookup and subtract coordinates | -x3 | y3 | Two modular subtractions |
| Negate x | x3 | y3 | Modular negation |

R is a classical mask incorporated into the middle table. It is loaded as a fixed 256-bit string for removal and then cleared with Clifford gates. The implementation excludes infinity and exceptional affine inputs A=T, A=-T, A=-2T; it is not a complete exceptional-case group law. Table addresses can be in superposition. Unlookup must preserve their relative phases, not merely erase classical values.

## 3. GCD recording: where the controlled adder disappears

The inherited architecture computes a compressed history of a binary GCD, uses that history to perform a modular product or quotient, then reverses the history computation. Thus one point addition contains **four** GCD traversals, not one.

The reconstruction maintains odd positive values with u<=v. For each iteration, set a=u[1] XOR v[1], using the second least significant bits. Compute

    v' = (v + (1-2a)u)/2,
    m = a AND [u > v'],
    (u,v) <- swap_m(u,v').

The chosen sum or difference is twice an odd integer. Its sign is selected by a, but there is always an addition/subtraction: we do not have to control every carry operation on whether to execute the arithmetic.

For an N-bit target, write J(z)=2^N-1-z. Then `J(J(z)+u)=z-u (mod 2^N)`. CNOTs controlled by a complement the target before and after an ordinary Gidney adder. Consequently the sign selector costs Clifford gates, while the carry circuit costs one ordinary adder. This does not eliminate the comparator or controlled swap.

| One GCD traversal | Baseline | Reconstruction |
|---|---:|---:|
| Main integer addition/subtraction | 120,248 | 60,526 |
| Initial controlled preparation | 0 | 514 |
| Controlled comparison | 28,177 | 28,272 |
| Controlled swaps | 60,124 | 60,783 |
| Compress/absorb history | 4,020 | 4,020 |
| **Total** | **212,569** | **154,115** |

The saving is 58,454 per traversal, or 6,546,848 over the 112 traversals in 28 additions. The increased comparator/swap/preparation costs are included, rather than attributing the whole adder reduction to the final total.

We keep the baseline's 402 iterations, shrinking-width schedule, and ternary history compressor. We use 77-bit truncated comparisons, one extra value bit, and an initial parity bit a0. Initially `(u,v)=(p,x+(1-a0)p)`, then swap under a0. The intended terminal values are `(1,1)`. The record contains a0 plus 670 compressed bits. These width/iteration truncations are statistical approximations, not exact for every field element.

## 4. Replay: a second, independent large saving

Recording the GCD and applying its history are different modules. Optimizing the record alone would miss the largest second contribution.

Each recorded step is a linear transformation modulo p: a signed addition, division by two, and possibly a swap. Let M be their product. Since p=0 in the field, the initialized pair is `(0,x)` or `(x,0)`. At termination M maps this pair to `(1,1)`.

For multiplication, initialize two coefficient registers to `(y,y)` using CNOTs. Apply the inverse transformations in reverse order: undo the swap, double the second register modulo p, then undo the signed addition. The output is `(0,xy)` after undoing the initial orientation. For division, run the forward transformations on the appropriately oriented `(0,y)`; they produce `(y/x,y/x)`, and a CNOT clears the duplicate. This is a reversible construction of multiplication/division from a GCD history; no quantum register is populated by a classical `pow` call.

This canonical-residue replay is an explicit reconstruction choice. It follows the same GCD matrices but is not a line-for-line implementation of the report's shifted coefficient representation.

| One multiplication replay | Baseline | New expected |
|---|---:|---:|
| Modular additions, including special zero handling | 255,954 | 137,641 |
| Modular doublings | 28,944 | 25,728 |
| Controlled swaps | 102,912 | 103,168 |
| History extraction | 8,040 | 8,040 |
| **Total** | **395,850** | **274,577** |

The new signed modular adder costs 336.5 expected Toffolis in a regular round. During the first 37 rounds, two approximate zero/p representation swaps increase this to 400.5. Therefore `365*336.5 + 37*400.5 = 137,641`. Doubling costs 64 per round instead of the baseline 72, because the retained padding is reduced to 32 bits.

Division replay costs another **1,512** Toffolis in our construction: 1,440 for additional compressed-history accesses and 72 for zero-target promise flags. Its expected total is 276,089. This extra cost and its workspace are fully included.

Including compute and erase of records, the new in-place multiply costs 582,807 expected Toffolis, and division costs 584,319. Their static costs are 589,440 and 590,952 respectively.

### Measurement cleanup and the phase bug caught during testing

For p=2^256-c with c=2^32+977, add into a 257-bit register, then fold its carry h into the low register by adding c. Measure h in the X basis. Outcome m contributes phase `(-1)^(m h)`. A phase comparison reconstructed from the surviving registers cancels this phase; simply resetting the measured bit would leave an address/input-dependent sign.

We use a 32-bit truncated carry predicate. Signed addition includes a sign/tie bit, hence a 33-bit phase comparator. `PhaseLT` prepares a scratch bit in |->, applies a reversible comparator into that target, then restores the scratch bit. This is a phase kickback circuit with actual gates, not a simulated mathematical phase oracle.

Tests exposed a concrete corner case in division: complementing a zero target before subtraction uses the noncanonical value 2^256-1. After reduction, the ordinary truncated comparison can miss the carry, producing the correct classical result with the wrong sign. We track a promise flag z saying that the target is zero in the early rounds and apply CZ(b,z), conditioned on measurement m. It contributes `(-1)^(m b z)` and cancels that missing phase. Those flag circuits are included in the 1,512-Toffoli overhead. A test checking only register values would have missed this defect.

## 5. Squaring: more than removing a control

The baseline uses 256 controlled modular additions, 255 doublings and 255 inverse doublings, plus 512 control-AND Toffolis:

    165,632 + 20,910 + 20,910 + 512 = 207,964.

The new construction first computes ordinary integer squares, then combines and reduces them. Write x=L+2^128 H and S=L+H. The identity

    x^2 = L^2 + 2^128(S^2-L^2-H^2) + 2^256 H^2

requires two 128-bit squares and one 129-bit square. Since 2^256=c modulo p, the large power becomes a sparse small constant. We use the signed expansion `c=2^32+2^10-2^6+2^4+1`.

The ordinary n-bit integer-square circuit uses the report's signed-add identity: conditional complements select additions/subtractions using CNOTs, and the triangular schedule shortens the adders. Its cost for n>=2 is `T(n)=n(n+3)/2-1`. Both computing and erasing the three square registers are charged.

| New modular-square submodule | Multiplicity | Expected Toffolis |
|---|---:|---:|
| Integer square, 128 bits, compute and erase | 4 | 33,532 |
| Integer square, 129 bits, compute and erase | 2 | 17,026 |
| Add shifted 256-bit square contribution | 2 | 2,262 |
| Subtract shifted 258-bit square contribution | 1 | 1,653 |
| Sparse-c reduction, including high correction compute/erase | 1 | 3,412 |
| Remaining full-width subtraction | 1 | 464 |
| Build and erase L+H | 2 | 256 |
| **Total** | | **58,605** |

The high correction alone costs 524 each way and is already inside the 3,412 row. The 50,558 integer-square leaf subtotal is also already included; it must not be added again. Nine 32-bit measurement phase comparisons account for the difference between static 58,749 and expected 58,605.

The saving of 149,359 per point addition combines a new squaring schedule, the three-square decomposition, cheap pseudo-Mersenne reduction, carry truncation, and measurement cleanup. This experiment does not isolate these interacting changes into additive per-trick ablations. The submodule ledger does isolate their actual implemented costs.

## 6. Coordinate arithmetic and lookup

Five standalone subtractions cost `5*464`, one addition costs 336, and negation costs 96: total **2,752**. The square's own internal subtraction is charged inside squaring, separately. The baseline's corresponding residual arithmetic costs 15,581.

The 65-bit constant correction and 32-bit carry/phase windows matter in these modules as well as in replay and squaring. A direct constant-adder class is not always cheapest: the baseline's constant-aware dispatch reduces controlled addition of c to 64 Toffolis here. We retain that dispatch rather than accidentally charging a larger generic constant circuit.

No lookup saving is claimed. The composed circuit uses the original coherent table load and measurement-based unlookup. It does not implement the report's delayed, merged-mask unlookup or hardware-specific lookup scheduling. Expanding a 16-bit lookup is consequently a remaining reproduction task, and the common allowance is explicitly an estimate.

## 7. Verification scope and limitations

`verify.py` checks output support, amplitude/sign, coherent test states, and all workspace-zero assertions. Newly written algorithm modules are expanded in simulation; none is replaced by its expected classical answer. Large tests retain Qarton's existing fast implementations of known exact primitives. `verify_phase.py` and the small-width groups separately decompose exact square, signed-adder, phase-comparison, and exact zero/p-swap primitives into gates.

The independent integer model in `gcd.py` uses Python modular arithmetic to validate the recorded transformations. The circuit tests compare against Python field multiplication/inversion and the original elliptic-curve implementation. Test sizes, seeds, timings and any failures are recorded in `results/verification.json`; phase tests are in `results/phase-verification.json`.

Completed verification (fixed seeds recorded in JSON):

| Test group | Passed cases |
|---|---:|
| Integer square, exhaustive 1–8 bits | 510 |
| Fully decomposed square and signed adder | 709 |
| Independent classical GCD/product model | 10,000 |
| 256-bit signed modular addition and zero promises | 1,041 |
| 256-bit modular square | 201 |
| 256-bit multiplication | 101 |
| 256-bit division | 101 |
| Complete point addition and coherent lookup | 33 |
| Original baseline point-addition control | 10 |
| Fully decomposed phase comparison and exact zero/p swap | 377 |
| Final allocation/short-mask integration checks | 3 |

There were **no failures in the randomized, exhaustive, or coherent groups above**. The deliberately adversarial 14-case signed-addition probe produced **6 failures**, recorded with inputs in the JSON. These probe failures are not hidden in the successful randomized total. They demonstrate that the truncated circuit is not exact on all inputs. The 10,000-case classical model is separate from the circuit simulations. Coherent cases are counted once per superposition test, not once per branch.

The long suite ran before the final allocation-only GCD workspace reuse change and general mask-width fix. The three final integration checks exercise the updated circuit, including a coherent two-address state and mask R=1; the resource ledger uses the reused allocation.

Truncated comparison, carry propagation and zero detection can fail on adversarial residues; such failures are deliberately recorded separately. Passing random tests does not prove the circuit is an exact unitary implementing field arithmetic on every input, or reproduce IonQ's million-sample error analysis and algorithmic success bound. Exceptional affine inputs are excluded. No hardware noise is simulated.

The eight-entry composed circuit uses **1,521 logical qubits**. Adding thirteen address bits gives an indicative 1,534 for the arithmetic layout with a 16-bit address, before any different lookup workspace is considered. This does not match IonQ's 1,457. In particular the extra division promise flags use workspace that their representation avoids. A closer qubit match requires another implementation, not renaming this estimate.

## 8. Reproduction

From this directory, run `bash setup-reconstruction.sh`, then:

```bash
./run-reconstruction.sh ionq_reconstruction.counts
./run-reconstruction.sh ionq_reconstruction.verify_phase
./run-reconstruction.sh ionq_reconstruction.verify --quick
./run-reconstruction.sh ionq_reconstruction.verify
```

The full suite takes substantially longer than the quick suite. Each verification run overwrites `results/verification.json`; preserve it before running another configuration. Resource counts are circuit-structural, so no random gate-count extrapolation is needed for the arithmetic. The 28-window and full-table scaling assumptions are separate and visible in `counts.py`.

Original files retain their original license and attribution. New reconstruction code is distributed under the same AGPL-3.0 terms; see `LICENSE.md`.
