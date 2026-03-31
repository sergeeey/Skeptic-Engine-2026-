import json, sys, time, numpy as np
from dataclasses import asdict
from pathlib import Path as P
from sklearn.preprocessing import StandardScaler

H25 = P(__file__).resolve().parents[1] / "h25_banking_ae_lcms"
sys.path.insert(0, str(H25))
sys.path.insert(0, str(P(__file__).resolve().parent))
sys.path.insert(0, str(P(__file__).resolve().parents[2] / "src"))

from constraint_builder import build_constraint_model
from run_h25 import (
    _download_bradshaw_data,
    fabricate_noise,
    fabricate_random,
    fabricate_shuffle,
    reconstruction_error,
    train_autoencoder,
)
from syndrome_features import compute_syndrome

RESULTS = P(__file__).resolve().parent / "results"
FABS = {
    "random": fabricate_random,
    "shuffle": fabricate_shuffle,
    "noise_10pct": lambda r, g: fabricate_noise(r, g, 0.10),
}


def main():
    t0 = time.time()
    print("=" * 70)
    print("H29 -- Biological Parity Violations / Syndrome Layer")
    print("=" * 70)
    print("\n[1/5] Loading CPTAC proteomics...")
    _, prot = _download_bradshaw_data()
    fnames = prot.columns.tolist()
    real = np.nan_to_num(prot.values.astype(np.float64), nan=0.0)
    ns, nf = real.shape
    print(f"  {ns} samples x {nf} proteins")

    print("\n[2/5] Training autoencoder...")
    sc = StandardScaler()
    rs = sc.fit_transform(real)
    ae = train_autoencoder(rs, epochs=150, latent_dim=32)
    rr = reconstruction_error(ae, rs)
    print(f"  AE recon: mean={rr.mean():.4f}")

    print("\n[3/5] Building constraints...")
    cm = build_constraint_model(
        real, feature_names=fnames, ae_model=ae, scaler=sc, top_k=200, seed=42
    )
    print(f"  {len(cm.pairwise)} pairwise constraints")

    print("\n[4/5] Computing syndromes...")
    res = []
    for label, mat, fab in [("real", real, "none")] + [
        (f"fab_{k}", FABS[k](real, np.random.default_rng(2026)), k) for k in FABS
    ]:
        syn = compute_syndrome(mat, cm, ae, sc)
        d = {"label": label, "fabrication": fab, **asdict(syn)}
        res.append(d)
        print(
            f"  {label:<16} syndrome={syn.syndrome_score:.4f} pw={syn.pairwise_violation_score:.4f} res={syn.residual_violation_score:.4f}"
        )
        if syn.top_violated_pairs:
            p0 = syn.top_violated_pairs[0]
            gi = fnames[p0["feature_i"]] if p0["feature_i"] < len(fnames) else str(p0["feature_i"])
            gj = fnames[p0["feature_j"]] if p0["feature_j"] < len(fnames) else str(p0["feature_j"])
            print(f"    Top: {gi} <-> {gj} delta={p0['delta']:.3f}")

    print("\n[5/5] Comparison...")
    real_s = res[0]["syndrome_score"]
    fab_s = [r["syndrome_score"] for r in res[1:]]
    sep = min(fab_s) - real_s if fab_s else 0
    print(
        f"  Real: {real_s:.4f}  Fab min: {min(fab_s):.4f}  Fab max: {max(fab_s):.4f}  Sep: {sep:.4f}"
    )

    if sep > 0.05:
        conc = f"SUCCESS: separation={sep:.4f}. Interpretable violations on top of AE."
    elif sep > 0.01:
        conc = f"WEAK: separation={sep:.4f}. Marginal value."
    else:
        conc = f"NEGATIVE: separation={sep:.4f}. No improvement over AE baseline."
    print(f"\n  CONCLUSION: {conc}")

    out = {
        "experiment": "H29",
        "n_samples": ns,
        "n_features": nf,
        "n_constraints": len(cm.pairwise),
        "separation": round(sep, 4),
        "conclusion": conc,
        "results": res,
        "top_constraints": [
            {
                "g_i": fnames[c[0]],
                "g_j": fnames[c[1]],
                "rho": round(c[2], 4),
                "stab": round(c[3], 4),
            }
            for c in cm.pairwise[:20]
        ],
        "elapsed_s": round(time.time() - t0, 1),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "h29_results.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )
    print(f"  Saved: {RESULTS / 'h29_results.json'}")


if __name__ == "__main__":
    main()
