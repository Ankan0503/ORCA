"""Copernicus Marine PFZ Pipeline — daily cloud-bypass PFZ predictions for India's EEZ.

This module implements the full pipeline:
1. Fetch daily SST, Chlorophyll, Currents, SSHA from CMEMS via copernicusmarine
2. Analyze: thermal fronts, biological fronts, cold-core eddies, ISRO advection
3. Filter: clip to India EEZ, exclude MPAs, downsample to ~200 points
4. Serialize: lightweight JSON for API serving

Cloud-bypass tiers:
- Tier 1 (Clear): SST + Chlorophyll → gradient intersection
- Tier 2 (Partial Cloud): SST L4 (microwave) → thermal fronts only
- Tier 3 (Heavy Cloud): SSHA + Currents + Last Known Fronts → ISRO Advection + Eddy detection
"""

from __future__ import annotations

import asyncio
import json
import math
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np
import xarray as xr

logger = logging.getLogger("orca.copernicus")

# India's EEZ and marine-protected-area geometry, resolved relative to this
# module so the pipeline works no matter what the working directory is.
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "geo"
EEZ_PATH = DATA_DIR / "india_eez.geojson"
MPA_PATH = DATA_DIR / "india_mpa.geojson"

# India EEZ bounding box
BBOX_MIN_LON = 65.0
BBOX_MAX_LON = 95.0
BBOX_MIN_LAT = 5.0
BBOX_MAX_LAT = 25.0

# Dataset IDs from the Copernicus Marine catalogue, with the variable each one carries.
# OSTIA is the gap-free L4 analysis (infrared blended with cloud-penetrating microwave),
# which is the whole point of this pipeline — and it reports Kelvin, not Celsius.
DATASET_SST = "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
VAR_SST = "analysed_sst"
DATASET_CHL = "cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D"
VAR_CHL = "CHL"
DATASET_CUR = "cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m"
VAR_CUR_U = "uo"
VAR_CUR_V = "vo"
# The 0.25 degree sea-level dataset stopped updating in Nov 2024; this one is live.
DATASET_SSHA = "cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D"
VAR_SSHA = "sla"

# Thresholds
SST_GRADIENT_THRESHOLD = 0.05  # °C per grid cell
CHL_THRESHOLD = 0.5  # mg/m³
EDDY_SSHA_M = -0.05  # a dip this deep marks a cold-core eddy
# The national file; the API serves only what falls in the caller's viewport, so this
# budget buys coverage of every coast rather than a bigger payload on a boat's phone.
MAX_OUTPUT_POINTS = 1200
DOWNSAMPLE_START_DEG = 0.1
DOWNSAMPLE_MAX_DEG = 2.0
# Past this, yesterday's front has drifted too far to be worth projecting (ISRO SAC).
ADVECTION_MAX_HOURS = 72.0
MAX_LAST_CLEAR_POINTS = 500
# Near-real-time products lag by a day or two, so "today" is often not there yet.
MAX_DAYS_BACK = 4
KELVIN_ZERO = 273.15

# Settings may give relative paths; they must not depend on the working directory.
ROOT = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


@dataclass
class PFZPoint:
    """A single PFZ prediction point."""
    latitude: float
    longitude: float
    source: str  # "thermal_front", "biological_front", "cold_eddy", "advection"
    sst_c: Optional[float] = None
    chlorophyll_mg_m3: Optional[float] = None
    ssha_m: Optional[float] = None
    front_strength_c: Optional[float] = None
    confidence: str = "HIGH"
    cloud_bypass: bool = False
    advection_hours: Optional[float] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Round coordinates to 4 decimal places (~11m)
        d["latitude"] = round(self.latitude, 4)
        d["longitude"] = round(self.longitude, 4)
        return d


