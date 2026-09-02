from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewpoint:
    id: str
    name: str
    lat: float
    lon: float
    elev_ft: int
    desc: str
    green_ft: tuple[int, int]   # fog base (LCL) range: above the layer with it in frame
    yellow_ft: tuple[int, int]  # right at the edge
    too_low: str
    too_high: str
    composition: str
    access: str
    cam_tip: str
    dawn_gated: bool = False


VIEWPOINTS: tuple[Viewpoint, ...] = (
    Viewpoint(
        id="hawk-hill", name="Hawk Hill", lat=37.8283, lon=-122.4997, elev_ft=923,
        desc="923 ft · Golden Gate Headlands", green_ft=(200, 850), yellow_ft=(850, 950),
        too_low="Fog base very low — the layer is likely thick enough to sock you in.",
        too_high="Fog base above Hawk Hill — you'd be inside the clouds, not above them.",
        composition="Shoot south into Rodeo Valley. Wide angle (24–35mm) for the fog-wave texture between ridgelines.",
        access="24hr access via Conzelman Rd (one-way). No gate.",
        cam_tip="Sweet spot is a fog base of 200–850 ft. Above ~950 ft you'll be under the layer, not above it.",
    ),
    Viewpoint(
        id="battery-spencer", name="Battery Spencer", lat=37.8278, lon=-122.4818, elev_ft=790,
        desc="790 ft · Golden Gate Headlands", green_ft=(200, 700), yellow_ft=(700, 800),
        too_low="Fog base very low — you'd be buried in the layer.",
        too_high="Fog base above the battery — the bridge and towers disappear.",
        composition="Shoot east at the Golden Gate Bridge with fog swirling around the towers. Longer focal length (100–200mm) compresses the layer.",
        access="24hr Tue–Sun. 6am–5pm Mon. Hit it on the way down from Hawk Hill.",
        cam_tip="Lower than Hawk Hill, so it works when the fog base is a touch lower. Bridge towers are ~746 ft — fog needs to sit near or below that.",
    ),
    Viewpoint(
        id="conzelman-pullouts", name="Conzelman Pullouts", lat=37.8270, lon=-122.4900, elev_ft=600,
        desc="~600 ft · Conzelman Rd", green_ft=(150, 550), yellow_ft=(550, 650),
        too_low="Fog base very low — pullouts will be inside the layer.",
        too_high="Fog base above the road — you're under the fog here.",
        composition="Intermediate elevations between Battery Spencer and Hawk Hill. Different angles at each pullout — scout in daylight first.",
        access="24hr access. Flexible stop when the fog base is sitting low.",
        cam_tip="Use these when the fog base is too low even for Hawk Hill — the lower pullouts get you back above it.",
    ),
    Viewpoint(
        id="twin-peaks-vantage", name="Twin Peaks (Arguello & Jackson)", lat=37.7874, lon=-122.4581, elev_ft=370,
        desc="370 ft vantage · shoot toward Twin Peaks", green_ft=(400, 750), yellow_ft=(750, 850),
        too_low="Fog below your vantage — you're in it rather than looking across at it.",
        too_high="Fog above Twin Peaks (922 ft) — the peaks vanish into the layer.",
        composition="From Arguello & Jackson (~370 ft) shoot SE toward Twin Peaks (922 ft) emerging above the fog, city glowing below. Best at sunset.",
        access="Street parking, no gates. This is a narrow window — the fog must sit between you (370 ft) and the peaks (922 ft).",
        cam_tip="Different geometry: you want the fog ABOVE your vantage but BELOW the peaks — a 400–750 ft fog base. Too low = you're socked in; too high = peaks gone.",
    ),
    Viewpoint(
        id="point-bonita", name="Point Bonita Lighthouse", lat=37.8156, lon=-122.5295, elev_ft=100,
        desc="100 ft · coastal", green_ft=(50, 200), yellow_ft=(200, 300),
        too_low="Completely socked in at the coast.",
        too_high="Fog base too high — loses the low, dramatic coastal fog.",
        composition="Suspension-bridge footbridge as foreground with fog rolling off the Pacific. Only works with a very low fog base.",
        access="Check NPS hours — intermittently closed for renovations. Verify before going.",
        cam_tip="A low-elevation, different shot entirely. Best when fog is hugging the coast below ~200 ft.",
    ),
    Viewpoint(
        id="trojan-point", name="Trojan Point", lat=37.9170, lon=-122.5980, elev_ft=1750,
        desc="~1,750 ft · Mt. Tamalpais", green_ft=(200, 1550), yellow_ft=(1550, 1750), dawn_gated=True,
        too_low="Fog base very low — a deep layer may reach up around you.",
        too_high="Fog base above Trojan Point — you're inside the clouds.",
        composition="Mid-mountain sea-of-clouds looking south/southwest. The layer wraps dramatically below without obscuring the view.",
        access="Gate on the summit road opens 7am — sunrise not viable. Short hike from parking.",
        cam_tip="Great when the fog base sits 1,200–1,700 ft. Note the 7am gate: shoot this at sunset, not dawn.",
    ),
    Viewpoint(
        id="west-peak", name="West Peak", lat=37.9279, lon=-122.6017, elev_ft=2560,
        desc="2,560 ft · Mt. Tamalpais", green_ft=(200, 2400), yellow_ft=(2400, 2560), dawn_gated=True,
        too_low="Fog base extremely low — a very deep layer could still reach you.",
        too_high="Fog base above West Peak — you're in the clouds.",
        composition="Faces the coast — ideal for fog rolling in. Trees as silhouette foreground over a sea of cloud.",
        access="Gate opens 7am — sunrise not viable. ~20 min hike from Rock Spring / $9 parking. Confirm which summit road is open.",
        cam_tip="Sits above nearly all marine-layer events. Almost always above the fog when a layer is present.",
    ),
    Viewpoint(
        id="east-peak", name="East Peak", lat=37.9236, lon=-122.5800, elev_ft=2571,
        desc="2,571 ft · Mt. Tamalpais", green_ft=(200, 2400), yellow_ft=(2400, 2571), dawn_gated=True,
        too_low="Fog base extremely low — a very deep layer could still reach you.",
        too_high="Fog base above East Peak — you're in the clouds.",
        composition="Highest vantage — 360° sea of cloud over all of Marin and SF. Trees/ridgeline as foreground.",
        access="Gate opens 7am — sunrise not viable. Parking currently restricted; confirm access before driving up.",
        cam_tip="The nuclear option: if everything lower is socked in, you'll almost certainly be above the fog here.",
    ),
)

DEFAULT_VIEWPOINT_ID = "east-peak"

_BY_ID = {v.id: v for v in VIEWPOINTS}


def viewpoint_by_id(vid: str) -> Viewpoint:
    return _BY_ID[vid]
