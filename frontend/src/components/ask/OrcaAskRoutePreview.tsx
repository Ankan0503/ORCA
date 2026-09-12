import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { AlertTriangle, Map as MapIcon, Navigation } from 'lucide-react';
import { AgentEvidence } from '../../services/orcaApi';

/** Hands a route from the Ask page to the full map, which plans it again there. */
export const PENDING_ROUTE_KEY = 'orca.pendingRoute';

interface LatLon {
  latitude: number;
  longitude: number;
}

export interface AskRoute {
  route: { waypoints: LatLon[]; totalDistanceKm: number; totalHours: number; avoided: string[] };
  origin: LatLon;
  destination: LatLon & { label: string };
  departure: string | null;
  backBy: string | null;
  weatherTurnsAt: string | null;
  fitsSafeWindow: boolean | null;
  estimate: boolean;
}

/** The route the route-planning agent returned, if it planned one. */
export function askRouteFrom(results: AgentEvidence[]): AskRoute | null {
  const hit = results.find((r) => r.agent === 'route_planning' && !r.error && r.data?.route);
  return hit ? (hit.data as unknown as AskRoute) : null;
}

const LABELS: Record<string, Record<string, string>> = {
  en: {
    title: 'Safest route',
    eachWay: 'each way',
    leave: 'Leave',
    back: 'Back by',
    turns: 'Weather turns',
    open: 'Open full map',
    unsafe: 'A full trip does not fit before the weather turns',
    estimate: 'Zone is an ORCA estimate, not an INCOIS advisory',
  },
  hi: {
    title: 'सबसे सुरक्षित रास्ता',
    eachWay: 'एक तरफ़',
    leave: 'निकलें',
    back: 'वापसी का समय',
    turns: 'मौसम बिगड़ेगा',
    open: 'पूरा नक्शा खोलें',
    unsafe: 'मौसम बिगड़ने से पहले पूरी यात्रा संभव नहीं',
    estimate: 'यह क्षेत्र ORCA का अनुमान है, INCOIS की सलाह नहीं',
  },
  bn: {
    title: 'সবচেয়ে নিরাপদ পথ',
    eachWay: 'এক দিকে',
    leave: 'রওনা',
    back: 'ফেরার সময়',
    turns: 'আবহাওয়া খারাপ হবে',
    open: 'পুরো মানচিত্র খুলুন',
    unsafe: 'আবহাওয়া খারাপ হওয়ার আগে পুরো যাত্রা সম্ভব নয়',
    estimate: 'এলাকাটি ORCA-র অনুমান, INCOIS পরামর্শ নয়',
  },
};

const clock = (iso: string | null) => (iso ? iso.slice(11, 16) : '—');

interface OrcaAskRoutePreviewProps {
  data: AskRoute;
  language: string;
  onOpenMap: () => void;
}

export const OrcaAskRoutePreview: React.FC<OrcaAskRoutePreviewProps> = ({ data, language, onOpenMap }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const t = LABELS[language] ?? LABELS.en;
  const warn = data.fitsSafeWindow === false;

  useEffect(() => {
    if (!mapRef.current) return;
    const map = L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: false,
      scrollWheelZoom: false,
    });
    L.tileLayer(import.meta.env.VITE_MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
    }).addTo(map);

    const path: L.LatLngTuple[] = [
      [data.origin.latitude, data.origin.longitude],
      ...data.route.waypoints.map((w): L.LatLngTuple => [w.latitude, w.longitude]),
      [data.destination.latitude, data.destination.longitude],
    ];
    L.polyline(path, { color: '#062A43', weight: 7, opacity: 0.2 }).addTo(map);
    L.polyline(path, { color: '#1677A8', weight: 4, dashArray: '8 6' }).addTo(map);
    L.circleMarker(path[0], { radius: 6, color: '#062A43', weight: 2, fillColor: '#FFFFFF', fillOpacity: 1 }).addTo(map);
    L.circleMarker(path[path.length - 1], {
      radius: 8,
      color: '#0F766E',
      weight: 2,
      fillColor: '#14B8A6',
      fillOpacity: 1,
    })
      .bindTooltip(data.destination.label)
      .addTo(map);
    map.fitBounds(L.latLngBounds(path), { padding: [20, 20] });

    return () => {
      map.remove();
    };
  }, [data]);

  return (
    <section className="w-full mt-3 rounded-2xl border border-[#BCD8EC] bg-white/90 overflow-hidden shadow-sm">
      <div className="flex items-center justify-between gap-2 px-4 pt-3">
        <span className="flex items-center gap-1.5 font-ui text-[12px] font-extrabold uppercase tracking-wider text-[#1677A8]">
          <Navigation size={14} />
          {t.title}
        </span>
        <span className="font-ui text-[13px] font-bold text-[#062A43]">
          {data.route.totalDistanceKm.toFixed(0)} km · {data.route.totalHours.toFixed(1)} h {t.eachWay}
        </span>
      </div>

      <div ref={mapRef} className="mt-2 h-48 w-full" role="img" aria-label={`${t.title}: ${data.destination.label}`} />

      <div className="grid grid-cols-3 gap-2 px-4 py-3 font-ui text-[12.5px] text-[#062A43]">
        <div>
          <div className="text-[11px] text-[#71869A]">{t.leave}</div>
          <div className="font-bold">{clock(data.departure)}</div>
        </div>
        <div>
          <div className="text-[11px] text-[#71869A]">{t.back}</div>
          <div className={`font-bold ${warn ? 'text-[#DC2626]' : ''}`}>{clock(data.backBy)}</div>
        </div>
        <div>
          <div className="text-[11px] text-[#71869A]">{t.turns}</div>
          <div className="font-bold">{clock(data.weatherTurnsAt)}</div>
        </div>
      </div>

      {(warn || data.estimate) && (
        <div className="mx-4 mb-3 flex items-start gap-2 rounded-xl bg-[#FEF3C7] px-3 py-2 font-ui text-[12px] text-[#92400E]">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>{[warn ? t.unsafe : null, data.estimate ? t.estimate : null].filter(Boolean).join(' · ')}</span>
        </div>
      )}

      <button
        type="button"
        onClick={onOpenMap}
        className="flex w-full items-center justify-center gap-2 border-t border-[#BCD8EC] py-3 font-ui text-[14px] font-bold text-[#1677A8] hover:bg-[#F0F7FC] transition-colors"
      >
        <MapIcon size={16} />
        {t.open}
      </button>
    </section>
  );
};
