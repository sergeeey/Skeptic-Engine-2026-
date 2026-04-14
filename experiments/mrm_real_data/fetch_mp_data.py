"""Fetch real data from Materials Project and run SE-MRM calibration."""
import os, json, sys, uuid
from pathlib import Path

# Load MP_API_KEY from environment (set via .env file)
mp_api_key = os.environ.get("MP_API_KEY")
if not mp_api_key:
    raise RuntimeError(
        "MP_API_KEY environment variable is required. "
        "Copy .env.example to .env and set your key: https://materialsproject.org/api"
    )
os.environ['MP_API_KEY'] = mp_api_key

print("=== Materials Project Data Fetch ===", flush=True)

from mp_api.client import MPRester
print("MP API imported OK", flush=True)

stable, marginal, unstable = [], [], []

with MPRester(mp_api_key) as mpr:
    # Stable: eah < 0.02 AND formation_energy < -0.5 (truly stable)
    # Exclude radioactive elements (Ac, Tc, Pm, Po, At, Rn, Fr, Ra, etc.)
    print("  Fetching stable (eah < 0.02, fe < -0.5)...", flush=True)
    radioactive = {'Ac', 'Tc', 'Pm', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Th', 'Pa', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr'}
    stable_docs = []
    for d in mpr.materials.summary.search(
        energy_above_hull=(0, 0.02), num_chunks=200,
        fields=['material_id','formula_pretty','energy_above_hull',
                'formation_energy_per_atom','band_gap','symmetry']
    ):
        fe = d.formation_energy_per_atom
        if fe is not None and fe < -0.5:
            # Check no radioactive elements
            formula = d.formula_pretty or ""
            elements = set()
            import re
            for elem in re.findall(r'[A-Z][a-z]?', formula):
                elements.add(elem)
            if not elements.intersection(radioactive):
                stable_docs.append(d)
        if len(stable_docs) >= 50:
            break
    
    for d in stable_docs[:50]:
        sym = d.symmetry
        cs = str(getattr(sym, 'crystal_system', 'unknown')) if sym else 'unknown'
        sg = getattr(sym, 'number', None) if sym else None
        stable.append({
            'material_id': str(d.material_id),
            'composition': d.formula_pretty,
            'energy_above_hull': float(d.energy_above_hull) if d.energy_above_hull else 0,
            'formation_energy': float(d.formation_energy_per_atom) if d.formation_energy_per_atom else None,
            'band_gap': float(d.band_gap) if d.band_gap is not None else None,
            'crystal_system': cs,
            'space_group': sg,
            'source': 'materials_project'
        })
    print(f"  Got {len(stable)} stable", flush=True)

    # Marginal: 0.1 < eah < 0.3 (exclude radioactive)
    print("  Fetching marginal (0.1 < eah < 0.3, no radioactive)...", flush=True)
    marginal_docs = []
    for d in mpr.materials.summary.search(
        energy_above_hull=(0.1, 0.3), num_chunks=200,
        fields=['material_id','formula_pretty','energy_above_hull',
                'formation_energy_per_atom','band_gap','symmetry']
    ):
        formula = d.formula_pretty or ""
        elements = set(re.findall(r'[A-Z][a-z]?', formula))
        if not elements.intersection(radioactive):
            marginal_docs.append(d)
        if len(marginal_docs) >= 30:
            break
    
    for d in marginal_docs[:30]:
        sym = d.symmetry
        cs = str(getattr(sym, 'crystal_system', 'unknown')) if sym else 'unknown'
        sg = getattr(sym, 'number', None) if sym else None
        marginal.append({
            'material_id': str(d.material_id),
            'composition': d.formula_pretty,
            'energy_above_hull': float(d.energy_above_hull) if d.energy_above_hull else 0.2,
            'formation_energy': float(d.formation_energy_per_atom) if d.formation_energy_per_atom else None,
            'band_gap': float(d.band_gap) if d.band_gap is not None else None,
            'crystal_system': cs,
            'space_group': sg,
            'source': 'materials_project'
        })
    print(f"  Got {len(marginal)} marginal", flush=True)

    # Unstable: eah > 0.5 (limit to first 50)
    print("  Fetching unstable (eah > 0.5)...", flush=True)
    docs = list(mpr.materials.summary.search(
        energy_above_hull=(0.5, 10), num_chunks=50,
        fields=['material_id','formula_pretty','energy_above_hull',
                'formation_energy_per_atom','band_gap','symmetry']
    ))[:50]
    for d in docs:
        sym = d.symmetry
        cs = str(getattr(sym, 'crystal_system', 'unknown')) if sym else 'unknown'
        sg = getattr(sym, 'number', None) if sym else None
        unstable.append({
            'material_id': str(d.material_id),
            'composition': d.formula_pretty,
            'energy_above_hull': float(d.energy_above_hull) if d.energy_above_hull else 1.0,
            'formation_energy': float(d.formation_energy_per_atom) if d.formation_energy_per_atom else None,
            'band_gap': float(d.band_gap) if d.band_gap is not None else None,
            'crystal_system': cs,
            'space_group': sg,
            'source': 'materials_project'
        })
    print(f"  Got {len(unstable)} unstable", flush=True)

# Convert to SE-MRM format
data = {'stable': stable, 'marginal': marginal, 'unstable': unstable}
candidates = []
for group, items in data.items():
    for item in items:
        eah = item.get('energy_above_hull', 0.5)
        profile = 'stable' if eah < 0.05 else ('marginal' if eah < 0.3 else 'unstable')
        candidates.append({
            'candidate_id': f"mp_{profile[:3]}_{uuid.uuid4().hex[:6]}",
            'source': 'materials_project',
            'composition': item['composition'],
            'structure_format': 'json',
            'structure_blob': json.dumps({
                'mp_id': item['material_id'],
                'composition': item['composition'],
                'energy_above_hull': eah,
                'formation_energy': item.get('formation_energy'),
                'band_gap': item.get('band_gap'),
                'crystal_system': item.get('crystal_system'),
                'space_group': item.get('space_group')
            }),
            'target_properties': {
                '_profile_type': profile,
                'energy_above_hull': eah,
                'formation_energy': item.get('formation_energy'),
                'band_gap': item.get('band_gap')
            },
            'novelty_context': {
                'crystal_system': item.get('crystal_system'),
                'space_group': item.get('space_group'),
                'mp_id': item['material_id']
            }
        })

out = Path(r'E:\nobel premia Boiko - 2026\experiments\mrm_real_data\data')
out.mkdir(parents=True, exist_ok=True)
(out / 'mp_real_candidates.json').write_text(
    json.dumps(candidates, indent=2, default=str), encoding='utf-8'
)
print(f"\nSaved {len(candidates)} MP candidates to mp_real_candidates.json", flush=True)
print(f"  Stable: {len(stable)}", flush=True)
print(f"  Marginal: {len(marginal)}", flush=True)
print(f"  Unstable: {len(unstable)}", flush=True)

# Now run calibration
print("\n=== Running SE-MRM Calibration on MP Data ===", flush=True)
from fetch_real_data import run_real_calibration
results = run_real_calibration(str(out / 'mp_real_candidates.json'))
