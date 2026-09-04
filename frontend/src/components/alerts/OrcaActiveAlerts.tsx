import React from 'react';
import { AlertTriangle, AlertOctagon, Info, ChevronRight, Waves, CloudRain } from 'lucide-react';
import { AlertItem } from '../../data/alertsData';

interface OrcaActiveAlertsProps {
  alerts: AlertItem[];
  title?: string;
  onAlertClick?: (alert: AlertItem) => void;
}

export const OrcaActiveAlerts: React.FC<OrcaActiveAlertsProps> = ({
  alerts,
  title = 'Active alerts',
  onAlertClick,
}) => {
  if (alerts.length === 0) return null;

  const renderIcon = (item: AlertItem) => {
    if (item.id.includes('wave')) {
      return <Waves size={20} className="stroke-[2.3]" />;
    }
    if (item.id.includes('rain')) {
      return <CloudRain size={20} className="stroke-[2.3]" />;
    }
    if (item.severity === 'high') {
      return <AlertOctagon size={20} className="stroke-[2.3]" />;
    }
    if (item.severity === 'caution') {
      return <AlertTriangle size={20} className="stroke-[2.3]" />;
    }
    return <Info size={20} className="stroke-[2.3]" />;
  };

  return (
    <section
      className="w-full flex flex-col gap-2.5 sm:gap-3 select-none"
      id="orca-active-alerts-section"
      aria-label="Active Sea Alerts"
    >
      <div className="flex items-center justify-between px-1">
        <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] text-[#062A43] tracking-tight">
          {title}
        </h3>
      </div>

      <div className="flex flex-col gap-2.5 sm:gap-3 w-full">
        {alerts.map((item) => {
          const isHigh = item.severity === 'high';
          const isCaution = item.severity === 'caution';

          const cardBg = isHigh
            ? 'bg-[#FEF2F2] border-[#FCA5A5]'
            : isCaution
            ? 'bg-[#FEFCE8] border-[#FDE047]'
            : 'bg-[#EBF7EE] border-[#A6DDB6]';

          const iconColor = isHigh
            ? 'bg-[#FEE2E2] text-[#DC2626]'
            : isCaution
            ? 'bg-[#FEF9C3] text-[#A16207]'
            : 'bg-[#DCFCE7] text-[#15803D]';

          const badgeBg = isHigh
            ? 'bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]'
            : isCaution
            ? 'bg-[#FEF9C3] text-[#854D0E] border-[#FDE047]'
            : 'bg-[#DCFCE7] text-[#15803D] border-[#86EFAC]';

          const dotEmoji = isHigh ? '🔴' : isCaution ? '🟠' : '🟢';

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onAlertClick?.(item)}
              id={`alert-card-${item.id}`}
              aria-label={`${item.badgeLabel}: ${item.title}`}
              className={`w-full text-left p-3.5 min-[390px]:p-4 rounded-2xl border flex items-center justify-between gap-3 shadow-2xs hover:shadow-sm transition-all duration-150 cursor-pointer active:scale-[0.99] ${cardBg}`}
            >
              {/* Left: Icon + Text */}
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div
                  className={`w-9 h-9 min-[390px]:w-10 min-[390px]:h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${iconColor}`}
                >
                  {renderIcon(item)}
                </div>

                <div className="flex flex-col min-w-0 flex-1">
                  {/* Badge & Time row */}
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-ui font-extrabold ${badgeBg}`}
                    >
                      <span aria-hidden="true">{dotEmoji}</span>
                      <span>{item.badgeLabel}</span>
                    </span>
                    <span className="text-[11.5px] text-[#557186] font-ui font-medium">
                      {item.timeAgo}
                    </span>
                  </div>

                  {/* Title */}
                  <h4 className="font-ui font-bold text-[15px] min-[390px]:text-[16px] text-[#062A43] leading-snug mt-1 truncate">
                    {item.title}
                  </h4>

                  {/* One short action / message */}
                  <p className="font-ui font-medium text-[13px] min-[390px]:text-[13.5px] text-[#425968] leading-tight mt-0.5 line-clamp-1">
                    “{item.message}”
                  </p>
                </div>
              </div>

              {/* Right Arrow */}
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-[#557186] shrink-0">
                <ChevronRight size={18} className="stroke-[2.5]" />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};
