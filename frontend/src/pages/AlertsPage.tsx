import React, { useState } from 'react';
import { OrcaAlertsHeader } from '../components/alerts/OrcaAlertsHeader';
import { OrcaMainAlertCard } from '../components/alerts/OrcaMainAlertCard';
import { OrcaWhatShouldIDoCard } from '../components/alerts/OrcaWhatShouldIDoCard';
import { OrcaActiveAlerts } from '../components/alerts/OrcaActiveAlerts';
import { OrcaRecentAlerts } from '../components/alerts/OrcaRecentAlerts';
import { OrcaAlertsAskOrca } from '../components/alerts/OrcaAlertsAskOrca';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import {
  AlertSeverity,
  getAlertsData,
  getAlertsTranslations,
} from '../data/alertsData';

// Reusing the existing watercolor background from safety/find fish/sea today pages
const BACKGROUND_IMAGE = '/assets/orca_safety_background.avif';

interface AlertsPageProps {
  currentLanguage?: LanguageOption;
  onNavigateHome: () => void;
  onNavigateTab?: (tab: NavTabId) => void;
  locationName?: string;
}

export const AlertsPage: React.FC<AlertsPageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateTab,
  locationName = 'Digha, West Bengal',
}) => {
  // Supports dynamic severity switching: 'high' | 'caution' | 'update' | 'none'
  // Defaults to 'high' as specified in prompt mock data
  const [severity, setSeverity] = useState<AlertSeverity>('high');

  const langCode = currentLanguage?.code || 'en';
  const translations = getAlertsTranslations(langCode);
  const data = getAlertsData(severity, langCode, locationName);

  const handleTabChange = (tabId: NavTabId) => {
    if (tabId === 'home') {
      onNavigateHome();
    } else {
      onNavigateTab?.(tabId);
    }
  };

  return (
    <div
      className="relative w-full min-h-[100svh] min-h-[100dvh] overflow-x-hidden bg-[#F7FAFC] text-[#062A43]"
      id="orca-alerts-page"
    >
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Reuses the existing /assets/orca_safety_background.avif asset
        - Positioned primarily toward the upper-right portion of the page
        - Left side remains clean and light so typography is 100% legible
        ===================================================================
      */}
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Reuses the existing /assets/orca_safety_background.avif asset
        - Positioned toward the upper-right portion with proper focal framing
        - Left side remains clean and light so typography is 100% legible
        ===================================================================
      */}
      <div
        className="pointer-events-none absolute top-0 right-0 z-0 w-[280px] min-[390px]:w-[320px] sm:w-[440px] md:w-[540px] max-w-[78%] h-[290px] min-[390px]:h-[320px] sm:h-[380px] overflow-hidden select-none"
        aria-hidden="true"
      >
        <img
          src={BACKGROUND_IMAGE}
          alt=""
          className="w-full h-full object-cover object-[right_36%] min-[390px]:object-[85%_35%] opacity-95 mix-blend-multiply"
          loading="eager"
          decoding="async"
        />
        {/* Soft edge feathering overlays to keep left side clean */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'linear-gradient(to right, #F7FAFC 0%, rgba(247, 250, 252, 0.8) 18%, rgba(247, 250, 252, 0.15) 36%, transparent 52%), linear-gradient(to bottom, transparent 65%, #F7FAFC 100%)',
          }}
        />
      </div>

      {/* 
        ===================================================================
        PAGE CONTAINER
        - Centered column, max-width 640px
        - Safe area padding for bottom navigation
        - 2–3 second comprehension:
          1. Is there anything dangerous?
          2. What is happening?
          3. What should I do?
        ===================================================================
      */}
      <main className="relative z-10 w-full max-w-[640px] mx-auto px-4 min-[390px]:px-5 sm:px-6 safe-pt pb-28 min-[390px]:pb-32 sm:pb-36 flex flex-col items-stretch">
        {/* 
          1. TOP HEADER:
          ←  ORCA       📍 Digha, West Bengal
        */}
        <OrcaAlertsHeader
          onBackClick={onNavigateHome}
          currentLanguage={currentLanguage}
          locationName={locationName}
        />

        {/* 
          2. PAGE TITLE:
          - Cormorant Garamond heading: "Alerts"
          - Small DM Sans text: "“Stay informed. Stay safe.”"
          - Constrained width (max-w-[56%] on mobile) so the scenic boat, mountains, and sea remain 100% visible on the right
        */}
        <div className="w-full mt-2.5 min-[390px]:mt-3 sm:mt-4 flex flex-col items-start select-none max-w-[56%] min-[390px]:max-w-[58%] sm:max-w-none">
          <h1
            className="font-display font-bold text-[34px] min-[390px]:text-[38px] sm:text-[44px] text-[#062A43] leading-[1.05] tracking-tight"
            id="alerts-page-title"
          >
            {translations.pageTitle}
          </h1>

          <p className="font-ui font-normal text-[13.5px] min-[390px]:text-[14.5px] sm:text-[16px] text-[#274A62] leading-[1.35] mt-1.5 sm:mt-2">
            “{translations.pageSubtitle}”
          </p>
        </div>

        {/* 
          3. MOST IMPORTANT ALERT (VISUALLY DOMINANT):
          - ONE large alert card first
          - ⚠️ HIGH ALERT (pale red background)
          - "Strong winds expected after 2 PM"
          - "Avoid going far offshore after 2 PM."
          - "2 hours ago"
          - Includes state simulator for testing
          - Lowered on mobile so the scenic boat and sea ripples are fully visible, matching the Find Fish and Safety sections
        */}
        <div className="w-full mt-[80px] min-[390px]:mt-[88px] sm:mt-9">
          <OrcaMainAlertCard
            alert={data.mainAlert}
            severity={data.severity}
            onSeverityChange={(sev) => setSeverity(sev)}
            stateSimulatorLabel={translations.stateSimulatorLabel}
            noAlertsTitle={translations.noAlertsTitle}
            noAlertsSubtitle={translations.noAlertsSubtitle}
          />
        </div>

        {/* 
          4. WHAT SHOULD I DO?
          - If serious alert exists:
            "What should I do?"
            “Stay close to shore and avoid going far offshore after 2 PM.”
          - If no serious alert:
            “You're good for now. Check again before you leave.”
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaWhatShouldIDoCard
            title={data.whatShouldIDoTitle}
            actionText={data.whatShouldIDo}
            severity={data.severity}
          />
        </div>

        {/* 
          5. ACTIVE ALERTS (If multiple active alerts, show only 2–3):
          - 🟠 CAUTION: Moderate waves today — “Be careful in open waters.” (6 hours ago)
          - 🟢 UPDATE: No heavy rain expected — “Light rainfall possible in the evening.” (12 hours ago)
        */}
        {data.activeAlerts.length > 0 && (
          <div className="w-full mt-5 sm:mt-6">
            <OrcaActiveAlerts
              alerts={data.activeAlerts}
              title={translations.activeAlertsTitle}
            />
          </div>
        )}

        {/* 
          6. RECENT ALERTS (2–3 previous alerts):
          - High tide at 4:30 PM — “Plan your return accordingly.”
          - Wind increasing tomorrow — “Expected 20–25 km/h.”
          - View all →
        */}
        <div className="w-full mt-5 sm:mt-6">
          <OrcaRecentAlerts
            recentAlerts={data.recentAlerts}
            title={translations.recentAlertsTitle}
            viewAllLabel={translations.viewAll}
          />
        </div>

        {/* 
          7. ASK ORCA:
          - Compact voice card near bottom
            Ask ORCA — “Want to know what this alert means?”
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaAlertsAskOrca translations={translations} />
        </div>
      </main>

      {/* 
        8. PERSISTENT 5-ITEM BOTTOM NAVIGATION:
        Home, Map, Ask, Alerts, Profile
        ALERTS is the active item with the red notification dot
      */}
      <OrcaBottomNav
        activeTab="alerts"
        currentLanguage={currentLanguage}
        onTabChange={handleTabChange}
      />
    </div>
  );
};