class CopernicusClient:
    """Authenticated subset fetcher for CMEMS datasets."""

    def __init__(self, username: str, password: str, output_dir: Path):
        self.username = username
        self.password = password
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _subset(
        self,
        dataset_id: str,
        date: datetime,
        variables: list[str],
        bbox: tuple[float, float, float, float],
        output_path: Path,
    ) -> Path:
        """Fetch a subset through the toolbox's Python API.

        Not the CLI: it lives in the virtualenv's Scripts directory, which is not on
        PATH unless the environment is activated, so shelling out failed with "file
        not found" every time. The API also keeps the password out of any argv.
        """
        import copernicusmarine

        min_lon, max_lon, min_lat, max_lat = bbox
        day = date.strftime("%Y-%m-%d")

        logger.info("Fetching %s for %s", dataset_id, date.date())
        response = copernicusmarine.subset(
            dataset_id=dataset_id,
            variables=list(variables),
            minimum_longitude=min_lon,
            maximum_longitude=max_lon,
            minimum_latitude=min_lat,
            maximum_latitude=max_lat,
            start_datetime=f"{day}T00:00:00",
            end_datetime=f"{day}T23:59:59",
            output_directory=str(self.output_dir),
            output_filename=output_path.name,
            username=self.username or None,
            password=self.password or None,
            overwrite=True,
            disable_progress_bar=True,
        )

        written = getattr(response, "file_path", None)
        return Path(written) if written else output_path

    def fetch_daily_sst(self, date: datetime, bbox: tuple) -> Path:
        out = self.output_dir / f"sst_{date:%Y%m%d}.nc"
        return self._subset(DATASET_SST, date, [VAR_SST], bbox, out)

    def fetch_daily_chlorophyll(self, date: datetime, bbox: tuple) -> Path:
        out = self.output_dir / f"chl_{date:%Y%m%d}.nc"
        return self._subset(DATASET_CHL, date, [VAR_CHL], bbox, out)

    def fetch_daily_currents(self, date: datetime, bbox: tuple) -> Path:
        out = self.output_dir / f"cur_{date:%Y%m%d}.nc"
        return self._subset(DATASET_CUR, date, [VAR_CUR_U, VAR_CUR_V], bbox, out)

    def fetch_daily_ssha(self, date: datetime, bbox: tuple) -> Path:
        out = self.output_dir / f"ssha_{date:%Y%m%d}.nc"
        return self._subset(DATASET_SSHA, date, [VAR_SSHA], bbox, out)


def _surface_slice(da: xr.DataArray) -> xr.DataArray:
    """The first time step at the surface, whatever optional axes a product carries."""
    for axis in ("time", "depth", "elevation"):
        if axis in da.dims:
            da = da.isel({axis: 0})
    return da


def _coord_names(da: xr.DataArray) -> tuple[str, str]:
    """Latitude and longitude coordinate names: products use either spelling."""
    lat = "latitude" if "latitude" in da.coords else "lat"
    lon = "longitude" if "longitude" in da.coords else "lon"
    return lat, lon


def _to_celsius(da: xr.DataArray) -> xr.DataArray:
    """OSTIA reports Kelvin; every threshold in ORCA is Celsius."""
    try:
        warmest = float(np.nanmax(np.asarray(da.values, dtype=float)))
    except (ValueError, TypeError):
        return da
    return da - KELVIN_ZERO if warmest > 100.0 else da


