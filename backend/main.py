import os
import io
import json
import base64
import numpy as np
import cv2
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from tensorflow.keras.models import load_model as load_model_tf
from keras.models import load_model as load_model_keras
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="CropGuard AI API")

# To connect Frontend (browser security requirement)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ==========================================
# FACE / PLANT SANITY CHECKS (from original main.py)
# ==========================================
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


def contains_face(pil_image):
    gray = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return len(faces) > 0


def looks_like_plant(pil_image):
    hsv = np.array(pil_image.resize((64, 64)).convert('HSV')).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    avg_saturation = s.mean()
    if avg_saturation < 25:          # near-grayscale image -> reject
        return False

    # among the colorful pixels, check if hues fall in plant range (green/yellow/brown)
    plant_hue = (h > 15) & (h < 170) & (s > 25)
    return plant_hue.mean() > 0.25


# ==========================================
# MODEL 1: original single-leaf classifier (plant_disease_model.h5)
# ==========================================
model = load_model_tf(str(MODELS_DIR / "plant_disease_model.h5"))

# Class names in the correct order (as obtained from Kaggle)
class_names = [
    'Pepper_Bacterial_spot',
    'Pepper_healthy',
    'Potato_Early_blight',
    'Potato_Late_blight',
    'Potato_healthy',
    'Tomato_Bacterial_spot',
    'Tomato_Early_blight',
    'Tomato_Late_blight',
    'Tomato_Leaf_Mold',
    'Tomato_Septoria_leaf_spot',
    'Tomato_Spider_mites',
    'Tomato_Target_Spot',
    'Tomato_YellowLeaf_Curl_Virus',
    'Tomato_mosaic_virus',
    'Tomato_healthy'
]

# ==========================================
# MODEL 2: CropGuard classifier + fallback (cropguard_model.h5)
# ==========================================
MODEL_PATH = MODELS_DIR / "cropguard_model.h5"
CLASS_INDICES_PATH = MODELS_DIR / "class_indices.json"

if MODEL_PATH.exists() and CLASS_INDICES_PATH.exists():
    model2 = load_model_keras(str(MODEL_PATH))
    with open(CLASS_INDICES_PATH, "r") as f:
        labels = {v: k for k, v in json.load(f).items()}
else:
    model2 = None
    labels = {0: "Tomato___Healthy", 1: "Potato___Early_blight", 2: "Potato___Late_blight"}

CONFIDENCE_GAP_THRESHOLD = 0.15

