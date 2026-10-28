import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from tensorflow.keras.models import load_model

# ==========================================
# 1. Paths and model files
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

model = load_model(BASE_DIR / "ann_model.keras")
scaler = joblib.load(BASE_DIR / "scaler.pkl")
feature_columns = list(
    joblib.load(BASE_DIR / "feature_columns.pkl")
)

if "purchase" in feature_columns:
    raise ValueError(
        "Target column 'purchase' must not be "
        "inside feature_columns.pkl"
    )

if len(feature_columns) != scaler.n_features_in_:
    raise ValueError(
        f"Feature mismatch: {len(feature_columns)} columns "
        f"but scaler expects {scaler.n_features_in_}"
    )

# ==========================================
# 2. FastAPI application
# ==========================================

app = FastAPI(
    title="ShopperPredict - Online Shoppers Purchase Prediction",
    description="ANN-based purchase prediction API",
    version="1.0.0"
)

# ==========================================
# 3. CORS (needed when the page is opened with
#    VS Code Live Server on port 5500/5501)
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 4. Static files
# ==========================================

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

# ==========================================
# 5. Input validation
# ==========================================

class ShopperInput(BaseModel):

    Administrative: int = Field(ge=0)
    Administrative_Duration: float = Field(ge=0)

    Informational: int = Field(ge=0)
    Informational_Duration: float = Field(ge=0)

    ProductRelated: int = Field(ge=0)
    ProductRelated_Duration: float = Field(ge=0)

    BounceRates: float = Field(ge=0, le=1)
    PageValues: float = Field(ge=0)
    SpecialDay: float = Field(ge=0, le=1)

    OperatingSystems: int = Field(ge=1)
    Browser: int = Field(ge=1)
    Region: int = Field(ge=1)
    TrafficType: int = Field(ge=1)

    Month: str
    VisitorType: str
    Weekend: bool


# ==========================================
# 6. Preprocessing
# ==========================================

def preprocess_input(data: ShopperInput):

    df = pd.DataFrame([data.model_dump()])

    # Feature engineering
    df["Total_pages_viewed"] = (
        df["Administrative"]
        + df["Informational"]
        + df["ProductRelated"]
    )

    df["Total_time_duration"] = (
        df["Administrative_Duration"]
        + df["Informational_Duration"]
        + df["ProductRelated_Duration"]
    ).round(0)

    df["Average_per_page_duration"] = (
        df["Total_time_duration"]
        / df["Total_pages_viewed"].replace(0, np.nan)
    ).fillna(0).round(0)

    df["Product_Page_Ratio"] = (
        df["ProductRelated"]
        / df["Total_pages_viewed"].replace(0, np.nan)
    ).fillna(0).round(2)

    df["Product_Duration_Ratio"] = (
        df["ProductRelated_Duration"]
        / df["Total_time_duration"].replace(0, np.nan)
    ).fillna(0).round(2)

    # One-hot encoding
    df = pd.get_dummies(
        df,
        columns=["Month", "VisitorType"],
        drop_first=True,
        dtype=int
    )

    # Match training columns and column order
    df = df.reindex(
        columns=feature_columns,
        fill_value=0
    )

    df = df.astype(float)

    # Apply the fitted scaler
    X_scaled = scaler.transform(df)

    return X_scaled


# ==========================================
# 7. Home page
# ==========================================

@app.get("/", include_in_schema=False)
def home():

    return FileResponse(STATIC_DIR / "index.html")


# ==========================================
# 8. Prediction endpoint
# ==========================================

@app.post("/predict")
def predict(data: ShopperInput):

    try:
        X_scaled = preprocess_input(data)

        output = model.predict(
            X_scaled,
            verbose=0
        )

        probability = float(
            np.asarray(output).reshape(-1)[0]
        )

        if not np.isfinite(probability):
            raise ValueError(
                "Model returned an invalid probability."
            )

        probability = min(max(probability, 0.0), 1.0)

        prediction = int(probability >= 0.5)

        return {
            "prediction": prediction,
            "prediction_label": (
                "Purchase" if prediction == 1
                else "No Purchase"
            ),
            "purchase_probability": round(
                probability, 6
            )
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) from e


# ==========================================
# 9. Health check
# ==========================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }