import React, { useState, useEffect } from 'react';
import { MapPin } from 'lucide-react';
import { LanguageOption } from '../types';
import { LANGUAGES } from '../data/languages';
import { getHomeTranslation } from '../data/homeTranslations';
import { LanguageSelector } from './LanguageSelector';

// =========================================================================
// REQUIRED CONSTANTS
// =========================================================================
const ORCA_LOGO = '/assets/orca-logo.svg';
const TOP_BACKGROUND = '/assets/home/orca_top_background.avif';

interface OrcaHomeHeroProps {
  locationName?: string;
  currentLanguage?: LanguageOption;
  onLanguageChange?: (language: LanguageOption) => void;
}

export const OrcaHomeHero: React.FC<OrcaHomeHeroProps> = ({
  locationName,
  currentLanguage = LANGUAGES[0],
  onLanguageChange,
}) => {
  const [selectedLang, setSelectedLang] = useState<LanguageOption>(currentLanguage);

  // Sync external language prop if provided
  useEffect(() => {
    setSelectedLang(currentLanguage);
  }, [currentLanguage]);

  const homeTranslation = getHomeTranslation(selectedLang?.code);
  const displayLocation = locationName || homeTranslation.locationName;

  // Compute dynamic greeting based on current local hour and selected language:
  // 05:00–11:59: morning
  // 12:00–16:59: afternoon
  // 17:00–04:59: evening
  const getTimeKey = (): 'morning' | 'afternoon' | 'evening' => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return 'morning';
    if (hour >= 12 && hour < 17) return 'afternoon';
    return 'evening';
  };

  const [timeOfDay, setTimeOfDay] = useState<'morning' | 'afternoon' | 'evening'>(getTimeKey);

  useEffect(() => {
    const updateGreeting = () => {
      setTimeOfDay(getTimeKey());
    };

    updateGreeting();
    // Re-check periodically
    const timer = setInterval(updateGreeting, 60000);
    return () => clearInterval(timer);
  }, []);

  const greeting = homeTranslation.greetings[timeOfDay];

  const handleSelectLanguage = (lang: LanguageOption) => {
    setSelectedLang(lang);
    if (onLanguageChange) {
      onLanguageChange(lang);
    }
  };

  return (
    <section
      /*
        No `overflow-hidden` here: it clipped the language dropdown at the hero's
        bottom edge, so the last languages were cut off and unreachable. The
        decorative background below has its own clipping, which is what this was
        actually for.
      */
      className="relative w-full select-none bg-[#F7FAFC] text-[#062A43]"
      style={{
        backgroundColor: 'var(--color-app-bg, #F7FAFC)',
      }}
      id="orca-authenticated-hero-section"
      aria-label="ORCA Welcome Section"
    >
      {/* 
        ===================================================================
        BACKGROUND ILLUSTRATION COMPOSITION
        - Positioned strictly on the RIGHT (65–75% mobile, 55–65% desktop)
        - Height 100% of hero section
        - Pulled up to align with top header and content
        - Soft, seamless bleed to the light left side without harsh cuts
        - Birds, watercolor clouds, and coastal mountains remain visible
        ===================================================================
      */}
      <div
        className="absolute top-0 right-0 h-full w-[72%] sm:w-[65%] lg:w-[58%] xl:w-[54%] pointer-events-none z-0 overflow-hidden"
        aria-hidden="true"
      >
        <img
          src={TOP_BACKGROUND}
          alt=""
          className="w-full h-full object-cover object-[right_top]"
          loading="eager"
          fetchPriority="high"
          decoding="async"
        />

        {/* 
          Extremely subtle fade from transparent image → light background toward the left and bottom.
          Allows the text on the left to sit over crisp #F7FAFC while keeping the mountains,
          sky, and ocean on the right pristine and undisturbed.
        */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'linear-gradient(to right, #F7FAFC 0%, rgba(247, 250, 252, 0.75) 16%, rgba(247, 250, 252, 0.25) 38%, transparent 60%), linear-gradient(to bottom, transparent 70%, #F7FAFC 100%)',
          }}
        />
      </div>

      {/* 
        ===================================================================
        MAIN CONTENT CONTAINER
        - Mobile width target: 390px (comfortable 20–24px horizontal padding)
        - Desktop max width: 1200px
        - Compact height pulling location and text up
        - Respects safe-area padding at top
        ===================================================================
      */}
      <div className="relative z-10 w-full max-w-[1200px] mx-auto px-5 sm:px-6 md:px-8 safe-pt pt-5 sm:pt-6 pb-4 sm:pb-5 flex flex-col justify-start">
        
        {/* ---------------------------------------------------------------
            TOP HEADER ROW:
            - Left: ORCA logo (105–115px wide, 24px padding)
            - Right: Subtle language selector pill (90–100px wide, 40px high)
        --------------------------------------------------------------- */}
        <header className="w-full flex items-center justify-between gap-3">
          {/* ORCA Logo */}
          <div className="shrink-0 flex items-center">
            <img
              src={ORCA_LOGO}
              alt=""
              className="w-[108px] sm:w-[114px] h-auto object-contain block"
            />
          </div>

          {/* One shared selector across the app — this page used to carry its
              own copy, which is why its scrolling and clipping bugs survived
              after the shared one was fixed. */}
          <div className="shrink-0">
            <LanguageSelector
              currentLanguage={selectedLang}
              onSelectLanguage={handleSelectLanguage}
            />
          </div>
        </header>

        {/* ---------------------------------------------------------------
            EDITORIAL BODY CONTENT:
            - Spacing pulled up: header → location 16–20px
            - Location → Greeting: 16–20px
            - "Good morning," → "Fisherman": 2px
            - "Fisherman" → "What do you need today?": 8–10px
            - Desktop width constrained to left 45%
        --------------------------------------------------------------- */}
        <div className="w-full lg:w-[48%] xl:w-[45%] flex flex-col items-start mt-4 sm:mt-5">
          
          {/* 
            LOCATION & STATUS
            - 📍 Digha, West Bengal (in a dedicated box)
            - ● Location detected (positioned outside the box)
          */}
          <div
            className="flex flex-col items-start gap-1.5 max-w-full"
            id="orca-home-location-block"
          >
            {/* Location Box */}
            <div
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 min-[390px]:px-4 min-[390px]:py-2 rounded-[12px] min-[390px]:rounded-[14px] bg-white border border-[#D8E6F0] shadow-[0_2px_8px_rgba(6,42,67,0.04)] max-w-full"
              role="region"
              aria-label={`Current location: ${displayLocation}`}
            >
              <MapPin size={15} className="text-[#1677A8] shrink-0 stroke-[2.2]" />
              <span className="font-ui text-[14px] min-[390px]:text-[15px] font-semibold tracking-tight text-[#062A43] truncate">
                {displayLocation}
              </span>
            </div>

            {/* Status indicator outside the box */}
            <div className="flex items-center gap-1.5 pl-1 max-w-full">
              <span
                className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"
                style={{
                  boxShadow: '0 0 5px rgba(16, 185, 129, 0.5)',
                }}
              />
              <span className="font-ui text-[12px] min-[390px]:text-[12.5px] font-normal text-[#274A62]/85 tracking-normal truncate">
                {homeTranslation.locationDetected}
              </span>
            </div>
          </div>

          {/* 
            PRIMARY GREETING & FUNCTIONAL PROMPT
            - Spacing pulled up from location: 16–20px
          */}
          <div className="mt-4 sm:mt-5 flex flex-col items-start max-w-full w-full">
            
            {/* Dynamic Greeting line (DM Sans 16–17px mobile / 22px desktop, 400, muted navy) */}
            <span
              className="font-ui text-[16px] min-[390px]:text-[17px] sm:text-[18px] lg:text-[22px] font-normal text-[#274A62] leading-snug break-words max-w-full"
              id="orca-home-greeting-prefix"
            >
              {greeting}
            </span>

            {/* Dominant Headline: "Fisherman" / "মৎস্যজীবী" / "മത്സ്യത്തൊഴിലാളി" */}
            <h1
              className="font-display text-[36px] min-[360px]:text-[42px] min-[400px]:text-[48px] sm:text-[56px] lg:text-[70px] xl:text-[78px] font-medium text-[#062A43] leading-[1.12] sm:leading-[1.05] tracking-tight mt-[2px] break-words max-w-full"
              id="orca-home-fisherman-headline"
            >
              {homeTranslation.fisherman}
            </h1>

            {/* Main Functional Question */}
            <p
              className="font-ui text-[17px] min-[390px]:text-[19px] sm:text-[21px] lg:text-[23px] font-medium text-[#274A62] leading-snug tracking-tight mt-2 sm:mt-2.5 break-words max-w-full"
              id="orca-home-main-question"
            >
              {homeTranslation.mainQuestion}
            </p>
          </div>

        </div>

        {/* 
          STRICT DESIGN DISCIPLINE:
          Per instruction, STOP after "What do you need today?".
          No action cards, no buttons, no weather cards, no dashboard widgets here.
          Generous natural breathing room preserved.
        */}
      </div>
    </section>
  );
};
export default OrcaHomeHero;
