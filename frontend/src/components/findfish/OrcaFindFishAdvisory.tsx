import React from 'react';
import { ArrowRight, Compass, Info, Waves } from 'lucide-react';
import { FindFishTranslations } from '../../data/findFishData';
import { PfzAdvisory, PfzPoint } from '../../services/orcaApi';

/**
 * The real INCOIS Potential Fishing Zone advisory for the user's coast.
 *
 * This replaces the earlier invented "best spot" numbers on the Find Fish page.
 * Every value shown here — landing centre, offshore distance, depth, bearing,
 * position — is the Indian government's own daily advisory, fetched by the
 * backend from INCOIS. The card is deliberately honest about its states: a real
 * "no advisory today", a stale fallback, and a fetch failure each look
 * different, so a fisherman is never shown a confident number that isn't real.
 */
interface OrcaFindFishAdvisoryProps {
  advisory: PfzAdvisory | null;
  loading: boolean;
  error: string | null;
  translations: FindFishTranslations;
  onGoHere: (point: PfzPoint) => void;
}

const formatOffshore = (p: PfzPoint): string => {
  if (p.distance_km_from == null || p.distance_km_to == null) {
    return p.range_km != null ? `~${p.range_km} km` : '';
  }
  return `${p.distance_km_from}–${p.distance_km_to} km offshore`;
};

const formatDepth = (p: PfzPoint): string | null => {
  if (p.depth_m_from == null || p.depth_m_to == null) return null;
  return `${p.depth_m_from}–${p.depth_m_to} m deep`;
};

const formatBearing = (p: PfzPoint): string =>
  p.bearing_deg != null ? `${p.direction} (${p.bearing_deg}°)` : p.direction;

