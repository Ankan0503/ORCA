import React, { useState, useEffect, useCallback } from 'react';
import { ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import { BackgroundImage } from './components/BackgroundImage';
import { Logo } from './components/Logo';
import { LanguageSelector } from './components/LanguageSelector';
import { OrcaLocationPicker } from './components/OrcaLocationPicker';
import { UserLocation, loadStoredLocation, storeLocation } from './data/location';
import { getHomeTranslation } from './data/homeTranslations';
import { GetStartedModal } from './components/GetStartedModal';
import { EditorialInfoModal } from './components/EditorialInfoModal';
import { OrcaHomeHero } from './components/OrcaHomeHero';
import { OrcaFeatureCards } from './components/OrcaFeatureCards';
import { OrcaAskSection } from './components/OrcaAskSection';
import { OrcaBottomNav } from './components/OrcaBottomNav';
import { SafetyPage } from './pages/SafetyPage';
import { FindFishPage } from './pages/FindFishPage';
import { SeaTodayPage } from './pages/SeaTodayPage';
import { AlertsPage } from './pages/AlertsPage';
import { AskOrcaPage } from './pages/AskOrcaPage';
import { MapPage } from './pages/MapPage';
import { ProfilePage } from './pages/ProfilePage';
import { loginUser } from './data/auth';
import { LANGUAGES } from './data/languages';
import { LanguageOption, ModalType } from './types';

// =========================================================================
// ASSET CONFIGURATION
// Separate Mobile & Desktop Hero Assets:
// Browser media queries ensure only the relevant asset is fetched.
// =========================================================================
const MOBILE_HERO_IMAGE = '/assets/landing/orca_landing_background.avif';
const DESKTOP_HERO_IMAGE = '/assets/landing/orca_desktop_hero.avif';
const ORCA_LOGO = '/assets/orca-logo.svg';

/**
 * Resolves current route from the URL pathname and hash.
 * - /ask, /ask/, #/ask, #ask -> 'ask'
 * - /alerts, /alerts/, #/alerts, #alerts -> 'alerts'
 * - /sea-today, /sea-today/, #/sea-today, #sea-today -> 'sea-today'
 * - /find-fish, /find-fish/, #/find-fish, #find-fish -> 'find-fish'
 * - /safety, /safety/, #/safety, #safety -> 'safety'
 * - /home, /home/, #/home, #home -> 'home'
 * - /landing, /landing/, #/landing, #landing -> 'landing'
 * - / -> 'landing'
 */
const getRouteFromUrl = (): 'home' | 'landing' | 'safety' | 'find-fish' | 'sea-today' | 'alerts' | 'ask' | 'map' | 'profile' => {
  if (typeof window === 'undefined') return 'home';
  const pathname = window.location.pathname.toLowerCase().replace(/\/$/, '') || '/';
  const hash = window.location.hash.toLowerCase().replace(/^#/, '').replace(/\/$/, '') || '';

  if (pathname === '/profile' || hash === '/profile' || hash === 'profile') {
    return 'profile';
  }
  if (pathname === '/map' || hash === '/map' || hash === 'map') {
    return 'map';
  }
  if (pathname === '/ask' || hash === '/ask' || hash === 'ask') {
    return 'ask';
  }
  if (pathname === '/alerts' || hash === '/alerts' || hash === 'alerts') {
    return 'alerts';
  }
  if (pathname === '/sea-today' || hash === '/sea-today' || hash === 'sea-today') {
    return 'sea-today';
  }
  if (pathname === '/find-fish' || hash === '/find-fish' || hash === 'find-fish') {
    return 'find-fish';
  }
  if (pathname === '/safety' || hash === '/safety' || hash === 'safety') {
    return 'safety';
  }
  if (pathname === '/home' || hash === '/home' || hash === 'home') {
    return 'home';
  }
  if (pathname === '/landing' || hash === '/landing' || hash === 'landing') {
    return 'landing';
  }
  return 'landing';
};

export default function App() {
  const [currentRoute, setCurrentRoute] = useState<'home' | 'landing' | 'safety' | 'find-fish' | 'sea-today' | 'alerts' | 'ask' | 'map' | 'profile'>(getRouteFromUrl);
  const [currentLanguage, setCurrentLanguage] = useState<LanguageOption>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('orca_lang');
      if (saved) {
        const found = LANGUAGES.find((l) => l.code === saved);
        if (found) return found;
      }
    }
    return LANGUAGES[0];
  });
  const [activeModal, setActiveModal] = useState<ModalType>(null);

  // Where the user actually is. Every forecast, fishing zone and boundary
  // distance is tied to this, so it is app-level state rather than per page.
  const [location, setLocation] = useState<UserLocation>(loadStoredLocation);
  const [isLocationPickerOpen, setIsLocationPickerOpen] = useState(false);

  const handleLocationSelected = useCallback((next: UserLocation) => {
    setLocation(next);
    storeLocation(next);
    setIsLocationPickerOpen(false);
  }, []);

  const openLocationPicker = useCallback(() => setIsLocationPickerOpen(true), []);

  // Rendered alongside every route: each page returns early, so the picker has
  // to travel with them rather than sit at the bottom of one tree.
  const locationPicker = (
    <OrcaLocationPicker
      isOpen={isLocationPickerOpen}
      current={location}
      onClose={() => setIsLocationPickerOpen(false)}
      onSelect={handleLocationSelected}
      translations={getHomeTranslation(currentLanguage.code).location}
    />
  );

  const handleLanguageChange = useCallback((lang: LanguageOption) => {
    setCurrentLanguage(lang);
    if (typeof window !== 'undefined') {
      localStorage.setItem('orca_lang', lang.code);
    }
  }, []);

  const navigateTo = useCallback((route: 'home' | 'landing' | 'safety' | 'find-fish' | 'sea-today' | 'alerts' | 'ask' | 'map' | 'profile') => {
    const targetPath =
      route === 'home'
        ? '/home'
        : route === 'safety'
        ? '/safety'
        : route === 'find-fish'
        ? '/find-fish'
        : route === 'sea-today'
        ? '/sea-today'
        : route === 'alerts'
        ? '/alerts'
        : route === 'ask'
        ? '/ask'
        : route === 'map'
        ? '/map'
        : route === 'profile'
        ? '/profile'
        : '/';
    if (typeof window !== 'undefined' && window.location.pathname !== targetPath) {
      window.history.pushState({}, '', targetPath);
    }
    setCurrentRoute(route);
  }, []);

  // Listen to browser navigation (back/forward & hash changes)
  useEffect(() => {
    const handlePopState = () => {
      setCurrentRoute(getRouteFromUrl());
    };

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, []);

  const isIndic = currentLanguage.code !== 'en';

  if (currentRoute === 'profile') {
    return (
      <>
        <ProfilePage
          currentLanguage={currentLanguage}
          onNavigateHome={() => navigateTo('home')}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
          onNavigateLanding={() => navigateTo('landing')}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'map') {
    return (
      <>
        <MapPage
          currentLanguage={currentLanguage}
          locationName={location.name}
          onLocationClick={openLocationPicker}
          onNavigateHome={() => navigateTo('home')}
          onNavigateFindFish={() => navigateTo('find-fish')}
          onNavigateSafety={() => navigateTo('safety')}
          onNavigateAlerts={() => navigateTo('alerts')}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'ask') {
    return (
      <>
        <AskOrcaPage
          currentLanguage={currentLanguage}
          locationName={location.name}
          onLocationClick={openLocationPicker}
          onNavigateHome={() => navigateTo('home')}
          onNavigateRoute={(route) => navigateTo(route)}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'alerts') {
    return (
      <>
        <AlertsPage
          currentLanguage={currentLanguage}
          locationName={location.name}
          onLocationClick={openLocationPicker}
          onNavigateHome={() => navigateTo('home')}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'sea-today') {
    return (
      <>
        <SeaTodayPage
          currentLanguage={currentLanguage}
          locationName={location.name}
          onLocationClick={openLocationPicker}
          onNavigateHome={() => navigateTo('home')}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'find-fish') {
    return (
      <>
        <FindFishPage
          currentLanguage={currentLanguage}
          locationName={location.name}
          onLocationClick={openLocationPicker}
          onNavigateHome={() => navigateTo('home')}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'safety') {
    return (
      <>
        <SafetyPage
          currentLanguage={currentLanguage}
          locationName={location.name}
          onLocationClick={openLocationPicker}
          onNavigateHome={() => navigateTo('home')}
          onNavigateTab={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />
        {locationPicker}
      </>
    );
  }

  if (currentRoute === 'home') {
    return (
      <div className="relative w-full min-h-[100svh] min-h-[100dvh] overflow-x-hidden bg-[#F7FAFC]">
        <main
          className="relative w-full min-h-full overflow-y-auto overflow-x-hidden bg-[#F7FAFC] text-[#062A43] flex flex-col select-none pb-28 min-[390px]:pb-32 sm:pb-36"
          id="orca-home-main"
        >
          {/* Top/Hero portion of the ORCA authenticated home screen */}
          <OrcaHomeHero
            currentLanguage={currentLanguage}
            onLanguageChange={handleLanguageChange}
            locationName={location.name}
            onLocationClick={openLocationPicker}
          />

          {/* 
            Four Primary Sea Operation Feature Cards:
            Directly underneath "What do you need today?"
            - “Is it safe?” card navigates to /safety
            - “Find Fish” card navigates to /find-fish
            - “Sea Today” card navigates to /sea-today
            - “Alerts” card navigates to /alerts
          */}
          <OrcaFeatureCards
            currentLanguage={currentLanguage}
            onCardClick={(cardId) => {
              if (cardId === 'is-it-safe') {
                navigateTo('safety');
              } else if (cardId === 'find-fish') {
                navigateTo('find-fish');
              } else if (cardId === 'sea-today') {
                navigateTo('sea-today');
              } else if (cardId === 'alerts') {
                navigateTo('alerts');
              }
            }}
          />

          {/* 
            Ask ORCA Section:
            Directly underneath the four feature cards
            Navigates to /ask when clicked
          */}
          <OrcaAskSection
            currentLanguage={currentLanguage}
            onCardClick={() => navigateTo('ask')}
            onVoiceClick={() => navigateTo('ask')}
            onSuggestionClick={() => navigateTo('ask')}
          />
        </main>

        {/* 
          Fixed Bottom Navigation Bar:
          5 tabs (Home, Map, Ask, Alerts, Profile) with active Home indicator
        */}
        <OrcaBottomNav
          activeTab="home"
          currentLanguage={currentLanguage}
          onTabChange={(tab) => {
            if (tab === 'home') {
              navigateTo('home');
            } else if (tab === 'map') {
              navigateTo('map');
            } else if (tab === 'alerts') {
              navigateTo('alerts');
            } else if (tab === 'ask') {
              navigateTo('ask');
            } else if (tab === 'profile') {
              navigateTo('profile');
            }
          }}
        />

        {locationPicker}
      </div>
    );
  }

  return (
    <main
      className="relative w-full min-h-[100svh] min-h-[100dvh] overflow-y-auto overflow-x-hidden bg-[#F6F3ED] text-[#062A43] flex flex-col justify-between select-none"
      id="orca-landing-main"
    >
      {/* 
        ===================================================================
        CINEMATIC HERO BACKGROUND (The emotional center of the page)
        Responsive: Only the device-matching image is downloaded!
        ===================================================================
      */}
      <BackgroundImage
        mobileSrc={MOBILE_HERO_IMAGE}
        desktopSrc={DESKTOP_HERO_IMAGE}
      />

      {/* 
        ===================================================================
        PAGE CONTAINER (Mobile-first, scales gracefully from 320px to 1200px)
        ===================================================================
      */}
      <div className="relative z-20 w-full min-h-[100svh] min-h-[100dvh] max-w-[1200px] mx-auto flex flex-col px-4 min-[390px]:px-6 sm:px-8 md:px-12 safe-pt safe-pb pt-2 sm:pt-4 pb-3 sm:pb-4">
        
        {/* -------------------------------------------------------------
            TOP NAVIGATION ROW (Mobile First)
            Mobile: Unboxed Logo on left, LanguageSelector on right
            Desktop: Logo on left, subtle nav links + language on right
        ------------------------------------------------------------- */}
        <header className="w-full shrink-0 flex items-center justify-between gap-3 pt-1 sm:pt-2">
          {/* Top-Left: Clean unboxed Logo */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="shrink-0"
          >
            <Logo logoSrc={ORCA_LOGO} />
          </motion.div>

          {/* Top-Right: Navigation & Language Selector */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="flex items-center gap-2.5 sm:gap-4 md:gap-6"
          >
            {/* Desktop Links (Artistic Flair Frosted Pill Links) */}
            <nav className="hidden md:flex items-center gap-2.5 text-[14px] text-[#062A43] font-ui font-medium tracking-wide">
              <button
                type="button"
                onClick={() => setActiveModal('about')}
                className="px-4 py-2 rounded-full bg-white/50 hover:bg-white/75 border border-[#062A43]/15 transition-all cursor-pointer backdrop-blur-md shadow-xs active:scale-98"
              >
                About
              </button>
              <button
                type="button"
                onClick={() => setActiveModal('how-it-helps')}
                className="px-4 py-2 rounded-full bg-white/50 hover:bg-white/75 border border-[#062A43]/15 transition-all cursor-pointer backdrop-blur-md shadow-xs active:scale-98"
              >
                How ORCA Helps
              </button>
              <button
                type="button"
                onClick={() => setActiveModal('safety')}
                className="px-4 py-2 rounded-full bg-white/50 hover:bg-white/75 border border-[#062A43]/15 transition-all cursor-pointer backdrop-blur-md shadow-xs active:scale-98"
              >
                Safety
              </button>
            </nav>

            {/* Language Selector (Touch-friendly & compact on mobile) */}
            <LanguageSelector
              currentLanguage={currentLanguage}
              onSelectLanguage={handleLanguageChange}
            />
          </motion.div>
        </header>

        {/* -------------------------------------------------------------
            TOP EDITORIAL HERO CONTENT (Comfortably spaced below header)
            Clear reading zone at eye level: Eyebrow + Headline + Supporting text
        ------------------------------------------------------------- */}
        <div className="w-full mt-6 min-[390px]:mt-8 sm:mt-8 md:mt-8 lg:mt-8 lg:w-[54%] xl:w-[48%] flex flex-col items-start text-left">
          
          {/* Eyebrow: Uppercase marine statement */}
          <motion.div
            key={`eyebrow-${currentLanguage.code}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
            className="mb-2.5 sm:mb-3"
          >
            <p
              className={`font-ui text-[#062A43] font-semibold leading-snug whitespace-pre-line drop-shadow-[0_1px_2px_rgba(255,255,255,0.8)] ${
                isIndic
                  ? 'text-[11px] min-[360px]:text-[11.5px] sm:text-[12.5px] tracking-normal'
                  : 'text-[11px] min-[360px]:text-[12px] sm:text-[13px] tracking-[0.2em] sm:tracking-[0.22em] uppercase'
              }`}
            >
              {currentLanguage.eyebrow}
            </p>
            {/* Thin horizontal decorative line */}
            <div className="w-10 sm:w-12 h-[1px] bg-[#062A43] mt-2 sm:mt-2.5 opacity-35" />
          </motion.div>

          {/* Main Headline: Optically balanced between English Display Serif and Indic glyph metrics */}
          <motion.h1
            key={`headline-${currentLanguage.code}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
            className={`text-[#062A43] mb-2 sm:mb-3 max-w-2xl drop-shadow-[0_1px_2px_rgba(255,255,255,0.8)] ${
              isIndic
                ? 'font-ui font-semibold text-[23px] min-[360px]:text-[26px] min-[390px]:text-[28px] sm:text-[36px] md:text-[44px] lg:text-[50px] leading-[1.28] sm:leading-[1.22] tracking-normal'
                : 'font-display font-medium tracking-tight leading-[0.94] sm:leading-[0.92] text-[38px] min-[360px]:text-[44px] min-[390px]:text-[48px] sm:text-[66px] md:text-[78px] lg:text-[88px]'
            }`}
          >
            <span className="block">{currentLanguage.headlineLine1}</span>
            <span className="block">{currentLanguage.headlineLine2}</span>
          </motion.h1>

          {/* Supporting Text: Legible, calm, respectful for coastal fishermen */}
          <motion.p
            key={`supporting-${currentLanguage.code}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className={`font-ui text-[#062A43]/90 font-medium leading-relaxed drop-shadow-[0_1px_2px_rgba(255,255,255,0.7)] ${
              isIndic
                ? 'text-[13px] min-[360px]:text-[14px] sm:text-[15.5px] md:text-[17px] max-w-[320px] sm:max-w-[420px]'
                : 'text-[14.5px] min-[360px]:text-[15.5px] sm:text-[17px] md:text-xl max-w-[320px] sm:max-w-[380px]'
            }`}
          >
            {currentLanguage.supporting}
          </motion.p>

          {/* Desktop Primary CTA: Prominently sized & placed directly below hero text */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.32, ease: [0.22, 1, 0.36, 1] }}
            className="hidden lg:block mt-7 xl:mt-8"
          >
            <button
              type="button"
              id="orca-primary-cta-desktop"
              onClick={() => {
                loginUser();
                navigateTo('home');
              }}
              className={`group inline-flex items-center justify-center gap-3 h-[54px] bg-[#E07A22] hover:bg-[#CB6B18] text-white rounded-full font-semibold transition-all duration-200 shadow-[0_6px_22px_rgba(224,122,34,0.38)] hover:shadow-[0_8px_28px_rgba(224,122,34,0.48)] hover:scale-[1.02] active:scale-95 cursor-pointer focus:outline-hidden focus:ring-3 focus:ring-[#E07A22]/40 border border-white/20 ${
                isIndic
                  ? 'px-8 text-[16px]'
                  : 'px-9 text-[17px]'
              }`}
              aria-label="Begin Sea Operations"
            >
              <span className="drop-shadow-[0_1px_1px_rgba(0,0,0,0.25)]">{currentLanguage.cta}</span>
              <ArrowRight
                size={19}
                className="transition-transform duration-200 group-hover:translate-x-1.5 shrink-0"
              />
            </button>
          </motion.div>
        </div>

        {/* -------------------------------------------------------------
            BOTTOM ONE-HANDED ACTION & TRUST ZONE (Anchored at the bottom)
            - Phone: Compact, high-contrast sunrise amber pill in thumb zone
            - Desktop: Trust statement cleanly anchored
        ------------------------------------------------------------- */}
        <div className="mt-auto w-full lg:w-[54%] xl:w-[48%] pt-6 pb-1 sm:pb-2 flex flex-col items-start gap-3 sm:gap-4">
          
          {/* Mobile-Only Primary CTA: Compact & high-contrast in natural thumb sweep zone */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.48, ease: [0.22, 1, 0.36, 1] }}
            className="lg:hidden"
          >
            <button
              type="button"
              id="orca-primary-cta"
              onClick={() => {
                loginUser();
                navigateTo('home');
              }}
              className={`group inline-flex items-center justify-center gap-2 sm:gap-2.5 h-[42px] min-[360px]:h-[44px] sm:h-[50px] bg-[#E07A22] hover:bg-[#CB6B18] text-white rounded-full font-semibold transition-all duration-200 shadow-[0_4px_16px_rgba(0,0,0,0.35)] active:scale-95 cursor-pointer focus:outline-hidden focus:ring-3 focus:ring-[#E07A22]/40 border border-white/20 ${
                isIndic
                  ? 'px-4 min-[360px]:px-5 sm:px-6 text-[13px] min-[360px]:text-[13.5px] sm:text-[15px]'
                  : 'px-5 sm:px-7 text-[14px] sm:text-[16px]'
              }`}
              aria-label="Begin Sea Operations"
            >
              <span className="drop-shadow-[0_1px_1px_rgba(0,0,0,0.2)]">{currentLanguage.cta}</span>
              <ArrowRight
                size={16}
                className="transition-transform duration-200 group-hover:translate-x-1 shrink-0"
              />
            </button>
          </motion.div>

          {/* Footer: "Built with..." line with guaranteed high contrast on both desktop and mobile */}
          <footer className="w-full">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.45, ease: 'easeOut' }}
              className="w-full text-left"
            >
              <div className="inline-flex items-center gap-2.5 py-1.5 px-3 min-[390px]:px-3.5 rounded-full bg-[#062A43]/90 text-white border border-white/25 shadow-[0_4px_16px_rgba(0,0,0,0.3)] backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0 shadow-[0_0_8px_rgba(52,211,153,0.9)] animate-pulse" />
                <p
                  className={`font-ui text-white font-medium uppercase leading-tight tracking-wide drop-shadow-[0_1px_2px_rgba(0,0,0,0.5)] ${
                    isIndic
                      ? 'text-[11px] sm:text-[12px] tracking-normal'
                      : 'text-[11px] sm:text-[12px] tracking-wider'
                  }`}
                >
                  {currentLanguage.trust}
                </p>
              </div>
            </motion.div>
          </footer>
        </div>
      </div>

      {/* 
        ===================================================================
        INTERACTIVE SHEETS & MODALS (Mobile-first bottom sheets)
        ===================================================================
      */}
      <GetStartedModal
        isOpen={activeModal === 'get-started'}
        onClose={() => setActiveModal(null)}
        language={currentLanguage}
        onSuccess={() => {
          setActiveModal(null);
          loginUser();
          navigateTo('home');
        }}
      />

      <EditorialInfoModal
        type={activeModal}
        onClose={() => setActiveModal(null)}
      />
    </main>
  );
}
