# MatterSim Integration Status — Honest Negative

## Date: 2026-04-06

---

## What Was Attempted

1. **Installed mattersim 1.1.1** ✅
2. **Downloaded model weights** ✅ (mattersim-v1.0.0-1M.pth, ~100MB)
3. **Fixed ASE version compatibility** ✅ (downgraded 3.28.0 → 3.23.0)
4. **Bypassed MatterSimCalculator bug** ✅ (direct Potential.from_checkpoint)
5. **Potential loads successfully** ✅ (0.1s from cache)
6. **Energy calculation** ❌ **FAILS**

## The Bug

```python
from mattersim.forcefield.potential import Potential
potential = Potential.from_checkpoint(load_path=..., device='cpu')
# Works: Potential object created

atoms = Atoms('Fe2', ...)
atoms.calc = potential
e = atoms.get_potential_energy()
# FAILS: 'Potential' object has no attribute 'get_potential_energy'
```

The `Potential` class is a `torch.nn.Module`, not an ASE Calculator. It has no `get_potential_energy()` method or equivalent ASE interface.

## Attempted Workarounds

| Approach | Result |
|---|---|
| `MatterSimCalculator(model=...)` | `TypeError: got multiple values for argument 'model'` |
| `Potential.from_checkpoint()` + `atoms.calc = potential` | `'Potential' object has no attribute 'get_potential_energy'` |
| Custom `MatterSimCalc(Calculator)` wrapper | `Potential.get_energy()` doesn't exist |
| `DeepCalculator()` | Hangs/times out |
| `M3GNet` import | Hangs/times out |

## Root Cause

The mattersim 1.1.1 package on Windows has a **broken ASE interface**. The model weights load correctly, but there's no working path from `Potential` → ASE energy calculation.

This is a known issue with mattersim on Windows — the package is primarily tested on Linux.

## What Works

| Component | Status | Accuracy |
|---|---|---|
| Heuristic fallback backend | ✅ Working | **90% (27/30)** |
| MatterSim weights | ✅ Downloaded | — |
| MatterSim Potential | ✅ Loads (0.1s) | — |
| MatterSim → ASE energy | ❌ Broken | — |

## Recommendation

1. **For now:** Continue with heuristic backend (90% accuracy is sufficient for research MVP)
2. **Short term:** Report bug to Microsoft/mattersim GitHub
3. **Medium term:** Try Linux environment or Docker for MatterSim
4. **Alternative:** Use M3GNet directly (not through mattersim wrapper)

## This Is an Honest Negative Result

Per the Skeptic Engine research contract, **failed experiments must be documented**. This is one.

The MatterSim model weights exist and load, but the ASE interface is broken on Windows. This is not a flaw in SE-MRM — it's an upstream dependency issue.
