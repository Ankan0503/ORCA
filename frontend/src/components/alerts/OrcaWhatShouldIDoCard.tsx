import React from 'react';
import { Compass, ShieldCheck, AlertCircle } from 'lucide-react';
import { AlertSeverity } from '../../data/alertsData';

interface OrcaWhatShouldIDoCardProps {
  title?: string;
  actionText: string;
  severity: AlertSeverity;
}

export const OrcaWhatShouldIDoCard: React.FC<OrcaWhatShouldIDoCardProps> = ({
  title = 'What should I do?',
  actionText,
  severity,
}) => {
  const isHigh = severity === 'high';
  const isNone = severity === 'none';

  const cardStyle = isHigh
    ? 'bg-[#FEF2F2] border-[#FCA5A5]'
    : isNone
    ? 'bg-[#EBF7EE] border-[#A6DDB6]'
    : 'bg-[#FEFCE8] border-[#FDE047]';

  const iconBg = isHigh
    ? 'bg-[#FEE2E2] text-[#DC2626]'
    : isNone
    ? 'bg-[#DCFCE7] text-[#15803D]'
    : 'bg-[#FEF9C3] text-[#A16207]';

  const titleColor = isHigh
    ? 'text-[#991B1B]'
    : isNone
    ? 'text-[#15803D]'
    : 'text-[#854D0E]';

  const textColor = isHigh
    ? 'text-[#7F1D1D]'
    : isNone
    ? 'text-[#1E4631]'
    : 'text-[#713F12]';

  return (
    <section
      className={`w-full p-4 min-[390px]:p-4.5 sm:p-5 rounded-2xl border-2 shadow-xs flex items-start gap-3.5 select-none transition-all ${cardStyle}`}
      role="region"
      aria-label="Action advice"
      id="orca-what-should-i-do-card"
    >
      {/* Visual icon */}
      <div
        className={`w-10 h-10 min-[390px]:w-11 min-[390px]:h-11 rounded-xl flex items-center justify-center shrink-0 shadow-2xs ${iconBg}`}
      >
        {isHigh ? (
          <AlertCircle size={22} className="stroke-[2.5]" />
        ) : isNone ? (
          <ShieldCheck size={22} className="stroke-[2.5]" />
        ) : (
          <Compass size={22} className="stroke-[2.5]" />
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col min-w-0">
        <h3 className={`font-ui font-extrabold text-[15px] min-[390px]:text-[16px] leading-tight ${titleColor}`}>
          {title}
        </h3>
        <p className={`font-ui font-bold text-[14px] min-[390px]:text-[15.5px] sm:text-[16px] leading-[1.35] mt-1 ${textColor}`}>
          “{actionText}”
        </p>
      </div>
    </section>
  );
};
