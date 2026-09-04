import React from 'react';
import { SeaStatus, SeaTodayData } from '../../data/seaTodayData';

interface OrcaSeaStatusCardProps {
  data: SeaTodayData;
  onStatusChange?: (status: SeaStatus) => void;
  testToggleLabel?: string;
}

export const OrcaSeaStatusCard: React.FC<OrcaSeaStatusCardProps> = ({
  data,
  onStatusChange,
  testToggleLabel = 'Sea state:',
}) => {
  const isCalm = data.seaStatus === 'calm';
  const isModerate = data.seaStatus === 'moderate';
  const isRough = data.seaStatus === 'rough';

  // Card theme styling according to prompt specifications:
  // - pale blue/green background for calm
  // - pale yellow for moderate
  // - pale red for rough
  const cardBgClass = isCalm
    ? 'bg-[#EBF7EE] border-[#A6DDB6]'
    : isModerate
    ? 'bg-[#FEFCE8] border-[#FDE047]'
    : 'bg-[#FEF2F2] border-[#FCA5A5]';

  const badgeBgClass = isCalm
    ? 'bg-[#DCFCE7] text-[#15803D] border-[#86EFAC]'
    : isModerate
    ? 'bg-[#FEF9C3] text-[#854D0E] border-[#FDE047]'
    : 'bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]';

  const iconCircleBg = isCalm
    ? 'bg-white/80 text-[#15803D] border-[#A6DDB6]'
    : isModerate
    ? 'bg-white/80 text-[#A16207] border-[#FDE047]'
    : 'bg-white/80 text-[#DC2626] border-[#FCA5A5]';

  return (
    <section
      className={`relative w-full rounded-2xl sm:rounded-3xl p-5 min-[390px]:p-6 sm:p-7 border-2 shadow-md transition-all duration-200 select-none ${cardBgClass}`}
      id="orca-main-sea-status-card"
      aria-label="Main Sea Status"
    >
      <div className="flex flex-col items-start gap-3 sm:gap-4">
        {/* Top line: Wave Icon + Condition Badge */}
        <div className="w-full flex items-center justify-between gap-2">
          {/* Large Wave Icon container */}
          <div
            className={`w-12 h-12 min-[390px]:w-14 min-[390px]:h-14 rounded-2xl border flex items-center justify-center text-3xl sm:text-4xl shadow-xs shrink-0 ${iconCircleBg}`}
            aria-hidden="true"
          >
            🌊
          </div>

          {/* Condition Status Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[13px] min-[390px]:text-[14px] font-ui font-extrabold tracking-tight shadow-2xs ${badgeBgClass}`}
            role="status"
          >
            <span>{data.statusBadge}</span>
          </div>
        </div>

        {/* 
          MOST IMPORTANT INFORMATION:
          "CALM SEA" - Visually dominant, instant 3-second comprehension
        */}
        <div className="w-full mt-1 flex flex-col items-start">
          <h2
            className="font-display font-extrabold text-[36px] min-[390px]:text-[42px] sm:text-[48px] text-[#062A43] leading-[1] tracking-tight uppercase"
            id="orca-sea-status-headline"
          >
            {data.statusTitle}
          </h2>

          {/* Sub-status: "Good day for fishing" */}
          <p className="font-ui font-bold text-[18px] min-[390px]:text-[20px] sm:text-[22px] text-[#166534] mt-2 leading-[1.25]">
            {data.statusDescription}
          </p>
        </div>

        {/* Last updated note */}
        <div className="w-full pt-2 flex items-center justify-between border-t border-black/5 text-[12px] min-[390px]:text-[12.5px] text-[#5A7385] font-ui font-medium">
          <span>{data.location}</span>
          <span>Updated {data.updatedAgo}</span>
        </div>
      </div>

      {/* 
        Subtle state selector to test/verify dynamic states:
        CALM SEA | MODERATE SEA | ROUGH SEA
      */}
      {onStatusChange && (
        <div className="mt-3.5 pt-3 border-t border-black/8 flex items-center justify-between gap-2 flex-wrap text-[11px] text-[#557186]">
          <span className="font-ui font-medium shrink-0">{testToggleLabel}</span>
          <div className="inline-flex items-center gap-1 bg-white/70 p-1 rounded-lg border border-black/10">
            <button
              type="button"
              onClick={() => onStatusChange('calm')}
              aria-label="Set state to Calm Sea"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                isCalm ? 'bg-[#15803D] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              Calm
            </button>
            <button
              type="button"
              onClick={() => onStatusChange('moderate')}
              aria-label="Set state to Moderate Sea"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                isModerate ? 'bg-[#CA8A04] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              Moderate
            </button>
            <button
              type="button"
              onClick={() => onStatusChange('rough')}
              aria-label="Set state to Rough Sea"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                isRough ? 'bg-[#DC2626] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              Rough
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
