import React from 'react';
import { ShieldCheck, ShieldAlert, TriangleAlert, Anchor } from 'lucide-react';
import { GeofenceResult } from '../../services/orcaApi';

/**
 * Live maritime-boundary status for the user's position.
 *
 * Crossing into Sri Lankan or Pakistani waters is one of the commonest ways
 * Indian fishermen are arrested, and it happens by drift far more often than by
 * intent. This badge keeps the distance to the nearest foreign boundary — and
 * whose it is — permanently in view.
 *
 * The distances behind the colours are ORCA's own caution margins, not a legal
 * limit; the badge says so on the warning states rather than implying an
 * official ruling.
 */
interface OrcaBoundaryBadgeProps {
  geofence: GeofenceResult | null;
  loading: boolean;
}

const STYLES: Record<string, { bg: string; border: string; text: string }> = {
  critical: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]' },
  outside: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]' },
  beyond_eez: { bg: 'bg-[#FEF2F2]', border: 'border-[#F0A9A9]', text: 'text-[#991B1B]' },
  warning: { bg: 'bg-[#FFFBEB]', border: 'border-[#F5D68B]', text: 'text-[#92400E]' },
  watch: { bg: 'bg-[#F0F6FA]', border: 'border-[#BED6E6]', text: 'text-[#0C587F]' },
  clear: { bg: 'bg-[#F0FDF4]', border: 'border-[#A6DDB6]', text: 'text-[#166534]' },
  not_at_sea: { bg: 'bg-[#F0F6FA]', border: 'border-[#BED6E6]', text: 'text-[#0C587F]' },
};

export const OrcaBoundaryBadge: React.FC<OrcaBoundaryBadgeProps> = ({ geofence, loading }) => {
  if (loading || !geofence) {
    return (
      <div className="absolute bottom-[178px] sm:bottom-[190px] left-3 sm:left-4 right-3 sm:right-4 z-20 pointer-events-none max-w-[620px] mx-auto">
        <div className="rounded-xl bg-white/95 border border-[#D0DFEB] shadow-md px-2.5 py-1.5 font-ui text-[11.5px] text-[#557186]">
          Checking waters…
        </div>
      </div>
    );
  }

  const style = STYLES[geofence.level] ?? STYLES.watch;
  const alarming =
    geofence.level === 'critical' ||
    geofence.level === 'outside' ||
    geofence.level === 'beyond_eez';
  const Icon = alarming
    ? TriangleAlert
    : geofence.level === 'warning'
      ? ShieldAlert
      : geofence.level === 'not_at_sea'
        ? Anchor
        : ShieldCheck;

  const nearest = geofence.nearestBoundary;

  const headline = geofence.insideEez
    ? 'Inside India’s EEZ'
    : geofence.level === 'not_at_sea'
      ? 'In harbour / inshore'
      : geofence.level === 'beyond_eez'
        ? 'Beyond India’s EEZ'
        : 'Outside India’s EEZ';

  return (
    <div
      className="absolute bottom-[178px] sm:bottom-[190px] left-3 sm:left-4 right-3 sm:right-4 z-20 pointer-events-auto max-w-[620px] mx-auto"
      id="orca-boundary-badge"
    >
      <div
        className={`rounded-xl ${style.bg} border ${style.border} shadow-md px-3 py-2 flex items-center justify-between gap-3`}
        title={geofence.message}
      >
        <div className="flex flex-col gap-0.5 min-w-0">
          <div className={`flex items-center gap-1.5 font-ui font-bold text-[12.5px] ${style.text}`}>
            <Icon size={14} className="stroke-[2.5] shrink-0" />
            <span className="truncate">{headline}</span>
          </div>
          {(geofence.level === 'critical' || geofence.level === 'warning') && (
            <span className="font-ui text-[10px] text-[#6B7C8A] leading-[1.25]">
              ORCA caution margin, not a legal limit
            </span>
          )}
        </div>

        {nearest && (
          <div className="font-ui text-[11.5px] text-[#3E5C70] leading-[1.3] text-right shrink-0">
            <div className="font-semibold">{nearest.neighbour}</div>
            <div>
              {nearest.distanceKm} km {nearest.bearing}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
