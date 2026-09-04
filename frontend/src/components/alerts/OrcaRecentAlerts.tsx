import React, { useState } from 'react';
import { History, ChevronRight } from 'lucide-react';
import { RecentAlertItem } from '../../data/alertsData';

interface OrcaRecentAlertsProps {
  recentAlerts: RecentAlertItem[];
  title?: string;
  viewAllLabel?: string;
}

export const OrcaRecentAlerts: React.FC<OrcaRecentAlertsProps> = ({
  recentAlerts,
  title = 'Recent alerts',
  viewAllLabel = 'View all →',
}) => {
  const [showToast, setShowToast] = useState(false);

  const handleViewAll = () => {
    setShowToast(true);
    setTimeout(() => setShowToast(false), 2500);
  };

  return (
    <section
      className="w-full flex flex-col gap-2.5 sm:gap-3 select-none"
      id="orca-recent-alerts-section"
      aria-label="Recent Past Sea Alerts"
    >
      {/* Header with Title and "View all →" */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-1.5">
          <History size={16} className="text-[#557186]" />
          <h3 className="font-ui font-bold text-[17px] min-[390px]:text-[18px] text-[#062A43] tracking-tight">
            {title}
          </h3>
        </div>

        <button
          type="button"
          onClick={handleViewAll}
          id="orca-recent-alerts-view-all"
          className="font-ui font-bold text-[13px] text-[#1677A8] hover:text-[#06365A] transition-colors cursor-pointer py-1 px-1.5 focus:outline-hidden"
        >
          {viewAllLabel}
        </button>
      </div>

      {/* 2-3 Compact Cards */}
      <div className="flex flex-col gap-2 sm:gap-2.5 w-full">
        {recentAlerts.map((item) => (
          <div
            key={item.id}
            id={`recent-alert-${item.id}`}
            className="w-full p-3 min-[390px]:p-3.5 rounded-xl sm:rounded-2xl bg-white/90 backdrop-blur-xs border border-[#D9E6F0] flex items-center justify-between gap-3 shadow-2xs hover:shadow-xs transition-shadow"
          >
            <div className="flex flex-col min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-ui font-bold text-[14px] min-[390px]:text-[14.5px] text-[#062A43] truncate">
                  {item.title}
                </span>
                <span className="text-[11px] text-[#71869A] font-ui shrink-0">
                  {item.time}
                </span>
              </div>
              <p className="font-ui font-medium text-[12.5px] min-[390px]:text-[13px] text-[#557186] mt-0.5 truncate">
                “{item.action}”
              </p>
            </div>

            <ChevronRight size={16} className="text-[#9BB1C2] shrink-0" />
          </div>
        ))}
      </div>

      {showToast && (
        <div
          role="status"
          className="w-full p-2.5 rounded-xl bg-[#062A43] text-white text-[12px] font-ui text-center transition-all animate-fade-in shadow-md"
        >
          Showing all recent advisory logs for Digha coast (past 7 days).
        </div>
      )}
    </section>
  );
};
