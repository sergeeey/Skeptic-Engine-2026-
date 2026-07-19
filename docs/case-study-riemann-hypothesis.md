# Case Study — Skeptic Engine vs the Riemann Hypothesis

**Date of underlying work:** 2026-06-14 (research) · 2026-07-17 (evidence gate closed, transferred here)
**Source repo:** `github.com/sergeeey/riemann-zeta-modern-methods` (`H - 12 Гипотеза Римана`)
**What this is:** a cross-domain demo of the Skeptic Engine's core mechanism — context-blind
adversarial review — applied to **logical/mathematical proof review**, not statistical anomaly
detection. Every other case study in this repo (`experiments/h23..h38`) scores a detector's AUC
against real or synthetic fraud data. This one has no AUC: the artifact under test is a chain
of reasoning, and the "detector" is a falsification-first agent asking "does this claim hold?"
It is included here because it demonstrates the same underlying capability — catching
assume-the-conclusion errors — generalizes past the statistical-detector product surface
described in `research-contract.md`. Whether that generalization belongs in the product's
stated scope, or stays a methodology appendix, is an open framing question for this project,
not settled by this document.

---

## What happened

Over one day, an AI research loop attacked the Riemann Hypothesis by atomization (8
sub-problems, no attempt to prove RH itself) and audited two outside "proof" papers
(Grant, 2026, both unpublished/non-peer-reviewed). At every step a context-blind skeptic
agent plus a code reviewer ran against each claim. The case collects **every circularity,
tautology, overclaim, and numerical error caught** — including one the author (the AI
itself) committed and did not notice until the skeptic flagged it.

## The catches (chronological, all tool-verified)

| # | Where | Claim as written | What the skeptic caught | Type | Resolution |
|---|-------|------------------|-------------------------|------|------------|
| 1 | Grant Doc A (outside paper) | "Geometric proof of RH" | §9 Step 4 inserts \|Σ xᵖ/ρ\|=O(√x) — which IS RH (von Koch). Assumes the conclusion. | **Circularity** | REJECT |
| 2 | Grant Doc B (outside paper) | "iHarmonic proof of RH" | Author's own text (p.87) marks the Spectral Isomorphism a *conjecture*; Thm 5.3 numerically false | **Conditional-as-proven** | REJECT |
| 3 | **Own code (Li criterion)** | "λ_n>0 ⟺ RH, verified" | Code set ρ=½+iγ — *assumed* Re=½, the very thing RH asserts ⟹ λ_n>0 automatic (Bombieri-Lagarias). **Same error as Grant Doc A.** | **Circularity (self-inflicted)** | Fixed: zero-free λ₁=0.0231 |
| 4 | Hilbert-Pólya atom | "1/(48π) emerges from xp geometry" | It's just the 3rd Stirling term of θ — a tautology, verified identical to T=5·10⁵ | **Tautology-as-discovery** | Reframed, not a result |
| 5 | RMT atom | "zeros follow GUE" | True only as *evidence* for a conjecture; Wigner surmise ≠ exact GUE; finite-T | **Overclaim** | Softened to "evidence" |
| 6 | Levinson density atom | "illustrates Levinson's method" | Speiser test ≠ the mollifier method; doesn't reproduce it | **Overclaim** | Reworded |
| 7 | Zero-free region atom | "ZFR does not approach ½" | True only for *pointwise* ZFR; density methods reach ½ | **Misleading scope** | Disclaimer added |
| 8 | Zero-free crossover | "VK overtakes at 10⁴³⁴" (lit-agent) | Wrong; bracketed solve gives 10³⁸⁷⁷ | **Numerical error** | Corrected, reverified 2026-07-17 |
| 9 | Prime error atom | table shows li(x)>π(x) everywhere | Invites "li>π always" — false; Littlewood: ∞ sign flips, first ~10³¹⁶ (Skewes) | **Dangerous extrapolation** | Warning added |
| 10 | Toolkit | "zeros found correctly" | reviewer: findroot single-point can run off-interval (latent P0) | **Latent bug** | Two-point Brent |
| 11 | Robin criterion | "27 exceptions" (from memory) | Tool: 26 exceptions in [3,5040]; memory was wrong | **Memory vs tool** | Corrected to 26, reverified 2026-07-17 |

## The error taxonomy

1. **Assume-the-conclusion (circularity)** — #1, #2, #3. The deadliest class: the "proof"
   silently inserts the target claim (or an equivalent) as a step. Caught in two outside
   papers *and* in the project's own code.
