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
