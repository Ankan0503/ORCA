import React from 'react';
import { Wind, Waves, CloudRain, Eye, ShieldAlert, Thermometer, ShieldCheck } from 'lucide-react';
import { ConditionItem } from '../../data/safetyData';

interface OrcaSafetyConditionsGridProps {
  conditions: ConditionItem[];
  title?: string;
}

export const OrcaSafetyConditionsGrid: React.FC<OrcaSafetyConditionsGridProps> = ({
  conditions,
  title = 'Current conditions',
}) => {
  const getIcon = (type: string, statusType: string) => {
    const iconClass = 'w-5 h-5 stroke-[2.2]';
    switch (type) {
      case 'wind':
        return <Wind className={`${iconClass} text-[#1677A8]`} />;
      case 'waves':
        return <Waves className={`${iconClass} text-[#0D9488]`} />;
      case 'rain':
        return <CloudRain className={`${iconClass} text-[#3B82F6]`} />;
      case 'visibility':
        return <Eye className={`${iconClass} text-[#6366F1]`} />;
      case 'warning':
        return statusType === 'good' ? (
          <ShieldCheck className={`${iconClass} text-[#15803D]`} />
        ) : (
          <ShieldAlert className={`${iconClass} text-[#D97706]`} />
        );
      case 'temperature':
        return <Thermometer className={`${iconClass} text-[#EA580C]`} />;
      default:
        return <Wind className={`${iconClass} text-[#1677A8]`} />;
    }
  };

  const getStatusBadgeStyle = (statusType: string) => {
    switch (statusType) {
      case 'good':
        return 'bg-[#EBF7EE] text-[#166534] border-[#C9EBD2]';
      case 'warning':
        return 'bg-[#FEF0C7] text-[#92400E] border-[#FCD34D]';
      case 'danger':
        return 'bg-[#FEE2E2] text-[#991B1B] border-[#FCA5A5]';
      case 'neutral':
      default:
        return 'bg-[#F1F5F9] text-[#334155] border-[#E2E8F0]';
    }
  };

  return (
    <section
      className="w-full mt-6 sm:mt-7 select-none"
      id="orca-safety-conditions-section"
      aria-label="Current Sea Conditions"
    >
      {/* Section Header */}
      <div className="w-full flex items-center justify-between mb-3 px-1">
        <h3 className="font-ui font-bold text-[18px] min-[390px]:text-[19px] sm:text-[20px] text-[#062A43] tracking-tight">
          {title}
        </h3>
        <span className="font-ui text-[12px] text-[#567389]">Open-Meteo marine forecast</span>
      </div>

      {/* 
        Clean 2-Column Grid (Cards):
        - Wind (12 km/h - Good)
        - Waves (0.8 m - Calm)
        - Rain (0 mm - No rain)
        - Visibility (10+ km - Good)
        - Weather warning (None - No active alerts)
        - Water temperature (28°C - Normal)
      */}
      <div className="grid grid-cols-2 gap-3 min-[390px]:gap-3.5 sm:gap-4">
        {conditions.map((item) => {
          return (
            <div
              key={item.id}
              className="bg-white rounded-[18px] min-[390px]:rounded-[20px] p-3.5 min-[390px]:p-4 sm:p-4.5 border border-[#D8E6F0] shadow-[0_2px_10px_rgba(6,42,67,0.03)] flex flex-col justify-between transition-all hover:shadow-[0_4px_16px_rgba(6,42,67,0.06)]"
            >
              {/* Card top row: Icon + Condition Name */}
              <div className="w-full flex items-center justify-between gap-2">
                <div className="w-8 h-8 rounded-full bg-[#F4F8FA] border border-[#E3EDF3] flex items-center justify-center shrink-0">
                  {getIcon(item.iconType, item.statusType)}
                </div>
                <span className="font-ui font-medium text-[12.5px] min-[390px]:text-[13px] text-[#567389] truncate">
                  {item.name}
                </span>
              </div>

              {/* Middle: Large Immediately Readable Value */}
              <div className="w-full mt-2 sm:mt-2.5">
                <span className="font-display font-bold text-[22px] min-[390px]:text-[24px] sm:text-[26px] text-[#062A43] leading-none tracking-tight block truncate">
                  {item.value}
                </span>
              </div>

              {/* Bottom: Very Short Status Pill */}
              <div className="w-full mt-2.5 pt-1.5 border-t border-black/5 flex items-center justify-between gap-1">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] min-[390px]:text-[11.5px] font-semibold border ${getStatusBadgeStyle(
                    item.statusType
                  )} truncate max-w-full`}
                >
                  {item.status}
                </span>
                {item.note && (
                  <span className="font-ui text-[10px] min-[390px]:text-[10.5px] text-[#7890A0] truncate hidden min-[360px]:inline">
                    {item.note}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