2. **Tautology-as-discovery** — #4. A known identity dressed up as an emergent finding.
3. **Overclaim** — #5, #6. Evidence presented as proof; an analogy presented as a method.
4. **Misleading scope / extrapolation** — #7, #9. A locally-true statement misleading when
   read globally.
5. **Numerical / memory error** — #8, #10, #11. Wrong constant, latent bug, stale recall.

## The headline result

**The Engine caught the project committing the exact error it had just rejected in an
outside paper.** Grant's Doc A was rejected for inserting RH as a step (circularity).
Three atoms later, the project's own Li-criterion code did the same thing — assumed
Re=½ to "verify" RH. A context-blind skeptic, given only the claim and the code (no
author intent, no reasoning chain), flagged it. The author had not noticed.

This is the core value proposition of a verification engine: **self-deception is nearly
invisible from the inside.** A reviewer who shares your goal shares your blind spot. A
context-blind adversary, scoring only "does the claim hold?", does not.

---

## Evidence chain (added 2026-07-17, closing the original case's stated gap)

The original case (2026-06-14) flagged its own limitation: *"the skeptic ran on Claude,
same model family as the author — cross-model would be stronger."* That gap is now closed:

1. **Catch-to-artifact traceability matrix** — all 11 catches above traced to a concrete
   source file/commit in the source repo, labeled TRACE-OK. Two numeric ground-truth catches
   (#8 crossover, #11 Robin exceptions) were rerun independently on 2026-07-17 and reproduced
   exactly.
2. **V5 cross-model blind review** — the three critical circularity catches (#1, #2, #3) were
   independently re-judged by a different model family (OpenAI gpt-5.5 via `codex exec`, not
   Claude), using an asymmetric-context prompt: the model received only the raw mathematical
   claim/data for each catch, with no framing, no prior verdict, and no session history —
   it had to judge circularity/falsity from scratch.

   | # | Catch | Independent verdict | Confidence |
   |---:|---|---|---|
   | 1 | Grant Doc A circularity | CIRCULAR-CONFIRMED | 9/10 |
   | 2 | Thm 5.3 falsification | FALSE-CONFIRMED | 10/10 |
   | 3 | Own-code Li circularity | CIRCULAR-CONFIRMED | 9/10 |

   3/3 independent agreement, with no shared reasoning context between the original
   (Claude-based) skeptic and this cross-model check. Full transcript and the traceability
   matrix are archived in the source repo under
   `evolution/20260630-evolve-solution/` (`catch_traceability_matrix.md`,
   `v5_codex_review_20260717.txt`).

This upgrades the case's independence from "same-model, context-asymmetric" (Weak-Medium on
this project's own independence ladder — see the source repo's `falsification-ladder.md` for
the ladder definition) to "different-model, context-asymmetric" (Medium), for the three catches
that matter most.

## Honest boundaries

- This is a methodology demo, not a benchmark. N=11 catches on one project, one day, one
  domain (analytic number theory). No claim of generalization rate across domains is made.
- "Caught" means flagged + tool-confirmed; severity varied (circularity = critical, memory
  slip = minor).
- The RH source project explicitly did **not** attempt to prove the Riemann Hypothesis and
  makes no such claim. All 8 sub-problems were closed as "mapped, not solved."
- Cross-model review (V5, above) covers the 3 most critical catches, not all 11 — the
  remaining 8 still rest on same-model context-asymmetric review only.

## Why this belongs in the manuscript

- It is a ready golden-set entry for a **logical/proof-review** track, distinct from this
  project's existing statistical-detector tracks (H23–H38): **RH proof-paper audit +
  self-audit**, with unambiguous ground truth (von Koch circularity is a known equivalence,
  not a judgment call).
- The assume-the-conclusion detector is domain-general — it generalizes past mathematics to
  any "we proved X" claim that secretly uses X, which is the same failure mode this project's
  `research-contract.md` and `working-contract.md` promotion gates exist to prevent internally.
- Possible next step (not started, not committed to): run the same loop on 3–5 more
  arXiv/Zenodo RH "proofs" to build a small labeled set for this track.

*Source material in `github.com/sergeeey/riemann-zeta-modern-methods`:
`SKEPTIC-ENGINE-CASE.md`, `evolution/20260630-evolve-solution/`, `experiments/` (8 atoms),
`null_results/20260614-grant-rh-audit.md`.*
