import os
import sys
import glob
import logging
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config

logger = logging.getLogger("crypto_bi_pipeline.ml_model")

MODEL_PATH = config.BASE_DIR / "models" / "price_direction_rf.pkl"
SCALER_PATH = config.BASE_DIR / "models" / "scaler.pkl"

# Ensure models directory exists
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

def prepare_features(df):
    """
    Extracts features and target labels from the dataframe.
    """
    feature_cols = [
        "market_cap_rank", 
        "current_price_usd", 
        "market_cap_usd", 
        "total_volume_usd", 
        "volatility_24h", 
        "volume_to_market_cap_ratio"
    ]
    
    # Check if all features exist
    for col in feature_cols:
        if col not in df.columns:
            raise KeyError(f"Feature column '{col}' missing from data.")
            
    X = df[feature_cols].copy()
    
    # Handle NaNs or Infinities
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0.0)
    
    y = None
    if "price_direction" in df.columns:
        y = df["price_direction"].copy()
        
    return X, y

def train_ml_model():
    """
    Loads historical processed CSVs, trains a Random Forest Classifier,
    and saves the model and scaler.
    """
    logger.info("Starting Machine Learning model training process...")
    
    # 1. Gather all processed files
    search_path = str(config.PROCESSED_DATA_DIR / "markets_processed_*.csv")
    files = glob.glob(search_path)
    
    if not files:
        latest_processed = config.PROCESSED_DATA_DIR / "latest.csv"
        if latest_processed.exists():
            files = [str(latest_processed)]
        else:
            raise FileNotFoundError("No processed CSV files found for training the model.")
            
    logger.info(f"Gathering data from {len(files)} files...")
    
    # Concatenate all datasets
    dfs = []
    for file in files:
        try:
            dfs.append(pd.read_csv(file))
        except Exception as e:
            logger.error(f"Error reading file {file}: {e}")
            
    if not dfs:
        raise ValueError("No valid data loaded for training.")
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Drop duplicates to prevent train leakage if we have multiple snapshots of the same coin
    full_df = full_df.drop_duplicates(subset=["coin_id", "snapshot_date"])
    
    if len(full_df) < 10:
        logger.warning("Very few data points available. Model may overfit.")
        
    X, y = prepare_features(full_df)
    
    if y is None or len(y.unique()) < 2:
        logger.error("Target label 'price_direction' must contain at least 2 distinct classes.")
        raise ValueError("Insufficient target labels for classification.")
        
    # 2. Train-Test Split
    test_size = 0.2 if len(full_df) >= 50 else 0.1
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    # 3. Standardize Features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 4. Train Random Forest Classifier
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf_model.fit(X_train_scaled, y_train)
    
    # 5. Evaluate Model
    y_pred = rf_model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    
    logger.info(f"Model Training Complete. Test Accuracy: {acc:.4f}")
    logger.info("Classification Report:")
    report = classification_report(y_test, y_pred)
    logger.info(f"\n{report}")
    
    # 6. Save Model and Scaler
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(rf_model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
        
    logger.info(f"Saved model to {MODEL_PATH} and scaler to {SCALER_PATH}")
    
    return {
        "accuracy": acc,
        "classification_report": report,
        "features": list(X.columns)
    }

def predict_latest_direction(df):
    """
    Loads the saved model and scaler, and runs predictions on the provided dataframe.
    Returns the dataframe with an added 'predicted_direction' column.
    """
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        logger.warning("ML Model or Scaler not found on disk. Run training first.")
        # Train model on the fly if files exist
        try:
            train_ml_model()
        except Exception as e:
            logger.error(f"Failed to auto-train model: {e}")
            df["predicted_direction"] = "Model Unavailable"
            return df
            
    # Load model and scaler
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
        
    X_latest, _ = prepare_features(df)
    X_latest_scaled = scaler.transform(X_latest)
    
    predictions = model.predict(X_latest_scaled)
    df["predicted_direction"] = predictions
    
    return df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Running ml_model.py standalone...")
    try:
        results = train_ml_model()
        print("Training successful!")
        print(f"Accuracy: {results['accuracy']:.2%}")
    except Exception as ex:
        print(f"Training failed: {ex}")
