import React, { useEffect, useImperativeHandle, useRef, forwardRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapTranslations } from '../../data/mapData';
import { MapFilterType } from './OrcaMapFilterBar';
import {
  getPfzLines,
  getPfzPoints,
  getProtectedAreas,
  getSeaGrid,
  SeaRoute,
} from '../../services/orcaApi';

/** Imperative handle so the page's existing +/-/GPS controls can drive the map. */
export interface OrcaLeafletMapHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  recenter: () => void;
}

interface OrcaLeafletMapProps {
  activeFilter: MapFilterType;
  translations: MapTranslations;
  /**
   * Preview mode: all pan/zoom gestures are disabled so the map cannot trap a
   * finger mid-scroll, and zones stop being individually tappable. Used by the
   * Find Fish card, which taps through to the full Map page instead.
   */
  interactive?: boolean;
  /** Whether to render Leaflet / OpenStreetMap attribution control. Defaults to true. */
  attributionControl?: boolean;
  /** Frame the preview on something other than the default harbour view. */
  center?: L.LatLngExpression;
  zoom?: number;
  /** App language, so INCOIS returns landing-centre names in the user's script. */
  language?: string;
  /** The user's real position, used for the "you are here" marker and recenter. */
  userLatitude?: number;
  userLongitude?: number;
  /**
   * Minimum zoom level for INCOIS advisory dots (individual landing centre points).
   * Below this zoom, coastal points cluster together into clutter, so only the
   * broader PFZ advisory lines are shown. At or above this zoom, individual
   * points appear with their distance, depth and bearing details.
   */
  dotsMinZoom?: number;
  /** A planned passage to draw, with a boat marker moving along it. */
  route?: SeaRoute | null;
  /**
   * Live position of the boat, when the device is actually reporting one.
   * Without it the marker animates along the route as a clearly-labelled
   * preview rather than pretending to be a real fix.
   */
  livePosition?: { latitude: number; longitude: number } | null;
}

/**
 * Which filters reveal the INCOIS fishing-zone layers. "Safety" and
 * "Restrictions" deliberately show no fishing zones — the EEZ boundary beneath
 * is the only real restriction data ORCA has, and inventing coloured hazard
 * blobs to fill those tabs would be worse than showing nothing.
 */
const FISHING_FILTERS: MapFilterType[] = ['fishing', 'pfz'];

/** INCOIS advisory styling — one colour, because every zone is equally official. */
const PFZ_COLOR = '#EA580C';

/**
 * The "Safety" filter previously showed nothing at all — there was no real
 * hazard data to put behind it. It now carries the live rain/storm overlay and
 * the current arrows, which is what that tab should have meant all along.
 */
const SEA_FILTERS: MapFilterType[] = ['safety'];

/** Hazard cell colours. Thunderstorm outranks rain however heavy. */
const HAZARD_STYLE: Record<string, { color: string; opacity: number; label: string }> = {
  thunderstorm: { color: '#7C3AED', opacity: 0.55, label: 'Thunderstorm — lightning' },
  heavy_rain: { color: '#1D4ED8', opacity: 0.45, label: 'Heavy rain' },
  moderate_rain: { color: '#3B82F6', opacity: 0.32, label: 'Moderate rain' },
  light_rain: { color: '#93C5FD', opacity: 0.22, label: 'Light rain' },
  fog: { color: '#94A3B8', opacity: 0.32, label: 'Fog — poor visibility' },
};

const DEFAULT_CENTER: L.LatLngExpression = [21.44, 87.56];
const DEFAULT_ZOOM = 10;

/**
 * Zoom threshold for INCOIS advisory dots (individual landing centre points).
 * - Below this zoom: only broad PFZ advisory lines are shown (no dot clutter).
 * - At or above this zoom: individual landing centre dots appear with distance/depth/bearing details.
 *
 * Change this number directly (e.g. 10, 11, 8, etc.):
 */
export const PFZ_DOTS_MIN_ZOOM = 8;

/**
 * The map is walled off to the Indian subcontinent and its seas. A fisherman has
 * no use for the rest of the globe, and being able to pan away from India is
 * disorienting — so panning and zooming out both stop at this box. It still
 * leaves the neighbouring coasts (Pakistan, Sri Lanka, Bangladesh, Myanmar,
 * Maldives) visible, which is what makes the sea around India readable.
 */
