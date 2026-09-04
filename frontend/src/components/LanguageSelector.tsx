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
        <span className="truncate tracking-tight font-medium">{currentLanguage.name}</span>
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
            className="absolute right-0 mt-2 w-48 rounded-2xl bg-white/95 backdrop-blur-xl border border-white/40 shadow-xl py-2 z-50 overflow-hidden font-ui"
            role="listbox"
          >
            <div className="max-h-64 overflow-y-auto py-0.5 overscroll-contain">
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
                    className={`w-full flex items-center justify-between px-4 py-2.5 text-left text-[13px] transition-colors duration-150 cursor-pointer ${
                      isSelected
                        ? 'bg-[#062A43]/10 text-[#062A43] font-semibold'
                        : 'text-[#062A43]/80 hover:bg-[#062A43]/5 hover:text-[#062A43]'
                    }`}
                  >
                    <div className="flex flex-col">
                      <span className="leading-tight font-medium">{lang.name}</span>
                      <span className="text-[11px] text-[#062A43]/50 font-normal">
                        {lang.nativeName}
                      </span>
                    </div>
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
