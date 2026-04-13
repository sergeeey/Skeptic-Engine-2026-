# SE-MRM Failure Taxonomy

## Failure Modes

| ID | Mode | Description | Detection Method |
|---|---|---|---|
| FM-01 | Thermodynamic instability | Formation energy above convex hull | Energy proxy from relaxation |
| FM-02 | Dynamic instability | Imaginary phonon modes | Dynamic stability proxy |
| FM-03 | Structure collapse | Relaxation diverges or produces invalid geometry | Convergence status |
| FM-04 | Temperature sensitivity | Properties degrade at elevated T | Temperature ramp attack |
| FM-05 | Pressure sensitivity | Structure collapses under pressure | Pressure ramp attack |
| FM-06 | Defect sensitivity | Single vacancy destroys properties | Defect injection attack |
| FM-07 | Symmetry collapse | Relaxation breaks key symmetry | Symmetry perturbation attack |
| FM-08 | Property collapse | Target property drops under perturbation | Property fragility test |
| FM-09 | OOD uncertainty | Candidate far from training distribution | Uncertainty estimation |
| FM-10 | Simulation disagreement | Different backends give conflicting results | Multi-backend comparison |

## Attack Types

| Attack | Target Failure Modes | Parameters |
|---|---|---|
| lattice_perturbation | FM-03, FM-07 | displacement_std |
| atomic_displacement | FM-02, FM-08 | max_displacement_A |
| temperature_ramp | FM-04 | t_start, t_end, steps |
| pressure_ramp | FM-05 | p_start, p_end, steps |
| repeated_relaxation | FM-01, FM-03 | n_cycles |
| defect_injection | FM-06 | vacancy_fraction |
| property_target_fragility | FM-08 | property, tolerance |
| symmetry_perturbation | FM-07 | noise_fraction |

## Kill Criteria

Auto-kill if ANY of:
1. Parsing/normalization failed
2. Severe geometry invalidity
3. Relaxation diverged repeatedly
4. Stability proxy < min_threshold (0.30)
5. Dynamic instability beyond threshold
6. Uncertainty too high (> 0.50)
7. Catastrophic collapse under minimal perturbation

## Hold Criteria

Hold if ANY of:
1. Promising novelty but mixed reliability evidence
2. Requires higher-fidelity validation
3. Conflict between backends
4. Uncertainty penalty in borderline range

## Promote Criteria

Promote if ALL of:
1. Passed minimum reliability gates (score > 0.65)
2. Acceptable uncertainty (< 0.50)
3. No collapse under standard stress suite
4. Ranked above threshold relative to cohort

## Honest Negatives Storage

All killed/held candidates are stored with:
- Full attack history
- Failure mode classification
- Score breakdown
- Decision rationale

This is mandatory per the Skeptic Engine research contract.