# ==========================================
# PYDANTIC SCHEMAS (STRICT VALIDATION)
# ==========================================
class SoilData(BaseModel):
    nitrogen: float = Field(..., ge=0, le=300, description="Nitrogen content")
    phosphorus: float = Field(..., ge=0, le=300, description="Phosphorus content")
    potassium: float = Field(..., ge=0, le=300, description="Potassium content")
    temperature: float = Field(..., ge=-10, le=55, description="Temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    ph: float = Field(..., ge=0.0, le=14.0, description="Soil pH value")
    rainfall: float = Field(..., ge=0, le=5000, description="Rainfall in mm")
    location: str


class CropRec(BaseModel):
    rank: int
    crop: str
    suitability_score: int
    reasoning: str
    growth_cycle: str


class RecommendationResponse(BaseModel):
    recommendations: list[CropRec]


# ==========================================
# DETERMINISTIC CROP DATABASE & RULES
# ==========================================
CROP_DATABASE = {
    "Rice": {"temp": (20, 35), "hum": (70, 100), "rain": (1000, 2500), "ph": (5.5, 7.5), "n": (80, 120), "p": (30, 60), "k": (30, 50), "cycle": "120-150 days"},
    "Wheat": {"temp": (10, 25), "hum": (40, 70), "rain": (300, 800), "ph": (6.0, 7.5), "n": (80, 120), "p": (40, 60), "k": (30, 50), "cycle": "120-150 days"},
    "Maize": {"temp": (18, 32), "hum": (50, 80), "rain": (500, 1000), "ph": (5.5, 7.5), "n": (80, 120), "p": (40, 60), "k": (30, 50), "cycle": "90-120 days"},
    "Cotton": {"temp": (22, 35), "hum": (50, 85), "rain": (500, 1000), "ph": (5.8, 8.0), "n": (100, 140), "p": (30, 60), "k": (40, 60), "cycle": "150-180 days"},
    "Sugarcane": {"temp": (25, 35), "hum": (70, 90), "rain": (1500, 2500), "ph": (6.0, 8.0), "n": (100, 150), "p": (40, 70), "k": (40, 60), "cycle": "300-360 days"},
    "Soybean": {"temp": (20, 30), "hum": (50, 70), "rain": (500, 1000), "ph": (6.0, 7.5), "n": (20, 40), "p": (40, 60), "k": (20, 40), "cycle": "90-120 days"},
    "Jute": {"temp": (25, 35), "hum": (70, 90), "rain": (1500, 2000), "ph": (6.0, 7.5), "n": (60, 90), "p": (30, 50), "k": (30, 50), "cycle": "120-150 days"},
    "Sorghum": {"temp": (25, 35), "hum": (40, 60), "rain": (400, 800), "ph": (6.0, 8.5), "n": (60, 90), "p": (30, 50), "k": (30, 50), "cycle": "100-130 days"},
    "Coconut": {"temp": (25, 30), "hum": (70, 90), "rain": (1500, 2500), "ph": (5.2, 8.0), "n": (80, 100), "p": (40, 60), "k": (80, 100), "cycle": "Perennial"},
    "Banana": {"temp": (25, 35), "hum": (75, 85), "rain": (1500, 2500), "ph": (6.5, 7.5), "n": (100, 150), "p": (30, 50), "k": (80, 120), "cycle": "Perennial"}
}

REGIONAL_RULES = {
    "Northern/Inland": {"boost": ["Wheat", "Rice", "Cotton", "Maize", "Sugarcane"], "veto": ["Coconut", "Banana", "Jute"]},
    "Southern/Coastal": {"boost": ["Banana", "Coconut", "Rice", "Sugarcane", "Cotton"], "veto": ["Wheat"]},
    "Eastern": {"boost": ["Jute", "Rice", "Banana", "Sugarcane"], "veto": ["Wheat", "Cotton"]},
    "Western": {"boost": ["Cotton", "Sugarcane", "Soybean"], "veto": ["Jute"]}
}


def evaluate_param(name, value, unit, min_val, max_val, max_penalty):
    # Strict mathematical inclusion
    if min_val <= value <= max_val:
        return 0.0, f"✓ {name}"

    # Calculate proportional deviation penalty
    spread = max_val - min_val if max_val != min_val else 1.0
    if value < min_val:
        penalty = min(max_penalty, (abs(value - min_val) / spread) * max_penalty)
        return penalty, f"• {name} ({value}{unit}) is below the preferred range ({min_val}-{max_val}{unit})."
    else:
        penalty = min(max_penalty, (abs(value - max_val) / spread) * max_penalty)
        return penalty, f"• {name} ({value}{unit}) is above the preferred range ({min_val}-{max_val}{unit})."


def calculate_crop_score(crop_name, crop_data, user_data):
    score = 100.0
    matched = []
    deviations = []

    params = [
        ("Temperature", user_data.temperature, "°C", crop_data["temp"][0], crop_data["temp"][1], 30.0),
        ("Rainfall", user_data.rainfall, " mm", crop_data["rain"][0], crop_data["rain"][1], 25.0),
        ("Humidity", user_data.humidity, "%", crop_data["hum"][0], crop_data["hum"][1], 15.0),
        ("Soil pH", user_data.ph, "", crop_data["ph"][0], crop_data["ph"][1], 15.0),
        ("Nitrogen", user_data.nitrogen, "", crop_data["n"][0], crop_data["n"][1], 3.33),
        ("Phosphorus", user_data.phosphorus, "", crop_data["p"][0], crop_data["p"][1], 3.33),
        ("Potassium", user_data.potassium, "", crop_data["k"][0], crop_data["k"][1], 3.34)
    ]

    for p_name, u_val, unit, c_min, c_max, max_pen in params:
        pen, msg = evaluate_param(p_name, u_val, unit, c_min, c_max, max_pen)
        score -= pen
        if pen == 0:
            matched.append(msg)
        else:
            deviations.append(msg)

    loc = user_data.location.lower()
    region_type = None
    if any(x in loc for x in ["punjab", "haryana", "up", "mp", "rajasthan", "uttar pradesh", "madhya pradesh"]):
        region_type = "Northern/Inland"
    elif any(x in loc for x in ["kerala", "tn", "karnataka", "andhra", "tamil nadu"]):
        region_type = "Southern/Coastal"
    elif any(x in loc for x in ["bengal", "bihar", "assam", "odisha"]):
        region_type = "Eastern"
    elif any(x in loc for x in ["gujarat", "maharashtra"]):
        region_type = "Western"

    if region_type:
        if crop_name in REGIONAL_RULES[region_type]["boost"]:
            matched.append("✓ Regional Suitability")
        elif crop_name in REGIONAL_RULES[region_type]["veto"]:
            score -= 50.0
            deviations.append(f"• Regional Suitability: {crop_name} is rarely viable in this region.")
        else:
            score -= 8.0
            deviations.append(f"• Regional Suitability: {crop_name} is not commonly cultivated in this region.")

    return {
        "crop": crop_name,
        "score": round(max(0.0, min(100.0, score))),
        "matched_text": "\n".join(matched) if matched else "✓ None",
        "deviations_text": "\n".join(deviations) if deviations else "• None",
        "cycle": crop_data["cycle"]
    }


# ==========================================
# HELPER FUNCTIONS (CropGuard single-leaf pipeline)
# ==========================================
def process_image(img_bytes):
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB").resize((224, 224))
    return np.expand_dims(np.array(image, dtype=np.float32) / 255.0, axis=0)


def predict_top2(tensor):
    """Renamed from the original helper `predict()` to avoid clashing
    with the /predict endpoint function below. Behavior is unchanged."""
    if model2 is None:
        return [("Potato___Early_blight", 0.48), ("Potato___Late_blight", 0.38)]
    preds = model2.predict(tensor, verbose=0)[0]
    for k, v in labels.items():
        if v == "PlantVillage":
            preds[k] = 0.0
            break
    top2 = np.argsort(preds)[::-1][:2]
    return (labels[top2[0]], float(preds[top2[0]])), (labels[top2[1]], float(preds[top2[1]]))


def get_llm_advice(disease, is_ambiguous, candidates):
    if is_ambiguous:
        prompt = f"Image visually matches both '{candidates[0]['label']}' and '{candidates[1]['label']}'. Provide a short 3-sentence message to a farmer explaining visual symptom overlap, advising a closer photo or expert verification. Do not force a fake single diagnosis."
    else:
        prompt = f"Crop leaf diagnosed with '{disease}'. Provide a brief 3-bullet farmer-friendly treatment recommendation grounded strictly in standard agricultural practices."
    try:
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a direct agricultural expert."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return "Recommendation unavailable. Please consult a local agricultural extension worker."


# ==========================================
# ENDPOINTS
# ==========================================

@app.post("/predict")
async def predict(file: UploadFile):
    """Original single-leaf classifier endpoint (plant_disease_model.h5),
    with face-detection and plant-sanity guards. Unchanged from before."""
    image_data = await file.read()
    image = Image.open(io.BytesIO(image_data)).convert("RGB").resize((224, 224))

    if contains_face(image):
        return {
            "disease": "No leaf detected — a face was detected in this image",
            "confidence": 0
        }

    if not looks_like_plant(image):
        return {
            "disease": "No leaf detected — please upload a clear photo of a single leaf",
            "confidence": 0
        }

    img_array = np.array(image) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)
    predicted_class = class_names[np.argmax(prediction)]
    confidence = float(np.max(prediction))

    return {
        "disease": predicted_class,
        "confidence": round(confidence * 100, 2)
    }


