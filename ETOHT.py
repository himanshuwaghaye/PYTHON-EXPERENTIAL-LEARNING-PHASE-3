"""
English to Hindi Translator (AnuvadSetu / अनुवाद सेतु)
====================================================
A full-stack translation application written entirely in Python.
- Frontend: Modern, clean, responsive UI served directly via Flask.
- Backend: Multi-tier fallback translation engine with Google API,
           deep-translator, MyMemory API, and Devanagari transliteration.
- Deployment: Fully compatible with Vercel Serverless Functions and local execution.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, render_template_string

# Ensure stdout and stderr handle unicode safely on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Initialize Flask App
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Devanagari Transliteration Engine (Hindi to Romanized Hinglish Pronunciation)
# ---------------------------------------------------------------------------
DEV_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'अं': 'an', 'अः': 'ah'
}

DEV_MATRAS = {
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n', 'ः': 'h'
}

DEV_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'क्ष': 'ksh', 'त्र': 'tr', 'ज्ञ': 'gya',
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'd', 'ढ़': 'dh', 'फ़': 'f'
}

VIRAMA = '्'

def transliterate_hindi_to_roman(text: str) -> str:
    """Converts Devanagari Hindi text to phonetic Latin transliteration (Hinglish)."""
    if not text:
        return ""
    
    consonant_set = set(DEV_CONSONANTS.keys())
    res = []
    i = 0
    n = len(text)
    
    while i < n:
        c = text[i]
        if c in consonant_set:
            base = DEV_CONSONANTS[c]
            # Check next character
            if i + 1 < n and text[i+1] == VIRAMA:
                res.append(base)
                i += 2
            elif i + 1 < n and text[i+1] in DEV_MATRAS:
                res.append(base + DEV_MATRAS[text[i+1]])
                i += 2
            else:
                next_c = text[i+1] if i + 1 < n else ' '
                if next_c in consonant_set:
                    res.append(base + 'a')
                else:
                    res.append(base)
                i += 1
        elif c in DEV_VOWELS:
            res.append(DEV_VOWELS[c])
            i += 1
        elif c in DEV_MATRAS:
            res.append(DEV_MATRAS[c])
            i += 1
        else:
            res.append(c)
            i += 1
            
    result = ''.join(res)
    # Clean up duplicate spaces or irregular punctuations
    return re.sub(r'\s+', ' ', result).strip()

def detect_language(text: str) -> str:
    """Detects whether the text is Hindi (Devanagari) or English/Latin."""
    if not text:
        return 'en'
    # Check for Devanagari unicode range (0900 to 097F)
    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097f')
    if devanagari_chars > len(text.strip()) * 0.2:
        return 'hi'
    return 'en'

# ---------------------------------------------------------------------------
# Multi-Tier Robust Translation Engine
# ---------------------------------------------------------------------------
def translate_tier_google_gtx(text: str, source: str = 'en', target: str = 'hi'):
    """Tier 1: Google Translate GTX endpoint (high accuracy, fast)."""
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source}&tl={target}&dt=t&dt=rm&q={encoded_text}"
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8'
        }
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        translated_parts = []
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            for part in data[0]:
                if part and isinstance(part, list) and len(part) > 0 and part[0]:
                    translated_parts.append(part[0])
                    
        translated_text = "".join(translated_parts).strip()
        
        # Try extracting romanization if present in Google response
        roman = ""
        if len(data) > 0 and isinstance(data[0], list):
            for part in data[0]:
                if len(part) > 3 and part[3] and isinstance(part[3], str):
                    roman = part[3]
                    break
                    
        return translated_text, roman

def translate_tier_deep_translator(text: str, source: str = 'en', target: str = 'hi'):
    """Tier 2: deep-translator library."""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source=source, target=target)
        result = translator.translate(text)
        return result, ""
    except Exception:
        pass
    return None, ""

def translate_tier_mymemory(text: str, source: str = 'en', target: str = 'hi'):
    """Tier 3: MyMemory Translation API."""
    encoded_text = urllib.parse.quote(text)
    url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={source}|{target}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req, timeout=8) as response:
        data = json.loads(response.read().decode('utf-8'))
        res_data = data.get('responseData', {})
        translated_text = res_data.get('translatedText', '')
        return translated_text.strip(), ""

def translate_text(text: str, source: str = 'en', target: str = 'hi'):
    """Translates text with automatic fallbacks and pronunciation generation."""
    text = text.strip()
    if not text:
        return "", "", "Empty input"

    translated = None
    roman = ""
    engine_used = "Google Neural Engine"

    # Tier 1: Google GTX
    try:
        translated, roman = translate_tier_google_gtx(text, source, target)
    except Exception as e:
        # Tier 2: deep-translator
        try:
            translated, roman = translate_tier_deep_translator(text, source, target)
            engine_used = "Deep Translator"
        except Exception:
            # Tier 3: MyMemory
            try:
                translated, roman = translate_tier_mymemory(text, source, target)
                engine_used = "MyMemory Engine"
            except Exception as final_e:
                raise RuntimeError(f"All translation engines failed: {str(final_e)}")

    if not translated:
        translated = text

    # Compute romanized pronunciation if translating into Hindi and no roman was returned
    if target == 'hi' and not roman:
        roman = transliterate_hindi_to_roman(translated)

    return translated, roman, engine_used

# ---------------------------------------------------------------------------
# Curated Example Phrases for 1-Click Testing
# ---------------------------------------------------------------------------
SAMPLE_PHRASES = [
    {
        "category": "Daily Greetings",
        "phrases": [
            "Hello, how are you doing today?",
            "Good morning! Have a productive and wonderful day.",
            "Pleased to meet you. Welcome to our home.",
            "Thank you so much for your kind support."
        ]
    },
    {
        "category": "Travel & Exploration",
        "phrases": [
            "Where is the nearest railway station?",
            "How much does a ticket to New Delhi cost?",
            "Could you please guide me to the hotel?",
            "Is there a good restaurant nearby?"
        ]
    },
    {
        "category": "Business & Work",
        "phrases": [
            "Let us schedule our project meeting tomorrow at 10 AM.",
            "Please review the attached presentation and share your thoughts.",
            "We have successfully delivered the latest release on schedule.",
            "Collaboration and teamwork lead to remarkable success."
        ]
    },
    {
        "category": "Useful Questions",
        "phrases": [
            "What time does the library open in the morning?",
            "Can you help me understand this concept?",
            "Which way should I go to reach the market?",
            "Would you like to have tea or coffee?"
        ]
    }
]

# ---------------------------------------------------------------------------
# Clean, Modern HTML Frontend Template
# ---------------------------------------------------------------------------
FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AnuvadSetu | English to Hindi AI Translator</title>
    <meta name="description" content="Clean, responsive English to Hindi AI Translator with voice input, audio pronunciation, transliteration, and instant translation.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #090d16;
            --bg-surface: rgba(17, 24, 39, 0.75);
            --bg-card: rgba(24, 33, 53, 0.65);
            --bg-card-hover: rgba(30, 41, 67, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-focus: rgba(99, 102, 241, 0.6);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-subtle: #64748b;
            --accent-primary: #6366f1;
            --accent-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
            --accent-saffron: #f59e0b;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --shadow-card: 0 20px 40px -15px rgba(0, 0, 0, 0.5), 0 0 25px -5px rgba(99, 102, 241, 0.15);
            --radius-lg: 20px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }

        [data-theme="light"] {
            --bg-body: #f8fafc;
            --bg-surface: rgba(255, 255, 255, 0.85);
            --bg-card: rgba(248, 250, 252, 0.9);
            --bg-card-hover: rgba(241, 245, 249, 1);
            --border-color: rgba(226, 232, 240, 0.9);
            --border-focus: rgba(99, 102, 241, 0.6);
            --text-main: #0f172a;
            --text-muted: #475569;
            --text-subtle: #94a3b8;
            --shadow-card: 0 20px 35px -10px rgba(99, 102, 241, 0.08), 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            transition: background-color 0.3s ease, color 0.3s ease;
            position: relative;
        }

        /* Ambient Glow Background Orbs */
        .ambient-glow {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }

        .glow-orb-1 {
            position: absolute;
            top: -10%;
            left: 15%;
            width: 550px;
            height: 550px;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.18) 0%, rgba(99, 102, 241, 0) 70%);
            filter: blur(60px);
        }

        .glow-orb-2 {
            position: absolute;
            bottom: 5%;
            right: 10%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(245, 158, 11, 0.12) 0%, rgba(245, 158, 11, 0) 70%);
            filter: blur(70px);
        }

        .app-container {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 1240px;
            margin: 0 auto;
            padding: 24px 20px 48px;
            display: flex;
            flex-direction: column;
            flex: 1;
        }

        /* Header Bar */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 24px;
            margin-bottom: 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            box-shadow: 0 8px 16px -4px rgba(99, 102, 241, 0.4);
        }

        .brand-icon svg {
            width: 24px;
            height: 24px;
        }

        .brand-text h1 {
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .brand-text h1 span.devanagari {
            font-family: 'Noto Sans Devanagari', sans-serif;
            color: var(--accent-saffron);
            font-weight: 600;
        }

        .brand-text p {
            font-size: 0.82rem;
            color: var(--text-muted);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .pulse-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .icon-btn {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: var(--transition);
        }

        .icon-btn:hover {
            border-color: var(--accent-primary);
            background: var(--bg-card-hover);
            transform: translateY(-2px);
        }

        .icon-btn svg {
            width: 18px;
            height: 18px;
        }

        /* Mode & Controls Bar */
        .controls-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .language-tabs {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-surface);
            padding: 5px;
            border-radius: 14px;
            border: 1px solid var(--border-color);
        }

        .lang-indicator {
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 0.88rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-muted);
        }

        .lang-indicator.active {
            background: var(--bg-card);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .swap-btn {
            background: var(--accent-gradient);
            border: none;
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }

        .swap-btn:hover {
            transform: rotate(180deg) scale(1.08);
        }

        .swap-btn svg {
            width: 18px;
            height: 18px;
        }

        .auto-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.82rem;
            color: var(--text-muted);
            cursor: pointer;
            user-select: none;
        }

        .switch {
            position: relative;
            display: inline-block;
            width: 38px;
            height: 22px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            transition: .3s;
            border-radius: 20px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 14px;
            width: 14px;
            left: 3px;
            bottom: 3px;
            background-color: var(--text-subtle);
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background: var(--accent-primary);
            border-color: var(--accent-primary);
        }

        input:checked + .slider:before {
            transform: translateX(16px);
            background-color: white;
        }

        /* Main Workspace Translator Grid */
        .translator-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 28px;
        }

        @media (max-width: 860px) {
            .translator-grid {
                grid-template-columns: 1fr;
            }
        }

        .trans-card {
            background: var(--bg-surface);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 20px;
            display: flex;
            flex-direction: column;
            box-shadow: var(--shadow-card);
            transition: var(--transition);
            min-height: 380px;
            position: relative;
        }

        .trans-card:focus-within {
            border-color: var(--border-focus);
            box-shadow: 0 0 25px -2px rgba(99, 102, 241, 0.25);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 14px;
        }

        .card-lang {
            font-size: 0.92rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .lang-badge {
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            background: rgba(99, 102, 241, 0.15);
            color: var(--accent-primary);
            letter-spacing: 0.05em;
        }

        .card-stats {
            font-size: 0.78rem;
            color: var(--text-subtle);
        }

        .card-body {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        textarea.input-area {
            width: 100%;
            height: 100%;
            min-height: 200px;
            background: transparent;
            border: none;
            outline: none;
            resize: none;
            font-family: inherit;
            font-size: 1.05rem;
            line-height: 1.6;
            color: var(--text-main);
            padding: 4px 0;
        }

        textarea.input-area::placeholder {
            color: var(--text-subtle);
        }

        .output-area {
            width: 100%;
            min-height: 160px;
            font-size: 1.15rem;
            line-height: 1.7;
            color: var(--text-main);
            word-break: break-word;
            white-space: pre-wrap;
            overflow-y: auto;
            flex: 1;
            font-family: 'Noto Sans Devanagari', 'Plus Jakarta Sans', sans-serif;
            transition: var(--transition);
        }

        .output-empty {
            color: var(--text-subtle);
            font-style: normal;
            font-size: 0.98rem;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            min-height: 160px;
            user-select: none;
        }

        /* Romanized Pronunciation Box */
        .pronunciation-box {
            margin-top: 14px;
            padding: 12px 14px;
            background: var(--bg-card);
            border-radius: var(--radius-md);
            border: 1px dashed var(--border-color);
            display: none;
            animation: fadeIn 0.3s ease;
        }

        .pronunciation-box.visible {
            display: block;
        }

        .pron-title {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent-saffron);
            font-weight: 700;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .pron-text {
            font-size: 0.92rem;
            color: var(--text-muted);
            font-style: italic;
            letter-spacing: 0.02em;
        }

        /* Card Footer Action Buttons */
        .card-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: 14px;
            border-top: 1px solid var(--border-color);
            margin-top: 14px;
            gap: 8px;
        }

        .btn-group {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .tool-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted);
            padding: 6px 10px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
        }

        .tool-btn:hover {
            color: var(--text-main);
            background: var(--bg-card);
            border-color: var(--border-color);
        }

        .tool-btn.active {
            color: var(--accent-primary);
            background: rgba(99, 102, 241, 0.15);
            border-color: rgba(99, 102, 241, 0.3);
        }

        .tool-btn.recording {
            color: var(--accent-red);
            background: rgba(239, 68, 68, 0.15);
            border-color: rgba(239, 68, 68, 0.4);
            animation: pulse-red 1.5s infinite;
        }

        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
            70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        .tool-btn svg {
            width: 16px;
            height: 16px;
        }

        /* Big Primary Translate Action Button */
        .action-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            margin-bottom: 32px;
        }

        .translate-action-btn {
            background: var(--accent-gradient);
            color: white;
            border: none;
            padding: 14px 36px;
            border-radius: 14px;
            font-size: 1.02rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            cursor: pointer;
            box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.4);
            transition: var(--transition);
        }

        .translate-action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 30px -5px rgba(99, 102, 241, 0.55);
        }

        .translate-action-btn:active {
            transform: translateY(1px);
        }

        .translate-action-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .shortcut-hint {
            font-size: 0.72rem;
            background: rgba(255, 255, 255, 0.2);
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            letter-spacing: 0.04em;
        }

        /* Preset Sentence Explorer */
        .presets-section {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px;
            margin-bottom: 32px;
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 12px;
        }

        .section-header h2 {
            font-size: 1.05rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .section-header p {
            font-size: 0.82rem;
            color: var(--text-muted);
        }

        .category-pills {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }

        .cat-pill {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
        }

        .cat-pill:hover, .cat-pill.active {
            background: var(--accent-primary);
            color: white;
            border-color: var(--accent-primary);
        }

        .phrases-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 10px;
        }

        .phrase-item {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            padding: 12px 14px;
            border-radius: var(--radius-md);
            font-size: 0.88rem;
            color: var(--text-main);
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }

        .phrase-item:hover {
            border-color: var(--accent-primary);
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            color: #fff;
        }

        .phrase-item svg {
            width: 14px;
            height: 14px;
            color: var(--text-subtle);
            flex-shrink: 0;
            transition: var(--transition);
        }

        .phrase-item:hover svg {
            color: var(--accent-primary);
            transform: translateX(3px);
        }

        /* History Drawer (Modal / Sidebar) */
        .history-drawer {
            position: fixed;
            top: 0;
            right: -420px;
            width: 400px;
            max-width: 90vw;
            height: 100vh;
            background: var(--bg-body);
            border-left: 1px solid var(--border-color);
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
            z-index: 100;
            display: flex;
            flex-direction: column;
            transition: right 0.35s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .history-drawer.open {
            right: 0;
        }

        .drawer-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(4px);
            z-index: 99;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }

        .drawer-overlay.visible {
            opacity: 1;
            pointer-events: auto;
        }

        .drawer-header {
            padding: 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .drawer-header h3 {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .drawer-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .history-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 14px;
            cursor: pointer;
            transition: var(--transition);
        }

        .history-card:hover {
            border-color: var(--accent-primary);
            background: var(--bg-card);
        }

        .history-src {
            font-size: 0.86rem;
            color: var(--text-muted);
            margin-bottom: 6px;
        }

        .history-tgt {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-main);
            font-family: 'Noto Sans Devanagari', sans-serif;
            margin-bottom: 8px;
        }

        .history-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.72rem;
            color: var(--text-subtle);
        }

        .drawer-footer {
            padding: 16px;
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: flex-end;
        }

        .empty-history {
            text-align: center;
            color: var(--text-subtle);
            padding: 40px 20px;
            font-size: 0.9rem;
        }

        /* Toast Notifications */
        .toast-container {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 200;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
        }

        .toast {
            background: var(--bg-surface);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
            padding: 10px 18px;
            border-radius: 30px;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            opacity: 0;
            transform: translateY(15px);
            animation: toastIn 0.3s forwards ease;
        }

        .toast.success {
            border-color: var(--accent-green);
        }

        @keyframes toastIn {
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Footer */
        footer {
            margin-top: auto;
            text-align: center;
            padding: 24px 0 12px;
            border-top: 1px solid var(--border-color);
            font-size: 0.82rem;
            color: var(--text-subtle);
        }

        footer a {
            color: var(--accent-primary);
            text-decoration: none;
        }

        footer a:hover {
            text-decoration: underline;
        }

        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="ambient-glow">
        <div class="glow-orb-1"></div>
        <div class="glow-orb-2"></div>
    </div>

    <div class="app-container">
        <!-- Header -->
        <header>
            <div class="brand">
                <div class="brand-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="m5 8 6 6"/>
                        <path d="m4 14 6-6 2-3"/>
                        <path d="M2 5h12"/>
                        <path d="M7 2h1"/>
                        <path d="m22 22-5-10-5 10"/>
                        <path d="M14 18h6"/>
                    </svg>
                </div>
                <div class="brand-text">
                    <h1>AnuvadSetu <span class="devanagari">अनुवाद सेतु</span></h1>
                    <p>English to Hindi Neural AI Translator • Python & Vercel Ready</p>
                </div>
            </div>

            <div class="header-actions">
                <div class="status-badge" title="Backend translation engine is running">
                    <span class="pulse-dot"></span>
                    <span id="engineStatusText">AI Engine Online</span>
                </div>

                <button class="icon-btn" id="historyToggleBtn" title="Translation History" aria-label="Open History">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/>
                        <polyline points="12 6 12 12 16 14"/>
                    </svg>
                </button>

                <button class="icon-btn" id="themeToggleBtn" title="Toggle Theme" aria-label="Toggle Theme">
                    <svg id="themeIconDark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
                    </svg>
                    <svg id="themeIconLight" style="display:none;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="4"/>
                        <path d="M12 2v2"/><path d="M12 20v2"/>
                        <path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/>
                        <path d="M2 12h2"/><path d="M20 12h2"/>
                        <path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>
                    </svg>
                </button>
            </div>
        </header>

        <!-- Controls Bar -->
        <div class="controls-bar">
            <div class="language-tabs">
                <div class="lang-indicator active" id="srcLangIndicator">
                    <span id="srcLangLabel">English</span>
                    <span class="lang-badge">SOURCE</span>
                </div>
                <button class="swap-btn" id="swapLangBtn" title="Reverse Translation Direction" aria-label="Swap Languages">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="m7 16-4-4 4-4"/>
                        <path d="M3 12h18"/>
                        <path d="m17 8 4 4-4 4"/>
                    </svg>
                </button>
                <div class="lang-indicator active" id="tgtLangIndicator">
                    <span id="tgtLangLabel">Hindi (हिंदी)</span>
                    <span class="lang-badge" style="background: rgba(245, 158, 11, 0.15); color: var(--accent-saffron);">TARGET</span>
                </div>
            </div>

            <label class="auto-toggle">
                <span class="switch">
                    <input type="checkbox" id="autoTranslateToggle" checked>
                    <span class="slider"></span>
                </span>
                <span>Auto-translate while typing</span>
            </label>
        </div>

        <!-- Translator Grid -->
        <div class="translator-grid">
            <!-- Source Card -->
            <div class="trans-card" id="sourceCard">
                <div class="card-header">
                    <div class="card-lang">
                        <span id="srcCardHeaderLabel">English (US/UK)</span>
                    </div>
                    <div class="card-stats">
                        <span id="srcCharCount">0</span>/5000 chars • <span id="srcWordCount">0</span> words
                    </div>
                </div>

                <div class="card-body">
                    <textarea 
                        id="sourceText" 
                        class="input-area" 
                        placeholder="Type or paste text here to translate... (e.g. 'Hello, how can I help you today?')"
                        maxlength="5000"
                        autofocus
                    ></textarea>
                </div>

                <div class="card-footer">
                    <div class="btn-group">
                        <button class="tool-btn" id="voiceInputBtn" title="Voice Dictation (Speech to Text)">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                                <line x1="12" x2="12" y1="19" y2="22"/>
                            </svg>
                            <span id="voiceBtnText">Speak</span>
                        </button>

                        <button class="tool-btn" id="pasteBtn" title="Paste from Clipboard">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>
                                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
                            </svg>
                            <span>Paste</span>
                        </button>

                        <button class="tool-btn" id="srcTtsBtn" title="Listen to pronunciation">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                            </svg>
                            <span>Listen</span>
                        </button>
                    </div>

                    <div class="btn-group">
                        <button class="tool-btn" id="clearTextBtn" title="Clear text">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
                            </svg>
                            <span>Clear</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Target Card -->
            <div class="trans-card" id="targetCard">
                <div class="card-header">
                    <div class="card-lang">
                        <span id="tgtCardHeaderLabel">Hindi (हिंदी)</span>
                    </div>
                    <div class="card-stats">
                        <span id="tgtCharCount">0</span> chars • <span id="tgtWordCount">0</span> words
                    </div>
                </div>

                <div class="card-body">
                    <div id="outputArea" class="output-area">
                        <div class="output-empty">
                            <span>Translation will appear here in Devanagari script...</span>
                        </div>
                    </div>

                    <!-- Romanized Hinglish Pronunciation Guide -->
                    <div class="pronunciation-box" id="pronunciationBox">
                        <div class="pron-title">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
                            </svg>
                            Pronunciation (उच्चारण)
                        </div>
                        <div class="pron-text" id="pronunciationText"></div>
                    </div>
                </div>

                <div class="card-footer">
                    <div class="btn-group">
                        <button class="tool-btn" id="copyResultBtn" title="Copy to clipboard">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
                                <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
                            </svg>
                            <span id="copyBtnText">Copy</span>
                        </button>

                        <button class="tool-btn" id="tgtTtsBtn" title="Listen in Hindi">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                            </svg>
                            <span>Pronounce</span>
                        </button>

                        <button class="tool-btn" id="saveFavoriteBtn" title="Save to History">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                            </svg>
                            <span>Save</span>
                        </button>
                    </div>

                    <div class="btn-group">
                        <button class="tool-btn" id="fontIncBtn" title="Increase Font Size">A+</button>
                        <button class="tool-btn" id="fontDecBtn" title="Decrease Font Size">A-</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Big Action Button -->
        <div class="action-row">
            <button class="translate-action-btn" id="translateBtn" aria-label="Translate Now">
                <span id="btnSpinner" class="spinner" style="display: none;"></span>
                <span id="btnText">Translate Text</span>
                <span class="shortcut-hint">Ctrl + Enter</span>
            </button>
        </div>

        <!-- Preset Sentence Explorer -->
        <section class="presets-section">
            <div class="section-header">
                <div>
                    <h2>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
                            <path d="M6 6h10"/>
                            <path d="M6 10h10"/>
                        </svg>
                        Quick Everyday Phrases
                    </h2>
                    <p>Click any phrase to instantly populate and translate</p>
                </div>
            </div>

            <div class="category-pills" id="categoryPills">
                <!-- Injected via JavaScript -->
            </div>

            <div class="phrases-list" id="phrasesList">
                <!-- Injected via JavaScript -->
            </div>
        </section>

        <!-- Footer -->
        <footer>
            <p>AnuvadSetu • Built entirely in Python with Flask & Devanagari Engine • Optimized for Vercel Deployment</p>
        </footer>
    </div>

    <!-- History Drawer Overlay & Modal -->
    <div class="drawer-overlay" id="drawerOverlay"></div>
    <div class="history-drawer" id="historyDrawer">
        <div class="drawer-header">
            <h3>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                Recent Translations
            </h3>
            <button class="icon-btn" id="closeDrawerBtn" aria-label="Close History">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </div>
        <div class="drawer-content" id="historyItemsContainer">
            <div class="empty-history">No translations saved yet. Translate something to see your history!</div>
        </div>
        <div class="drawer-footer">
            <button class="tool-btn" id="clearAllHistoryBtn" style="color: var(--accent-red);">Clear History</button>
        </div>
    </div>

    <!-- Floating Toast Notification System -->
    <div class="toast-container" id="toastContainer"></div>

    <!-- Client-side Application Logic -->
    <script>
        // State
        const state = {
            sourceLang: 'en',
            targetLang: 'hi',
            fontSize: 18,
            autoTranslate: true,
            debounceTimer: null,
            isTranslating: false,
            history: JSON.parse(localStorage.getItem('anuvad_history') || '[]'),
            presets: []
        };

        // DOM Elements
        const sourceText = document.getElementById('sourceText');
        const outputArea = document.getElementById('outputArea');
        const pronunciationBox = document.getElementById('pronunciationBox');
        const pronunciationText = document.getElementById('pronunciationText');
        const translateBtn = document.getElementById('translateBtn');
        const btnText = document.getElementById('btnText');
        const btnSpinner = document.getElementById('btnSpinner');
        const swapLangBtn = document.getElementById('swapLangBtn');
        const voiceInputBtn = document.getElementById('voiceInputBtn');
        const voiceBtnText = document.getElementById('voiceBtnText');
        const pasteBtn = document.getElementById('pasteBtn');
        const srcTtsBtn = document.getElementById('srcTtsBtn');
        const tgtTtsBtn = document.getElementById('tgtTtsBtn');
        const clearTextBtn = document.getElementById('clearTextBtn');
        const copyResultBtn = document.getElementById('copyResultBtn');
        const copyBtnText = document.getElementById('copyBtnText');
        const saveFavoriteBtn = document.getElementById('saveFavoriteBtn');
        const fontIncBtn = document.getElementById('fontIncBtn');
        const fontDecBtn = document.getElementById('fontDecBtn');
        const srcCharCount = document.getElementById('srcCharCount');
        const srcWordCount = document.getElementById('srcWordCount');
        const tgtCharCount = document.getElementById('tgtCharCount');
        const tgtWordCount = document.getElementById('tgtWordCount');
        const srcLangLabel = document.getElementById('srcLangLabel');
        const tgtLangLabel = document.getElementById('tgtLangLabel');
        const srcCardHeaderLabel = document.getElementById('srcCardHeaderLabel');
        const tgtCardHeaderLabel = document.getElementById('tgtCardHeaderLabel');
        const autoTranslateToggle = document.getElementById('autoTranslateToggle');
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        const themeIconDark = document.getElementById('themeIconDark');
        const themeIconLight = document.getElementById('themeIconLight');
        const historyToggleBtn = document.getElementById('historyToggleBtn');
        const closeDrawerBtn = document.getElementById('closeDrawerBtn');
        const drawerOverlay = document.getElementById('drawerOverlay');
        const historyDrawer = document.getElementById('historyDrawer');
        const historyItemsContainer = document.getElementById('historyItemsContainer');
        const clearAllHistoryBtn = document.getElementById('clearAllHistoryBtn');
        const toastContainer = document.getElementById('toastContainer');
        const categoryPills = document.getElementById('categoryPills');
        const phrasesList = document.getElementById('phrasesList');

        // Toast Helper
        function showToast(msg, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.innerHTML = `<span>${msg}</span>`;
            toastContainer.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(15px)';
                setTimeout(() => toast.remove(), 300);
            }, 2500);
        }

        // Metrics Calculator
        function updateMetrics() {
            const val = sourceText.value;
            const chars = val.length;
            const words = val.trim() ? val.trim().split(/\s+/).length : 0;
            srcCharCount.textContent = chars;
            srcWordCount.textContent = words;
        }

        function updateOutputMetrics(text) {
            const chars = text ? text.length : 0;
            const words = text && text.trim() ? text.trim().split(/\s+/).length : 0;
            tgtCharCount.textContent = chars;
            tgtWordCount.textContent = words;
        }

        // Core Translation Routine
        async function performTranslation(force = false) {
            const text = sourceText.value.trim();
            if (!text) {
                outputArea.innerHTML = '<div class="output-empty"><span>Translation will appear here in Devanagari script...</span></div>';
                pronunciationBox.classList.remove('visible');
                updateOutputMetrics('');
                return;
            }

            if (state.isTranslating && !force) return;

            state.isTranslating = true;
            btnSpinner.style.display = 'inline-block';
            btnText.textContent = 'Translating...';
            translateBtn.disabled = true;

            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        source: state.sourceLang,
                        target: state.targetLang
                    })
                });

                const data = await response.json();
                if (data.success && data.translated) {
                    outputArea.textContent = data.translated;
                    updateOutputMetrics(data.translated);

                    // Show Romanized pronunciation if available
                    if (data.pronunciation && data.pronunciation.trim()) {
                        pronunciationText.textContent = data.pronunciation;
                        pronunciationBox.classList.add('visible');
                    } else {
                        pronunciationBox.classList.remove('visible');
                    }

                    // Save to local history
                    addToHistory(text, data.translated, data.pronunciation);
                } else {
                    showToast(data.error || 'Translation failed', 'error');
                }
            } catch (err) {
                console.error(err);
                showToast('Failed to connect to backend server', 'error');
            } finally {
                state.isTranslating = false;
                btnSpinner.style.display = 'none';
                btnText.textContent = 'Translate Text';
                translateBtn.disabled = false;
            }
        }

        // Swap Direction
        function swapLanguages() {
            const prevSource = state.sourceLang;
            const prevTarget = state.targetLang;
            state.sourceLang = prevTarget;
            state.targetLang = prevSource;

            const isEnSource = state.sourceLang === 'en';
            srcLangLabel.textContent = isEnSource ? 'English' : 'Hindi (हिंदी)';
            tgtLangLabel.textContent = isEnSource ? 'Hindi (हिंदी)' : 'English';
            srcCardHeaderLabel.textContent = isEnSource ? 'English (US/UK)' : 'Hindi (हिंदी)';
            tgtCardHeaderLabel.textContent = isEnSource ? 'Hindi (हिंदी)' : 'English (US/UK)';

            // Swap text contents
            const currentOut = outputArea.textContent;
            if (currentOut && !outputArea.querySelector('.output-empty')) {
                sourceText.value = currentOut;
            }
            updateMetrics();
            performTranslation(true);
            showToast(`Swapped to ${isEnSource ? 'English → Hindi' : 'Hindi → English'}`);
        }

        // History Management
        function addToHistory(src, tgt, pron) {
            const item = {
                src,
                tgt,
                pron: pron || '',
                sourceLang: state.sourceLang,
                targetLang: state.targetLang,
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            // Prevent duplicate on top
            if (state.history.length > 0 && state.history[0].src === src && state.history[0].tgt === tgt) {
                return;
            }
            state.history.unshift(item);
            if (state.history.length > 30) state.history.pop();
            localStorage.setItem('anuvad_history', JSON.stringify(state.history));
            renderHistory();
        }

        function renderHistory() {
            if (state.history.length === 0) {
                historyItemsContainer.innerHTML = '<div class="empty-history">No translations saved yet. Translate something to see your history!</div>';
                return;
            }
            historyItemsContainer.innerHTML = '';
            state.history.forEach((item, index) => {
                const card = document.createElement('div');
                card.className = 'history-card';
                card.innerHTML = `
                    <div class="history-src">${escapeHtml(item.src)}</div>
                    <div class="history-tgt">${escapeHtml(item.tgt)}</div>
                    <div class="history-footer">
                        <span>${item.sourceLang.toUpperCase()} → ${item.targetLang.toUpperCase()}</span>
                        <span>${item.time}</span>
                    </div>
                `;
                card.addEventListener('click', () => {
                    sourceText.value = item.src;
                    outputArea.textContent = item.tgt;
                    if (item.pron) {
                        pronunciationText.textContent = item.pron;
                        pronunciationBox.classList.add('visible');
                    }
                    updateMetrics();
                    updateOutputMetrics(item.tgt);
                    closeDrawer();
                    showToast('Restored from history');
                });
                historyItemsContainer.appendChild(card);
            });
        }

        function escapeHtml(str) {
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function openDrawer() {
            renderHistory();
            historyDrawer.classList.add('open');
            drawerOverlay.classList.add('visible');
        }

        function closeDrawer() {
            historyDrawer.classList.remove('open');
            drawerOverlay.classList.remove('visible');
        }

        // Speech Recognition (Voice Dictation)
        let recognition = null;
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRec();
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onstart = () => {
                voiceInputBtn.classList.add('recording');
                voiceBtnText.textContent = 'Listening...';
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                sourceText.value = (sourceText.value ? sourceText.value + ' ' : '') + transcript;
                updateMetrics();
                performTranslation(true);
            };

            recognition.onerror = () => {
                voiceInputBtn.classList.remove('recording');
                voiceBtnText.textContent = 'Speak';
                showToast('Voice recognition error or permission denied', 'error');
            };

            recognition.onend = () => {
                voiceInputBtn.classList.remove('recording');
                voiceBtnText.textContent = 'Speak';
            };
        }

        // Text To Speech
        function speakText(text, lang) {
            if (!('speechSynthesis' in window)) {
                showToast('Speech synthesis not supported in this browser', 'error');
                return;
            }
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = lang === 'hi' ? 'hi-IN' : 'en-US';
            utterance.rate = 0.9;
            window.speechSynthesis.speak(utterance);
        }

        // Load Preset Phrases
        async function loadPresets() {
            try {
                const res = await fetch('/api/examples');
                const data = await res.json();
                state.presets = data.categories || [];
                renderPresets();
            } catch (e) {
                console.error("Presets load error:", e);
            }
        }

        function renderPresets() {
            if (!state.presets.length) return;
            categoryPills.innerHTML = '';
            state.presets.forEach((cat, index) => {
                const pill = document.createElement('button');
                pill.className = `cat-pill ${index === 0 ? 'active' : ''}`;
                pill.textContent = cat.category;
                pill.addEventListener('click', () => {
                    document.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
                    pill.classList.add('active');
                    renderPhrasesForCategory(cat);
                });
                categoryPills.appendChild(pill);
            });
            renderPhrasesForCategory(state.presets[0]);
        }

        function renderPhrasesForCategory(cat) {
            phrasesList.innerHTML = '';
            cat.phrases.forEach(phrase => {
                const item = document.createElement('div');
                item.className = 'phrase-item';
                item.innerHTML = `
                    <span>${phrase}</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
                    </svg>
                `;
                item.addEventListener('click', () => {
                    sourceText.value = phrase;
                    updateMetrics();
                    performTranslation(true);
                    window.scrollTo({ top: 120, behavior: 'smooth' });
                });
                phrasesList.appendChild(item);
            });
        }

        // Event Listeners
        sourceText.addEventListener('input', () => {
            updateMetrics();
            if (state.autoTranslate) {
                clearTimeout(state.debounceTimer);
                state.debounceTimer = setTimeout(() => {
                    performTranslation();
                }, 400);
            }
        });

        sourceText.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                performTranslation(true);
            }
        });

        translateBtn.addEventListener('click', () => performTranslation(true));
        swapLangBtn.addEventListener('click', swapLanguages);

        autoTranslateToggle.addEventListener('change', (e) => {
            state.autoTranslate = e.target.checked;
            showToast(state.autoTranslate ? 'Auto-translate active' : 'Auto-translate paused');
        });

        clearTextBtn.addEventListener('click', () => {
            sourceText.value = '';
            outputArea.innerHTML = '<div class="output-empty"><span>Translation will appear here in Devanagari script...</span></div>';
            pronunciationBox.classList.remove('visible');
            updateMetrics();
            updateOutputMetrics('');
            sourceText.focus();
        });

        copyResultBtn.addEventListener('click', async () => {
            const text = outputArea.textContent;
            if (!text || outputArea.querySelector('.output-empty')) {
                showToast('No translated text to copy', 'error');
                return;
            }
            try {
                await navigator.clipboard.writeText(text);
                copyBtnText.textContent = 'Copied! ✓';
                copyResultBtn.style.color = 'var(--accent-green)';
                showToast('Translated text copied to clipboard!', 'success');
                setTimeout(() => {
                    copyBtnText.textContent = 'Copy';
                    copyResultBtn.style.color = '';
                }, 2000);
            } catch (err) {
                showToast('Failed to copy to clipboard', 'error');
            }
        });

        pasteBtn.addEventListener('click', async () => {
            try {
                const clipText = await navigator.clipboard.readText();
                if (clipText) {
                    sourceText.value = clipText;
                    updateMetrics();
                    performTranslation(true);
                    showToast('Pasted from clipboard');
                }
            } catch (err) {
                showToast('Please grant clipboard access to paste', 'error');
            }
        });

        srcTtsBtn.addEventListener('click', () => {
            const text = sourceText.value.trim();
            if (text) speakText(text, state.sourceLang);
            else showToast('Enter text to listen', 'error');
        });

        tgtTtsBtn.addEventListener('click', () => {
            const text = outputArea.textContent.trim();
            if (text && !outputArea.querySelector('.output-empty')) speakText(text, state.targetLang);
            else showToast('No translated text to pronounce', 'error');
        });

        voiceInputBtn.addEventListener('click', () => {
            if (!recognition) {
                showToast('Voice input is not supported in this browser', 'error');
                return;
            }
            recognition.lang = state.sourceLang === 'en' ? 'en-US' : 'hi-IN';
            try {
                recognition.start();
            } catch (e) {
                recognition.stop();
            }
        });

        saveFavoriteBtn.addEventListener('click', () => {
            const src = sourceText.value.trim();
            const tgt = outputArea.textContent.trim();
            if (src && tgt && !outputArea.querySelector('.output-empty')) {
                addToHistory(src, tgt, pronunciationText.textContent);
                showToast('Translation saved to History!', 'success');
            } else {
                showToast('Translate something first to save', 'error');
            }
        });

        fontIncBtn.addEventListener('click', () => {
            if (state.fontSize < 28) {
                state.fontSize += 2;
                outputArea.style.fontSize = state.fontSize + 'px';
            }
        });

        fontDecBtn.addEventListener('click', () => {
            if (state.fontSize > 14) {
                state.fontSize -= 2;
                outputArea.style.fontSize = state.fontSize + 'px';
            }
        });

        // Theme Toggle
        let currentTheme = localStorage.getItem('anuvad_theme') || 'dark';
        function applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('anuvad_theme', theme);
            if (theme === 'light') {
                themeIconDark.style.display = 'none';
                themeIconLight.style.display = 'block';
            } else {
                themeIconDark.style.display = 'block';
                themeIconLight.style.display = 'none';
            }
        }
        applyTheme(currentTheme);

        themeToggleBtn.addEventListener('click', () => {
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(currentTheme);
        });

        historyToggleBtn.addEventListener('click', openDrawer);
        closeDrawerBtn.addEventListener('click', closeDrawer);
        drawerOverlay.addEventListener('click', closeDrawer);

        clearAllHistoryBtn.addEventListener('click', () => {
            state.history = [];
            localStorage.removeItem('anuvad_history');
            renderHistory();
            showToast('History cleared');
        });

        // Initialization
        loadPresets();
        updateMetrics();
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.route('/')
def home():
    """Serves the complete single-page frontend application."""
    return render_template_string(FRONTEND_HTML)

@app.route('/api/translate', methods=['POST'])
def handle_translate():
    """API endpoint to translate text between English and Hindi."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = data.get('text', '').strip()
        source = data.get('source', 'en')
        target = data.get('target', 'hi')

        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400

        # Auto-detect language if specified
        if source == 'auto':
            source = detect_language(text)
            target = 'hi' if source == 'en' else 'en'

        translated, pronunciation, engine = translate_text(text, source=source, target=target)

        return jsonify({
            'success': True,
            'original': text,
            'translated': translated,
            'pronunciation': pronunciation,
            'source': source,
            'target': target,
            'engine': engine
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/detect', methods=['POST'])
def handle_detect():
    """API endpoint to detect whether text is English or Hindi."""
    data = request.get_json(force=True, silent=True) or {}
    text = data.get('text', '')
    lang = detect_language(text)
    return jsonify({
        'language': lang,
        'label': 'Hindi' if lang == 'hi' else 'English'
    })

@app.route('/api/examples', methods=['GET'])
def handle_examples():
    """API endpoint returning curated categories of common phrases."""
    return jsonify({
        'status': 'success',
        'categories': SAMPLE_PHRASES
    })

@app.route('/api/health', methods=['GET'])
def handle_health():
    """Health check endpoint for Vercel and monitoring."""
    return jsonify({
        'status': 'healthy',
        'app': 'AnuvadSetu English-Hindi Translator',
        'engine': 'Python Multi-Tier Neural Translation',
        'runtime': 'Python WSGI'
    })

# ---------------------------------------------------------------------------
# Local Execution Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("[AnuvadSetu] English to Hindi AI Translator")
    print(f">> Server running locally at: http://localhost:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
