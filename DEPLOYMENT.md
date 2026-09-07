# WeatherGPT — Render Deployment Guide (Step-by-Step)

This guide walks you through deploying **WeatherGPT** online to **Render** (Free Tier).

---

## 📋 Prerequisites

1. A **GitHub Account**: [github.com](https://github.com)
2. A **Render Account**: [render.com](https://render.com) (Free account)
3. *(Optional)* A **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

---

## 🚀 Step 1: Push Your Project to GitHub

If your project is not yet on GitHub, run these commands from your project root:

```powershell
# 1. Navigate to the project root
cd C:\Users\nsidd\.gemini\antigravity-ide\scratch\WeatherGPT

# 2. Initialize git (if not already initialized)
git init

# 3. Add all project files
git add .

# 4. Commit your changes
git commit -m "Initial commit of WeatherGPT platform"

# 5. Set default branch to main
git branch -M main

# 6. Link to your GitHub repository (replace with your repo URL)
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/WeatherGPT.git

# 7. Push the code to GitHub
git push -u origin main
```

---

## 🌐 Step 2: Create a New Web Service on Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click the **"New +"** button at the top right and select **"Web Service"**.
3. Select **"Build and deploy from a Git repository"** and click **Next**.
4. Connect your GitHub account and select your **`WeatherGPT`** repository.

---

## ⚙️ Step 3: Configure Web Service Settings

Fill in the configuration fields with the exact values below:

| Configuration Field | Value |
|---|---|
| **Name** | `weathergpt` *(or your custom name)* |
| **Region** | Select the closest region (e.g., *Singapore* or *Frankfurt*) |
| **Branch** | `main` |
| **Root Directory** | *(Leave blank)* |
| **Runtime** | `Python` |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` ($0/month) |

---

## 🔑 Step 4: Add Environment Variables

Scroll down to the **"Environment Variables"** section and add the following keys:

| Key | Value | Description |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Sets the Python runtime on Render |
| `ENVIRONMENT` | `production` | Production environment flag |
| `GEMINI_API_KEY` | `AIzaSy...` *(your Gemini API key)* | Optional but recommended for AI answers |

*(Note: WeatherGPT will work automatically with deterministic fallback even if `GEMINI_API_KEY` is not provided).*

---

## 🩺 Step 5: Configure Health Check Path

1. Click **"Advanced"** at the bottom of the page.
2. Under **"Health Check Path"**, enter:
   ```text
   /health
   ```
3. Click **"Create Web Service"**.

---

## ⏳ Step 6: Deployment & Verification

Render will automatically build and start the service:
1. It installs all dependencies from `backend/requirements.txt`.
2. It starts Uvicorn bound to `0.0.0.0:$PORT`.
3. Once the build logs display `Your service is live 🎉`, click the URL at the top (e.g., `https://weathergpt-xxxx.onrender.com`).

---

## ✅ Live Verification Checklist

Once deployed, verify the following:

- [ ] **Root URL**: Opening `https://<your-app>.onrender.com/` opens the full WeatherGPT Dashboard.
- [ ] **GPS Location**: Browser prompts for location permission and automatically displays your local weather.
- [ ] **Conversational Search**: Type *"Will it rain tomorrow?"* or click prompt chips to get immediate AI answers.
- [ ] **Indian Language Support**: Try asking in Telugu (`ఈరోజు గుంటూరులో వాతావరణం ఎలా ఉంది?`) or Roman Telugu (`eroju guntur lo weather ela vundhi`).
- [ ] **Voice Controls**: Click **"🔊 Listen"** to hear the response read aloud and **"🔇 Stop"** to mute.
- [ ] **Health Endpoint**: `https://<your-app>.onrender.com/health` returns `{"status": "ok", "service": "WeatherGPT"}`.
- [ ] **API Documentation**: `https://<your-app>.onrender.com/docs` opens interactive Swagger UI.

---

## 💡 Notes for Render Free Tier

- **Spin-down after inactivity**: Render's free tier spins down the web service after 15 minutes of no traffic. When someone visits the site after it spins down, the first request may take ~30–50 seconds to boot up. Subsequent requests are instant.
- **In-Memory Caching**: WeatherGPT's built-in 5-minute caching prevents upstream Open-Meteo 429 rate limit issues in cloud environments.