class PFZAnalyzer:
    """Mathematical analysis on xarray DataArrays."""

    def __init__(self):
        self.last_clear_fronts: list[PFZPoint] = []
        self.last_clear_saved_at: datetime | None = None

    def load_last_clear(self, path: Path) -> None:
        """Load the last clear-sky fronts, and when they were seen, for advection."""
        self.last_clear_fronts = []
        self.last_clear_saved_at = None
        if not Path(path).exists():
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return

        # Files written before this carried a bare list, with no timestamp.
        rows = data.get("points", []) if isinstance(data, dict) else data
        # Prefer when the front was observed; fall back to when the file was written.
        saved_at = (data.get("observed_at") or data.get("saved_at")) if isinstance(data, dict) else None
        try:
            self.last_clear_fronts = [PFZPoint(**row) for row in rows]
        except TypeError as exc:
            logger.warning("Unreadable front in %s: %s", path, exc)
            return
        if saved_at:
            try:
                self.last_clear_saved_at = datetime.fromisoformat(saved_at)
            except ValueError:
                self.last_clear_saved_at = None
        logger.info("Loaded %d last clear fronts from %s", len(self.last_clear_fronts), path)

    def save_last_clear(
        self, path: Path, fronts: list[PFZPoint], observed_at: datetime | None = None
    ) -> None:
        """Save these fronts, and when the satellite saw them, for the next cloudy day."""
        payload = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            # Drift is measured from the observation, not from this run: the data is
            # already a day or two old when it arrives.
            "observed_at": (observed_at or datetime.now(timezone.utc)).isoformat(),
            "points": [p.to_dict() for p in fronts[:MAX_LAST_CLEAR_POINTS]],
        }
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.info("Saved %d clear fronts to %s", len(payload["points"]), path)
        except OSError as exc:
            logger.warning("Could not save %s: %s", path, exc)

    def hours_since_last_clear(self, now: datetime | None = None) -> float | None:
        """How long the stored fronts have had to drift; None when there are none."""
        if not self.last_clear_fronts:
            return None
        if self.last_clear_saved_at is None:
            return 24.0
        moment = now or datetime.now(timezone.utc)
        return max(0.0, (moment - self.last_clear_saved_at).total_seconds() / 3600.0)

    def thermal_gradient(self, sst_da: xr.DataArray) -> np.ndarray:
        """Gradient magnitude of the whole grid, computed once rather than per point."""
        dy, dx = np.gradient(np.asarray(sst_da.values, dtype=float))
        return np.sqrt(dx**2 + dy**2)

    def detect_thermal_fronts(
        self,
        sst_da: xr.DataArray,
        threshold: float = SST_GRADIENT_THRESHOLD,
        gradient: np.ndarray | None = None,
    ) -> xr.DataArray:
        """Detect SST fronts via gradient magnitude > threshold."""
        grad_mag = self.thermal_gradient(sst_da) if gradient is None else gradient
        return xr.DataArray(grad_mag > threshold, coords=sst_da.coords, dims=sst_da.dims)

    def detect_biological_fronts(self, chl_da: xr.DataArray, threshold: float = CHL_THRESHOLD) -> xr.DataArray:
        """Detect chlorophyll fronts where Chl > threshold."""
        return chl_da > threshold

    def detect_cold_core_eddies(self, ssha_da: xr.DataArray) -> xr.DataArray:
        """Detect cold-core eddies as negative SSHA anomalies (< -0.05 m)."""
        return ssha_da < -0.05

    def advect_fronts(
        self,
        front_points: list[PFZPoint],
        u_da: xr.DataArray,
        v_da: xr.DataArray,
        hours_elapsed: float,
    ) -> list[PFZPoint]:
        """ISRO Current-Vector Advection: drift fronts by surface currents."""
        advected = []
        dt_seconds = hours_elapsed * 3600.0

        u_lat, u_lon = _coord_names(u_da)
        v_lat, v_lon = _coord_names(v_da)

        for pt in front_points:
            # The current in the cell the front sits in.
            try:
                u_val = float(
                    u_da.sel({u_lat: pt.latitude, u_lon: pt.longitude}, method="nearest").values
                )
                v_val = float(
                    v_da.sel({v_lat: pt.latitude, v_lon: pt.longitude}, method="nearest").values
                )
            except Exception:  # noqa: BLE001 - a front outside the current grid is simply dropped
                continue

            if np.isnan(u_val) or np.isnan(v_val):
                continue

            # ISRO advection formula
            delta_x = u_val * dt_seconds
            delta_y = v_val * dt_seconds

            lat_rad = math.radians(pt.latitude)
            delta_lon = delta_x / (111320.0 * math.cos(lat_rad))
            delta_lat = delta_y / 110540.0

            new_lat = pt.latitude + delta_lat
            new_lon = pt.longitude + delta_lon

            drift_km = math.sqrt(delta_x**2 + delta_y**2) / 1000.0

            advected.append(PFZPoint(
                latitude=new_lat,
                longitude=new_lon,
                source="advection",
                sst_c=pt.sst_c,
                chlorophyll_mg_m3=pt.chlorophyll_mg_m3,
                confidence="MEDIUM",
                cloud_bypass=True,
                advection_hours=hours_elapsed,
                front_strength_c=pt.front_strength_c,
            ))

        return advected

    def combine_pfz_layers(
        self,
        sst_da: Optional[xr.DataArray] = None,
        chl_da: Optional[xr.DataArray] = None,
        cur_u_da: Optional[xr.DataArray] = None,
        cur_v_da: Optional[xr.DataArray] = None,
        ssha_da: Optional[xr.DataArray] = None,
        last_clear_path: Optional[Path] = None,
        observed_at: Optional[datetime] = None,
    ) -> tuple[list[PFZPoint], str]:
        """Zones from whatever arrived: fronts, cold eddies, and yesterday's fronts drifted."""
        all_points: list[PFZPoint] = []

        # Load last clear fronts if available
        if last_clear_path:
            self.load_last_clear(last_clear_path)

        # Thermal fronts, narrowed to productive water when chlorophyll came through.
        if sst_da is not None:
            lat_name, lon_name = _coord_names(sst_da)
            lats = np.asarray(sst_da.coords[lat_name].values, dtype=float)
            lons = np.asarray(sst_da.coords[lon_name].values, dtype=float)
            sst_values = np.asarray(sst_da.values, dtype=float)
            gradient = self.thermal_gradient(sst_da)
            mask = gradient > SST_GRADIENT_THRESHOLD

            chl_values = None
            if chl_da is not None:
                # Chlorophyll is a 4 km grid and SST is 0.05 degrees: they have to be put
                # on one grid, not indexed as though they matched. Nearest-neighbour, so
                # this needs no interpolation library for a difference under a kilometre.
                chl_lat, chl_lon = _coord_names(chl_da)
                chl_values = np.asarray(
                    chl_da.sel({chl_lat: lats, chl_lon: lons}, method="nearest").values,
                    dtype=float,
                )
                mask = mask & (chl_values > CHL_THRESHOLD)

            for row, col in zip(*np.where(mask)):
                all_points.append(PFZPoint(
                    latitude=float(lats[row]),
                    longitude=float(lons[col]),
                    source="thermal_front",
                    sst_c=round(float(sst_values[row, col]), 2),
                    chlorophyll_mg_m3=(
                        round(float(chl_values[row, col]), 3) if chl_values is not None else None
                    ),
                    front_strength_c=round(float(gradient[row, col]), 3),
                    confidence="HIGH" if chl_values is not None else "MEDIUM",
                ))

            # Today's fronts are the seed the next cloudy day drifts forward.
            if all_points and last_clear_path:
                self.save_last_clear(last_clear_path, all_points, observed_at)

        # Cold-core eddies: radar altimetry sees them straight through cloud.
        if ssha_da is not None:
            lat_name, lon_name = _coord_names(ssha_da)
            ssha_lats = np.asarray(ssha_da.coords[lat_name].values, dtype=float)
            ssha_lons = np.asarray(ssha_da.coords[lon_name].values, dtype=float)
            ssha_values = np.asarray(ssha_da.values, dtype=float)

            for row, col in zip(*np.where(ssha_values < EDDY_SSHA_M)):
                all_points.append(PFZPoint(
                    latitude=float(ssha_lats[row]),
                    longitude=float(ssha_lons[col]),
                    source="cold_eddy",
                    ssha_m=round(float(ssha_values[row, col]), 3),
                    confidence="MEDIUM",
                    cloud_bypass=True,
                ))

        # ISRO SAC's method: drift the last clear fronts forward by the measured currents.
        hours = self.hours_since_last_clear()
        if (
            cur_u_da is not None
            and cur_v_da is not None
            and hours is not None
            and hours <= ADVECTION_MAX_HOURS
        ):
            all_points.extend(
                self.advect_fronts(self.last_clear_fronts, cur_u_da, cur_v_da, hours)
            )
        elif hours is not None and hours > ADVECTION_MAX_HOURS:
            logger.info("Last clear fronts are %.0f h old; too stale to drift forward", hours)

        # The label describes what the points are, never which download happened to fail.
        if any(p.source == "thermal_front" and p.chlorophyll_mg_m3 is not None for p in all_points):
            tier = "fronts_with_chlorophyll"
        elif any(p.source == "thermal_front" for p in all_points):
            tier = "thermal_fronts_only"
        elif any(p.cloud_bypass for p in all_points):
            tier = "cloud_bypass_only"
        else:
            tier = "no_data"

        logger.info(
            "PFZ analysis: tier=%s, points=%d, cloud_bypass=%d",
            tier,
            len(all_points),
            sum(1 for p in all_points if p.cloud_bypass),
        )
        return all_points, tier


