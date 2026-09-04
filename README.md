# 🥗 Smart Pantry & Sourcing Engine

A full-stack, location-aware pantry management and recipe sourcing application built with **FastAPI** and **React (Vite)**. It identifies missing ingredients across recipes, routes users to nearby stores using zero-cost navigation intents, and offers global dynamic currency conversion.

---

## ✨ Features

- **Location-Aware Sourcing:** Calculates distance to nearby grocery stores using custom Haversine geographic formulas with default fallback coordinates (`40.1872, 44.5152`).
- **Zero-Cost Navigation:** Directs users to stores via free Google Maps directions intent links without requiring paid SDKs or API keys.
- **Global Currency Switching:** Toggle seamlessly between local regional currencies (e.g., **AMD ֏**, **EUR €**) and **USD $** across all recipe costs, budget summaries, and sourcing lists.
- **Secure Authentication:** JWT-based user authentication and protected API endpoints.
- **Resilient Fallbacks:** Guarantees non-null store options and fallback pricing logic even when specific user coordinates or store datasets are missing.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3.10+, SQLite, SQLAlchemy, Pytest, Uvicorn
- **Frontend:** React 18, Vite, Tailwind CSS
- **Deployment:** Render (Backend API), Vercel (Frontend Client)

---

## 🚀 Setup & Local Development

### Prerequisites

- [Python 3.10+](https://www.python.org/)
- [Node.js 18+](https://nodejs.org/) & `npm`

---

### Complete Installation Walkthrough

# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# 2. Setup & start Backend (Terminal 1)
cd backend
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
echo "SECRET_KEY=dev_secret_key" > .env
uvicorn app.main:app --reload   # Server starts at http://localhost:8000

# 3. Setup & start Frontend (Terminal 2)
cd ../frontend
npm install
npm run dev                     # App starts at http://localhost:5173

# 3. Setup & start Frontend (Terminal 2)
cd ../frontend
npm install
npm run dev                     # App starts at http://localhost:5173
