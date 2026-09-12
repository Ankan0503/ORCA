import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Radio, X } from 'lucide-react';
import { maritimeSiren } from '../../services/audio/maritimeSirenService';
import { XponderFrame, XponderMessageType } from '../../services/xponder/frame';
import { LinkStatus, MockXponderLink, XponderLink, createXponderLink } from '../../services/xponder/link';

/**
 * A cyclone warning arriving from the transponder.
 *
 * The message carries a type code and a wind speed, never a sentence — twenty bytes
 * is what survives a satellite link to a boat. The words below are written here, in
 * the fisherman's own language, from those few numbers.
 */

const WARNINGS: Record<string, { title: string; body: (wind: number) => string; source: string; dismiss: string }> = {
  en: {
    title: 'CYCLONE WARNING',
    body: (wind) => `Cyclone warning. Winds up to ${wind} kilometres per hour. Return to harbour immediately.`,
    source: 'Received on the transponder',
    dismiss: 'Understood',
  },
  bn: {
    title: 'ঘূর্ণিঝড় সতর্কতা',
    body: (wind) => `ঘূর্ণিঝড়ের সতর্কতা। বাতাসের গতি ঘণ্টায় ${wind} কিলোমিটার পর্যন্ত। এখনই বন্দরে ফিরে আসুন।`,
    source: 'ট্রান্সপন্ডারে পাওয়া বার্তা',
    dismiss: 'বুঝেছি',
  },
  hi: {
    title: 'चक्रवात चेतावनी',
    body: (wind) => `चक्रवात की चेतावनी। हवा की गति ${wind} किलोमीटर प्रति घंटा तक। तुरंत बंदरगाह लौटें।`,
    source: 'ट्रांसपोंडर पर प्राप्त संदेश',
    dismiss: 'समझ गया',
  },
};

const SEVERITY_LABEL: Record<number, string> = {
  1: 'Advisory',
  2: 'Watch',
  3: 'Warning',
  4: 'Severe',
};

/**
 * The language the app is set to.
 *
 * Read from storage rather than taken as a prop: this alert is mounted beside the
 * app so a warning reaches whatever screen is open, which puts it outside the state
 * holding the chosen language.
 */
function selectedLanguage(): string {
  try {
    return localStorage.getItem('orca_lang') || 'en';
  } catch {
    return 'en';
  }
}

export const OrcaXponderAlert: React.FC = () => {
  const [language, setLanguage] = useState<string>(selectedLanguage);
  const [frame, setFrame] = useState<XponderFrame | null>(null);
  const [status, setStatus] = useState<LinkStatus>('idle');
  const [detail, setDetail] = useState<string>('');
  const linkRef = useRef<XponderLink | null>(null);

  const words = WARNINGS[language] ?? WARNINGS.en;

  useEffect(() => {
    const link = createXponderLink();
    linkRef.current = link;

    const stopFrames = link.onFrame((received) => {
      if (received.type !== XponderMessageType.Cyclone) return;
      // Read at the moment it matters: the fisherman may have switched language
      // since this mounted.
      setLanguage(selectedLanguage());
      setFrame(received);
    });
    const stopStatus = link.onStatus((next, why) => {
      setStatus(next);
      setDetail(why ?? '');
    });

    // The simulated terminal needs no pairing; Bluetooth waits for the user to connect.
    if (link instanceof MockXponderLink) {
      void link.connect();
      (window as unknown as { orcaXponder?: MockXponderLink }).orcaXponder = link;
    }

    return () => {
      stopFrames();
      stopStatus();
      void link.disconnect();
    };
  }, []);

  // Siren and voice, once per warning.
  useEffect(() => {
    if (!frame) return;
    let cancelled = false;

    const sound = async () => {
      await maritimeSiren.unlock();
      if (cancelled) return;
      maritimeSiren.playCriticalSiren(3.5);

      if (typeof window === 'undefined' || !window.speechSynthesis) return;
      // Let the siren clear before speaking, or the two tread on each other.
      window.setTimeout(() => {
        if (cancelled) return;
        const utterance = new SpeechSynthesisUtterance(words.body(frame.value));
        utterance.lang = language === 'bn' ? 'bn-IN' : language === 'hi' ? 'hi-IN' : 'en-IN';
        utterance.rate = 0.95;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
      }, 3600);
    };

    void sound();
    return () => {
      cancelled = true;
      if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, [frame, language, words]);

  const received = useMemo(() => new Date().toLocaleTimeString(), [frame]);
  const simulated = linkRef.current instanceof MockXponderLink;

  const handleChipTap = async () => {
    const link = linkRef.current;
    if (!link) return;
    // Without hardware the chip is the trigger, so the warning can be shown from the
    // phone itself rather than a developer console.
    if (link instanceof MockXponderLink) {
      link.sendCyclone({ severity: 4, windKmh: 120 });
      return;
    }
    if (status === 'connected') return;
    try {
      await link.connect();
    } catch {
      // connect() has already reported why through the status listener.
    }
  };

  if (!frame) {
    const label =
      simulated
        ? 'Xponder · simulated'
        : status === 'connected'
          ? `Xponder · ${detail || 'connected'}`
          : status === 'scanning'
            ? 'Xponder · scanning…'
            : status === 'unavailable'
              ? 'Xponder · retry'
              : 'Xponder · connect';

    const dot =
      status === 'connected' ? 'bg-[#22C55E]' : status === 'unavailable' ? 'bg-[#DC2626]' : 'bg-[#94A3B8]';

    return (
      <button
        type="button"
        onClick={handleChipTap}
        title={detail || undefined}
        className="fixed bottom-24 right-3 z-[9000] flex items-center gap-2 rounded-full border border-[#BCD8EC] bg-white/90 px-3 py-1.5 font-ui text-[11px] font-bold text-[#062A43] shadow-md backdrop-blur"
      >
        <span className={`h-2 w-2 rounded-full ${dot}`} />
        <Radio size={12} className="text-[#1677A8]" />
        {label}
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-[#450A0A]/95 px-5">
      <div className="w-full max-w-md rounded-3xl border-2 border-[#F87171] bg-[#7F1D1D] p-6 shadow-2xl">
        <div className="flex items-center gap-2 font-ui text-[11px] font-extrabold uppercase tracking-[0.18em] text-[#FCA5A5]">
          <Radio size={14} />
          {words.source}
          {status === 'connected' && detail ? ` · ${detail}` : ''}
        </div>

        <div className="mt-3 flex items-start gap-3">
          <AlertTriangle size={40} className="shrink-0 text-[#FEF08A]" />
          <div>
            <h2 className="font-display text-3xl font-bold leading-tight text-white">{words.title}</h2>
            <p className="mt-1 font-ui text-[13px] font-semibold text-[#FCA5A5]">
              {SEVERITY_LABEL[frame.severity] ?? 'Warning'} · {frame.value} km/h
            </p>
          </div>
        </div>

        <p className="mt-4 font-ui text-[16px] leading-relaxed text-white">{words.body(frame.value)}</p>

        <div className="mt-4 rounded-xl bg-black/25 px-3 py-2 font-mono text-[11px] text-[#FCA5A5]">
          {frame.latitude.toFixed(4)}°N, {frame.longitude.toFixed(4)}°E · {received} · 20 bytes
        </div>

        <button
          type="button"
          onClick={() => setFrame(null)}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-white py-3 font-ui text-[15px] font-bold text-[#7F1D1D]"
        >
          <X size={16} />
          {words.dismiss}
        </button>
      </div>
    </div>
  );
};
