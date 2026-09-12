# Narration plan, written before the second revision

Read: the main manuscript, Parts I–VI and Appendices A–G, including the arithmetic failure proof, factory stopping-time calculation, and resource totals. The physical Pauli strings in Appendix G are implementation evidence; their role is support weight and measurement compatibility.

## The talk

We know how Shor's algorithm extracts a discrete logarithm. The question is what a machine must actually do to extract a 256-bit key. Start with Q=dP, follow one addition, and then follow the operations needed to make that addition reliable. The estimate is the consequence of that construction.

1. Equal values of kP+lQ form a hidden relation. Fourier sampling exposes it. Window tables reduce the quantum work to 28 expensive point additions and a first lookup; classical recovery handles the omitted windows.
2. One addition needs a slope. Work a small modular division before introducing gcd notation. Record the denominator's reductions, apply those same steps to the numerator, and erase the record. Only then introduce the odd representation and explain why changing stored values makes signed addition cheaper.
3. Reuse the two coordinate registers. The slope becomes the new y coordinate; the square changes the x coordinate. Explain every temporary register's purpose and cleanup before giving counts.
4. Approximate arithmetic saves work. Show a missed carry and a residual phase, then explain random masks, per-input failure, and the amplitude bound. Keep statistical and proved bounds distinct.
5. A gate count does not yet give a duration. Place the registers, move them when needed, overlap movement with the serial carry chain, and track measurement corrections. Explain the scheduler through one operation before its compiler machinery.
6. A logical measurement uses a verified cat state. Reuse the physical carriers, account for their travel, and explain the code and loss model needed to keep the stored state alive.
7. Direct CCZ injection avoids a sequence of T gates. Disjoint physical representatives allow parallel interactions. Clifford frames defer corrections; fresh encoded Bell pairs periodically clear the frame.
8. Prepare the consumed CCZ states. Start with noisy encoded H states, explain the parity test, then repetitions, restarts, and factory throughput. Derive four factories from production and consumption times.
9. Combine separately the footprint, expected duration per attempt, and success probability. End with the precise hardware assumptions and the remaining evidence gaps in Limitations.

## Page-level rule

Every section first tells the listener what must happen and why. Its equation then expresses that operation, and the following prose explains what changed. Keep intermediate reasoning. Introduce notation at its first use. Preserve all figures, tables, interactive controls, equation content, and stable anchors. Reference lessons teach the imported construction, then connect it to this calculation. Navigation and notation pages serve their existing roles.
