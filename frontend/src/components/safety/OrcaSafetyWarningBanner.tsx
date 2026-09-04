import React from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { SafetyWarning } from '../../data/safetyData';

interface OrcaSafetyWarningBannerProps {
  warning: SafetyWarning | null;
  noWarningTitle?: string;
  noWarningSubtitle?: string;
}

export const OrcaSafetyWarningBanner: React.FC<OrcaSafetyWarningBannerProps> = ({
  warning,
  noWarningTitle = 'No active warnings',
  noWarningSubtitle = 'All clear across Digha coastal waters.',
}) => {
  // 1. ACTIVE WARNING STATE: Prominent pale red card
  if (warning) {
    return (
      <section
        className="w-full mt-5 select-none"
        id="orca-safety-warning-banner"
        aria-label="Active Weather Warning"
      >
        <div className="w-full rounded-[20px] bg-[#FDECEB] border border-[#F7C4C0] p-4 min-[390px]:p-5 shadow-[0_4px_16px_rgba(239,68,68,0.1)] flex flex-col gap-2">
          {/* Header row with alert icon and badge */}
          <div className="flex items-center gap-2">
            <span className="w-7 h-7 rounded-full bg-[#FCA5A5]/40 flex items-center justify-center shrink-0">
              <AlertTriangle className="w-4 h-4 text-[#B91C1C] stroke-[2.4]" />
            </span>
            <span className="font-ui font-bold text-[13px] min-[390px]:text-[14px] text-[#991B1B] tracking-wide uppercase">
              ⚠️ {warning.title}
            </span>
            {warning.activeFrom && (
              <span className="ml-auto font-ui text-[11px] font-semibold text-[#991B1B] bg-white/70 px-2 py-0.5 rounded-full">
                {warning.activeFrom}
              </span>
            )}
          </div>

          {/* Warning Summary & Practical Advisory */}
          <div className="flex flex-col gap-1 pl-9">
            <p className="font-ui font-bold text-[15px] min-[390px]:text-[16px] text-[#991B1B] leading-snug">
              {warning.summary}
            </p>
            <p className="font-ui font-medium text-[13.5px] min-[390px]:text-[14px] text-[#7F1D1D] leading-normal">
              {warning.advisory}
            </p>
          </div>
        </div>
      </section>
    );
  }

  // 2. NO WARNING STATE: Compact and reassuring
  return (
    <section
      className="w-full mt-4 sm:mt-5 select-none"
      id="orca-safety-no-warning-banner"
      aria-label="No active warnings"
    >
      <div className="w-full rounded-[16px] bg-[#EBF7EE] border border-[#C9EBD2] px-4 py-3 flex items-center justify-between gap-3 shadow-2xs">
        <div className="flex items-center gap-2.5 min-w-0">
          <CheckCircle2 className="w-5 h-5 text-[#16A34A] shrink-0 stroke-[2.3]" />
          <div className="flex flex-col min-w-0">
            <span className="font-ui font-semibold text-[13px] min-[390px]:text-[13.5px] text-[#166534] leading-tight truncate">
              ✓ {noWarningTitle}
            </span>
            <span className="font-ui font-normal text-[11.5px] min-[390px]:text-[12px] text-[#2D5A40] leading-tight truncate">
              {noWarningSubtitle}
            </span>
          </div>
        </div>
        <span className="font-ui font-medium text-[11px] text-[#15803D] bg-white/80 px-2.5 py-0.5 rounded-full shrink-0 border border-[#C9EBD2]">
          Coast Clear
        </span>
      </div>
    </section>
  );
};
