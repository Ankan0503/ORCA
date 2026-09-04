import React from 'react';
import { ArrowRight } from 'lucide-react';
import { LanguageOption } from '../types';
import { getHomeTranslation } from '../data/homeTranslations';

interface OrcaFeatureCardsProps {
  currentLanguage?: LanguageOption;
  onCardClick?: (cardId: string) => void;
}

interface FeatureCardConfig {
  id: 'find-fish' | 'is-it-safe' | 'sea-today' | 'alerts';
  bg: string;
  iconSrc: string;
  iconHeightClass: string;
}

const CARDS_CONFIG: FeatureCardConfig[] = [
  {
    id: 'find-fish',
    bg: '#E4F3FC', // very light ocean blue
    iconSrc: '/assets/home/orca_fish.avif',
    iconHeightClass: 'h-[36px] min-[390px]:h-[40px] sm:h-[44px]',
  },
  {
    id: 'is-it-safe',
    bg: '#FFF4E2', // very light warm cream/beige
    iconSrc: '/assets/home/orca_safety_shield.svg',
    iconHeightClass: 'h-[38px] min-[390px]:h-[42px] sm:h-[46px]',
  },
  {
    id: 'sea-today',
    bg: '#E3F5F1', // very light mint/seafoam green
    iconSrc: '/assets/home/orca_wave.svg',
    iconHeightClass: 'h-[32px] min-[390px]:h-[36px] sm:h-[40px]',
  },
  {
    id: 'alerts',
    bg: '#FBE7E7', // very light pale pink/coral
    iconSrc: '/assets/home/orca_alert.svg',
    iconHeightClass: 'h-[34px] min-[390px]:h-[38px] sm:h-[42px]',
  },
];

export const OrcaFeatureCards: React.FC<OrcaFeatureCardsProps> = ({
  currentLanguage,
  onCardClick,
}) => {
  const langCode = currentLanguage?.code || 'en';
  const homeTranslation = getHomeTranslation(langCode);
  const cardsTranslation = homeTranslation.cards;

  return (
    <section
      className="relative w-full max-w-[1200px] mx-auto px-5 sm:px-6 md:px-8 mt-0 pb-12 sm:pb-16 select-none"
      id="orca-feature-cards-section"
      aria-label="Sea Operations Features"
    >
      {/* 
        ===================================================================
        2-COLUMN GRID (Row 1: Find Fish, Is it safe? | Row 2: Sea Today, Alerts)
        - Mobile reference width ~390px
        - 2 equal columns across 360px, 390px, 430px, and desktop
        - Horizontal and vertical gap ~14-16px
        - Corner radius 18–20px
        - auto-rows-fr ensures cards on the same row match height seamlessly
        ===================================================================
      */}
      <div className="grid grid-cols-2 gap-3.5 min-[390px]:gap-4 sm:gap-5 md:gap-6 w-full max-w-[880px] auto-rows-fr">
        {CARDS_CONFIG.map((card) => {
          const content = cardsTranslation[card.id] || cardsTranslation['find-fish'];
          const cardLabel = `${content.title}: ${content.description}`;

          return (
            <button
              key={card.id}
              id={`orca-card-${card.id}`}
              type="button"
              onClick={() => onCardClick?.(card.id)}
              aria-label={cardLabel}
              style={{ backgroundColor: card.bg }}
              className="group relative flex flex-col justify-between items-start text-left w-full min-h-[178px] min-[390px]:min-h-[186px] sm:min-h-[196px] h-full p-3.5 min-[390px]:p-4 sm:p-5 rounded-[18px] min-[390px]:rounded-[20px] transition-all duration-200 hover:shadow-[0_6px_20px_rgba(6,42,67,0.08)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.985] cursor-pointer focus:outline-hidden focus-visible:ring-3 focus-visible:ring-[#062A43]/30"
            >
              {/* 
                Upper Portion: Illustration
                Placed toward the upper portion, original proportions preserved
              */}
              <div className="w-full flex items-center justify-start h-[40px] min-[390px]:h-[44px] shrink-0">
                <img
                  src={card.iconSrc}
                  alt=""
                  className={`${card.iconHeightClass} w-auto max-w-[85%] object-contain object-left block`}
                  loading="eager"
                  decoding="async"
                />
              </div>

              {/* 
                Text Hierarchy: Title then Short Description
                Clean typography in DM Sans (font-ui), bold navy title, muted blue-gray description
                break-words and whitespace-normal prevent overflow in all script languages
              */}
              <div className="w-full flex flex-col items-start mt-2">
                <h2 className="font-ui font-semibold text-[15.5px] min-[390px]:text-[17px] sm:text-[19px] text-[#062A43] leading-[1.2] tracking-tight break-words max-w-full">
                  {content.title}
                </h2>
                <p className="font-ui font-normal text-[12px] min-[390px]:text-[13px] sm:text-[14px] text-[#3E5C73] leading-[1.35] mt-1 break-words whitespace-normal tracking-normal pr-9 min-[390px]:pr-11 pb-2">
                  {content.description}
                </p>
              </div>

              {/* 
                Bottom-Right Circular White Arrow Button
                - Pure/near-white background
                - Subtle shadow
                - Dark navy right arrow icon
                - Centered and minimal
              */}
              <div
                className="absolute bottom-3 right-3 min-[390px]:bottom-3.5 min-[390px]:right-3.5 sm:bottom-4 sm:right-4 w-[38px] h-[38px] min-[390px]:w-[42px] min-[390px]:h-[42px] sm:w-[46px] sm:h-[46px] rounded-full bg-white shadow-[0_2px_8px_rgba(6,42,67,0.08)] flex items-center justify-center shrink-0 group-hover:scale-105 group-active:scale-95 transition-transform duration-150"
                aria-hidden="true"
              >
                <ArrowRight
                  size={18}
                  className="text-[#062A43] stroke-[2.3] group-hover:translate-x-0.5 transition-transform duration-150"
                />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
};

export default OrcaFeatureCards;
