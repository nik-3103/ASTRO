from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional
import math

import swisseph as swe
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="AstroSight API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Common locations for a reliable one-day/demo setup. Coordinates are city-center
# coordinates; for production, replace these with exact birthplace geocoding.
LOCATIONS = {
    "mumbai": (19.0760, 72.8777, "Asia/Kolkata"),
    "delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "new delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "bengaluru": (12.9716, 77.5946, "Asia/Kolkata"),
    "bangalore": (12.9716, 77.5946, "Asia/Kolkata"),
    "chennai": (13.0827, 80.2707, "Asia/Kolkata"),
    "kolkata": (22.5726, 88.3639, "Asia/Kolkata"),
    "hyderabad": (17.3850, 78.4867, "Asia/Kolkata"),
    "pune": (18.5204, 73.8567, "Asia/Kolkata"),
    "ahmedabad": (23.0225, 72.5714, "Asia/Kolkata"),
    "jaipur": (26.9124, 75.7873, "Asia/Kolkata"),
    "lucknow": (26.8467, 80.9462, "Asia/Kolkata"),
    "new york": (40.7128, -74.0060, "America/New_York"),
    "london": (51.5074, -0.1278, "Europe/London"),
    "dubai": (25.2048, 55.2708, "Asia/Dubai"),
    "singapore": (1.3521, 103.8198, "Asia/Singapore"),
}

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
SIGN_SANSKRIT = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}

# Classical sign dignities used for a compact traditional summary.
OWN = {
    "Sun": {"Leo"}, "Moon": {"Cancer"}, "Mars": {"Aries", "Scorpio"},
    "Mercury": {"Gemini", "Virgo"}, "Jupiter": {"Sagittarius", "Pisces"},
    "Venus": {"Taurus", "Libra"}, "Saturn": {"Capricorn", "Aquarius"},
}
EXALT = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
    "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra"
}
DEBIL = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
    "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries"
}

class BirthRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    gender: Optional[str] = None
    dob: str
    time: str
    place: str = Field(min_length=1, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone_name: Optional[str] = None
    ayanamsa: str = "Lahiri"
    node_type: str = "mean"


def norm360(x: float) -> float:
    return x % 360.0


def sign_index(longitude: float) -> int:
    return int(norm360(longitude) // 30)


def degree_in_sign(longitude: float) -> float:
    return norm360(longitude) % 30.0


def format_degree(deg: float) -> str:
    d = int(deg)
    minutes = int(round((deg - d) * 60))
    if minutes == 60:
        d += 1
        minutes = 0
    return f"{d:02d}° {minutes:02d}′"


def nakshatra_info(longitude: float) -> dict:
    # 27 nakshatras × 13°20′; each has 4 padas.
    x = norm360(longitude)
    span = 360.0 / 27.0
    idx = int(x // span)
    within = x - idx * span
    pada = int(within // (span / 4.0)) + 1
    return {
        "name": NAKSHATRAS[idx],
        "index": idx + 1,
        "pada": min(4, pada),
        "degree": round(within, 4),
    }


def dignity(planet: str, sign: str) -> str:
    if planet in EXALT and sign == EXALT[planet]:
        return "Exalted"
    if planet in DEBIL and sign == DEBIL[planet]:
        return "Debilitated"
    if planet in OWN and sign in OWN[planet]:
        return "Own sign"
    return "Neutral"


def resolve_location(place: str, lat: Optional[float], lon: Optional[float], tz_name: Optional[str]):
    if lat is not None and lon is not None and tz_name:
        try:
            ZoneInfo(tz_name)
        except Exception as e:
            raise HTTPException(400, f"Invalid timezone: {tz_name}") from e
        return lat, lon, tz_name, "User-supplied coordinates/timezone"

    key = place.strip().lower()
    if key in LOCATIONS:
        la, lo, tz = LOCATIONS[key]
        return la, lo, tz, "AstroSight city database"

    # Helpful fallback: a few common formats such as "Mumbai, India".
    for city, values in LOCATIONS.items():
        if city in key:
            return values[0], values[1], values[2], "AstroSight city database (matched city name)"

    raise HTTPException(
        400,
        "Place not in the built-in city database. For an exact birthplace, enter latitude, longitude and IANA timezone in Advanced Location settings."
    )


def parse_local_datetime(dob: str, t: str, tz_name: str):
    dob = str(dob).strip()
    t = str(t).strip()

    parsed_date = None

    # Accept YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed_date = datetime.strptime(dob, fmt).date()
            break
        except ValueError:
            continue

    if parsed_date is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid birth date: '{dob}'. Use DD-MM-YYYY or YYYY-MM-DD."
        )

    # Accept HH:MM
    try:
        parsed_time = datetime.strptime(t, "%H:%M").time()
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid birth time: '{t}'. Use HH:MM."
        ) from e

    try:
        local = datetime.combine(parsed_date, parsed_time)
        return local.replace(tzinfo=ZoneInfo(tz_name))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not create local birth datetime: {e}"
        ) from e

def planet_record(name: str, lon: float, lat: float, speed: float, house: int):
    si = sign_index(lon)
    sign = SIGNS[si]
    nak = nakshatra_info(lon)
    return {
        "planet": name,
        "longitude": round(norm360(lon), 6),
        "latitude": round(lat, 6),
        "degree": format_degree(degree_in_sign(lon)),
        "sign": sign,
        "sign_sanskrit": SIGN_SANSKRIT[si],
        "nakshatra": nak["name"],
        "nakshatra_pada": nak["pada"],
        "house": house,
        "retrograde": speed < 0 if name not in ("Sun", "Moon") else False,
        "speed": round(speed, 6),
        "dignity": dignity(name, sign),
    }


def house_from_longitude(planet_lon: float, asc_lon: float) -> int:
    # Whole-sign Vedic houses: ascendant sign is house 1.
    asc_sign = sign_index(asc_lon)
    p_sign = sign_index(planet_lon)
    return ((p_sign - asc_sign) % 12) + 1


def graha_aspects(planet: str, house: int):
    # Traditional Parashari graha drishti, expressed as target houses.
    offsets = [7]
    if planet == "Mars": offsets += [4, 8]
    if planet == "Jupiter": offsets += [5, 9]
    if planet == "Saturn": offsets += [3, 10]
    return [((house - 1 + off - 1) % 12) + 1 for off in offsets]


def build_insights(planets, asc_sign: str):
    by_name = {p["planet"]: p for p in planets}
    insights = []
    moon = by_name.get("Moon")
    sun = by_name.get("Sun")
    mars = by_name.get("Mars")
    jupiter = by_name.get("Jupiter")
    saturn = by_name.get("Saturn")

    if moon:
        insights.append(f"Moon is in {moon['sign']} ({moon['nakshatra']} nakshatra, pada {moon['nakshatra_pada']}).")
    if sun:
        insights.append(f"Sun is in {sun['sign']} in the {sun['house']}th house.")
    if mars and mars["house"] in {1, 4, 7, 8, 12}:
        insights.append("Traditional Manglik/Kuja Dosha screening flag: Mars occupies house " + str(mars["house"]) + ". This is a classical rule indicator, not a standalone conclusion.")
    if jupiter and jupiter["dignity"] in {"Exalted", "Own sign"}:
        insights.append(f"Jupiter has a traditional strength indicator: {jupiter['dignity']} in {jupiter['sign']}.")
    if saturn and saturn["retrograde"]:
        insights.append("Saturn is retrograde in the computed chart.")
    retro = [p["planet"] for p in planets if p["retrograde"]]
    if retro:
        insights.append("Retrograde planets: " + ", ".join(retro) + ".")
    insights.append(f"Lagna (Ascendant) is {asc_sign}; houses are presented using the Whole Sign Vedic house method.")
    return insights


@app.get("/api/health")
def health():
    return {"ok": True, "engine": "Swiss Ephemeris", "zodiac": "Sidereal", "ayanamsa": "Lahiri"}


@app.post("/api/chart")
def calculate_chart(req: BirthRequest):
    lat, lon, tz_name, location_source = resolve_location(req.place, req.latitude, req.longitude, req.timezone_name)
    local_dt = parse_local_datetime(req.dob, req.time, tz_name)
    utc_dt = local_dt.astimezone(timezone.utc)

    # UTC -> Julian Day, then Swiss Ephemeris calculations.
    jd_ut = swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    )

    if req.ayanamsa.lower() != "lahiri":
        raise HTTPException(400, "This prototype currently supports Lahiri ayanamsa only.")
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    # Sidereal Whole Sign houses. Swiss Ephemeris documents W as Whole Sign.
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b"W", flags)
    asc_lon = norm360(ascmc[0])
    mc_lon = norm360(ascmc[1])
    asc_si = sign_index(asc_lon)

    bodies = []
    planet_map = dict(PLANETS)
    planet_map["Rahu"] = swe.TRUE_NODE if req.node_type == "true" else swe.MEAN_NODE
    for name, body_id in planet_map.items():
        xx, retflags = swe.calc_ut(jd_ut, body_id, flags)
        bodies.append(planet_record(name, xx[0], xx[1], xx[3], house_from_longitude(xx[0], asc_lon)))

    # Ketu is exactly opposite the selected Rahu node.
    rahu = next(p for p in bodies if p["planet"] == "Rahu")
    ketu_lon = norm360(rahu["longitude"] + 180)
    ketu = planet_record("Ketu", ketu_lon, 0.0, rahu["speed"], house_from_longitude(ketu_lon, asc_lon))
    ketu["retrograde"] = True
    bodies.append(ketu)

    # Sort in a stable Vedic-friendly order.
    order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    bodies.sort(key=lambda x: order.index(x["planet"]))

    houses = []
    for h in range(1, 13):
        sign_i = (asc_si + h - 1) % 12
        houses.append({
            "house": h,
            "sign": SIGNS[sign_i],
            "sign_sanskrit": SIGN_SANSKRIT[sign_i],
            "start_degree": round(sign_i * 30.0, 6),
        })

    planets_by_house = {str(h): [] for h in range(1, 13)}
    for p in bodies:
        planets_by_house[str(p["house"])].append(p["planet"])

    return {
        "engine": {
            "name": "Swiss Ephemeris",
            "zodiac": "Sidereal",
            "ayanamsa": "Lahiri",
            "house_system": "Whole Sign",
            "node": "Mean Node" if req.node_type == "mean" else "True Node",
        },
        "birth": {
            "name": req.name,
            "gender": req.gender,
            "local_datetime": local_dt.isoformat(),
            "utc_datetime": utc_dt.isoformat(),
            "julian_day_ut": round(jd_ut, 8),
            "place": req.place,
            "latitude": lat,
            "longitude": lon,
            "timezone": tz_name,
            "location_source": location_source,
        },
        "angles": {
            "ascendant": {
                "longitude": round(asc_lon, 6),
                "sign": SIGNS[asc_si],
                "sign_sanskrit": SIGN_SANSKRIT[asc_si],
                "degree": format_degree(degree_in_sign(asc_lon)),
                "nakshatra": nakshatra_info(asc_lon),
            },
            "mc": {
                "longitude": round(mc_lon, 6),
                "sign": SIGNS[sign_index(mc_lon)],
                "degree": format_degree(degree_in_sign(mc_lon)),
            },
        },
        "planets": bodies,
        "houses": houses,
        "planets_by_house": planets_by_house,
        "insights": build_insights(bodies, SIGNS[asc_si]),
        "disclaimer": "Planetary positions are astronomical calculations. The interpretive labels and traditional indicators are astrological conventions and should not be treated as scientific predictions.",
    }
