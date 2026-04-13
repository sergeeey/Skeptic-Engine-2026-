# SE-MRM CLI Reference

## Commands

### skeptic-mrm
Show help and available commands.
```bash
skeptic-mrm
```

### skeptic-mrm ingest
Load and validate candidates from file.
```bash
skeptic-mrm ingest <input_path>
```
Supported formats: `.cif`, `.poscar`, `.vasp`, `.json`, `.jsonl`

Output:
- Total / kept / rejected / deduplicated counts
- Rejection reasons
- First 10 candidate summaries

### skeptic-mrm run
Run the full MRM pipeline.
```bash
skeptic-mrm run --input <path> [options]
```

Options:
| Flag | Default | Description |
|---|---|---|
| `--input` | (required) | Input candidates file |
| `--backend` | mattersim | Simulation backend |
| `--mode` | standard | quick / standard / deep |
| `--out` | mrm_output | Output directory |
| `--max-attacks` | 8 | Max attacks per candidate |
| `--kill-below` | 0.35 | Kill threshold |
| `--hold-below` | 0.65 | Hold threshold |
| `--promote-above` | 0.65 | Promote threshold |

Output:
- Batch summary (JSON)
- Top survivors list
- Individual candidate reports

### skeptic-mrm report
Display a batch report.
```bash
skeptic-mrm report <batch_summary.json> [--format json|html]
```

### skeptic-mrm benchmark
Run benchmark suite.
```bash
skeptic-mrm benchmark <name>
```

## Python API

```python
from skeptic_mrm.runner import MRMConfig, MRMRunner

config = MRMConfig(
    mode="standard",
    max_attacks_per_candidate=8,
    kill_below=0.35,
    hold_below=0.65,
    promote_above=0.65,
)
runner = MRMRunner(config=config)
result = runner.run_batch("data/candidates.jsonl")

print(result.summary())
print(result.top_survivors(5))
result.save("results/batch_001.json")
```

## Configuration File (YAML)

```yaml
project:
  name: se_mrm
  version: 0.1.0

scope:
  domain: inorganic_crystals
  mode: standard

simulation:
  backend: mattersim

attacks:
  policy: rules_v1
  max_attacks_per_candidate: 8

adjudication:
  thresholds:
    kill_below: 0.35
    hold_below: 0.65
    promote_above: 0.65
```
