import React, { useEffect, useImperativeHandle, useRef, forwardRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapTranslations } from '../../data/mapData';
import { MapFilterType } from './OrcaMapFilterBar';
import { getPfzLines, getPfzPoints } from '../../services/orcaApi';

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

const DEFAULT_CENTER: L.LatLngExpression = [21.44, 87.56];
const DEFAULT_ZOOM = 10;

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
    },
    ref,
  ) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const mapRef = useRef<L.Map | null>(null);
    // The real INCOIS PFZ layer (advisory lines + scraped zone points), fetched
    // once. `pfzReady` re-runs the visibility effect when the load finishes.
    const pfzLayerRef = useRef<L.LayerGroup | null>(null);
    const [pfzReady, setPfzReady] = useState(false);
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

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
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

      // India's real Potential Fishing Zones, straight from INCOIS via the
      // backend: the advisory lines plus every scraped advisory row as a point.
      // Built once into one group, toggled by the filter effect below.
      Promise.all([getPfzLines(), getPfzPoints(languageRef.current)])
        .then(([lines, points]) => {
          if (!mapRef.current) return;
          const forecastDate = lines.orca_forecast_date ?? points.orca_forecast_date;
          const stale = lines.orca_stale || points.orca_stale;
          const dateLabel = forecastDate
            ? `${forecastDate}${stale ? ' (last available)' : ''}`
            : 'today';

          const group = L.layerGroup();

          L.geoJSON(lines as unknown as GeoJSON.GeoJsonObject, {
            style: { color: PFZ_COLOR, weight: 3, opacity: 0.9 },
            interactive: false, // the points carry the detail; lines never eat taps
          }).addTo(group);

          L.geoJSON(points as unknown as GeoJSON.GeoJsonObject, {
            pointToLayer: (_feature, latlng) =>
              L.circleMarker(latlng, {
                radius: 6,
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
          }).addTo(group);

          pfzLayerRef.current = group;
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
        map.remove();
        mapRef.current = null;
      };
      // Mount-only: translations are re-bound by the tooltip effect below.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /* ---- 2. Toggle the INCOIS PFZ layer with the filter ---- */
    useEffect(() => {
      const map = mapRef.current;
      const layer = pfzLayerRef.current;
      if (!map || !layer) return;

      if (FISHING_FILTERS.includes(activeFilter)) {
        layer.addTo(map);
      } else {
        map.removeLayer(layer);
      }
    }, [activeFilter, pfzReady]);

    return <div ref={containerRef} className="absolute inset-0 z-0" id="orca-leaflet-map" />;
  },
);

OrcaLeafletMap.displayName = 'OrcaLeafletMap';
