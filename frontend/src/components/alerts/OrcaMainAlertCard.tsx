import React from 'react';
import { AlertTriangle, AlertOctagon, Info, CheckCircle2, Clock } from 'lucide-react';
import { AlertItem, AlertSeverity } from '../../data/alertsData';

interface OrcaMainAlertCardProps {
  alert: AlertItem | null;
  severity: AlertSeverity;
  onSeverityChange?: (severity: AlertSeverity) => void;
  stateSimulatorLabel?: string;
  noAlertsTitle?: string;
  noAlertsSubtitle?: string;
}

export const OrcaMainAlertCard: React.FC<OrcaMainAlertCardProps> = ({
  alert,
  severity,
  onSeverityChange,
  stateSimulatorLabel = 'Alert state:',
  noAlertsTitle = 'No important alerts',
  noAlertsSubtitle = 'Sea conditions look normal near you.',
}) => {
  // If NO ALERTS state
  if (severity === 'none' || !alert) {
    return (
      <section
        className="w-full rounded-2xl sm:rounded-3xl p-5 min-[390px]:p-6 sm:p-7 border-2 bg-[#EBF7EE] border-[#A6DDB6] shadow-md transition-all duration-200 select-none"
        id="orca-main-alert-none"
        aria-label="No Important Alerts"
      >
        <div className="flex flex-col items-start gap-3.5">
          {/* Checkmark icon & badge */}
          <div className="w-full flex items-center justify-between gap-2">
            <div
              className="w-12 h-12 min-[390px]:w-14 min-[390px]:h-14 rounded-2xl bg-[#DCFCE7] border border-[#86EFAC] text-[#15803D] flex items-center justify-center shadow-xs shrink-0"
              aria-hidden="true"
            >
              <CheckCircle2 size={32} className="stroke-[2.5]" />
            </div>

            <div
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#86EFAC] bg-[#DCFCE7] text-[#15803D] text-[13px] min-[390px]:text-[14px] font-ui font-extrabold tracking-tight shadow-2xs"
              role="status"
            >
              <span>Normal conditions</span>
            </div>
          </div>

          {/* Title */}
          <div className="w-full mt-1">
            <h2 className="font-display font-extrabold text-[32px] min-[390px]:text-[38px] sm:text-[42px] text-[#062A43] leading-[1.05] tracking-tight">
              {noAlertsTitle}
            </h2>
            <p className="font-ui font-semibold text-[16px] min-[390px]:text-[18px] text-[#15803D] mt-1.5 leading-snug">
              “{noAlertsSubtitle}”
            </p>
          </div>

          {/* Updated timestamp */}
          <div className="w-full pt-2 flex items-center justify-between border-t border-black/5 text-[12px] min-[390px]:text-[12.5px] text-[#5A7385] font-ui font-medium">
            <span>Digha, West Bengal</span>
            <span>Updated 10 mins ago</span>
          </div>
        </div>

        {/* State Simulator Switcher */}
        {onSeverityChange && (
          <div className="mt-3.5 pt-3 border-t border-black/8 flex items-center justify-between gap-2 flex-wrap text-[11px] text-[#557186]">
            <span className="font-ui font-medium shrink-0">{stateSimulatorLabel}</span>
            <div className="inline-flex items-center gap-1 bg-white/70 p-1 rounded-lg border border-black/10">
              <button
                type="button"
                onClick={() => onSeverityChange('high')}
                className="px-2 py-0.5 rounded-md font-ui font-bold text-[#DC2626] hover:bg-black/5 transition-all cursor-pointer"
              >
                High
              </button>
              <button
                type="button"
                onClick={() => onSeverityChange('caution')}
                className="px-2 py-0.5 rounded-md font-ui font-bold text-[#A16207] hover:bg-black/5 transition-all cursor-pointer"
              >
                Caution
              </button>
              <button
                type="button"
                onClick={() => onSeverityChange('update')}
                className="px-2 py-0.5 rounded-md font-ui font-bold text-[#15803D] hover:bg-black/5 transition-all cursor-pointer"
              >
                Update
              </button>
              <button
                type="button"
                onClick={() => onSeverityChange('none')}
                className="px-2 py-0.5 rounded-md font-ui font-bold bg-[#15803D] text-white shadow-xs transition-all cursor-pointer"
              >
                None
              </button>
            </div>
          </div>
        )}
      </section>
    );
  }

  // Active Warning States: High Alert | Caution | Update
  const isHigh = alert.severity === 'high';
  const isCaution = alert.severity === 'caution';

  const cardBgClass = isHigh
    ? 'bg-[#FEF2F2] border-[#FCA5A5]'
    : isCaution
    ? 'bg-[#FEFCE8] border-[#FDE047]'
    : 'bg-[#EBF7EE] border-[#A6DDB6]';

  const badgeBgClass = isHigh
    ? 'bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]'
    : isCaution
    ? 'bg-[#FEF9C3] text-[#854D0E] border-[#FDE047]'
    : 'bg-[#DCFCE7] text-[#15803D] border-[#86EFAC]';

  const iconCircleBg = isHigh
    ? 'bg-white/90 text-[#DC2626] border-[#FCA5A5]'
    : isCaution
    ? 'bg-white/90 text-[#A16207] border-[#FDE047]'
    : 'bg-white/90 text-[#15803D] border-[#A6DDB6]';

  const textColorClass = isHigh
    ? 'text-[#991B1B]'
    : isCaution
    ? 'text-[#854D0E]'
    : 'text-[#166534]';

  return (
    <section
      className={`relative w-full rounded-2xl sm:rounded-3xl p-5 min-[390px]:p-6 sm:p-7 border-2 shadow-md transition-all duration-200 select-none ${cardBgClass}`}
      id="orca-main-alert-card"
      aria-label="Most Important Sea Alert"
    >
      <div className="flex flex-col items-start gap-3 sm:gap-4">
        {/* Top line: Alert Icon + Severity Badge */}
        <div className="w-full flex items-center justify-between gap-2">
          {/* Warning Icon Container */}
          <div
            className={`w-12 h-12 min-[390px]:w-14 min-[390px]:h-14 rounded-2xl border flex items-center justify-center shadow-xs shrink-0 ${iconCircleBg}`}
            aria-hidden="true"
          >
            {isHigh ? (
              <AlertOctagon size={32} className="stroke-[2.5]" />
            ) : isCaution ? (
              <AlertTriangle size={32} className="stroke-[2.5]" />
            ) : (
              <Info size={32} className="stroke-[2.5]" />
            )}
          </div>

          {/* Severity Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full border text-[13px] min-[390px]:text-[14px] font-ui font-extrabold tracking-tight shadow-2xs ${badgeBgClass}`}
            role="status"
          >
            <span aria-hidden="true">{isHigh ? '⚠️' : isCaution ? '🟠' : '🟢'}</span>
            <span>{alert.badgeLabel}</span>
          </div>
        </div>

        {/* 
          IMPORTANT MESSAGE: VERY LARGE
          "Strong winds expected after 2 PM"
          Immediate 2–3 second comprehension
        */}
        <div className="w-full mt-1 flex flex-col items-start">
          <h2
            className="font-display font-extrabold text-[30px] min-[390px]:text-[34px] sm:text-[40px] text-[#062A43] leading-[1.1] tracking-tight"
            id="orca-main-alert-headline"
          >
            {alert.title}
          </h2>

          {/* Sub-action: Avoid going far offshore after 2 PM */}
          <p className={`font-ui font-bold text-[16px] min-[390px]:text-[18px] sm:text-[20px] mt-2 leading-[1.3] ${textColorClass}`}>
            “{alert.message}”
          </p>
        </div>

        {/* Timestamp */}
        <div className="w-full pt-2 flex items-center justify-between border-t border-black/5 text-[12px] min-[390px]:text-[12.5px] text-[#5A7385] font-ui font-medium">
          <span>Digha, West Bengal</span>
          <div className="inline-flex items-center gap-1">
            <Clock size={12} className="stroke-[2]" />
            <span>{alert.timeAgo}</span>
          </div>
        </div>
      </div>

      {/* 
        Interactive state simulator to test all requested states:
        HIGH ALERT | CAUTION | UPDATE | NO ALERTS
      */}
      {onSeverityChange && (
        <div className="mt-3.5 pt-3 border-t border-black/8 flex items-center justify-between gap-2 flex-wrap text-[11px] text-[#557186]">
          <span className="font-ui font-medium shrink-0">{stateSimulatorLabel}</span>
          <div className="inline-flex items-center gap-1 bg-white/70 p-1 rounded-lg border border-black/10">
            <button
              type="button"
              onClick={() => onSeverityChange('high')}
              aria-label="Set state to High Alert"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                isHigh ? 'bg-[#DC2626] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              High
            </button>
            <button
              type="button"
              onClick={() => onSeverityChange('caution')}
              aria-label="Set state to Caution"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                isCaution ? 'bg-[#CA8A04] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              Caution
            </button>
            <button
              type="button"
              onClick={() => onSeverityChange('update')}
              aria-label="Set state to Update"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                severity === 'update' ? 'bg-[#15803D] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              Update
            </button>
            <button
              type="button"
              onClick={() => onSeverityChange('none')}
              aria-label="Set state to No Alert"
              className={`px-2 py-0.5 rounded-md font-ui font-bold transition-all cursor-pointer ${
                severity === 'none' ? 'bg-[#15803D] text-white shadow-xs' : 'text-[#062A43] hover:bg-black/5'
              }`}
            >
              None
            </button>
          </div>
        </div>
      )}
    </section>
  );
};
