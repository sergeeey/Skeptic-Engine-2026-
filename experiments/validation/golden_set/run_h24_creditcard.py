"""
H24 Benford Forensics — Credit Card Fraud Detection (Real Data)

Adapts H24 experiment from scRNA-seq to credit card transactions.
Tests Benford's Law on REAL fraud labels (not synthetic fabrication).

Dataset: MLG-ULB Credit Card Fraud (284,807 transactions, 492 fraud)
Goal: Compare AUC on real fraud vs H24's synthetic fabrication (AUC 0.978).

Usage:
    python experiments/validation/golden_set/run_h24_creditcard.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit

# Import H24 Benford feature extractor
# Note: digit_features.py has extract_features_per_sample, not extract_benford_digit_distribution
# We'll implement our own Benford features here


def load_creditcard_data(csv_path: str | None = None):
    """
    Load MLG-ULB credit card fraud dataset.

    Returns:
        pd.DataFrame: Full dataset with columns [Time, V1-V28, Amount, Class]
    """
    # Default path: look in script's directory
    if csv_path is None:
        csv_path = Path(__file__).parent / "creditcard_fraud_dataset.csv"
    else:
        csv_path = Path(csv_path)

    if not csv_path.exists():
        print(f"[ERROR] Dataset not found: {csv_path}")
        print("[ACTION] Run load_real_fraud_data.py first to download dataset.")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    print(f"[INFO] Loaded {len(df):,} transactions")
    print(f"[INFO] Fraud: {df['Class'].sum():,} ({df['Class'].mean()*100:.3f}%)")
    return df


def extract_benford_features(df: pd.DataFrame) -> np.ndarray:
    """
    Extract Benford first-digit features from transaction amounts.

    H24 uses Benford on UMI counts. Here: Benford on Amount column.

    Args:
        df: Credit card transactions with 'Amount' column

    Returns:
        np.ndarray: (n_transactions, n_benford_features)
    """
    amounts = df["Amount"].values

    # Extract first digit (skip zeros)
    first_digits = []
    for amt in amounts:
        if amt > 0:
            # Get first digit
            s = str(int(amt * 100))  # Convert to cents to handle decimals
            if s and s[0] != "0":
                first_digits.append(int(s[0]))
            else:
                first_digits.append(0)  # Placeholder for zero amounts
        else:
            first_digits.append(0)

    # Count distribution of digits 1-9
    digit_counts = np.zeros(9)
    for d in first_digits:
        if 1 <= d <= 9:
            digit_counts[d - 1] += 1

    # Normalize to probability distribution
    total = digit_counts.sum()
    digit_dist = digit_counts / total if total > 0 else np.zeros(9)

    # Benford's Law expected distribution
    benford_expected = np.log10(1 + 1 / np.arange(1, 10))

    # Features: [digit_dist (9), deviation from Benford (9), chi-square (1)]
    deviation = digit_dist - benford_expected
    chi_square = np.sum((digit_dist - benford_expected) ** 2 / benford_expected)

    features = np.concatenate([digit_dist, deviation, [chi_square]])
    return features.reshape(1, -1)  # Single feature vector per dataset


def extract_features_per_transaction(df: pd.DataFrame, window_size: int = 100):
    """
    Extract Benford features using sliding window.

    For each transaction, compute Benford distribution on last N transactions.

    Args:
        df: Transactions sorted by Time
        window_size: Number of prior transactions to analyze

    Returns:
        np.ndarray: (n_transactions, n_benford_features)
    """
    print(f"[INFO] Extracting Benford features (window={window_size})...")

    features = []
    amounts = df["Amount"].values

    for i in range(len(df)):
        start_idx = max(0, i - window_size)
        window_amounts = amounts[start_idx : i + 1]

        # Extract first digits
        first_digits = []
        for amt in window_amounts:
            if amt > 0:
                s = str(int(amt * 100))
                if s and s[0] != "0":
                    first_digits.append(int(s[0]))

        # Count distribution
        digit_counts = np.zeros(9)
        for d in first_digits:
            if 1 <= d <= 9:
                digit_counts[d - 1] += 1

        # Normalize
        total = digit_counts.sum()
        digit_dist = digit_counts / total if total > 0 else np.zeros(9)

        # Benford expected
        benford_expected = np.log10(1 + 1 / np.arange(1, 10))

        # Features
        deviation = digit_dist - benford_expected
        chi_square = np.sum((digit_dist - benford_expected) ** 2 / (benford_expected + 1e-10))

        feat = np.concatenate([digit_dist, deviation, [chi_square]])
        features.append(feat)

    return np.array(features)


def run_h24_creditcard_experiment():
    """
    Main experiment: H24 Benford on real credit card fraud.

    Steps:
        1. Load MLG-ULB dataset
        2. Extract Benford features (per-transaction sliding window)
        3. Train RF + LogReg classifiers
        4. Report AUC on real fraud labels
        5. Compare to H24 synthetic AUC (0.978)
    """
    print("=" * 60)
    print("H24 Benford — Credit Card Fraud (Real Data)")
    print("=" * 60)

    # Load data
    df = load_creditcard_data()

    # Sort by Time (transactions are temporal)
    df = df.sort_values("Time").reset_index(drop=True)

    # Extract features
    X = extract_features_per_transaction(df, window_size=100)
    y = df["Class"].values

    print(f"[INFO] Feature matrix: {X.shape}")
    print(f"[INFO] Labels: {y.shape}, fraud rate: {y.mean()*100:.3f}%")

    # Train/test split (stratified)
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
    train_idx, test_idx = next(sss.split(X, y))

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    print(f"[INFO] Train: {len(X_train):,} | Test: {len(X_test):,}")

    # Train classifiers
    print("\n[TRAINING] Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)

    print("[TRAINING] Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    lr.fit(X_train, y_train)

    # Evaluate
    results = {}
    for name, clf in [("RandomForest", rf), ("LogisticRegression", lr)]:
        y_pred_proba = clf.predict_proba(X_test)[:, 1]

        auc = roc_auc_score(y_test, y_pred_proba)
        ap = average_precision_score(y_test, y_pred_proba)

        results[name] = {
            "auc_roc": float(auc),
            "average_precision": float(ap),
        }

        print(f"\n[RESULTS] {name}:")
        print(f"  AUC-ROC: {auc:.4f}")
        print(f"  AP: {ap:.4f}")

    # Compare to H24 synthetic
    print("\n" + "=" * 60)
    print("COMPARISON: Real Fraud vs H24 Synthetic Fabrication")
    print("=" * 60)
    print("H24 (scRNA synthetic fabrication): AUC 0.978")
    print(f"H24 (credit card REAL fraud):      AUC {results['RandomForest']['auc_roc']:.3f}")
    print(f"\nDelta: {results['RandomForest']['auc_roc'] - 0.978:.3f}")

    if results["RandomForest"]["auc_roc"] < 0.65:
        print("\n⚠️  [FAIL] AUC < 0.65 — Benford ineffective on real fraud")
    elif results["RandomForest"]["auc_roc"] < 0.80:
        print("\n⚠️  [WEAK] AUC < 0.80 — Benford works but not strong")
    else:
        print("\n✅ [PASS] AUC ≥ 0.80 — Benford effective on real fraud")

    # Save results
    output_path = Path(__file__).parent / "h24_creditcard_real_fraud_results.json"
    output_path.write_text(json.dumps(results, indent=2))

    print(f"\n[SAVED] Results: {output_path}")

    return results


if __name__ == "__main__":
    run_h24_creditcard_experiment()