def _point_in_ring(lat: float, lon: float, ring: list) -> bool:
    """Ray-casting test on a GeoJSON ring of [lon, lat] pairs."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def _point_in_polygon(lat: float, lon: float, polygon: list) -> bool:
    """A GeoJSON polygon: first ring is the outer edge, the rest are holes."""
    if not polygon or not _point_in_ring(lat, lon, polygon[0]):
        return False
    return not any(_point_in_ring(lat, lon, hole) for hole in polygon[1:])


def _load_polygons(path: Path) -> list[list]:
    """Read a GeoJSON FeatureCollection into a list of polygon coordinate lists."""
    if not Path(path).exists():
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        logger.warning("Could not read GeoJSON at %s", path)
        return []

    polygons: list[list] = []
    for feature in data.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "Polygon":
            polygons.append(geometry.get("coordinates") or [])
        elif geometry.get("type") == "MultiPolygon":
            polygons.extend(geometry.get("coordinates") or [])
    return polygons


class PFZSerializer:
    """Clip, filter, and export PFZ points."""

    def __init__(self, eez_geojson: Path, mpa_geojson: Path):
        self.eez_geojson = eez_geojson
        self.mpa_geojson = mpa_geojson
        self._eez_polygons: list[list] | None = None
        self._mpa_polygons: list[list] | None = None

    def _load(self) -> None:
        if self._eez_polygons is None:
            self._eez_polygons = _load_polygons(self.eez_geojson)
            self._mpa_polygons = _load_polygons(self.mpa_geojson)

    def clip_to_eez(self, points: list[PFZPoint]) -> list[PFZPoint]:
        """Keep only points inside India EEZ."""
        self._load()
        clipped = []
        for pt in points:
            if any(
                _point_in_polygon(pt.latitude, pt.longitude, polygon)
                for polygon in self._eez_polygons
            ):
                clipped.append(pt)
        logger.info("Clipped to EEZ: %d -> %d points", len(points), len(clipped))
        return clipped

    def exclude_mpas(self, points: list[PFZPoint]) -> list[PFZPoint]:
        """Remove points inside Marine Protected Areas."""
        self._load()
        filtered = []
        for pt in points:
            if not any(
                _point_in_polygon(pt.latitude, pt.longitude, polygon)
                for polygon in self._mpa_polygons
            ):
                filtered.append(pt)
        logger.info("Excluded MPAs: %d -> %d points", len(points), len(filtered))
        return filtered

    def downsample(self, points: list[PFZPoint], max_points: int = MAX_OUTPUT_POINTS) -> list[PFZPoint]:
        """Thin the points evenly along the coast, keeping the best one in each cell.

        The cell grows until the whole EEZ fits the budget. Taking the first cells of a
        fixed grid instead truncated by latitude: a national run published 200 points
        inside one degree off Kerala and none at all for the Bay of Bengal, so that
        coast's layer was empty every day whatever the sea was doing.
        """
        if len(points) <= max_points:
            return points

        rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        cell_deg = DOWNSAMPLE_START_DEG
        while True:
            grid: dict[tuple[int, int], PFZPoint] = {}
            for pt in points:
                key = (int(pt.latitude / cell_deg), int(pt.longitude / cell_deg))
                held = grid.get(key)
                if held is None or rank.get(pt.confidence, 9) < rank.get(held.confidence, 9):
                    grid[key] = pt
            if len(grid) <= max_points or cell_deg >= DOWNSAMPLE_MAX_DEG:
                break
            cell_deg *= 2

        result = list(grid.values())[:max_points]
        logger.info(
            "Downsampled: %d -> %d points on a %.2f degree grid", len(points), len(result), cell_deg
        )
        return result

    def to_json(self, points: list[PFZPoint], metadata: dict) -> dict:
        """Serialize to API-ready GeoJSON FeatureCollection."""
        features = []
        for pt in points:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pt.longitude, pt.latitude],
                },
                "properties": pt.to_dict(),
            })

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": metadata,
        }


async def run_copernicus_pfz_pipeline(settings) -> dict:
    """Daily pipeline: fetch, analyze, serialize, save JSON."""
    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(IST)
    target_date = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)

    # Initialize components
    client = CopernicusClient(
        settings.copernicus_username,
        settings.copernicus_password,
        _resolve(settings.copernicus_output_dir),
    )
    analyzer = PFZAnalyzer()
    serializer = PFZSerializer(EEZ_PATH, MPA_PATH)

    bbox = (
        settings.copernicus_bbox_min_lon,
        settings.copernicus_bbox_max_lon,
        settings.copernicus_bbox_min_lat,
        settings.copernicus_bbox_max_lat,
    )

    # Fetch datasets (each optional: a missing product degrades the run, never fails it)
    sst_da = chl_da = cur_u_da = cur_v_da = ssha_da = None
    sources_used: list[str] = []

    source_dates: dict[str, str] = {}

    def fetch_recent(fetch, label: str) -> tuple[Path, datetime]:
        """The most recent day this product actually holds, not the day we wish it had."""
        last_error: Exception | None = None
        for days_back in range(MAX_DAYS_BACK + 1):
            day = target_date - timedelta(days=days_back)
            try:
                return fetch(day, bbox), day
            except Exception as exc:  # noqa: BLE001 - step back a day and try again
                last_error = exc
        raise last_error if last_error else RuntimeError(f"{label} is unavailable")

    async def grab(fetch, variable: str, label: str):
        """Download and open one product off the event loop, so the API keeps serving."""
        try:
            path, day = await asyncio.to_thread(fetch_recent, fetch, label)
            dataset = await asyncio.to_thread(xr.open_dataset, path)
            source_dates[label] = day.strftime("%Y-%m-%d")
            sources_used.append(f"{label} ({day:%d %b})")
            return _surface_slice(dataset[variable])
        except Exception as exc:  # noqa: BLE001 - any provider failure is a degraded run
            logger.warning("%s fetch failed: %s", label, exc)
            return None

    sst_da = await grab(client.fetch_daily_sst, VAR_SST, "SST")
    if sst_da is not None:
        sst_da = _to_celsius(sst_da)
    chl_da = await grab(client.fetch_daily_chlorophyll, VAR_CHL, "Chlorophyll")
    ssha_da = await grab(client.fetch_daily_ssha, VAR_SSHA, "SSHA")

    try:
        cur_path, cur_day = await asyncio.to_thread(
            fetch_recent, client.fetch_daily_currents, "Currents"
        )
        cur_ds = await asyncio.to_thread(xr.open_dataset, cur_path)
        cur_u_da = _surface_slice(cur_ds[VAR_CUR_U])
        cur_v_da = _surface_slice(cur_ds[VAR_CUR_V])
        source_dates["Currents"] = cur_day.strftime("%Y-%m-%d")
        sources_used.append(f"Currents ({cur_day:%d %b})")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Currents fetch failed: %s", exc)

    # Analyze
    last_clear_path = _resolve(settings.copernicus_last_clear_output)
    sst_observed = (
        datetime.fromisoformat(source_dates["SST"]).replace(tzinfo=timezone.utc)
        if source_dates.get("SST")
        else None
    )
    points, tier = analyzer.combine_pfz_layers(
        sst_da, chl_da, cur_u_da, cur_v_da, ssha_da, last_clear_path, sst_observed
    )

    # Filter
    points = serializer.clip_to_eez(points)
    points = serializer.exclude_mpas(points)
    points = serializer.downsample(points)

    # Serialize
    metadata = {
        "generated_at_ist": now_ist.isoformat(),
        "forecast_date": target_date.strftime("%Y-%m-%d"),
        "tier": tier,
        # True only where a point actually came from a cloud-bypass source.
        "cloud_bypass_active": any(p.cloud_bypass for p in points),
        "sources_used": sources_used,
        # The day each product was actually observed: NRT lags, and an answer must not
        # imply a satellite pass that has not happened yet.
        "source_dates": source_dates,
        "points_count": len(points),
        "bbox": {
            "min_lon": settings.copernicus_bbox_min_lon,
            "max_lon": settings.copernicus_bbox_max_lon,
            "min_lat": settings.copernicus_bbox_min_lat,
            "max_lat": settings.copernicus_bbox_max_lat,
        },
    }

    output = serializer.to_json(points, metadata)

    # Save
    output_path = _resolve(settings.copernicus_pfz_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    logger.info("Pipeline complete: %d points saved to %s", len(points), output_path)
    return metadata


def output_is_fresh(settings) -> bool:
    """Whether today's file is already on disk, so a restart does not re-download it."""
    path = _resolve(settings.copernicus_pfz_output)
    if not path.exists():
        return False
    try:
        metadata = json.loads(path.read_text(encoding="utf-8")).get("metadata", {})
    except (OSError, ValueError):
        return False
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    return metadata.get("forecast_date") == today
    return metadata