export const OrcaFindFishAdvisory: React.FC<OrcaFindFishAdvisoryProps> = ({
  advisory,
  loading,
  error,
  translations,
  onGoHere,
}) => {
  /* ---- Loading ---- */
  if (loading) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl p-6 bg-[#EBF7EE] border-2 border-[#A6DDB6] animate-pulse">
        <div className="h-4 w-40 bg-[#C7E6D2] rounded mb-4" />
        <div className="h-9 w-56 bg-[#C7E6D2] rounded mb-2" />
        <div className="h-4 w-48 bg-[#C7E6D2] rounded" />
      </div>
    );
  }

  /* ---- INCOIS unreachable, nothing cached ---- */
  if (error || !advisory) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl p-5 sm:p-6 bg-white border border-[#E2C9C9] shadow-sm">
        <div className="flex items-center gap-2 text-[#B45309]">
          <Info size={18} className="stroke-[2.4]" />
          <span className="font-ui font-semibold text-[15px]">
            INCOIS advisory unavailable right now
          </span>
        </div>
        <p className="font-ui text-[13.5px] text-[#557186] mt-1.5 leading-[1.4]">
          Couldn’t reach the government fishing-zone service. Please check again shortly —
          nothing here is invented in its place.
        </p>
      </div>
    );
  }

  /* ---- Real "no PFZ issued for this coast today" ---- */
  if (advisory.empty || advisory.points.length === 0) {
    return (
      <div className="w-full rounded-2xl sm:rounded-3xl p-5 sm:p-6 bg-white border border-[#D5E4EE] shadow-sm">
        <div className="flex items-center gap-2 text-[#0C587F]">
          <Info size={18} className="stroke-[2.4]" />
          <span className="font-ui font-semibold text-[15px]">
            No fishing-zone advisory today
          </span>
        </div>
        <p className="font-ui text-[13.5px] text-[#557186] mt-1.5 leading-[1.4]">
          INCOIS issued no Potential Fishing Zone for {advisory.sector_name}
          {advisory.forecast_date ? ` on ${advisory.forecast_date}` : ''} — usually because
          cloud cover hid the satellite. This is the real status, not a failure.
        </p>
      </div>
    );
  }

  const [best, ...rest] = advisory.points;
  const alternatives = rest.slice(0, 3);

  return (
    <div className="w-full flex flex-col gap-4">
      {/* Source + date strip — the credibility line */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] font-ui px-1">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[#0C587F] text-white font-semibold tracking-wide">
          INCOIS
        </span>
        <span className="text-[#557186]">
          Govt. Potential Fishing Zone · {advisory.sector_name}
        </span>
        {advisory.forecast_date && (
          <span className="text-[#557186]">
            · {advisory.forecast_date}
            {advisory.valid_upto ? ` → ${advisory.valid_upto}` : ''}
          </span>
        )}
        {advisory.stale && (
          <span className="text-[#B45309] font-semibold">· last available (offline)</span>
        )}
      </div>

      {/* Primary: nearest INCOIS zone */}
      <div
        className="relative w-full rounded-2xl sm:rounded-3xl p-5 min-[390px]:p-6 sm:p-7 bg-[#EBF7EE] border-2 border-[#A6DDB6] shadow-md select-none"
        id="orca-main-recommendation-card"
      >
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-white border border-[#A6DDB6] flex items-center justify-center text-2xl shadow-xs shrink-0">
            <span role="img" aria-label="Fishing hook and fish">🎣</span>
          </div>
          <span className="inline-flex items-center px-3 py-1 rounded-full bg-[#15803D] text-white font-ui font-extrabold text-[12px] tracking-wider uppercase shadow-xs">
            {translations.bestAreaBadge}
          </span>
        </div>

        <div className="mt-4 flex flex-col items-start">
          <h2 className="font-display font-bold text-[30px] min-[390px]:text-[34px] sm:text-[40px] text-[#062A43] leading-[1.05] tracking-tight">
            {formatOffshore(best)}
          </h2>
          <p className="font-ui font-bold text-[17px] sm:text-[19px] text-[#15803D] mt-1.5">
            Off {best.landing_centre}
          </p>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 font-ui text-[14px] text-[#244A37]">
            <span className="inline-flex items-center gap-1.5">
              <Compass size={15} className="stroke-[2.4]" /> {formatBearing(best)}
            </span>
            {formatDepth(best) && (
              <span className="inline-flex items-center gap-1.5">
                <Waves size={15} className="stroke-[2.4]" /> {formatDepth(best)}
              </span>
            )}
          </div>

          <p className="font-ui text-[12.5px] text-[#4A677B] mt-1.5">
            {best.latitude_dms} · {best.longitude_dms}
          </p>
        </div>

        <div className="mt-5 pt-4 border-t border-[#A6DDB6]/60">
          <button
            type="button"
            onClick={() => onGoHere(best)}
            className="w-full h-12 sm:h-14 px-6 rounded-xl sm:rounded-2xl bg-[#0B4A34] text-white hover:bg-[#073625] active:scale-[0.98] shadow-md transition-all flex items-center justify-center gap-3 cursor-pointer"
          >
            <span className="font-ui font-bold text-[16px] tracking-wide uppercase">
              {translations.goHereBtn}
            </span>
            <ArrowRight size={20} className="stroke-[2.8]" />
          </button>
        </div>
      </div>

      {/* Alternatives: the remaining INCOIS zones */}
      {alternatives.length > 0 && (
        <section className="w-full flex flex-col gap-2.5">
          <h3 className="font-ui font-semibold text-[14px] text-[#4A677B] tracking-tight uppercase px-1">
            {translations.otherOptionsTitle}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {alternatives.map((point, i) => (
              <button
                key={`${point.landing_centre}-${i}`}
                type="button"
                onClick={() => onGoHere(point)}
                className="w-full text-left p-3.5 rounded-xl bg-white/90 border border-[#D5E4EE] hover:border-[#BED6E6] hover:bg-white active:scale-[0.99] shadow-2xs transition-all flex items-center justify-between gap-3 cursor-pointer group"
              >
                <div className="flex flex-col items-start min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#EAB308] shrink-0" />
                    <span className="font-display font-bold text-[17px] text-[#062A43] leading-none">
                      {formatOffshore(point)}
                    </span>
                  </div>
                  <span className="font-ui text-[13px] text-[#557186] font-medium mt-1 truncate max-w-[180px]">
                    Off {point.landing_centre}
                  </span>
                  <span className="font-ui text-[12px] font-semibold text-[#1677A8] mt-0.5">
                    {formatBearing(point)}
                    {formatDepth(point) ? ` · ${formatDepth(point)}` : ''}
                  </span>
                </div>
                <div className="w-8 h-8 rounded-full bg-[#F0F6FA] group-hover:bg-[#E3EFF7] flex items-center justify-center text-[#1677A8] shrink-0 transition-colors">
                  <ArrowRight size={16} />
                </div>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
