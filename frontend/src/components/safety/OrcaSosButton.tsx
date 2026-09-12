import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AlertOctagon, Check, Loader2, Radio, X } from 'lucide-react';
import {
  SosEmergency,
  XponderMessageType,
  encodeSos,
  frameToHex,
} from '../../services/xponder/frame';
import { LinkStatus, getXponderLink } from '../../services/xponder/link';

/**
 * The distress call.
 *
 * Twenty bytes go up the same link a cyclone warning comes down: what is wrong,
 * where the boat is, and how many people are aboard. Nothing else fits, and
 * nothing else is needed to start a rescue.
 *
 * Held rather than tapped, because the one thing worse than an SOS that will not
 * send is one that sends from a pocket.
 */

const HOLD_MS = 2000;

type Phase = 'idle' | 'choosing' | 'holding' | 'sending' | 'sent' | 'acknowledged' | 'failed';

interface Words {
  button: string;
  choose: string;
  hold: string;
  holding: string;
  sending: string;
  failed: string;
  notConnected: string;
  cancel: string;
  aboard: string;
  emergencies: Record<SosEmergency, string>;
  sent: string;
  acknowledged: string;
}

const TEXT: Record<string, Words> = {
  en: {
    button: 'SOS',
    choose: 'What is wrong?',
    hold: 'Hold to send',
    holding: 'Keep holding…',
    sending: 'Sending…',
    failed: 'Could not send',
    notConnected: 'Connect the transponder first',
    cancel: 'Cancel',
    aboard: 'People on board',
    emergencies: {
      [SosEmergency.Medical]: 'Medical emergency',
      [SosEmergency.EngineFailure]: 'Engine failure',
      [SosEmergency.ManOverboard]: 'Man overboard',
      [SosEmergency.Sinking]: 'Boat sinking',
    },
    sent: 'Sent — waiting for the transponder',
    acknowledged: 'Transponder has your message',
  },
  bn: {
    button: 'বিপদ',
    choose: 'কী হয়েছে?',
    hold: 'পাঠাতে চেপে ধরুন',
    holding: 'ধরে রাখুন…',
    sending: 'পাঠানো হচ্ছে…',
    failed: 'পাঠানো যায়নি',
    notConnected: 'আগে ট্রান্সপন্ডার যুক্ত করুন',
    cancel: 'বাতিল',
    aboard: 'নৌকায় কতজন',
    emergencies: {
      [SosEmergency.Medical]: 'চিকিৎসা জরুরি',
      [SosEmergency.EngineFailure]: 'ইঞ্জিন বিকল',
      [SosEmergency.ManOverboard]: 'একজন জলে পড়েছে',
      [SosEmergency.Sinking]: 'নৌকা ডুবছে',
    },
    sent: 'পাঠানো হয়েছে — অপেক্ষা করুন',
    acknowledged: 'ট্রান্সপন্ডার বার্তা পেয়েছে',
  },
  hi: {
    button: 'एसओएस',
    choose: 'क्या हुआ है?',
    hold: 'भेजने के लिए दबाए रखें',
    holding: 'दबाए रखें…',
    sending: 'भेजा जा रहा है…',
    failed: 'भेजा नहीं जा सका',
    notConnected: 'पहले ट्रांसपोंडर जोड़ें',
    cancel: 'रद्द करें',
    aboard: 'नाव पर कितने लोग',
    emergencies: {
      [SosEmergency.Medical]: 'चिकित्सा आपातकाल',
      [SosEmergency.EngineFailure]: 'इंजन खराब',
      [SosEmergency.ManOverboard]: 'कोई पानी में गिरा',
      [SosEmergency.Sinking]: 'नाव डूब रही है',
    },
    sent: 'भेजा गया — प्रतीक्षा करें',
    acknowledged: 'ट्रांसपोंडर को संदेश मिला',
  },
};

const ORDER: SosEmergency[] = [
  SosEmergency.ManOverboard,
  SosEmergency.Sinking,
  SosEmergency.Medical,
  SosEmergency.EngineFailure,
];

interface OrcaSosButtonProps {
  languageCode?: string;
  /** Fallback position, used only if the handset cannot produce a fix in time. */
  latitude?: number;
  longitude?: number;
  /**
   * `block` is the full-width button on the safety page; `chip` is the small
   * pill that sits in every page header, so distress is never more than one tap
   * away from wherever the fisherman happens to be.
   */
  variant?: 'block' | 'chip';
}

/**
 * The best position available, quickly.
 *
 * A real fix is worth waiting a few seconds for — it is the whole point of the
 * message — but never worth blocking a distress call on, so the screen's own
 * position stands in when the handset cannot answer.
 */
