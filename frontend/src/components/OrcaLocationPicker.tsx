import React, { useEffect, useRef, useState } from 'react';
import { Crosshair, LoaderCircle, MapPin, Search, X } from 'lucide-react';
import { PlaceResult, reverseGeocode, searchPlaces } from '../services/orcaApi';
import { UserLocation, coordinateLabel } from '../data/location';
import { LocationTranslation } from '../data/homeTranslations';

interface OrcaLocationPickerProps {
  isOpen: boolean;
  current: UserLocation;
  onClose: () => void;
  onSelect: (location: UserLocation) => void;
  translations: LocationTranslation;
}

type DetectState = 'idle' | 'detecting' | 'blocked' | 'failed';

export const OrcaLocationPicker: React.FC<OrcaLocationPickerProps> = ({
  isOpen,
  current,
  onClose,
  onSelect,
  translations,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [detectState, setDetectState] = useState<DetectState>('idle');
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    // Reset on both edges: a detection error from a previous visit must not
    // greet the user as though they had just pressed the button again.
    setQuery('');
    setResults([]);
    setDetectState('idle');

    if (!isOpen) return;
    // Focus the search field on open: typing a place is the common case.
    const id = window.setTimeout(() => inputRef.current?.focus(), 80);
    return () => window.clearTimeout(id);
  }, [isOpen]);

  // Debounced search. The abort controller stops an older, slower response from
  // overwriting the results of a newer query.
  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) {
      setResults([]);
      setIsSearching(false);
      return;
    }

    const controller = new AbortController();
    setIsSearching(true);
    const id = window.setTimeout(async () => {
      try {
        setResults(await searchPlaces(term, controller.signal));
      } catch {
        if (!controller.signal.aborted) setResults([]);
      } finally {
        if (!controller.signal.aborted) setIsSearching(false);
      }
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(id);
    };
  }, [query]);

  const choosePlace = (place: PlaceResult) => {
    onSelect({
      name: [place.name, place.admin].filter(Boolean).join(', '),
      latitude: place.latitude,
      longitude: place.longitude,
      source: 'manual',
    });
  };

  const detect = () => {
    if (!navigator.geolocation) {
      setDetectState('failed');
      return;
    }
    setDetectState('detecting');

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        // The coordinate is what the forecast needs; the name is decoration, so
        // a failed lookup still yields a usable location.
        let name = coordinateLabel(latitude, longitude);
        try {
          const place = await reverseGeocode(latitude, longitude);
          const composed = [place.name, place.admin].filter(Boolean).join(', ');
          if (composed) name = composed;
        } catch {
          /* keep the coordinate label */
        }
        setDetectState('idle');
        onSelect({ name, latitude, longitude, source: 'gps' });
      },
      (error) => {
        setDetectState(error.code === error.PERMISSION_DENIED ? 'blocked' : 'failed');
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
    );
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-[#062A43]/40 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={translations.title}
      onClick={onClose}
    >
      <div
        className="w-full sm:max-w-[440px] max-h-[85vh] flex flex-col bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl overflow-hidden animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 px-5 pt-5 pb-3 shrink-0">
          <h2 className="font-ui font-bold text-[18px] text-[#062A43]">{translations.title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-9 h-9 rounded-full flex items-center justify-center text-[#557186] hover:bg-[#F1F6FA] cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1677A8]"
          >
            <X size={18} className="stroke-[2.4]" />
          </button>
        </header>

        {/* Current location, so it is clear what is being replaced. */}
        <div className="px-5 pb-3 shrink-0">
          <div className="flex items-center gap-2 rounded-xl bg-[#F1F6FA] px-3 py-2">
            <MapPin size={15} className="text-[#1677A8] shrink-0 stroke-[2.2]" />
            <span className="font-ui text-[13px] text-[#274A62] truncate">
              <span className="font-semibold text-[#062A43]">{translations.current}:</span>{' '}
              {current.name}
            </span>
          </div>
        </div>

        {/* 1. Search */}
        <div className="px-5 shrink-0">
          <div className="flex items-center gap-2 rounded-full border-2 border-[#CFE3F2] focus-within:border-[#1677A8] px-4 h-[48px] transition-colors">
            <Search size={17} className="text-[#71869A] shrink-0 stroke-[2.4]" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={translations.searchPlaceholder}
              aria-label={translations.searchPlaceholder}
              className="flex-1 min-w-0 bg-transparent outline-none font-ui text-[15px] text-[#062A43] placeholder:text-[#9CADBC]"
            />
            {isSearching && (
              <LoaderCircle size={16} className="text-[#1677A8] shrink-0 animate-spin" />
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto orca-scrollarea px-5 py-3 min-h-[80px]">
          {results.map((place) => (
            <button
              key={`${place.latitude},${place.longitude},${place.name}`}
              type="button"
              onClick={() => choosePlace(place)}
              className="w-full flex items-start gap-2.5 text-left px-3 py-2.5 rounded-xl hover:bg-[#F1F6FA] cursor-pointer transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1677A8]"
            >
              <MapPin size={16} className="text-[#1677A8] shrink-0 mt-0.5 stroke-[2.2]" />
              <span className="min-w-0">
                <span className="block font-ui font-semibold text-[14.5px] text-[#062A43] truncate">
                  {place.name}
                </span>
                <span className="block font-ui text-[12px] text-[#71869A] truncate">
                  {[place.admin, place.country].filter(Boolean).join(', ')}
                </span>
              </span>
            </button>
          ))}

          {query.trim().length >= 2 && !isSearching && results.length === 0 && (
            <p className="font-ui text-[13px] text-[#71869A] text-center py-4">
              {translations.noResults}
            </p>
          )}
        </div>

        {/* 2. Automatic detection, below the search as requested */}
        <div className="px-5 pb-5 pt-2 border-t border-[#EDF4F9] shrink-0">
          <button
            type="button"
            onClick={detect}
            disabled={detectState === 'detecting'}
            className="w-full flex items-center justify-center gap-2 h-[50px] rounded-full bg-[#062A43] text-white font-ui font-bold text-[15px] cursor-pointer transition-colors hover:bg-[#06365A] disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-4 focus-visible:ring-[#062A43]/40"
          >
            {detectState === 'detecting' ? (
              <>
                <LoaderCircle size={18} className="animate-spin" />
                {translations.detecting}
              </>
            ) : (
              <>
                <Crosshair size={18} className="stroke-[2.4]" />
                {translations.detect}
              </>
            )}
          </button>

          {(detectState === 'blocked' || detectState === 'failed') && (
            <p className="font-ui text-[12.5px] text-[#B91C1C] mt-2 text-center" role="alert">
              {detectState === 'blocked' ? translations.blocked : translations.unavailable}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
