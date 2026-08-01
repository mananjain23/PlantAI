from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
import io

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

@app.post("/predict")
async def predict(file: UploadFile):
    image_data = await file.read()
    image = Image.open(io.BytesIO(image_data)).convert("RGB").resize((224, 224))

    img_array = np.array(image) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)
    predicted_class = class_names[np.argmax(prediction)]
    confidence = float(np.max(prediction))

    return {
        "disease": predicted_class,
        "confidence": round(confidence * 100, 2)
    }