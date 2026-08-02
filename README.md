# 🌿 PlantAI — AI-Powered Crop Disease Detection

An AI system that helps farmers detect crop diseases early from a simple 
leaf photo — reducing yield losses caused by late diagnosis.

## What It Does
Upload or capture a photo of a crop leaf, and PlantAI instantly identifies 
whether it's healthy or diseased, which disease it is, and returns a 
confidence score — no agricultural expert required.

## Problem
Farmers often cannot detect crop diseases early enough, leading to major 
yield losses. Most existing solutions require internet-heavy apps or 
manual expert consultation, which isn't always accessible.

## Solution
A transfer-learning computer vision model (MobileNetV2, fine-tuned on the 
PlantVillage dataset) served through a FastAPI backend, with a simple 
web interface for image upload and instant results.

## Tech Stack
- **ML:** TensorFlow/Keras, MobileNetV2 (transfer learning)
- **Backend:** FastAPI, Python
- **Frontend:** HTML/CSS/JavaScript
- **Dataset:** PlantVillage (15 classes — Tomato, Potato, Pepper)

## Current Status
- Model trained: 98.5% training accuracy, 91.3% validation accuracy
- End-to-end pipeline working: image upload → prediction → results display
- Actively improving real-world image robustness via data augmentation

## Team
Built by [Member 1 name] & [Member 2 name] for [Hackathon Name] 2026, 
Track 4 — Artificial Intelligence & Machine Learning.

## Requirements
absl-py==2.5.0
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.14.2
astunparse==1.6.3
certifi==2026.7.22
charset-normalizer==3.4.9
click==8.4.2
colorama==0.4.6
fastapi==0.141.1
flatbuffers==25.12.19
gast==0.7.0
google-pasta==0.2.0
groq
grpcio==1.83.0
h11==0.16.0
h5py==3.14.0
idna==3.18
keras==3.15.1
libclang==18.1.1
markdown-it-py==4.2.0
mdurl==0.1.2
ml_dtypes==0.5.4
namex==0.1.0
numpy==2.4.6
opencv-python
opt_einsum==3.4.0
optree==0.19.1
packaging==26.2
pillow==12.3.0
protobuf==7.35.1
pydantic==2.13.4
pydantic_core==2.46.4
Pygments==2.20.0
python-dotenv
python-multipart==0.0.32
requests==2.34.2
rich==15.0.0
six==1.17.0
starlette==1.3.1
tensorflow==2.21.0
termcolor==3.3.0
typing-inspection==0.4.2
typing_extensions==4.16.0
urllib3==2.7.0
uvicorn==0.52.0
wrapt==2.3.0
