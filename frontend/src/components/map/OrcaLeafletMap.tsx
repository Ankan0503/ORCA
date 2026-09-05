import React, { useEffect, useImperativeHandle, useRef, forwardRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { HARBOUR, MapZone, MapTranslations, MAP_ZONES_CONFIG } from '../../data/mapData';
import { MapFilterType } from './OrcaMapFilterBar';

/** Imperative handle so the page's existing +/-/GPS controls can drive the map. */
export interface OrcaLeafletMapHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  recenter: () => void;
}

interface OrcaLeafletMapProps {
  activeFilter: MapFilterType;
  showRoute: boolean;
  onSelectZone: (zone: MapZone) => void;
  selectedZoneId?: string;
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
}

const ZONE_COLORS: Record<MapZone['type'], string> = {
  best: '#10B981',
  good: '#F59E0B',
  avoid: '#EF4444',
  restricted: '#475569',
};

/** Which zone types each filter chip reveals. */
const FILTER_ZONES: Record<MapFilterType, MapZone['type'][]> = {
  fishing: ['best', 'good', 'avoid'],
  safety: ['avoid', 'restricted'],
  pfz: ['best', 'good'],
  restrictions: ['restricted'],
};

const DEFAULT_CENTER: L.LatLngExpression = [21.44, 87.56];
const DEFAULT_ZOOM = 10;

export const OrcaLeafletMap = forwardRef<OrcaLeafletMapHandle, OrcaLeafletMapProps>(
  (
    {
      activeFilter,
      showRoute,
      onSelectZone,
      selectedZoneId,
      translations,
      interactive = true,
      attributionControl = true,
      center,
      zoom,
    },
    ref,
  ) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const mapRef = useRef<L.Map | null>(null);
    const zoneLayerRef = useRef<L.LayerGroup | null>(null);
    const routeLayerRef = useRef<L.LayerGroup | null>(null);

    // Keep the latest callback without forcing the zone layer to rebuild.
    const onSelectZoneRef = useRef(onSelectZone);
    onSelectZoneRef.current = onSelectZone;

    useImperativeHandle(ref, () => ({
      zoomIn: () => mapRef.current?.zoomIn(),
      zoomOut: () => mapRef.current?.zoomOut(),
      recenter: () => mapRef.current?.setView(DEFAULT_CENTER, DEFAULT_ZOOM, { animate: true }),
    }));

    /* ---- 1. Create the map once, then load the permanent EEZ overlay ---- */
    useEffect(() => {
      if (!containerRef.current || mapRef.current) return;

      const map = L.map(containerRef.current, {
        center: center ?? DEFAULT_CENTER,
        zoom: zoom ?? DEFAULT_ZOOM,
        minZoom: 4,
        maxZoom: 16,
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

        })
        .catch((err) => console.error('Failed to load India EEZ boundary', err));

      zoneLayerRef.current = L.layerGroup().addTo(map);
      routeLayerRef.current = L.layerGroup().addTo(map);

      // Harbour marker — "You are here".
      const harbour = L.marker([HARBOUR.lat, HARBOUR.lng], {
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

    /* ---- 2. Redraw zone circles when the filter or selection changes ---- */
    useEffect(() => {
      const layer = zoneLayerRef.current;
      if (!layer) return;
      layer.clearLayers();

      const visibleTypes = FILTER_ZONES[activeFilter] ?? [];

      MAP_ZONES_CONFIG.filter((z) => visibleTypes.includes(z.type)).forEach((zone) => {
        const color = ZONE_COLORS[zone.type];
        const isSelected = zone.id === selectedZoneId;

        // Hazard zones read as warnings, so they carry more weight than the
        // fishing zones a user is merely choosing between.
        const isHazard = zone.type === 'avoid' || zone.type === 'restricted';

        const circle = L.circle([zone.lat, zone.lng], {
          radius: zone.radiusKm * 1000,
          color,
          weight: isSelected ? 3.5 : isHazard ? 3 : 2,
          opacity: 1,
          fillColor: color,
          fillOpacity: isSelected ? 0.4 : isHazard ? 0.3 : 0.2,
          dashArray: zone.type === 'restricted' ? '6 5' : undefined,
          // A preview card handles taps as a whole, so zones must not intercept.
          interactive,
        });

        if (interactive) {
          circle.on('click', () => onSelectZoneRef.current(zone));
          circle.bindTooltip(zone.name, { direction: 'top' });
        }
        circle.addTo(layer);
      });
    }, [activeFilter, selectedZoneId, interactive]);

    /* ---- 3. Recommended route: harbour -> best zone ---- */
    useEffect(() => {
      const layer = routeLayerRef.current;
      if (!layer) return;
      layer.clearLayers();
      if (!showRoute) return;

      const best = MAP_ZONES_CONFIG.find((z) => z.id === 'best-zone');
      if (!best) return;

      L.polyline(
        [
          [HARBOUR.lat, HARBOUR.lng],
          [best.lat, best.lng],
        ],
        {
          color: '#0EA5E9',
          weight: 3,
          opacity: 0.9,
          dashArray: '8 6',
          // Decorative only: it overlaps the best zone, so it must not eat taps.
          interactive: false,
        },
      ).addTo(layer);
    }, [showRoute]);

    return <div ref={containerRef} className="absolute inset-0 z-0" id="orca-leaflet-map" />;
  },
);

OrcaLeafletMap.displayName = 'OrcaLeafletMap';
