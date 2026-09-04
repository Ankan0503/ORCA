import React, { useState } from 'react';
import { OrcaFindFishHeader } from '../components/findfish/OrcaFindFishHeader';
import { OrcaFindFishMap } from '../components/findfish/OrcaFindFishMap';
import { OrcaFindFishRecommendation } from '../components/findfish/OrcaFindFishRecommendation';
import { OrcaFindFishOtherOptions } from '../components/findfish/OrcaFindFishOtherOptions';
import { OrcaFindFishQuickTip } from '../components/findfish/OrcaFindFishQuickTip';
import { OrcaFindFishAskOrca } from '../components/findfish/OrcaFindFishAskOrca';
import { OrcaNavigationModal } from '../components/findfish/OrcaNavigationModal';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import { getFindFishTranslations } from '../data/findFishData';

const BACKGROUND_IMAGE = '/assets/orca_safety_background.avif';

interface FindFishPageProps {
  currentLanguage?: LanguageOption;
  onNavigateHome: () => void;
  onNavigateTab?: (tab: NavTabId) => void;
  locationName?: string;
}

export const FindFishPage: React.FC<FindFishPageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateTab,
  locationName = 'Digha, West Bengal',
}) => {
  const [selectedZone, setSelectedZone] = useState<string>('best-spot');
  const [isNavModalOpen, setIsNavModalOpen] = useState<boolean>(false);

  const langCode = currentLanguage?.code || 'en';
  const translations = getFindFishTranslations(langCode);

  const handleTabChange = (tabId: NavTabId) => {
    if (tabId === 'home') {
      onNavigateHome();
    } else {
      onNavigateTab?.(tabId);
    }
  };

  const handleScrollToRecommendation = () => {
    const el = document.getElementById('orca-main-recommendation-card');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div
      className="relative w-full min-h-[100svh] min-h-[100dvh] overflow-x-hidden bg-[#F7FAFC] text-[#062A43]"
      id="orca-find-fish-page"
    >
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Reuses /assets/orca_safety_background.avif
        - Positioned primarily toward the upper-right portion of the page
        - Left side remains light/clean so the title is 100% readable
        ===================================================================
      */}
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Reuses /assets/orca_safety_background.avif
        - Positioned toward the upper-right portion with proper focal framing
        - Left side remains clean so text sits on soft background without interference
        ===================================================================
      */}
      <div
        className="pointer-events-none absolute top-0 right-0 z-0 w-[240px] min-[390px]:w-[280px] sm:w-[400px] md:w-[500px] max-w-[70%] h-[260px] min-[390px]:h-[290px] sm:h-[360px] overflow-hidden select-none"
        aria-hidden="true"
      >
        <img
          src={BACKGROUND_IMAGE}
          alt=""
          className="w-full h-full object-cover object-[right_36%] opacity-95 mix-blend-multiply transition-opacity duration-300"
          loading="eager"
          decoding="async"
        />
        {/* Soft edge feathering overlays to keep left side clean */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'linear-gradient(to right, #F7FAFC 0%, rgba(247, 250, 252, 0.8) 18%, rgba(247, 250, 252, 0.2) 38%, transparent 55%), linear-gradient(to bottom, transparent 65%, #F7FAFC 100%)',
          }}
        />
      </div>

      {/* Main Container */}
      <main className="relative z-10 w-full max-w-[640px] md:max-w-[720px] lg:max-w-[800px] mx-auto px-4 min-[390px]:px-5 sm:px-6 md:px-8 safe-pt pb-32 sm:pb-36 flex flex-col items-stretch">
        {/* 
          1. TOP HEADER:
          ←  ORCA       📍 Digha, West Bengal
        */}
        <OrcaFindFishHeader
          onBackClick={onNavigateHome}
          currentLanguage={currentLanguage}
          locationName={locationName}
        />

        {/* 
          2. PAGE TITLE:
          - Cormorant Garamond editorial style
          - "Where should I fish today?"
          - Subtitle: "“ORCA found the best spots near you.”" (DM Sans)
          - Constrained width (max-w-[60%] on mobile) so the scenic boat and sea remain 100% visible on the right
        */}
        <div className="w-full mt-2.5 min-[390px]:mt-3 sm:mt-4 flex flex-col items-start select-none max-w-[60%] min-[390px]:max-w-[64%] sm:max-w-none">
          <h1
            className="font-display font-bold text-[32px] min-[390px]:text-[36px] sm:text-[44px] text-[#062A43] leading-[1.06] tracking-tight"
            id="find-fish-title"
          >
            <span>{translations.pageTitleLine1}</span>{' '}
            <span className="block">{translations.pageTitleLine2}</span>
          </h1>

          <p className="font-ui font-normal text-[13px] min-[390px]:text-[14px] sm:text-[16px] text-[#274A62] leading-[1.35] mt-1.5 sm:mt-2">
            “{translations.pageSubtitle}”
          </p>
        </div>

        {/* 
          3. MAIN MAP:
          - Most important visual element
          - Digha / current location
          - 3 zones: 🟢 BEST FISHING, 🟡 GOOD, 🔴 AVOID
          - Map controls: location, zoom +/-
        */}
        <div className="w-full mt-4 min-[390px]:mt-5 sm:mt-6">
          <OrcaFindFishMap
            translations={translations}
            selectedZoneId={selectedZone}
            onSelectZone={setSelectedZone}
            onGoToBest={handleScrollToRecommendation}
          />
        </div>

        {/* 
          4. MAIN RECOMMENDATION:
          - Second most important element
          - Soft pale-green background
          - 🎣 BEST AREA
          - 12 km offshore
          - Good fishing chance
          - Good fish conditions + safe sea
          - Prominent "GO HERE →" button
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaFindFishRecommendation
            translations={translations}
            onGoHere={() => setIsNavModalOpen(true)}
          />
        </div>

        {/* 
          5. OTHER OPTIONS:
          - Secondary horizontal cards
          - 18 km offshore | Moderate chance | Still a good option →
          - 25 km offshore | Moderate chance | Good conditions →
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaFindFishOtherOptions
            translations={translations}
            onSelectOption={(distance) => {
              setSelectedZone('good-spot-1');
              setIsNavModalOpen(true);
            }}
          />
        </div>

        {/* 
          6. QUICK TIP:
          - Lightbulb icon
          - "Try the green area first. Check sea conditions again if you go farther."
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaFindFishQuickTip translations={translations} />
        </div>

        {/* 
          7. ASK ORCA:
          - Compact voice question card
          - “Want to know why this spot is good?”
          - Microphone button
          - “Why this spot?” chip
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaFindFishAskOrca translations={translations} />
        </div>
      </main>

      {/* 
        NAVIGATION DETAILS MODAL:
        Shows clear compass heading, distance, and sea status when clicking "GO HERE →"
      */}
      <OrcaNavigationModal
        isOpen={isNavModalOpen}
        onClose={() => setIsNavModalOpen(false)}
        translations={translations}
      />

      {/* 
        8. PERSISTENT BOTTOM NAVIGATION:
        - Same bottom navigation used across ORCA
        - Map should be the active item on this page!
      */}
      <OrcaBottomNav
        activeTab="map"
        currentLanguage={currentLanguage}
        onTabChange={handleTabChange}
      />
    </div>
  );
};
