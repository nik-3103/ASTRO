# AstroSight — Working Vedic Chart Prototype

This version includes a real Python backend using **Swiss Ephemeris (pyswisseph)**. The frontend sends birth details to the API and receives calculated sidereal planetary positions.

## What works now

- Birth date + local birth time input
- Built-in city coordinates/timezones for common cities (including Mumbai, Delhi, Bengaluru, Chennai, Kolkata, Hyderabad and Pune)
- Optional exact latitude, longitude and IANA timezone fields
- UTC conversion and Julian Day calculation
- Sidereal zodiac with **Lahiri ayanamsa**
- **Whole Sign** Vedic houses
- Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn
- Mean Rahu and Ketu
- Ascendant (Lagna) and MC
- Planetary sign, degree, house, nakshatra and pada
- Retrograde status
- Basic traditional dignity labels (own sign, exalted, debilitated)
- Basic traditional screening/summary insights
- Interactive chart preview and planetary table
- Existing palm-image upload UI remains available

## Run on Windows

### 1. Open a terminal in this folder

```text
AstroSight_UI
```

### 2. Install the Python packages

```bash
python -m pip install -r requirements.txt
```

If `python` does not work, try:

```bash
py -m pip install -r requirements.txt
```

### 3. Start the backend

Windows:

```text
run_backend.bat
```

or:

```bash
python -m uvicorn backend:app --reload --host 127.0.0.1 --port 8000
```

You should see the API running at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

### 4. Start the frontend

Use VS Code Live Server on `index.html`.

Do **not** close the backend terminal while using Generate My Chart.

### 5. Test

Try:

```text
Name: Test User
Date: 2003-08-15
Time: 10:30
Place: Mumbai
```

Click **Generate My Chart**.

## Accuracy notes

The astronomical positions are calculated by Swiss Ephemeris rather than by the LLM or JavaScript. The application uses sidereal calculations with Lahiri ayanamsa. Swiss Ephemeris documents `calc_ut()` for UT-based planetary calculations and `houses_ex()` for house calculations; its house documentation includes the Whole Sign (`W`) method and sidereal flags.

For a production-quality birthplace workflow, replace the built-in city list with a proper geocoder plus timezone database, and allow the user to verify the exact coordinates/timezone before calculating. Exact birth time and location matter for the Ascendant and house placements.

The astrological interpretation text is a traditional-rule layer, not scientific validation or a prediction guarantee. BPHS/RAG should be added as a separate source-backed interpretation layer after the deterministic chart calculation.

## Architecture

```text
Browser UI
   ↓ POST /api/chart
FastAPI backend
   ↓
Local birth time + timezone
   ↓
UTC → Julian Day
   ↓
Swiss Ephemeris
   ↓
Sidereal Lahiri planetary positions
   ↓
Whole Sign houses + Vedic features
   ↓
JSON response
   ↓
Chart UI + planetary table + insights

Next:
JSON chart → BPHS RAG → LLM explanation
```
