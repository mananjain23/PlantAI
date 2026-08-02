from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
import io
import cv2
import base64
from fastapi import HTTPException

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def contains_face(pil_image):
    gray = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return len(faces) > 0

app = FastAPI()

# To connect Frontend (browser security requirement)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loading trained model
model = load_model("plant_disease_model.h5")

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

def looks_like_plant(pil_image):
    hsv = np.array(pil_image.resize((64, 64)).convert('HSV')).astype(np.float32)
    h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]

    avg_saturation = s.mean()
    if avg_saturation < 25:          # near-grayscale image -> reject
        return False

    # among the colorful pixels, check if hues fall in plant range (green/yellow/brown)
    plant_hue = (h > 15) & (h < 170) & (s > 25)
    return plant_hue.mean() > 0.25

@app.post("/predict")
async def predict(file: UploadFile):
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


@app.post("/api/diagnose/field")
async def field_scan(file: UploadFile):
    img_bytes = await file.read()
    img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Invalid image upload.")

    b, g, r = cv2.split(img.astype(np.float32))
    exg = 2 * g - r - b
    exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    stress_map = cv2.applyColorMap(255 - exg_norm, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(img, 0.4, stress_map, 0.6, 0)

    b64 = base64.b64encode(cv2.imencode('.jpg', overlay)[1]).decode('utf-8')

    return {
        "mode": "field_scan",
        "heatmap_url": f"data:image/jpeg;base64,{b64}",
        "note": "Red/yellow zones = low vegetation health (possible disease, stress, or soil). Zoom into flagged zones and run /predict for a specific diagnosis."
    }