import React from 'react';
import { Lightbulb, AlertTriangle, AlertOctagon } from 'lucide-react';

interface OrcaSeaTodayAdviceProps {
  advice: {
    title: string;
    quote: string;
    type: 'good' | 'caution' | 'danger';
  };
}

export const OrcaSeaTodayAdvice: React.FC<OrcaSeaTodayAdviceProps> = ({ advice }) => {
  const isGood = advice.type === 'good';
  const isCaution = advice.type === 'caution';
  const isDanger = advice.type === 'danger';

  const cardStyle = isGood
    ? 'bg-[#EBF7EE] border-[#A6DDB6]'
    : isCaution
    ? 'bg-[#FEFCE8] border-[#FDE047]'
    : 'bg-[#FEF2F2] border-[#FCA5A5]';

  const iconBg = isGood
    ? 'bg-[#DCFCE7] text-[#15803D]'
    : isCaution
    ? 'bg-[#FEF9C3] text-[#A16207]'
    : 'bg-[#FEE2E2] text-[#DC2626]';

  const titleColor = isGood
    ? 'text-[#15803D]'
    : isCaution
    ? 'text-[#854D0E]'
    : 'text-[#991B1B]';

  const quoteColor = isGood
    ? 'text-[#1E4631]'
    : isCaution
    ? 'text-[#713F12]'
    : 'text-[#7F1D1D]';

  return (
    <div
      className={`w-full p-4 min-[390px]:p-4.5 sm:p-5 rounded-2xl border-2 shadow-xs flex items-start gap-3.5 select-none transition-all ${cardStyle}`}
      role="note"
      aria-label="Important fisherman advice"
      id="orca-sea-today-advice-card"
    >
      {/* Visual icon */}
      <div
        className={`w-10 h-10 min-[390px]:w-11 min-[390px]:h-11 rounded-xl flex items-center justify-center shrink-0 shadow-2xs ${iconBg}`}
      >
        {isGood ? (
          <Lightbulb size={22} className="stroke-[2.5]" />
        ) : isCaution ? (
          <AlertTriangle size={22} className="stroke-[2.5]" />
        ) : (
          <AlertOctagon size={22} className="stroke-[2.5]" />
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col min-w-0">
        <h4 className={`font-ui font-extrabold text-[15px] min-[390px]:text-[16px] leading-tight ${titleColor}`}>
          {isGood ? '💡 ' : isCaution ? '⚠️ ' : '🔴 '}
          {advice.title}
        </h4>
        <p className={`font-ui font-bold text-[14px] min-[390px]:text-[15px] sm:text-[16px] leading-[1.35] mt-1 ${quoteColor}`}>
          {advice.quote}
        </p>
      </div>
    </div>
  );
};
