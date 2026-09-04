import React, { useState } from 'react';
import { OrcaSafetyHeader } from '../components/safety/OrcaSafetyHeader';
import { OrcaSafetyHeroCard } from '../components/safety/OrcaSafetyHeroCard';
import { OrcaSafetyWhySection } from '../components/safety/OrcaSafetyWhySection';
import { OrcaSafetyConditionsGrid } from '../components/safety/OrcaSafetyConditionsGrid';
import { OrcaSafetyWarningBanner } from '../components/safety/OrcaSafetyWarningBanner';
import { OrcaSafetyMapCard } from '../components/safety/OrcaSafetyMapCard';
import { OrcaSafetyAdviceCard } from '../components/safety/OrcaSafetyAdviceCard';
import { OrcaSafetyAskOrca } from '../components/safety/OrcaSafetyAskOrca';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import {
  SafetyStatus,
  getSafetyData,
  getSafetyTranslations,
} from '../data/safetyData';

const SAFETY_BACKGROUND_IMAGE = '/assets/orca_safety_background.avif';

interface SafetyPageProps {
  currentLanguage?: LanguageOption;
  onNavigateHome: () => void;
  onNavigateTab?: (tab: NavTabId) => void;
  locationName?: string;
}

export const SafetyPage: React.FC<SafetyPageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateTab,
  locationName = 'Digha, West Bengal',
}) => {
  // Support all 3 states: 🟢 safe | 🟡 caution | 🔴 danger (defaults to 'safe')
  const [safetyStatus, setSafetyStatus] = useState<SafetyStatus>('safe');

  const langCode = currentLanguage?.code || 'en';
  const translations = getSafetyTranslations(langCode);
  const data = getSafetyData(safetyStatus, langCode);

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
      id="orca-safety-page"
    >
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Placed exactly at /assets/safety/orca_safety_background.avif
        - Positioned primarily toward the upper-right portion of the page
        - Left side remains clean/light so text remains 100% legible
        - Atmospheric gradient blend for natural watercolor integration
        ===================================================================
      */}
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Placed at /assets/orca_safety_background.avif
        - Positioned toward the upper-right portion with proper focal framing
        - Left side remains clean/light so text remains 100% legible
        - Atmospheric gradient blend for natural watercolor integration
        ===================================================================
      */}
      <div
        className="pointer-events-none absolute top-0 right-0 z-0 w-[240px] min-[390px]:w-[280px] sm:w-[400px] md:w-[500px] max-w-[70%] h-[260px] min-[390px]:h-[290px] sm:h-[360px] overflow-hidden select-none"
        aria-hidden="true"
      >
        <img
          src={SAFETY_BACKGROUND_IMAGE}
          alt=""
          className="w-full h-full object-cover object-[right_36%] opacity-95 mix-blend-multiply"
          loading="eager"
          decoding="async"
        />
        {/* Soft edge feathering so text on the left is crisp and completely readable */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'linear-gradient(to right, #F7FAFC 0%, rgba(247, 250, 252, 0.8) 18%, rgba(247, 250, 252, 0.2) 38%, transparent 55%), linear-gradient(to bottom, transparent 65%, #F7FAFC 100%)',
          }}
        />
      </div>

      {/* 
        ===================================================================
        PAGE CONTAINER (Mobile-first centered column, max-width 640px)
        - Desktop: centered readable content width
        - Mobile: edge-to-edge breathing room
        - Generous safe-area bottom padding for the fixed bottom navigation
        ===================================================================
      */}
      <main className="relative z-10 w-full max-w-[640px] mx-auto px-4 min-[390px]:px-5 sm:px-6 safe-pt pb-28 min-[390px]:pb-32 sm:pb-36 flex flex-col items-stretch">
        
        {/* 1. TOP HEADER (← ORCA   📍 Digha, West Bengal) */}
        <OrcaSafetyHeader
          onBackClick={onNavigateHome}
          currentLanguage={currentLanguage}
          locationName={locationName}
        />

        {/* 
          2. PAGE TITLE
          - Editorial Cormorant Garamond font style
          - "Is it safe to go fishing today?"
          - Constrained width (max-w-[60%] on mobile) so the scenic boat and sea remain 100% visible on the right
        */}
        <div className="w-full mt-2.5 min-[390px]:mt-3 sm:mt-4 flex flex-col items-start select-none max-w-[60%] min-[390px]:max-w-[64%] sm:max-w-none">
          <h1
            className="font-display font-bold text-[32px] min-[390px]:text-[36px] sm:text-[44px] leading-[1.06] text-[#062A43] tracking-tight"
            id="orca-safety-page-title"
          >
            <span>{translations.pageTitleLine1}</span>{' '}
            <span className="block">{translations.pageTitleLine2}</span>
          </h1>
        </div>

        {/* 
          3. MOST IMPORTANT SECTION — SAFETY RESULT CARD
          - 2–3 second instant comprehension
          - 🟢 SAFE TO GO (Low risk today. / “Sea conditions look favourable...”)
          - Dynamic switcher between:
            🟢 SAFE TO GO
            🟡 BE CAREFUL
            🔴 DO NOT GO
        */}
        <div className="w-full mt-4 min-[390px]:mt-5 sm:mt-6">
          <OrcaSafetyHeroCard
            data={data}
            onStateSelect={(status) => setSafetyStatus(status)}
            statusChangeLabel={translations.testToggleLabel}
          />
        </div>

        {/* 
          4. WHY?
          - Short explainability
          - 4 evidence chips
        */}
        <OrcaSafetyWhySection
          data={data}
          whyTitle={translations.whyTitle}
        />

        {/* 
          5. IMPORTANT WARNING (If active: prominent pale red card; If none: compact ✓ No active warnings)
        */}
        <OrcaSafetyWarningBanner
          warning={data.warning}
          noWarningTitle={translations.noWarningTitle}
          noWarningSubtitle={translations.noWarningSubtitle}
        />

        {/* 
          6. CURRENT CONDITIONS (2-column clean grid: Wind, Waves, Rain, Visibility, Warning, Water Temp)
        */}
        <OrcaSafetyConditionsGrid
          conditions={data.conditions}
          title={translations.conditionsTitle}
        />

        {/* 
          7. AREA SAFETY MAP (Compact risk zones: 0–15km green safe, 15–30km yellow caution, >30km red danger)
        */}
        <OrcaSafetyMapCard
          status={safetyStatus}
          title={translations.mapTitle}
          subtext={translations.mapSubtext}
          viewFullMapText={translations.viewFullMap}
          safeLegend={translations.safeZoneLegend}
          cautionLegend={translations.cautionZoneLegend}
          dangerLegend={translations.dangerZoneLegend}
          onViewFullMap={() => {
            // Can switch to Map tab
            onNavigateTab?.('map');
          }}
        />

        {/* 
          8. WHAT SHOULD I DO? (Practical, non-technical advice for the fisherman)
        */}
        <OrcaSafetyAdviceCard
          data={data}
          title={translations.adviceTitle}
        />

        {/* 
          9. ASK ORCA (Compact follow-up voice prompt)
        */}
        <OrcaSafetyAskOrca
          title={translations.askTitle}
          subtext={translations.askSubtext}
          prompt1={translations.askPrompt1}
          prompt2={translations.askPrompt2}
          onVoiceClick={() => {
            // Could navigate to ask tab
            onNavigateTab?.('ask');
          }}
          onPromptClick={(prompt) => {
            onNavigateTab?.('ask');
          }}
        />
      </main>

      {/* 
        ===================================================================
        BOTTOM NAVIGATION
        - Same 5-item bottom nav (Home, Map, Ask, Alerts, Profile)
        - Home is NOT active on this page (activeTab={null})
        - Safety is NOT a new bottom nav item
        ===================================================================
      */}
      <OrcaBottomNav
        activeTab={null}
        currentLanguage={currentLanguage}
        onTabChange={handleTabChange}
      />
    </div>
  );
};

export default SafetyPage;
