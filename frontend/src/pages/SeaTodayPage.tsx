import React, { useState } from 'react';
import { OrcaSeaTodayHeader } from '../components/seatoday/OrcaSeaTodayHeader';
import { OrcaSeaStatusCard } from '../components/seatoday/OrcaSeaStatusCard';
import { OrcaSeaTodayConditions } from '../components/seatoday/OrcaSeaTodayConditions';
import { OrcaSeaTodayForecast } from '../components/seatoday/OrcaSeaTodayForecast';
import { OrcaSeaTodayAdvice } from '../components/seatoday/OrcaSeaTodayAdvice';
import { OrcaSeaTodayAskOrca } from '../components/seatoday/OrcaSeaTodayAskOrca';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import {
  SeaStatus,
  getSeaTodayData,
  getSeaTodayTranslations,
} from '../data/seaTodayData';
import { useConditions } from '../hooks/useConditions';
import { useForecastTimeline } from '../hooks/useForecastTimeline';
import { OrcaForecastChart } from '../components/charts/OrcaForecastChart';
import { OrcaTrendChart } from '../components/charts/OrcaTrendChart';
import { useTrends } from '../hooks/useTrends';
import { applySeaTodayLive, pendingSeaToday, toSeaStatus } from '../data/liveAdapters';

// Reusing the existing watercolor background from safety/find fish pages
const BACKGROUND_IMAGE = '/assets/orca_safety_background.avif';

interface SeaTodayPageProps {
  currentLanguage?: LanguageOption;
  onNavigateHome: () => void;
  onNavigateTab?: (tab: NavTabId) => void;
  locationName?: string;
  latitude?: number;
  longitude?: number;
  onLocationClick?: () => void;
}

