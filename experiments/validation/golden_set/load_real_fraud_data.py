"""
Load Real Fraud Dataset — MLG-ULB Credit Card Fraud

Dataset: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
Size: 284,807 transactions, 492 fraudulent (0.172%)
Features: Time, V1-V28 (PCA transformed), Amount, Class (0=normal, 1=fraud)

Uses kagglehub — no manual authentication needed (OAuth flow on first use).
"""

import kagglehub
from kagglehub import KaggleDatasetAdapter


def load_creditcard_fraud_dataset():
    """
    Load MLG-ULB Credit Card Fraud dataset from Kaggle.

    Returns:
        pd.DataFrame: Full dataset (284K+ transactions)
    """
    print("[INFO] Loading MLG-ULB Credit Card Fraud dataset via kagglehub...")
    print("[INFO] First use may prompt OAuth authentication in browser.")

    # Load dataset (kagglehub will handle authentication)
    # NOTE: file_path must be explicit filename, not empty string
    # FIX: UnicodeDecodeError — add encoding parameter for pandas
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "mlg-ulb/creditcardfraud",
        "creditcard.csv",  # Explicit filename required
        pandas_kwargs={"encoding": "latin-1"},  # Fix encoding issue
    )

    print(f"[SUCCESS] Dataset loaded: {len(df)} transactions")
    print(f"[INFO] Fraud count: {df['Class'].sum()} ({df['Class'].mean()*100:.3f}%)")
    print(f"[INFO] Features: {list(df.columns)}")
    print("\nFirst 5 records:")
    print(df.head())

    return df


if __name__ == "__main__":
    df = load_creditcard_fraud_dataset()

    # Basic stats
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    print(f"Total transactions: {len(df):,}")
    print(f"Fraudulent: {df['Class'].sum():,} ({df['Class'].mean()*100:.4f}%)")
    print(f"Normal: {(df['Class']==0).sum():,} ({(df['Class']==0).mean()*100:.4f}%)")
    print(f"\nFeatures: {df.shape[1]} columns")
    print("  - Time: transaction timestamp (seconds)")
    print("  - V1-V28: PCA-transformed features (anonymized)")
    print("  - Amount: transaction amount")
    print("  - Class: 0=normal, 1=fraud")

    # Save to CSV for inspection
    output_path = "creditcard_fraud_dataset.csv"
    df.to_csv(output_path, index=False)
    print(f"\n[SAVED] Dataset written to: {output_path}")
