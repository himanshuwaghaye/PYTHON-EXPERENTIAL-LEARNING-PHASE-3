# AnuvadSetu (अनुवाद सेतु) - English to Hindi AI Translator

A full-stack, clean English-to-Hindi neural translation web application built **entirely in Python** with Flask, featuring modern glassmorphism UI aesthetics, Devanagari romanization, voice dictation, speech synthesis, and ready for **1-click Vercel deployment**.

---

## ✨ Features

- **Built Entirely in Python**: Both the backend API routes and the clean frontend interface are served and orchestrated via Python (`ETOHT.py`).
- **Multi-Tier Neural Translation Engine**:
  - **Tier 1**: Google Neural Translation Engine (zero API key required, high speed and accuracy).
  - **Tier 2**: Deep Translator fallback.
  - **Tier 3**: MyMemory translation fallback.
- **Phonetic Pronunciation Guide (उच्चारण)**: Automatic Devanagari transliteration into Latin/Hinglish (e.g. *“shubh prabhaat”*) so English speakers can pronounce Hindi words accurately.
- **Clean, Modern UI (Glassmorphism & Aesthetics)**:
  - Responsive split cards (English input on the left/top, Hindi output on the right/bottom).
  - Light and Dark mode toggle with persistent preferences.
  - Character and word count metrics in real-time.
  - Voice dictation (Speech-to-Text).
  - Audio pronunciation (Hindi and English Text-to-Speech).
  - 1-Click Copy with animated toast notification.
  - Adjustable Devanagari typography sizing (A+ / A-).
  - Everyday phrase library across multiple categories (Greetings, Travel, Business, Questions).
  - Translation history drawer with local storage persistence and 1-click restore.
  - Direction swap (English ⇄ Hindi) with smooth 360° animation.
  - Auto-translate as you type (with debouncing) or manual button click (`Ctrl + Enter`).
- **Vercel Deployable**: Pre-configured with `vercel.json`, `api/index.py`, and `requirements.txt`.

---

## 🚀 Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
```bash
python ETOHT.py
```

Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🌐 Deploying to Vercel

### Method A: Deploy via Vercel CLI (Fastest)

1. Open PowerShell or Terminal in the project root:
   ```bash
   npx vercel
   ```
2. Follow the interactive prompts (Accept defaults).
3. Deploy to production:
   ```bash
   npx vercel --prod
   ```

### Method B: Deploy via GitHub & Vercel Dashboard

1. Push this directory to your GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of English to Hindi Translator"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```
2. Go to [vercel.com](https://vercel.com/) and click **"Add New..." -> "Project"**.
3. Import your GitHub repository.
4. Keep the default settings and click **Deploy**.
5. Vercel will automatically detect Python, install `requirements.txt`, and deploy the serverless function!

---

## 📂 Project Architecture

```
├── ETOHT.py             # Main application: translation engine + Flask routes + clean UI
├── api/
│   └── index.py         # Vercel Serverless Function entry point
├── vercel.json          # Vercel routing and runtime configuration
├── requirements.txt     # Python dependencies (Flask, requests, deep-translator)
├── .gitignore           # Python and Vercel git ignore rules
└── README.md            # Documentation and deployment instructions
```

---

## 📡 API Endpoints

- `GET /` — Serves the responsive, modern web UI.
- `POST /api/translate` — Translates text:
  ```json
  {
    "text": "Good morning, have a wonderful day!",
    "source": "en",
    "target": "hi"
  }
  ```
  Returns:
  ```json
  {
    "success": true,
    "original": "Good morning, have a wonderful day!",
    "translated": "शुभ प्रभात आपका दिन शुभ रहे!",
    "pronunciation": "shubh prabhaat aapakaa din shubh rahe!",
    "source": "en",
    "target": "hi",
    "engine": "Google Neural Engine"
  }
  ```
- `POST /api/detect` — Detects language (`en` or `hi`).
- `GET /api/examples` — Returns curated phrases for instant testing.
- `GET /api/health` — Returns server health status.
