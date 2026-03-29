# Working Contract

## Purpose

This document defines the practical operating contract for work in this project.

It exists to keep execution aligned with the real mission:

- find strong interdisciplinary opportunities
- reject weak or romanticized claims quickly
- turn the strongest candidates into reproducible research artifacts

## Core Rules

1. Do a brief context check, then execute.
2. Prefer fixing and verifying over proposing and waiting.
3. Ground important claims in local code, files, command output, tests, or primary sources.
4. Do not stay attached to one hypothesis if the evidence turns against it.
5. Every serious hypothesis must have a falsification path.
6. Build research machinery, not just idea lists.
7. Prefer narrow, executable scopes over broad, vague ambition.
8. Surface hidden risks when they materially affect correctness, novelty, safety, or maintenance.
9. Do not pause for approval on normal local work inside the project.
10. Ask only at the real safety boundary.
11. Always separate `Implemented`, `Verified`, and `Unverified` when needed.
12. Optimize for honest research throughput, not for impressive sounding output.

## What We Are Building

This project is not a notes repository.

It is a Python-first research engine for:

- collecting evidence across domains
- finding underexplored transfer opportunities
- ranking candidate hypotheses
- selecting a defensible `top-5`
- validating the strongest candidates reproducibly

## Decision Standard

Candidates should be judged by:

- novelty after review
- data readiness
- Python-first tractability
- falsifiability
- expected value for the overall project

## Execution Posture

Default behavior:

- read local evidence first
- make scoped changes
- verify the smallest sufficient surface
- move to the next viable route if the current one stalls

Do not force a weak route to survive.
If one path fails, downgrade it honestly and move to the next strong candidate.

## Safety Boundary

Ask before proceeding only when one of these is true:

- destructive operation
- production deploy or production write
- irreversible data or schema operation
- secret creation, rotation, or exposure risk
- force push, hard reset, or history rewrite
- edit outside the intended workspace

## Research Standard

The project must avoid:

- hallucinated facts
- fake novelty
- ungrounded scientific claims
- benchmark claims without fair baselines
- claims of superiority without reproducible evidence

## Practical Rule

The goal is not to sound visionary.

The goal is to reliably convert interdisciplinary intuition into defensible, testable, and reproducible research output.