const REGION_BOUNDS = L.latLngBounds([2.0, 62.0], [28.5, 99.0]);
const REGION_MIN_ZOOM = 5;

/** Outer ring of the dimming mask — comfortably larger than REGION_BOUNDS. */
const MASK_OUTER_RING: L.LatLngExpression[] = [
  [-20, 30],
  [-20, 130],
  [50, 130],
  [50, 30],
];

/**
 * Collects the outer ring of every polygon in a (Multi)Polygon GeoJSON feature,
 * converted from GeoJSON [lng, lat] to Leaflet [lat, lng].
 */
const collectOuterRings = (geojson: GeoJSON.FeatureCollection): L.LatLngExpression[][] => {
  const rings: L.LatLngExpression[][] = [];

  for (const feature of geojson.features ?? []) {
    const geometry = feature.geometry;
    if (!geometry) continue;

    const polygons =
      geometry.type === 'Polygon'
        ? [geometry.coordinates]
        : geometry.type === 'MultiPolygon'
          ? geometry.coordinates
          : [];

    for (const polygon of polygons) {
      const outer = polygon[0];
      if (outer) rings.push(outer.map(([lng, lat]) => [lat, lng] as L.LatLngExpression));
    }
  }

  return rings;
};

export const OrcaLeafletMap = forwardRef<OrcaLeafletMapHandle, OrcaLeafletMapProps>(
  (
    {
      activeFilter,
      translations,
      interactive = true,
      attributionControl = true,
      center,
      zoom,
      language = 'en',
      userLatitude,
      userLongitude,
      dotsMinZoom,
      route,
      livePosition,
    },
    ref,
  ) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const mapRef = useRef<L.Map | null>(null);
    // The real INCOIS PFZ layers: lines (always shown with fishing filter) and
    // points (shown only when zoomed in to avoid dot clutter when zoomed out).
    const pfzLinesLayerRef = useRef<L.GeoJSON | null>(null);
    const pfzPointsLayerRef = useRef<L.GeoJSON | null>(null);
    const [pfzReady, setPfzReady] = useState(false);
    // Live rain/storm cells and current arrows for the area around the user.
    const seaLayerRef = useRef<L.LayerGroup | null>(null);
    const [seaReady, setSeaReady] = useState(false);
    // The planned passage and the boat moving along it.
    const routeLayerRef = useRef<L.LayerGroup | null>(null);
    const boatMarkerRef = useRef<L.Marker | null>(null);
    const boatTimerRef = useRef<number | null>(null);

    const activeFilterRef = useRef(activeFilter);
    activeFilterRef.current = activeFilter;

    const effectiveDotsMinZoom = dotsMinZoom ?? PFZ_DOTS_MIN_ZOOM;
    const dotsMinZoomRef = useRef(effectiveDotsMinZoom);
    dotsMinZoomRef.current = effectiveDotsMinZoom;
    // Read inside the mount-only effect, so the popup text follows the app's
    // language without making the map rebuild on every language change.
    const languageRef = useRef(language);
    languageRef.current = language;

    // Where the user actually is. Falls back to the default view only when the
    // app has no location yet — never to a hardcoded harbour.
    const userLat = userLatitude ?? (DEFAULT_CENTER as [number, number])[0];
    const userLng = userLongitude ?? (DEFAULT_CENTER as [number, number])[1];

    useImperativeHandle(ref, () => ({
      zoomIn: () => mapRef.current?.zoomIn(),
      zoomOut: () => mapRef.current?.zoomOut(),
      recenter: () => mapRef.current?.setView([userLat, userLng], DEFAULT_ZOOM, { animate: true }),
    }));

    /* ---- 1. Create the map once, then load the permanent EEZ overlay ---- */
    useEffect(() => {
      if (!containerRef.current || mapRef.current) return;

      const map = L.map(containerRef.current, {
        center: center ?? DEFAULT_CENTER,
        zoom: zoom ?? DEFAULT_ZOOM,
        minZoom: REGION_MIN_ZOOM,
        maxZoom: 16,
        maxBounds: REGION_BOUNDS,
        maxBoundsViscosity: 1.0, // hard wall, not a rubber band
        zoomControl: false, // the page supplies its own controls
        attributionControl,
        preferCanvas: true, // canvas renderer keeps panning smooth on phones
        // In preview mode every gesture is off, so a drag scrolls the page
        // underneath instead of panning a map the user cannot escape.
        dragging: interactive,
        scrollWheelZoom: interactive,
        doubleClickZoom: interactive,
        touchZoom: interactive,
        boxZoom: interactive,
        keyboard: interactive,
      });
      mapRef.current = map;

      const tileUrl =
        import.meta.env.VITE_MAP_TILE_URL ||
        'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

      L.tileLayer(tileUrl, {
        attribution: attributionControl
          ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | EEZ: Marine Regions v12'
          : '',
        maxZoom: 19,
      }).addTo(map);

      // India's EEZ — static, never changes, so it is loaded once and left on.
      fetch('/geo/india_eez.simplified.geojson')
        .then((r) => r.json())
        .then((geojson) => {
          if (!mapRef.current) return;
          L.geoJSON(geojson, {
            style: {
              color: '#0369A1',
              weight: 1.5,
              opacity: 0.85,
              fillColor: '#38BDF8',
              fillOpacity: 0.06,
            },
            interactive: false, // never steal taps from the zones above it
          })
            .addTo(mapRef.current)
            .bringToBack();

          // Dim everything outside India's EEZ so Indian waters read as "yours"
          // at a glance. One polygon: an outer ring covering the region, with
          // each EEZ polygon punched out as a hole (Leaflet fills even-odd).
          L.polygon([MASK_OUTER_RING, ...collectOuterRings(geojson)], {
            stroke: false,
            fillColor: '#1E293B',
            fillOpacity: 0.16,
            interactive: false,
          })
            .addTo(mapRef.current)
            .bringToBack(); // sits under the EEZ outline, above the tiles
        })
        .catch((err) => console.error('Failed to load India EEZ boundary', err));

      // Dynamically toggle points visibility and adjust marker radius on zoom
      const updateDotsVisibility = () => {
        const m = mapRef.current;
        const pointsLayer = pfzPointsLayerRef.current;
        if (!m || !pointsLayer) return;

        const isFishing = FISHING_FILTERS.includes(activeFilterRef.current);
        const currentZoom = m.getZoom();
        const minZoom = dotsMinZoomRef.current;

        if (isFishing && currentZoom >= minZoom) {
          if (!m.hasLayer(pointsLayer)) {
            pointsLayer.addTo(m);
          }
          const r = currentZoom >= 12 ? 6.5 : currentZoom >= 11 ? 5.5 : 4.5;
          pointsLayer.eachLayer((lyr) => {
            if (lyr instanceof L.CircleMarker) {
              lyr.setRadius(r);
            }
          });
        } else {
          if (m.hasLayer(pointsLayer)) {
            m.removeLayer(pointsLayer);
          }
        }
      };

      map.on('zoom', updateDotsVisibility);
      map.on('zoomend', updateDotsVisibility);
      map.on('moveend', updateDotsVisibility);
      map.on('viewreset', updateDotsVisibility);

      // Marine protected areas — sanctuaries and national parks where fishing is
      // restricted or forbidden. Drawn permanently rather than behind a filter:
      // a boat can drift into one on a calm, sunny day with a good catch showing
      // and nothing in the weather to warn it.
      getProtectedAreas()
        .then((collection) => {
          if (!mapRef.current) return;
          L.geoJSON(collection as unknown as GeoJSON.GeoJsonObject, {
            style: {
              color: '#6D28D9',
              weight: 1.5,
              opacity: 0.9,
              fillColor: '#7C3AED',
              fillOpacity: 0.18,
            },
            interactive,
            onEachFeature: (feature, lyr) => {
              if (!interactive) return;
              const p = (feature.properties ?? {}) as Record<string, unknown>;
              lyr.bindTooltip(
                `${p.name ?? 'Protected area'} — ${p.designation ?? 'restricted'}`,
                { sticky: true },
              );
            },
          })
            .addTo(mapRef.current)
            .bringToBack();
        })
        .catch((err) => console.error('Failed to load protected areas', err));

      // International maritime boundaries (Marine Regions v12). These are the
      // lines that get fishermen arrested when crossed, so they are drawn
      // permanently rather than hidden behind a filter, and each one names the
      // country on the other side. India's own straight baselines and 200 NM
      // limit are skipped — they are technical reference lines, not borders.
      fetch('/geo/india_eez_boundaries.geojson')
        .then((r) => r.json())
        .then((geojson) => {
          if (!mapRef.current) return;
          L.geoJSON(geojson, {
            filter: (feature) => {
              const p = feature?.properties ?? {};
              return Boolean(p.SOVEREIGN1 && p.SOVEREIGN2 && p.SOVEREIGN1 !== p.SOVEREIGN2);
            },
            style: {
              color: '#B91C1C',
              weight: 2,
              opacity: 0.85,
              dashArray: '7 5',
            },
            interactive,
            onEachFeature: (feature, lyr) => {
              if (!interactive) return;
              const p = (feature.properties ?? {}) as Record<string, string>;
              const other =
                p.SOVEREIGN1 && p.SOVEREIGN1 !== 'India' ? p.TERRITORY1 : p.TERRITORY2;
              lyr.bindTooltip(`Maritime boundary — ${other ?? p.LINE_NAME}`, {
                sticky: true,
              });
            },
          }).addTo(mapRef.current);
        })
        .catch((err) => console.error('Failed to load maritime boundaries', err));

      // Live sea conditions around the user: where the rain and lightning are,
      // and which way the water is setting. Built once into one group and
      // toggled by the filter effect below.
      getSeaGrid(userLat, userLng, 1.5)
        .then((grid) => {
          if (!mapRef.current) return;
          const group = L.layerGroup();
          // Cell size in degrees, so the squares tile the grid without gaps.
          const step = grid.cells.length > 1 ? (grid.spanDeg * 2) / 8 : 0.3;

          for (const cell of grid.cells) {
            const style = HAZARD_STYLE[cell.hazard];
            if (style) {
              const half = step / 2;
              L.rectangle(
                [
                  [cell.latitude - half, cell.longitude - half],
                  [cell.latitude + half, cell.longitude + half],
                ],
                {
                  stroke: false,
                  fillColor: style.color,
                  fillOpacity: style.opacity,
                  interactive,
                },
              )
                .bindTooltip(
                  `${style.label}${
                    cell.precipitationMm != null ? ` — ${cell.precipitationMm} mm/h` : ''
                  }`,
                  { sticky: true },
                )
                .addTo(group);
            }

            // Current arrow: a short line pointing the way the water is going.
            if (cell.currentSpeedMs != null && cell.currentDirectionDeg != null) {
              const speed = cell.currentSpeedMs;
              const len = Math.min(0.35, 0.06 + speed * 0.12) * (step / 0.3);
              const rad = (cell.currentDirectionDeg * Math.PI) / 180;
              const dLat = Math.cos(rad) * len;
              const dLon = Math.sin(rad) * len;
              L.polyline(
                [
                  [cell.latitude, cell.longitude],
                  [cell.latitude + dLat, cell.longitude + dLon],
                ],
                {
                  color: cell.currentSuspect ? '#94A3B8' : '#0E7490',
                  weight: 2,
                  opacity: cell.currentSuspect ? 0.5 : 0.85,
                  interactive,
                },
              )
                .bindTooltip(
                  `Current ${speed.toFixed(1)} m/s towards ${cell.currentTowards ?? '?'}` +
                    (cell.currentSuspect ? ' (speed looks high near shore — treat with care)' : ''),
                  { sticky: true },
                )
                .addTo(group);
            }
          }

          seaLayerRef.current = group;
          setSeaReady(true);
        })
        .catch((err) => console.error('Failed to load sea conditions grid', err));

      // India's real Potential Fishing Zones, straight from INCOIS via the
      // backend: the advisory lines plus every scraped advisory row as a point.
      // Lines are always shown on fishing filters; points only appear when zoomed in.
      Promise.all([getPfzLines(), getPfzPoints(languageRef.current)])
        .then(([lines, points]) => {
          if (!mapRef.current) return;
          const forecastDate = lines.orca_forecast_date ?? points.orca_forecast_date;
          const stale = lines.orca_stale || points.orca_stale;
          const dateLabel = forecastDate
            ? `${forecastDate}${stale ? ' (last available)' : ''}`
            : 'today';

          // 1. PFZ Lines Layer (broad oceanographic frontal boundaries)
          const linesGeoJson = L.geoJSON(lines as unknown as GeoJSON.GeoJsonObject, {
            style: { color: PFZ_COLOR, weight: 3, opacity: 0.9 },
            interactive: false, // the points carry the detail; lines never eat taps
          });
          pfzLinesLayerRef.current = linesGeoJson;

          // 2. PFZ Points Layer (individual landing centre advisory dots)
          const currentZoom = mapRef.current.getZoom();
          const initialRadius = currentZoom >= 12 ? 6.5 : currentZoom >= 11 ? 5.5 : 4.5;

          const pointsGeoJson = L.geoJSON(points as unknown as GeoJSON.GeoJsonObject, {
            pointToLayer: (_feature, latlng) =>
              L.circleMarker(latlng, {
                radius: initialRadius,
                color: '#ffffff',
                weight: 1.5,
                fillColor: PFZ_COLOR,
                fillOpacity: 0.95,
                interactive,
              }),
            onEachFeature: (feature, lyr) => {
              if (!interactive) return;
              const p = (feature.properties ?? {}) as Record<string, unknown>;
              const offshore =
                p.distance_km_from != null && p.distance_km_to != null
                  ? `${p.distance_km_from}–${p.distance_km_to} km offshore`
                  : '';
              const depth =
                p.depth_m_from != null && p.depth_m_to != null
                  ? `${p.depth_m_from}–${p.depth_m_to} m deep`
                  : '';
              const bearing =
                p.bearing_deg != null ? `${p.direction} (${p.bearing_deg}°)` : `${p.direction ?? ''}`;
              lyr.bindPopup(
                `<div style="font-family:system-ui;font-size:13px;line-height:1.45;min-width:180px">
                   <div style="font-weight:700;color:#0C587F">INCOIS fishing zone</div>
                   <div style="font-weight:600;margin-top:2px">Off ${p.landing_centre ?? ''}</div>
                   <div style="margin-top:4px">${offshore}</div>
                   <div>${bearing}${depth ? ` · ${depth}` : ''}</div>
                   <div style="margin-top:4px;color:#557186">${p.latitude_dms ?? ''} · ${p.longitude_dms ?? ''}</div>
                   <div style="margin-top:4px;color:#557186">${p.sector ?? ''} · ${dateLabel}</div>
                 </div>`,
              );
            },
          });
          pfzPointsLayerRef.current = pointsGeoJson;

          setPfzReady(true);
        })
        .catch((err) => console.error('Failed to load INCOIS PFZ data', err));

      // "You are here" — the user's own position, not a fixed harbour.
      const harbour = L.marker([userLat, userLng], {
        icon: L.divIcon({
          className: '',
          html: `<div style="position:relative;width:22px;height:22px">
                   <div style="position:absolute;inset:0;border-radius:9999px;background:#2563EB;opacity:.25"></div>
                   <div style="position:absolute;inset:5px;border-radius:9999px;background:#2563EB;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>
                 </div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        }),
        interactive,
      }).addTo(map);

      if (interactive) {
        harbour.bindTooltip(translations.youAreHere, { direction: 'top', offset: [0, -10] });
      }

      return () => {
        map.off('zoom', updateDotsVisibility);
        map.off('zoomend', updateDotsVisibility);
        map.off('moveend', updateDotsVisibility);
        map.off('viewreset', updateDotsVisibility);
        map.remove();
        mapRef.current = null;
      };
      // Mount-only: translations are re-bound by the tooltip effect below.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /* ---- 2. Toggle the INCOIS PFZ layers with the filter and current zoom ---- */
    useEffect(() => {
      const map = mapRef.current;
      const linesLayer = pfzLinesLayerRef.current;
      const pointsLayer = pfzPointsLayerRef.current;
      if (!map) return;

      if (FISHING_FILTERS.includes(activeFilter)) {
        if (linesLayer && !map.hasLayer(linesLayer)) {
          linesLayer.addTo(map);
        }
        if (pointsLayer) {
          const currentZoom = map.getZoom();
          const minZoom = dotsMinZoomRef.current;
          if (currentZoom >= minZoom) {
            if (!map.hasLayer(pointsLayer)) pointsLayer.addTo(map);
            const r = currentZoom >= 12 ? 6.5 : currentZoom >= 11 ? 5.5 : 4.5;
            pointsLayer.eachLayer((lyr) => {
              if (lyr instanceof L.CircleMarker) {
                lyr.setRadius(r);
              }
            });
          } else {
            if (map.hasLayer(pointsLayer)) map.removeLayer(pointsLayer);
          }
        }
      } else {
        if (linesLayer && map.hasLayer(linesLayer)) map.removeLayer(linesLayer);
        if (pointsLayer && map.hasLayer(pointsLayer)) map.removeLayer(pointsLayer);
      }
    }, [activeFilter, pfzReady]);

    /* ---- 2a. Draw the planned passage, and move the boat along it ---- */
    useEffect(() => {
      const map = mapRef.current;
      if (!map) return;

      // Clear any previous route and stop its animation.
      if (boatTimerRef.current !== null) {
        window.clearInterval(boatTimerRef.current);
        boatTimerRef.current = null;
      }
      if (routeLayerRef.current) {
        map.removeLayer(routeLayerRef.current);
        routeLayerRef.current = null;
      }
      boatMarkerRef.current = null;

      if (!route || route.waypoints.length < 2) return;

      const group = L.layerGroup().addTo(map);
      routeLayerRef.current = group;

      const path: L.LatLngExpression[] = route.waypoints.map((w) => [w.latitude, w.longitude]);

      // A casing under the line keeps it readable over both sea and land.
      L.polyline(path, { color: '#ffffff', weight: 7, opacity: 0.9, interactive: false }).addTo(group);
      L.polyline(path, {
        color: '#0EA5E9',
        weight: 4,
        opacity: 0.95,
        dashArray: '10 6',
        interactive: false,
      }).addTo(group);

      // Destination marker.
      const last = route.waypoints[route.waypoints.length - 1];
      L.circleMarker([last.latitude, last.longitude], {
        radius: 8,
        color: '#ffffff',
        weight: 2,
        fillColor: '#0B4A34',
        fillOpacity: 1,
        interactive: false,
      }).addTo(group);

      const boatIcon = (heading: number, live: boolean) =>
        L.divIcon({
          className: '',
          html: `<div style="transform:rotate(${heading}deg);width:30px;height:30px;display:flex;align-items:center;justify-content:center">
                   <div style="font-size:20px;line-height:1;filter:drop-shadow(0 1px 3px rgba(0,0,0,.45))">${live ? '🛥️' : '⛵'}</div>
                 </div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        });

      const firstHeading = route.legs[0]?.headingDeg ?? 0;
      const marker = L.marker(path[0] as L.LatLngExpression, {
        icon: boatIcon(firstHeading, Boolean(livePosition)),
        interactive: false,
        zIndexOffset: 1000,
      }).addTo(group);
      boatMarkerRef.current = marker;

      if (livePosition) {
        // A real fix: put the boat where it actually is. No animation — the
        // marker must never move on its own when it is claiming to be live.
        marker.setLatLng([livePosition.latitude, livePosition.longitude]);
        marker.bindTooltip('Your boat (live position)', { direction: 'top', offset: [0, -12] });
        return;
      }

      // No live fix: walk the marker along the plotted route as a preview, and
      // label it as one so it is never mistaken for a real position.
      marker.bindTooltip('Route preview — not a live position', {
        direction: 'top',
        offset: [0, -12],
      });

      let step = 0;
      const stepsPerLeg = 24;
      const totalSteps = route.legs.length * stepsPerLeg;
      boatTimerRef.current = window.setInterval(() => {
        step = (step + 1) % totalSteps;
        const legIndex = Math.floor(step / stepsPerLeg);
        const t = (step % stepsPerLeg) / stepsPerLeg;
        const leg = route.legs[legIndex];
        if (!leg) return;
        const lat = leg.from.latitude + (leg.to.latitude - leg.from.latitude) * t;
        const lon = leg.from.longitude + (leg.to.longitude - leg.from.longitude) * t;
        marker.setLatLng([lat, lon]);
        marker.setIcon(boatIcon(leg.headingDeg, false));
      }, 120);

      return () => {
        if (boatTimerRef.current !== null) {
          window.clearInterval(boatTimerRef.current);
          boatTimerRef.current = null;
        }
      };
    }, [route, livePosition]);

    /* ---- 2b. Toggle the live sea-conditions layer (Safety filter) ---- */
    useEffect(() => {
      const map = mapRef.current;
      const layer = seaLayerRef.current;
      if (!map || !layer) return;

      if (SEA_FILTERS.includes(activeFilter)) {
        layer.addTo(map);
      } else {
        map.removeLayer(layer);
      }
    }, [activeFilter, seaReady]);

    return <div ref={containerRef} className="absolute inset-0 z-0" id="orca-leaflet-map" />;
  },
);

OrcaLeafletMap.displayName = 'OrcaLeafletMap';