export const SeaTodayPage: React.FC<SeaTodayPageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateTab,
  locationName = 'Digha, West Bengal',
  latitude,
  longitude,
  onLocationClick,
}) => {
  // The sea state is read from the live forecast, not chosen by hand.
  const { data: live, loading, error } = useConditions(latitude, longitude);
  // The hourly series behind the chart. Fetched alongside, not inside, the
  // conditions hook so a slow series never holds up the status card above it.
  const { data: timeline, error: timelineError } = useForecastTimeline(latitude, longitude);
  // A decade deep, and the slowest call in the app — so the section simply
  // appears when it lands rather than holding anything above it.
  const { data: trends, loading: trendsLoading } = useTrends(latitude, longitude);

  const langCode = currentLanguage?.code || 'en';
  const translations = getSeaTodayTranslations(langCode);
  const seaStatus: SeaStatus = live ? toSeaStatus(live.seaToday.seaStatus) : 'calm';
  const baseData = getSeaTodayData(seaStatus, langCode, locationName);
  const data = live
    ? applySeaTodayLive(baseData, live, {
        good: translations.adviceCalmTitle,
        caution: translations.adviceModerateTitle,
        danger: translations.adviceRoughTitle,
      })
    : pendingSeaToday(baseData, !loading && !!error);

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
      id="orca-sea-today-page"
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
        - Minimal scrolling required: 3-second comprehension
        ===================================================================
      */}
      <main className="relative z-10 w-full max-w-[640px] mx-auto px-4 min-[390px]:px-5 sm:px-6 safe-pt pb-28 min-[390px]:pb-32 sm:pb-36 flex flex-col items-stretch">
        {/* 
          1. TOP HEADER:
          ←  ORCA       📍 Digha, West Bengal
        */}
        <OrcaSeaTodayHeader
          onLocationClick={onLocationClick}
          onBackClick={onNavigateHome}
          currentLanguage={currentLanguage}
          locationName={locationName}
        />

        {/* 
          2. PAGE TITLE:
          - Cormorant Garamond heading: "Sea Today"
          - Small DM Sans text: "“Know the sea before you go.”"
          - Constrained width (max-w-[56%] on mobile) so the scenic boat, mountains, and sea remain 100% visible on the right
        */}
        <div className="w-full mt-2.5 min-[390px]:mt-3 sm:mt-4 flex flex-col items-start select-none max-w-[56%] min-[390px]:max-w-[58%] sm:max-w-none">
          <h1
            className="font-display font-bold text-[34px] min-[390px]:text-[38px] sm:text-[44px] text-[#062A43] leading-[1.05] tracking-tight"
            id="sea-today-title"
          >
            {translations.pageTitle}
          </h1>

          <p className="font-ui font-normal text-[13.5px] min-[390px]:text-[14.5px] sm:text-[16px] text-[#274A62] leading-[1.35] mt-1.5 sm:mt-2">
            “{translations.pageSubtitle}”
          </p>
        </div>

        {/* 
          3. MAIN SEA STATUS:
          - ONE large status card
          - Dominant CALM SEA + Good day for fishing + 🟢 Good conditions
          - Visually dominant focal point
          - Lowered on mobile so the scenic boat and sea ripples are fully visible, matching the Find Fish and Safety sections
        */}
        <div className="w-full mt-[80px] min-[390px]:mt-[88px] sm:mt-9">
          <OrcaSeaStatusCard
            data={data}
          />
        </div>

        {/* 
          4. KEY CONDITIONS:
          - Title: "Today"
          - 2 × 2 simple grid with 4 cards:
            Wind (12 km/h - Moderate)
            Waves (0.8 m - Calm)
            Rain (0 mm - No rain)
            Visibility (10+ km - Good)
        */}
        <div className="w-full mt-5 sm:mt-6">
          <OrcaSeaTodayConditions
            conditions={data.conditions}
            title={translations.conditionsTitle}
          />
        </div>

        {/* 
          5. TODAY'S SIMPLE FORECAST:
          - Title: "Today"
          - Glanceable horizontal forecast strip:
            6 AM, 9 AM, 12 PM, 3 PM, 6 PM
        */}
        <div className="w-full mt-5 sm:mt-6">
          <OrcaSeaTodayForecast
            forecast={data.forecast}
            title={translations.forecastTitle}
          />
        </div>

        {/*
          5b. THE 48-HOUR CHART:
          - Wave and wind traces drawn against IMD's and INCOIS's own warning
            levels, so "safe until 10:00" becomes something the reader can see
            rather than a sentence they have to believe.
        */}
        <div className="w-full mt-5 sm:mt-6">
          {timeline ? (
            <OrcaForecastChart timeline={timeline} />
          ) : timelineError ? (
            <p className="font-ui text-[12.5px] text-[#B45309] px-1">
              The hourly forecast could not be loaded, so the 48-hour chart is not shown.
            </p>
          ) : null}
        </div>

        {/*
          5c. HAS THE SEA CHANGED?
          - Ten years of the same weeks, from ERA5 and NOAA's satellite record.
            The one question ORCA could not previously approach — and the one
            place it has to say out loud what it does not measure.
        */}
        <div className="w-full mt-5 sm:mt-6">
          {trends ? (
            <OrcaTrendChart trends={trends} />
          ) : trendsLoading ? (
            <p className="font-ui text-[12.5px] text-[#8AA0B0] px-1">
              Reading ten years of records for this place…
            </p>
          ) : null}
        </div>

        {/* 
          6. IMPORTANT ADVICE:
          - One small advice card:
            💡 Good to go - “Sea conditions look good today.”
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaSeaTodayAdvice advice={data.advice} />
        </div>

        {/* 
          7. ASK ORCA:
          - Compact voice card near bottom
            Ask ORCA - “Want to know more?”
        */}
        <div className="w-full mt-4 sm:mt-5">
          <OrcaSeaTodayAskOrca translations={translations} />
        </div>
      </main>

      {/* 
        8. PERSISTENT 5-ITEM BOTTOM NAVIGATION:
        Home, Map, Ask, Alerts, Profile
        Home remains the active navigation context
      */}
      <OrcaBottomNav
        activeTab="home"
        currentLanguage={currentLanguage}
        onTabChange={handleTabChange}
      />
    </div>
  );
};