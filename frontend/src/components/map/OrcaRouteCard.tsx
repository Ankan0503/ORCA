import React from 'react';
import { Compass, Navigation, TriangleAlert, X } from 'lucide-react';
import { RoutePlan } from '../../services/orcaApi';

/**
 * The passage card: what to steer, how long it takes, and what it went around.
 *
 * The heading shown is not the bearing to the destination — it is the heading
 * that *makes good* that bearing once the current has been allowed for. A boat
 * that steers straight at its target in a cross-current arrives somewhere else,
 * and this is the one place in ORCA that says so.
 */
interface OrcaRouteCardProps {
  plan: RoutePlan | null;
  loading: boolean;
  error: string | null;
  live: boolean;
  onClose: () => void;
}

const hazardLabel: Record<string, string> = {
  thunderstorm: 'thunderstorms',
  heavy_rain: 'heavy rain',
  moderate_rain: 'rain',
  fog: 'fog',
};

export const OrcaRouteCard: React.FC<OrcaRouteCardProps> = ({
  plan,
  loading,
  error,
  live,
  onClose,
}) => {
  if (loading) {
    return (
      <div className="absolute bottom-[80px] left-3 right-3 z-30 max-w-[620px] mx-auto rounded-2xl bg-white/95 border border-[#D0DFEB] shadow-lg p-4 animate-pulse">
        <div className="h-4 w-40 bg-[#E3EFF7] rounded mb-2" />
        <div className="h-3 w-56 bg-[#E3EFF7] rounded" />
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="absolute bottom-[80px] left-3 right-3 z-30 max-w-[620px] mx-auto rounded-2xl bg-white/95 border border-[#E2C9C9] shadow-lg p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-[#B45309]">
            <TriangleAlert size={17} className="stroke-[2.4] shrink-0" />
            <span className="font-ui font-semibold text-[14px]">
              {error ?? 'No route available'}
            </span>
          </div>
          <button type="button" onClick={onClose} aria-label="Close route" className="shrink-0">
            <X size={18} className="text-[#557186]" />
          </button>
        </div>
      </div>
    );
  }

  const { route, destination, origin } = plan;
  const first = route.legs[0];

  return (
    <section
      className="absolute bottom-[80px] left-3 right-3 z-30 max-w-[620px] mx-auto rounded-2xl bg-white/96 backdrop-blur-md border-2 border-[#0EA5E9] shadow-[0_8px_30px_rgba(6,42,67,0.18)] p-3.5 flex flex-col gap-2"
      id="orca-route-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Navigation size={17} className="stroke-[2.5] text-[#0369A1] shrink-0" />
          <span className="font-ui font-bold text-[14.5px] text-[#062A43] truncate">
            To {destination.landingCentre ?? 'the fishing ground'}
          </span>
        </div>
        <button type="button" onClick={onClose} aria-label="Close route" className="shrink-0">
          <X size={18} className="text-[#557186]" />
        </button>
      </div>

      {/* The heading that actually makes the course good. */}
      {first && (
        <div className="flex items-center gap-2 font-ui text-[13.5px] text-[#0B4A34] bg-[#EBF7EE] border border-[#A6DDB6] rounded-xl px-2.5 py-2">
          <Compass size={15} className="stroke-[2.4] shrink-0" />
          <span>
            Steer <span className="font-bold">{first.headingDeg}°</span> ({first.headingCompass})
            {first.currentSpeedMs != null && first.headingDeg !== first.courseDeg && (
              <>
                {' '}— {Math.abs(first.headingDeg - first.courseDeg)}° into the current
              </>
            )}
          </span>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 font-ui text-center">
        <div className="rounded-lg bg-[#F0F6FA] py-1.5">
          <div className="text-[15px] font-bold text-[#062A43]">{route.totalDistanceKm} km</div>
          <div className="text-[10.5px] text-[#557186]">to run</div>
        </div>
        <div className="rounded-lg bg-[#F0F6FA] py-1.5">
          <div className="text-[15px] font-bold text-[#062A43]">
            {route.totalHours.toFixed(1)} h
          </div>
          <div className="text-[10.5px] text-[#557186]">one way</div>
        </div>
        <div className="rounded-lg bg-[#F0F6FA] py-1.5">
          <div className="text-[15px] font-bold text-[#062A43]">
            {first ? `${first.speedOverGroundKmh}` : '—'}
          </div>
          <div className="text-[10.5px] text-[#557186]">km/h made good</div>
        </div>
      </div>

      {route.avoided.length > 0 && (
        <div className="font-ui text-[12px] text-[#991B1B] bg-[#FEF2F2] border border-[#F0A9A9] rounded-lg px-2.5 py-1.5">
          Routed {route.detourKm} km around{' '}
          {route.avoided.map((h) => hazardLabel[h] ?? h).join(', ')} — the direct line is{' '}
          {route.directDistanceKm} km.
        </div>
      )}

      {!origin.atSea && origin.nearestLandingCentre && (
        <div className="font-ui text-[11.5px] text-[#0C587F]">
          Starting from {origin.nearestLandingCentre} — the nearest landing centre to you, not
          your exact position.
        </div>
      )}

      <div className="font-ui text-[10.5px] text-[#6B7C8A] leading-[1.3]">
        {live ? 'Following your live position. ' : 'Boat shown is a preview, not a live fix. '}
        {route.assumption}
      </div>

      {/*
        The current data behind these headings is modelled at ~8 km and its own
        provider states it "is not suitable for coastal navigation and does not
        replace your nautical almanac". Giving someone a heading to steer
        without passing that on would be the worst kind of false confidence, so
        it sits on the card itself rather than buried in a docstring.
      */}
      <div className="font-ui text-[10.5px] text-[#92400E] bg-[#FFFBEB] border border-[#F5D68B] rounded-lg px-2.5 py-1.5 leading-[1.35]">
        Planning guide only — currents are modelled at about 8 km and are unreliable close
        to shore. This does not replace your own judgement, a chart or an almanac.
      </div>
    </section>
  );
};