async function bestPosition(
  fallbackLat?: number,
  fallbackLon?: number,
): Promise<{ latitude: number; longitude: number }> {
  const fallback = {
    latitude: fallbackLat ?? 21.6266,
    longitude: fallbackLon ?? 87.5074,
  };
  if (typeof navigator === 'undefined' || !navigator.geolocation) return fallback;

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      () => resolve(fallback),
      { enableHighAccuracy: true, timeout: 6000, maximumAge: 30000 },
    );
  });
}

export const OrcaSosButton: React.FC<OrcaSosButtonProps> = ({
  languageCode = 'en',
  latitude,
  longitude,
  variant = 'block',
}) => {
  const words = TEXT[languageCode] ?? TEXT.en;
  const link = useMemo(() => getXponderLink(), []);

  const [phase, setPhase] = useState<Phase>('idle');
  const [emergency, setEmergency] = useState<SosEmergency>(SosEmergency.ManOverboard);
  const [aboard, setAboard] = useState(4);
  const [status, setStatus] = useState<LinkStatus>(link.connected ? 'connected' : 'idle');
  const [detail, setDetail] = useState('');
  const [progress, setProgress] = useState(0);

  const holdTimer = useRef<number | null>(null);
  const holdStart = useRef(0);

  useEffect(() => {
    const stopStatus = link.onStatus((next) => setStatus(next));
    const stopFrames = link.onFrame((frame) => {
      // The terminal confirming it has the call. Anything else on this link is
      // a warning coming down, and the alert overlay owns that.
      if (frame.type === XponderMessageType.SosAck) setPhase('acknowledged');
    });
    return () => {
      stopStatus();
      stopFrames();
      if (holdTimer.current) window.clearInterval(holdTimer.current);
    };
  }, [link]);

  const connected = status === 'connected' || link.connected;

  const send = async () => {
    setPhase('sending');
    try {
      const position = await bestPosition(latitude, longitude);
      const bytes = encodeSos({
        emergency,
        latitude: position.latitude,
        longitude: position.longitude,
        peopleAboard: aboard,
      });
      // Logged so the hex on screen and the hex in the serial monitor can be
      // compared byte for byte when something looks wrong.
      console.info('[sos] sending', frameToHex(bytes), position);
      await link.send(bytes);
      setPhase('sent');
      setDetail(`${position.latitude.toFixed(4)}, ${position.longitude.toFixed(4)}`);
    } catch (error) {
      setPhase('failed');
      setDetail(error instanceof Error ? error.message : String(error));
    }
  };

  const startHold = () => {
    if (!connected) return;
    setPhase('holding');
    holdStart.current = Date.now();
    holdTimer.current = window.setInterval(() => {
      const held = Date.now() - holdStart.current;
      setProgress(Math.min(1, held / HOLD_MS));
      if (held >= HOLD_MS) {
        if (holdTimer.current) window.clearInterval(holdTimer.current);
        holdTimer.current = null;
        setProgress(0);
        void send();
      }
    }, 50);
  };

  const cancelHold = () => {
    if (holdTimer.current) window.clearInterval(holdTimer.current);
    holdTimer.current = null;
    setProgress(0);
    setPhase((current) => (current === 'holding' ? 'choosing' : current));
  };

  const close = () => {
    cancelHold();
    setPhase('idle');
  };

  // ---------------------------------------------------------------- trigger

  if (phase === 'idle') {
    if (variant === 'chip') {
      return (
        <button
          type="button"
          onClick={() => setPhase('choosing')}
          aria-label={words.button}
          className="inline-flex shrink-0 items-center gap-1 rounded-full border border-[#B91C1C] bg-[#DC2626] px-3 py-1.5 font-ui text-[12px] font-extrabold tracking-wide text-white shadow-xs active:scale-95"
        >
          <AlertOctagon size={13} className="stroke-[2.4]" />
          {words.button}
        </button>
      );
    }
    return (
      <button
        type="button"
        onClick={() => setPhase('choosing')}
        className="flex w-full items-center justify-center gap-3 rounded-2xl border-2 border-[#B91C1C] bg-[#DC2626] py-4 font-ui text-[18px] font-extrabold tracking-wide text-white shadow-lg active:scale-[0.99]"
      >
        <AlertOctagon size={22} />
        {words.button}
      </button>
    );
  }

  // ------------------------------------------------------------------ panel

  const panel = (
    <div className="rounded-2xl border-2 border-[#B91C1C] bg-[#7F1D1D] p-4 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-ui text-[11px] font-extrabold uppercase tracking-[0.18em] text-[#FCA5A5]">
          <Radio size={13} />
          {connected
            ? link.name === 'Simulated'
              ? 'Simulated terminal'
              : 'Transponder'
            : words.notConnected}
        </div>
        <button
          type="button"
          onClick={close}
          className="rounded-full bg-black/25 p-1.5 text-[#FCA5A5]"
          aria-label={words.cancel}
        >
          <X size={14} />
        </button>
      </div>

      {(phase === 'choosing' || phase === 'holding') && (
        <>
          <p className="mt-3 font-ui text-[15px] font-bold text-white">{words.choose}</p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {ORDER.map((kind) => (
              <button
                key={kind}
                type="button"
                onClick={() => setEmergency(kind)}
                className={`rounded-xl px-3 py-2.5 text-left font-ui text-[13px] font-bold leading-tight ${
                  emergency === kind ? 'bg-white text-[#7F1D1D]' : 'bg-black/25 text-[#FECACA]'
                }`}
              >
                {words.emergencies[kind]}
              </button>
            ))}
          </div>

          <div className="mt-3 flex items-center justify-between rounded-xl bg-black/25 px-3 py-2">
            <span className="font-ui text-[13px] font-semibold text-[#FECACA]">{words.aboard}</span>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setAboard((n) => Math.max(1, n - 1))}
                className="h-7 w-7 rounded-full bg-white/15 font-ui text-[16px] font-bold text-white"
              >
                −
              </button>
              <span className="w-6 text-center font-mono text-[16px] font-bold text-white">{aboard}</span>
              <button
                type="button"
                onClick={() => setAboard((n) => Math.min(99, n + 1))}
                className="h-7 w-7 rounded-full bg-white/15 font-ui text-[16px] font-bold text-white"
              >
                +
              </button>
            </div>
          </div>

          <button
            type="button"
            disabled={!connected}
            onPointerDown={startHold}
            onPointerUp={cancelHold}
            onPointerLeave={cancelHold}
            onContextMenu={(event) => event.preventDefault()}
            className="relative mt-3 w-full overflow-hidden rounded-2xl bg-white py-4 font-ui text-[16px] font-extrabold text-[#7F1D1D] disabled:opacity-50"
          >
            <span
              className="absolute inset-y-0 left-0 bg-[#FCA5A5]"
              style={{ width: `${progress * 100}%`, transition: 'width 50ms linear' }}
            />
            <span className="relative">
              {!connected ? words.notConnected : phase === 'holding' ? words.holding : words.hold}
            </span>
          </button>
        </>
      )}

      {phase === 'sending' && (
        <p className="mt-4 flex items-center gap-2 font-ui text-[15px] font-bold text-white">
          <Loader2 size={16} className="animate-spin" />
          {words.sending}
        </p>
      )}

      {(phase === 'sent' || phase === 'acknowledged') && (
        <div className="mt-4">
          {/*
            The terminal holding the bytes is all this can honestly confirm.
            Whether a coastguard has read them is not something the terminal
            knows, so nothing here says it.
          */}
          <p className="flex items-center gap-2 font-ui text-[15px] font-bold text-white">
            {phase === 'acknowledged' ? (
              <Check size={18} className="text-[#86EFAC] stroke-[3]" />
            ) : (
              <Loader2 size={16} className="animate-spin" />
            )}
            {phase === 'acknowledged' ? words.acknowledged : words.sent}
          </p>

          <div className="mt-3 rounded-xl bg-black/25 px-3 py-2 font-mono text-[11px] text-[#FCA5A5]">
            {words.emergencies[emergency]} · {aboard} · {detail} · 20 bytes
          </div>
        </div>
      )}

      {phase === 'failed' && (
        <div className="mt-4">
          <p className="font-ui text-[15px] font-bold text-white">{words.failed}</p>
          <p className="mt-1 font-mono text-[11px] text-[#FCA5A5]">{detail}</p>
          <button
            type="button"
            onClick={() => setPhase('choosing')}
            className="mt-3 w-full rounded-2xl bg-white py-3 font-ui text-[15px] font-bold text-[#7F1D1D]"
          >
            {words.hold}
          </button>
        </div>
      )}
    </div>
  );

  // From the header the panel has nowhere to live inline, so it opens over the
  // page — which is also what an emergency should do to whatever came before it.
  if (variant === 'chip') {
    return (
      <div className="fixed inset-0 z-[9500] flex items-center justify-center bg-black/60 px-4">
        <div className="w-full max-w-md">{panel}</div>
      </div>
    );
  }

  return panel;
};
