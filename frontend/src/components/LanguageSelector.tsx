import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { LANGUAGES } from '../data/languages';
import { LanguageOption } from '../types';

interface LanguageSelectorProps {
  currentLanguage: LanguageOption;
  onSelectLanguage: (lang: LanguageOption) => void;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  currentLanguage,
  onSelectLanguage,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={containerRef} id="orca-language-selector-wrap">
      <button
        id="orca-language-toggle-btn"
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Select language"
        className="group flex items-center justify-between gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 h-[36px] sm:h-[40px] min-w-[88px] sm:min-w-[100px] rounded-full bg-white/50 hover:bg-white/70 backdrop-blur-md border border-[#062A43]/15 shadow-xs transition-all duration-200 text-[#062A43] font-ui text-[13px] sm:text-[14px] font-semibold leading-none cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-[#062A43]/30 active:scale-98"
      >
        <span className="truncate tracking-tight font-medium">{currentLanguage.nativeName}</span>
        <ChevronDown
          size={13}
          className={`shrink-0 text-[#062A43]/80 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            id="orca-language-dropdown"
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
            className="absolute right-0 mt-2 w-40 rounded-2xl bg-white/95 backdrop-blur-xl border border-white/40 shadow-xl z-50 overflow-hidden font-ui"
            role="listbox"
          >
            {/*
              The scroll container is the dropdown body itself, with no padded
              wrapper above it — otherwise a wheel over that padding scrolls the
              page instead of the list. `orca-scrollarea` keeps the scrollbar
              visible so it is obvious there are more languages below.
            */}
            <div className="max-h-[232px] overflow-y-auto overscroll-contain py-1.5 orca-scrollarea">
              {LANGUAGES.map((lang) => {
                const isSelected = lang.code === currentLanguage.code;
                return (
                  <button
                    key={lang.code}
                    id={`orca-lang-option-${lang.code}`}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onSelectLanguage(lang);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between gap-2 px-3.5 py-2 text-left text-[13px] transition-colors duration-150 cursor-pointer ${
                      isSelected
                        ? 'bg-[#062A43]/10 text-[#062A43] font-semibold'
                        : 'text-[#062A43]/80 hover:bg-[#062A43]/5 hover:text-[#062A43]'
                    }`}
                  >
                    {/* Native name only — a speaker recognises their own script,
                        and the English gloss just made every row twice as tall. */}
                    <span className="min-w-0 truncate leading-snug font-medium text-[13.5px]">
                      {lang.nativeName}
                    </span>
                    {isSelected && <Check size={14} className="text-[#062A43] shrink-0" />}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
