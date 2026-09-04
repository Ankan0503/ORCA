import React from 'react';
import { ShieldCheck, AlertTriangle, ShieldAlert, ArrowRight } from 'lucide-react';
import { SafetyData, SafetyStatus } from '../../data/safetyData';

interface OrcaSafetyHeroCardProps {
  data: SafetyData;
  onStateSelect?: (status: SafetyStatus) => void;
  statusChangeLabel?: string;
}

export const OrcaSafetyHeroCard: React.FC<OrcaSafetyHeroCardProps> = ({
  data,
  onStateSelect,
  statusChangeLabel = 'Safety Simulator',
}) => {
  const isSafe = data.status === 'safe';
  const isCaution = data.status === 'caution';
  const isDanger = data.status === 'danger';

  // State-specific visual styling
  const styleConfig = isSafe
    ? {
        cardBg: '#EBF7EE',
        cardBorder: '#C9EBD2',
        shadow: 'shadow-[0_6px_24px_rgba(34,197,94,0.12)]',
        badgeBg: '#D7F2DF',
        badgeText: '#0F5132',
        dotColor: 'bg-[#16A34A]',
        dotRing: 'shadow-[0_0_8px_rgba(22,163,74,0.6)]',
        titleColor: 'text-[#062A43]',
        riskColor: 'text-[#166534]',
        explanationColor: 'text-[#2D5A40]',
        iconBg: 'bg-[#D7F2DF]',
        iconBorder: 'border-[#B4E5C2]',
        iconColor: 'text-[#15803D]',
        arrowBg: 'bg-white',
        arrowColor: 'text-[#0F5132]',
      }
    : isCaution
    ? {
        cardBg: '#FEF7E6',
        cardBorder: '#F8E2AC',
        shadow: 'shadow-[0_6px_24px_rgba(234,179,8,0.14)]',
        badgeBg: '#FEF0C7',
        badgeText: '#854D0E',
        dotColor: 'bg-[#D97706]',
        dotRing: 'shadow-[0_0_8px_rgba(217,119,6,0.6)]',
        titleColor: 'text-[#062A43]',
        riskColor: 'text-[#92400E]',
        explanationColor: 'text-[#64441F]',
        iconBg: 'bg-[#FDE68A]',
        iconBorder: 'border-[#FCD34D]',
        iconColor: 'text-[#B45309]',
        arrowBg: 'bg-white',
        arrowColor: 'text-[#854D0E]',
      }
    : {
        cardBg: '#FDECEB',
        cardBorder: '#F7C4C0',
        shadow: 'shadow-[0_6px_24px_rgba(239,68,68,0.14)]',
        badgeBg: '#FEE2E2',
        badgeText: '#991B1B',
        dotColor: 'bg-[#DC2626]',
        dotRing: 'shadow-[0_0_8px_rgba(220,38,38,0.6)]',
        titleColor: 'text-[#062A43]',
        riskColor: 'text-[#B91C1C]',
        explanationColor: 'text-[#6D2829]',
        iconBg: 'bg-[#FCA5A5]/30',
        iconBorder: 'border-[#F87171]/40',
        iconColor: 'text-[#B91C1C]',
        arrowBg: 'bg-white',
        arrowColor: 'text-[#991B1B]',
      };

  return (
    <section
      className="relative z-10 w-full mt-4 sm:mt-5"
      id="orca-safety-result-section"
      aria-label="Primary safety decision"
    >
      {/* 
        ===================================================================
        PRIMARY SAFETY RESULT CARD
        - Visual Hierarchy:
          1. Large decision badge (🟢 SAFE TO GO / 🟡 BE CAREFUL / 🔴 DO NOT GO)
          2. Low risk today.
          3. Short explanation
        - Large rounded corners (22–24px)
        - Pale background, no heavy border, subtle shadow
        - Generous padding
        - Immediate 2-3 second comprehension
        ===================================================================
      */}
      <div
        id="orca-safety-primary-card"
        style={{
          backgroundColor: styleConfig.cardBg,
          borderColor: styleConfig.cardBorder,
        }}
        className={`relative w-full rounded-[22px] min-[390px]:rounded-[26px] p-5 min-[390px]:p-6 sm:p-7 border ${styleConfig.shadow} transition-all duration-300 flex flex-col justify-between overflow-hidden`}
      >
        {/* Top row: Status indicator + Large shield icon */}
        <div className="w-full flex items-start justify-between gap-3">
          {/* Status Badge */}
          <div
            className="inline-flex items-center gap-2 px-3.5 py-1.5 min-[390px]:px-4 min-[390px]:py-2 rounded-full border border-black/5"
            style={{ backgroundColor: styleConfig.badgeBg }}
          >
            <span
              className={`w-2.5 h-2.5 rounded-full ${styleConfig.dotColor} ${styleConfig.dotRing} shrink-0 animate-pulse`}
              aria-hidden="true"
            />
            <span
              className={`font-ui font-bold text-[13px] min-[390px]:text-[14px] sm:text-[15px] tracking-wide uppercase ${styleConfig.badgeText}`}
            >
              {data.statusLabel}
            </span>
          </div>

          {/* Large Shield Visual Icon */}
          <div
            className={`w-[54px] h-[54px] min-[390px]:w-[60px] min-[390px]:h-[60px] sm:w-[68px] sm:h-[68px] rounded-2xl ${styleConfig.iconBg} border ${styleConfig.iconBorder} flex items-center justify-center shrink-0 shadow-xs`}
            aria-hidden="true"
          >
            {isSafe ? (
              <ShieldCheck
                className={`w-[32px] h-[32px] min-[390px]:w-[36px] min-[390px]:h-[36px] sm:w-[40px] sm:h-[40px] ${styleConfig.iconColor} stroke-[2.3]`}
              />
            ) : isCaution ? (
              <AlertTriangle
                className={`w-[32px] h-[32px] min-[390px]:w-[36px] min-[390px]:h-[36px] sm:w-[40px] sm:h-[40px] ${styleConfig.iconColor} stroke-[2.3]`}
              />
            ) : (
              <ShieldAlert
                className={`w-[32px] h-[32px] min-[390px]:w-[36px] min-[390px]:h-[36px] sm:w-[40px] sm:h-[40px] ${styleConfig.iconColor} stroke-[2.3]`}
              />
            )}
          </div>
        </div>

        {/* 
          EXACT VISUAL HIERARCHY:
          1. SAFE TO GO (Large title)
          2. Low risk today. (Risk subhead)
        */}
        <div className="w-full flex flex-col items-start mt-3 sm:mt-4">
          <h2
            className={`font-display font-bold text-[32px] min-[390px]:text-[36px] sm:text-[42px] leading-[1.05] tracking-tight ${styleConfig.titleColor}`}
          >
            {data.statusLabel}
          </h2>

          <span
            className={`font-ui font-semibold text-[17px] min-[390px]:text-[18.5px] sm:text-[20px] ${styleConfig.riskColor} mt-1`}
          >
            {data.riskSubtitle}
          </span>
        </div>

        {/* Bottom indicator row: Action arrow + last updated timestamp */}
        <div className="w-full flex items-center justify-between gap-2 mt-4 pt-3.5 border-t border-black/5">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1677A8] shrink-0" />
            <span className="font-ui text-[12px] min-[390px]:text-[12.5px] text-[#4A677D] font-medium">
              Checked 12 mins ago
            </span>
          </div>

          <div
            className={`w-[36px] h-[36px] min-[390px]:w-[38px] min-[390px]:h-[38px] rounded-full ${styleConfig.arrowBg} border border-black/5 shadow-2xs flex items-center justify-center shrink-0`}
            aria-hidden="true"
          >
            <ArrowRight size={17} className={`${styleConfig.arrowColor} stroke-[2.4]`} />
          </div>
        </div>
      </div>

      {/* 
        Interactive State Selector:
        Allows users or testers to verify all 3 mandatory states (🟢 SAFE TO GO, 🟡 BE CAREFUL, 🔴 DO NOT GO)
      */}
      {onStateSelect && (
        <div
          className="w-full flex items-center justify-between flex-wrap gap-2 mt-2 px-1 text-xs text-[#527086]"
          aria-label="Safety condition state preview"
        >
          <span className="font-ui font-medium text-[11px] min-[390px]:text-[11.5px] text-[#527086]">
            {statusChangeLabel}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => onStateSelect('safe')}
              aria-label="Set state to Safe to Go"
              className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer ${
                isSafe
                  ? 'bg-[#16A34A] text-white shadow-xs'
                  : 'bg-white/80 text-[#166534] border border-[#C9EBD2] hover:bg-[#EBF7EE]'
              }`}
            >
              🟢 Safe
            </button>
            <button
              type="button"
              onClick={() => onStateSelect('caution')}
              aria-label="Set state to Be Careful"
              className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer ${
                isCaution
                  ? 'bg-[#D97706] text-white shadow-xs'
                  : 'bg-white/80 text-[#92400E] border border-[#F8E2AC] hover:bg-[#FEF7E6]'
              }`}
            >
              🟡 Caution
            </button>
            <button
              type="button"
              onClick={() => onStateSelect('danger')}
              aria-label="Set state to Do Not Go"
              className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer ${
                isDanger
                  ? 'bg-[#DC2626] text-white shadow-xs'
                  : 'bg-white/80 text-[#B91C1C] border border-[#F7C4C0] hover:bg-[#FDECEB]'
              }`}
            >
              🔴 Danger
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
