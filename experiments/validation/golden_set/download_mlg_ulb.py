"""
Download MLG-ULB Credit Card Fraud Dataset

Dataset: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
Size: 284,807 transactions, 492 fraudulent (0.172%)
Features: Time, V1-V28 (PCA transformed), Amount, Class (0=normal, 1=fraud)

NOTE: This script requires Kaggle API credentials.
Setup: https://github.com/Kaggle/kaggle-api#api-credentials

Alternative: Manual download from Kaggle → place creditcard.csv in this directory.
"""

import sys
from pathlib import Path


def download_via_kaggle_api():
    """Download using Kaggle API (requires authentication)."""
    try:
        import kaggle

        print("[INFO] Kaggle API found. Downloading MLG-ULB dataset...")
        kaggle.api.dataset_download_files("mlg-ulb/creditcardfraud", path=".", unzip=True)
        print("[SUCCESS] Dataset downloaded: creditcard.csv")
        return True
    except ImportError:
        print("[ERROR] Kaggle package not installed. Install: pip install kaggle")
        return False
    except Exception as e:
        print(f"[ERROR] Kaggle API failed: {e}")
        print("[INFO] Manual download required:")
        print("  1. Go to https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
        print("  2. Click 'Download' (requires Kaggle login)")
        print("  3. Extract creditcard.csv to this directory")
        return False


def check_dataset_exists():
    """Check if dataset already downloaded."""
    if Path("creditcard.csv").exists():
        print("[INFO] Dataset already exists: creditcard.csv")
        return True
    return False


if __name__ == "__main__":
    if check_dataset_exists():
        print("[SKIP] Dataset already present.")
        sys.exit(0)

    success = download_via_kaggle_api()
    if not success:
        print("\n[ACTION REQUIRED] Manual download needed.")
        print("Run this script again after placing creditcard.csv in this directory.")
        sys.exit(1)