@app.post("/api/diagnose/single")
async def single_leaf(file: UploadFile = File(...)):
    """CropGuard single-leaf endpoint (cropguard_model.h5), with
    ambiguity detection + Groq LLM-generated advice. Unchanged from before."""
    img_bytes = await file.read()
    if len(img_bytes) > 8000000:
        raise HTTPException(status_code=400, detail="File size exceeds 8MB limit.")
    tensor = process_image(img_bytes)
    top1, top2 = predict_top2(tensor)
    is_ambiguous = (top1[1] - top2[1]) < CONFIDENCE_GAP_THRESHOLD
    candidates = [{"label": top1[0], "confidence": top1[1]}, {"label": top2[0], "confidence": top2[1]}]
    return {
        "mode": "single_leaf",
        "disease_label": "Ambiguous / Needs Verification" if is_ambiguous else top1[0],
        "confidence": top1[1],
        "is_ambiguous": is_ambiguous,
        "candidates": candidates,
        "recommendation": get_llm_advice(top1[0], is_ambiguous, candidates),
        "heatmap_url": None
    }


@app.post("/api/diagnose/field")
async def field_scan(file: UploadFile = File(...)):
    """Field-level ExG vegetation stress heatmap. Identical in both
    original files — kept once here."""
    img_bytes = await file.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image upload.")

    b, g, r = cv2.split(img.astype(np.float32))
    exg = 2 * g - r - b
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    stress_map = cv2.applyColorMap(255 - exg_norm, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(img, 0.4, stress_map, 0.6, 0)

    b64 = base64.b64encode(cv2.imencode('.jpg', overlay)[1]).decode('utf-8')

    return {
        "mode": "field_scan",
        "disease_label": "Drone Scan Complete: Vegetation Stress Map Generated",
        "is_ambiguous": True,
        "heatmap_url": f"data:image/jpeg;base64,{b64}",
        "recommendation": "RGB Drone imagery analyzed using Excess Green (ExG) vegetation index. Red/Yellow zones indicate low chlorophyll density (stress, disease, or exposed soil). Deploy field workers to red zones for single-leaf CNN triage.",
        "note": "Red/yellow zones = low vegetation health (possible disease, stress, or soil). Zoom into flagged zones and run /predict for a specific diagnosis."
    }


@app.post("/api/recommend", response_model=RecommendationResponse)
async def recommend_crop(data: SoilData):
    # Hard guardrails for mathematically unviable land
    if data.ph < 3.5 or data.ph > 10.0 or data.rainfall < 50:
        return RecommendationResponse(recommendations=[{
            "rank": 1,
            "crop": "Non-Agricultural Field / Restoration Required",
            "suitability_score": 0,
            "reasoning": f"Matched Parameters:\n✓ None\n\nMinor Deviations:\n• Extreme Conditions Detected\n\nAgronomic Reasoning:\nThe provided parameters (pH: {data.ph}, Rainfall: {data.rainfall}mm) fall outside commercial agricultural viability. Soil requires intense biological restoration and pH balancing before planting.",
            "growth_cycle": "N/A"
        }])

    # 1 & 2 & 3. Python Math Algorithm
    scored_crops = []
    for crop_name, crop_data in CROP_DATABASE.items():
        scored_crops.append(calculate_crop_score(crop_name, crop_data, data))

    # Sort and take top 3
    scored_crops.sort(key=lambda x: x["score"], reverse=True)
    top_3 = scored_crops[:3]

    # 4 & 5. LLM as a Formatter ONLY (No Math, No Bounds)
    system_prompt = """
    You are an Agricultural Formatting AI. The core mathematical scoring and parameter matching has already been executed perfectly in Python.

    Your ONLY task is to take the structured JSON data provided by the user and format it into the final output schema.

    CRITICAL INSTRUCTIONS:
    1. DO NOT alter the `crop`, `score`, `rank`, or `cycle` provided to you.
    2. Construct the `reasoning` string for each crop EXACTLY in this format:

       Matched Parameters:
       [Insert matched_text verbatim from the prompt]

       Minor Deviations:
       [Insert deviations_text verbatim from the prompt]

       Agronomic Reasoning:
       [Write 1-2 concise, professional sentences explaining why this crop makes sense for the user's location based on the data.]

    3. Output strictly valid JSON matching the exact output schema.

    You must output ONLY a valid JSON object matching this exact structure:
    {
      "recommendations": [
        {
          "rank": 1,
          "crop": "Name from input",
          "suitability_score": 95,
          "reasoning": "Matched Parameters:\n✓ ...\n\nMinor Deviations:\n• ...\n\nAgronomic Reasoning:\n[Your 1-2 sentences here]",
          "growth_cycle": "Cycle from input"
        }
      ]
    }
    """

    user_prompt = json.dumps([
        {
            "rank": idx + 1,
            "crop": item["crop"],
            "score": item["score"],
            "matched_text": item["matched_text"],
            "deviations_text": item["deviations_text"],
            "cycle": item["cycle"]
        } for idx, item in enumerate(top_3)
    ], indent=2)

    try:
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )

        json_payload = json.loads(res.choices[0].message.content.strip())
        validated_response = RecommendationResponse(**json_payload)
        return validated_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop recommendation formatter failure: {str(e)}")