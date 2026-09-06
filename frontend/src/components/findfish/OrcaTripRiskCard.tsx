import React from 'react';
import { Clock, ShieldAlert, ShieldCheck, TriangleAlert } from 'lucide-react';
import { RiskResult } from '../../services/orcaApi';

/**
 * The combined "should I go, and can I get back?" verdict.
 *
 * The other cards on this page each answer half the question: INCOIS says where
 * the fish are, the forecast says when the sea turns. Neither notices that an
 * advised ground 60 km offshore is a nine-hour round trip that will not fit
 * inside a three-hour weather window. This card is the only place that does.
 *
 * The boat speed behind the timing is an assumption, and the card says so
 * rather than presenting an estimate as a measurement.
 */
interface OrcaTripRiskCardProps {
  risk: RiskResult | null;
  loading: boolean;
}

const STYLES: Record<string, { bg: string; border: string; text: string; Icon: typeof ShieldCheck }> = {
  low: { bg: 'bg-[#F0FDF4]', border: 'border-[#A6DDB6]', text: 'text-[#166534]', Icon: ShieldCheck },
  moderate: { bg: 'bg-[#FFFBEB]', border: 'border-[#F5D68B]', text: 'text-[#92400E]', Icon: ShieldAlert },
  high: { bg: 'bg-[#FFF7ED]', border: 'border-[#F3C48B]', text: 'text-[#9A3412]', Icon: TriangleAlert },
  severe: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]', Icon: TriangleAlert },
};

export const OrcaTripRiskCard: React.FC<OrcaTripRiskCardProps> = ({ risk, loading }) => {
  if (loading || !risk) {
    return (
      <div className="w-full rounded-2xl bg-white border border-[#D5E4EE] shadow-sm p-4 animate-pulse">
        <div className="h-4 w-32 bg-[#E3EFF7] rounded mb-2" />
        <div className="h-3 w-52 bg-[#E3EFF7] rounded" />
      </div>
    );
  }

  const data = risk.data ?? ({} as RiskResult['data']);
  const style = STYLES[data.level] ?? STYLES.moderate;
  const { Icon } = style;
  const trip = data.trip ?? {};
  const hasTiming = trip.roundTripHours != null && data.safeHours != null;
  const dangerous = data.level === 'severe' || data.level === 'high';

  return (
    <section
      className={`w-full rounded-2xl ${style.bg} border ${style.border} shadow-sm p-4 flex flex-col gap-2.5`}
      id="orca-trip-risk-card"
      aria-label="Overall trip risk"
    >
      <div className={`flex items-center gap-2 font-ui font-bold text-[15px] ${style.text}`}>
        <Icon size={17} className="stroke-[2.5] shrink-0" />
        <span>{data.headline ?? 'Trip risk'}</span>
      </div>

      <p className="font-ui text-[13.5px] text-[#2C4A5E] leading-[1.45]">{risk.summary}</p>

      {hasTiming && (
        <div className="flex flex-col gap-1 pt-2 border-t border-black/5">
          <div className="flex items-center gap-2 font-ui text-[13px] text-[#2C4A5E]">
            <Clock size={14} className="stroke-[2.4] shrink-0 text-[#557186]" />
            <span>
              <span className="font-semibold">{trip.distanceKm} km</span> out ·{' '}
              <span className="font-semibold">~{trip.roundTripHours} h</span> round trip ·
              conditions hold <span className="font-semibold">{data.safeHours} h</span>
            </span>
          </div>

          {/*
            Reachability is only good news when nothing else is wrong. Next to a
            "do not go" verdict, a green "you can be back in time" reads as
            encouragement to sail into a thunderstorm, so on the dangerous
            levels the same fact is stated plainly and the risk keeps the floor.
          */}
          <div
            className={`font-ui text-[12.5px] font-semibold ${
              !trip.reachable
                ? 'text-[#991B1B]'
                : dangerous
                  ? 'text-[#6B7C8A]'
                  : 'text-[#166534]'
            }`}
          >
            {!trip.reachable
              ? 'You cannot get there and back before conditions turn.'
              : dangerous
                ? 'The distance itself is manageable — but the risk above still stands.'
                : 'You can reach it and be back before conditions turn.'}
          </div>

          <div className="font-ui text-[10.5px] text-[#6B7C8A] leading-[1.3]">
            Assumes about {trip.assumedSpeedKmh} km/h and {trip.fishingHours} h fishing — a
            slower boat has less margin.
          </div>
        </div>
      )}
    </section>
  );
};
