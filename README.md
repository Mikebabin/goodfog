# inversion-watch

**Marin Inversion Checker** — a single-page web app that tells you whether a
Bay Area fog *inversion* is worth photographing from a given viewpoint, and
whether you'll be standing **above** the marine layer or lost **inside** it.

When the summer marine layer sits low in the valleys and you're above it, you
get that classic "sea of clouds" shot. When the fog base is above your
elevation, you're just socked in. This app estimates where the fog base sits
and compares it to each viewpoint so you know before you set the 4:30am alarm.

## How it works

1. **Forecast** — pulls hourly cloud cover, wind, temperature, dewpoint, and
   sunrise/sunset from the free [Open-Meteo](https://open-meteo.com) API. No API
   key, no account.
2. **Fog base (LCL)** — computes the lifted condensation level (the approximate
   fog-base height) from temperature and dewpoint using the Espy/Bolton
   approximation (~125 m of lift per °C of temp–dewpoint spread).
3. **Per-location thresholds** — every viewpoint has a calibrated "sweet spot"
   range for the fog base. The app reports whether you'd be **above the layer**,
   **right at the edge**, or **inside the fog / socked in**.
4. **Likelihood score** — combines low-cloud coverage, wind, clear sky above the
   inversion, and rain into an inversion-likelihood %. The fog-base position
   *gates* the score: no marine layer (or being stuck inside it) can't produce a
   high likelihood no matter how calm and clear it is.

The numbers are a **heuristic guide, not a precise measurement** — always
confirm against the live cameras and Windy before committing to a drive.

## Viewpoints

| Spot | Elevation | Notes |
|------|-----------|-------|
| Point Bonita Lighthouse | 100 ft | Coastal; only works with a very low fog base |
| Twin Peaks (from Arguello & Jackson) | 370 ft vantage | Shoot *toward* the 922 ft peaks emerging above the fog |
| Conzelman Pullouts | ~600 ft | Flexible stops when the fog base is low |
| Battery Spencer | 790 ft | Golden Gate Bridge framed in fog |
| Hawk Hill | 922 ft | Classic Marin valley inversion |
| Trojan Point | ~1,750 ft | Mid-mountain sea of clouds (summit gate opens 7am) |
| West Peak | 2,560 ft | Faces the coast (gate opens 7am) |
| East Peak | 2,571 ft | Highest vantage — above nearly all layers (gate opens 7am) |

## Viewing windows

Four tabs: **Tonight** (sunset), **Tom. AM** (sunrise), **Tom. PM** (sunset),
and **Plan** — which compares all three windows to find the best one for the
selected viewpoint.

## Running it

It's a single static `index.html` with no build step and no dependencies.

- **Locally:** open `index.html` in a browser.
- **Deploy:** serve the file from any static host (e.g. Netlify) — no server or
  API key required.

## Verify before you go

The app links out to Windy (cloud/fog/wind layers), [fog.today](https://fog.today)
(NOAA GOES satellite), yr.no, and ALERTCalifornia live cameras on Mt. Tam and at
Muir Beach so you can ground-truth the forecast with your own eyes.
