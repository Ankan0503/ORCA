import React from 'react';
import { Home, Map, Mic, Bell, User } from 'lucide-react';
import { LanguageOption } from '../types';
import { getHomeTranslation } from '../data/homeTranslations';

export type NavTabId = 'home' | 'map' | 'ask' | 'alerts' | 'profile';

interface OrcaBottomNavProps {
  activeTab?: NavTabId | null;
  onTabChange?: (tab: NavTabId) => void;
  currentLanguage?: LanguageOption;
}

export const OrcaBottomNav: React.FC<OrcaBottomNavProps> = ({
  activeTab = 'home',
  onTabChange,
  currentLanguage,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const homeTranslation = getHomeTranslation(langCode);
  const labels = homeTranslation.nav;

  const handleTabClick = (tabId: NavTabId) => {
    onTabChange?.(tabId);
  };

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 w-full bg-white rounded-t-[28px] min-[390px]:rounded-t-[32px] shadow-[0_-4px_24px_rgba(6,42,67,0.08)] select-none"
      id="orca-bottom-navigation"
      aria-label="Main Application Navigation"
    >
      {/* Container aligned with page content max-width */}
      <div className="w-full max-w-[880px] mx-auto px-2 min-[390px]:px-3 sm:px-4 pt-2.5 min-[390px]:pt-3 pb-[max(12px,env(safe-area-inset-bottom,12px))] flex items-start justify-between">
        
        {/* 1. HOME TAB */}
        <button
          type="button"
          id="orca-nav-home"
          onClick={() => handleTabClick('home')}
          aria-label="Home"
          aria-current={activeTab === 'home' ? 'page' : undefined}
          className="flex-1 min-w-0 flex flex-col items-center justify-start py-0.5 cursor-pointer focus:outline-hidden group active:scale-95 transition-transform duration-150"
        >
          <div className="h-[28px] flex items-center justify-center">
            <Home
              size={25}
              className={
                activeTab === 'home'
                  ? 'fill-[#06365A] text-[#06365A]'
                  : 'text-[#71869A] stroke-[2]'
              }
            />
          </div>
          <span
            className={`font-ui text-[11px] min-[390px]:text-[12.5px] sm:text-[13.5px] font-medium leading-tight mt-1 text-center truncate max-w-full px-0.5 ${
              activeTab === 'home' ? 'text-[#06365A]' : 'text-[#71869A]'
            }`}
          >
            {labels.home}
          </span>
          {/* Active indicator bar: 32–38px wide, 3px high, rounded ends */}
          {activeTab === 'home' ? (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] rounded-full bg-[#06365A] mt-1.5 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] mt-1.5 opacity-0 shrink-0"
              aria-hidden="true"
            />
          )}
        </button>

        {/* 2. MAP TAB */}
        <button
          type="button"
          id="orca-nav-map"
          onClick={() => handleTabClick('map')}
          aria-label="Map"
          aria-current={activeTab === 'map' ? 'page' : undefined}
          className="flex-1 min-w-0 flex flex-col items-center justify-start py-0.5 cursor-pointer focus:outline-hidden group active:scale-95 transition-transform duration-150"
        >
          <div className="h-[28px] flex items-center justify-center">
            <Map
              size={25}
              className={
                activeTab === 'map'
                  ? 'text-[#06365A] stroke-[2.4]'
                  : 'text-[#71869A] group-hover:text-[#06365A] stroke-[2] transition-colors'
              }
            />
          </div>
          <span
            className={`font-ui text-[11px] min-[390px]:text-[12.5px] sm:text-[13.5px] font-medium leading-tight mt-1 text-center truncate max-w-full px-0.5 ${
              activeTab === 'map'
                ? 'text-[#06365A]'
                : 'text-[#71869A] group-hover:text-[#06365A] transition-colors'
            }`}
          >
            {labels.map}
          </span>
          {activeTab === 'map' ? (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] rounded-full bg-[#06365A] mt-1.5 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] mt-1.5 opacity-0 shrink-0"
              aria-hidden="true"
            />
          )}
        </button>

        {/* 3. ASK TAB */}
        <button
          type="button"
          id="orca-nav-ask"
          onClick={() => handleTabClick('ask')}
          aria-label="Ask"
          aria-current={activeTab === 'ask' ? 'page' : undefined}
          className="flex-1 min-w-0 flex flex-col items-center justify-start py-0.5 cursor-pointer focus:outline-hidden group active:scale-95 transition-transform duration-150"
        >
          <div className="h-[28px] flex items-center justify-center">
            <Mic
              size={25}
              className={
                activeTab === 'ask'
                  ? 'text-[#06365A] stroke-[2.4]'
                  : 'text-[#71869A] group-hover:text-[#06365A] stroke-[2] transition-colors'
              }
            />
          </div>
          <span
            className={`font-ui text-[11px] min-[390px]:text-[12.5px] sm:text-[13.5px] font-medium leading-tight mt-1 text-center truncate max-w-full px-0.5 ${
              activeTab === 'ask'
                ? 'text-[#06365A]'
                : 'text-[#71869A] group-hover:text-[#06365A] transition-colors'
            }`}
          >
            {labels.ask}
          </span>
          {activeTab === 'ask' ? (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] rounded-full bg-[#06365A] mt-1.5 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] mt-1.5 opacity-0 shrink-0"
              aria-hidden="true"
            />
          )}
        </button>

        {/* 4. ALERTS TAB (with red notification dot) */}
        <button
          type="button"
          id="orca-nav-alerts"
          onClick={() => handleTabClick('alerts')}
          aria-label="Alerts"
          aria-current={activeTab === 'alerts' ? 'page' : undefined}
          className="flex-1 min-w-0 flex flex-col items-center justify-start py-0.5 cursor-pointer focus:outline-hidden group active:scale-95 transition-transform duration-150"
        >
          <div className="h-[28px] flex items-center justify-center relative">
            <Bell
              size={25}
              className={
                activeTab === 'alerts'
                  ? 'text-[#06365A] stroke-[2.4]'
                  : 'text-[#71869A] group-hover:text-[#06365A] stroke-[2] transition-colors'
              }
            />
            {/* Red notification dot: 8–10px, upper-right side of bell */}
            <span
              className="absolute -top-0.5 -right-1 w-[9px] h-[9px] rounded-full bg-[#E53935] ring-2 ring-white"
              aria-label="New alerts available"
            />
          </div>
          <span
            className={`font-ui text-[11px] min-[390px]:text-[12.5px] sm:text-[13.5px] font-medium leading-tight mt-1 text-center truncate max-w-full px-0.5 ${
              activeTab === 'alerts'
                ? 'text-[#06365A]'
                : 'text-[#71869A] group-hover:text-[#06365A] transition-colors'
            }`}
          >
            {labels.alerts}
          </span>
          {activeTab === 'alerts' ? (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] rounded-full bg-[#06365A] mt-1.5 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] mt-1.5 opacity-0 shrink-0"
              aria-hidden="true"
            />
          )}
        </button>

        {/* 5. PROFILE TAB */}
        <button
          type="button"
          id="orca-nav-profile"
          onClick={() => handleTabClick('profile')}
          aria-label="Profile"
          aria-current={activeTab === 'profile' ? 'page' : undefined}
          className="flex-1 min-w-0 flex flex-col items-center justify-start py-0.5 cursor-pointer focus:outline-hidden group active:scale-95 transition-transform duration-150"
        >
          <div className="h-[28px] flex items-center justify-center">
            <User
              size={25}
              className={
                activeTab === 'profile'
                  ? 'text-[#06365A] stroke-[2.4]'
                  : 'text-[#71869A] group-hover:text-[#06365A] stroke-[2] transition-colors'
              }
            />
          </div>
          <span
            className={`font-ui text-[11px] min-[390px]:text-[12.5px] sm:text-[13.5px] font-medium leading-tight mt-1 text-center truncate max-w-full px-0.5 ${
              activeTab === 'profile'
                ? 'text-[#06365A]'
                : 'text-[#71869A] group-hover:text-[#06365A] transition-colors'
            }`}
          >
            {labels.profile}
          </span>
          {activeTab === 'profile' ? (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] rounded-full bg-[#06365A] mt-1.5 shrink-0"
              aria-hidden="true"
            />
          ) : (
            <span
              className="w-[32px] min-[390px]:w-[38px] h-[3px] mt-1.5 opacity-0 shrink-0"
              aria-hidden="true"
            />
          )}
        </button>

      </div>
    </nav>
  );
};

export default OrcaBottomNav;
