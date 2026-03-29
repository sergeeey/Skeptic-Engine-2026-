# Report Ingestion Notes

This project treats locally imported analytical reports as candidate-generating inputs, not as final proof.

## Current Imported Report

- `Прорывные Гипотезы  Трансдисциплинарный Анализ Биологии, Материаловедения и Теории Управления.md`

## Safe Usage Rule

The report may contribute:

- candidate hypothesis titles
- claimed datasets
- claimed tools
- proposed falsification routes
- prioritization hints

The report may not directly establish:

- novelty for humanity
- absence of prior art
- correctness of Discovery Score values
- dataset availability without link-level checking
- package suitability without environment-level checking

## Ingestion Outcome

The report is converted into `candidate seeds` with:

- `verification_status = unverified`
- explicit `next_verification_step`
- priority queue for top-5 validation

## First Verification Queue

1. H20: PH predictor for SOC degradation
2. H4: TDA signature of cancer drug resistance
3. H10: GNN prediction of MOF synthesizability
4. H2: Persistent homology as predictor of glass transition behavior
5. H1: Koopman fingerprints for IDP phase separation
