import React, { useState, useRef, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { OrcaAskHeader } from '../components/ask/OrcaAskHeader';
import { OrcaVoiceCard, VoiceState } from '../components/ask/OrcaVoiceCard';
import { OrcaQuickQuestions } from '../components/ask/OrcaQuickQuestions';
import { OrcaAnswerCard } from '../components/ask/OrcaAnswerCard';
import { OrcaTextInput } from '../components/ask/OrcaTextInput';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { askOrca, askOrcaByVoice, audioUrlFromBase64 } from '../services/orcaApi';
import { QuickQuestion, getAskTranslations, getQuickQuestionsList } from '../data/askData';

// Reusing the existing watercolor background from safety/find fish/sea today pages
const BACKGROUND_IMAGE = '/assets/orca_safety_background.avif';

interface AskOrcaPageProps {
  currentLanguage?: LanguageOption;
  onNavigateHome: () => void;
  onNavigateRoute?: (route: 'home' | 'find-fish' | 'safety' | 'sea-today' | 'alerts' | 'ask') => void;
  onNavigateTab?: (tab: NavTabId) => void;
  locationName?: string;
}

interface ActiveConversation {
  question: string;
  answer: string;
  actionLabel?: string;
  actionRoute?: 'find-fish' | 'safety' | 'sea-today' | 'alerts';
  whyExplanation?: string;
  /** Language ORCA answered in — may differ from the UI language. */
  language: string;
  audioUrl?: string | null;
  usedStubData: boolean;
}

/** Route the "next step" button to the page that matches the agent that answered. */
const AGENT_ROUTES: Record<string, 'find-fish' | 'safety' | 'sea-today' | 'alerts'> = {
  ocean_analytics: 'find-fish',
  weather_intelligence: 'safety',
  risk_assessment: 'safety',
  geospatial: 'find-fish',
};

export const AskOrcaPage: React.FC<AskOrcaPageProps> = ({
  currentLanguage,
  onNavigateHome,
  onNavigateRoute,
  onNavigateTab,
  locationName = 'Digha, West Bengal',
}) => {
  const langCode = currentLanguage?.code || 'en';
  const translations = getAskTranslations(langCode);
  const quickQuestions = getQuickQuestionsList(langCode);

  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [activeConversation, setActiveConversation] = useState<ActiveConversation | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  // Shown live while ORCA is working, so the user sees their own words echoed
  // back rather than staring at a spinner.
  const [heardTranscript, setHeardTranscript] = useState<string | null>(null);

  const recorder = useVoiceRecorder();
  const audioUrlRef = useRef<string | null>(null);

  // Object URLs for spoken answers must be released or they leak.
  useEffect(() => {
    return () => {
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  const recorderErrorMessage = (code: string): string => {
    if (code === 'permission-denied') return translations.micDenied;
    if (code === 'unsupported') return translations.micUnsupported;
    return translations.couldNotHear;
  };

  const handleTabChange = (tabId: NavTabId) => {
    if (tabId === 'home') {
      onNavigateHome();
    } else if (tabId === 'map') {
      onNavigateRoute?.('find-fish');
    } else if (tabId === 'alerts') {
      onNavigateRoute?.('alerts');
    } else {
      onNavigateTab?.(tabId);
    }
  };

  /** Label the follow-up button from whichever agent actually answered. */
  const actionFor = (agents: string[]): { label?: string; route?: ActiveConversation['actionRoute'] } => {
    const route = agents.map((agent) => AGENT_ROUTES[agent]).find(Boolean);
    if (!route) return {};
    const labels = {
      'find-fish': translations.viewSpot,
      safety: translations.checkSafety,
      'sea-today': translations.seaDetails,
      alerts: translations.viewAlerts,
    } as const;
    return { label: labels[route], route };
  };

  /**
   * Voice flow: tap to record, tap again to send.
   *
   * Nothing is faked here. If the microphone fails or nothing was said, the
   * user is told so — the old build answered a canned question instead, which
   * meant the reply had no relationship to what was actually asked.
   */
  const handleMicClick = async () => {
    if (voiceState === 'thinking') return;

    if (recorder.isRecording) {
      const audio = await recorder.stop();
      if (!audio) {
        setVoiceState('idle');
        setErrorMessage(recorderErrorMessage(recorder.error ?? 'no-audio'));
        return;
      }

      setVoiceState('thinking');
      setErrorMessage(null);

      try {
        const result = await askOrcaByVoice({
          audio,
          // "unknown" lets the backend identify the spoken language rather than
          // trusting the UI selector — a user may speak Bengali with the app in
          // English.
          language: 'unknown',
          latitude: 21.6272,
          longitude: 87.5079,
        });

        setHeardTranscript(result.transcript);

        if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = result.audio_base64
          ? audioUrlFromBase64(result.audio_base64)
          : null;

        const action = actionFor(result.agents_used);
        setActiveConversation({
          question: result.transcript,
          answer: result.answer,
          actionLabel: action.label,
          actionRoute: action.route,
          whyExplanation: result.reasoning.map((step) => step.detail).join(' '),
          language: result.detected_language || result.language,
          audioUrl: audioUrlRef.current,
          usedStubData: result.used_stub_data,
        });
      } catch {
        setErrorMessage(translations.connectionFailed);
      } finally {
        setVoiceState('idle');
      }
      return;
    }

    setErrorMessage(null);
    setHeardTranscript(null);
    const started = await recorder.start();
    if (!started) {
      setErrorMessage(recorderErrorMessage(recorder.error ?? 'failed'));
      return;
    }
    setVoiceState('listening');
  };

  /** Typed questions and quick questions both go to the orchestrator. */
  const processQuestion = async (queryText: string) => {
    setVoiceState('thinking');
    setErrorMessage(null);
    setHeardTranscript(queryText);

    try {
      const result = await askOrca({
        message: queryText,
        language: langCode,
        latitude: 21.6272,
        longitude: 87.5079,
      });

      const action = actionFor(result.agents_used);
      setActiveConversation({
        question: queryText,
        answer: result.answer,
        actionLabel: action.label,
        actionRoute: action.route,
        whyExplanation: result.reasoning.map((step) => step.detail).join(' '),
        language: result.language,
        audioUrl: null,
        usedStubData: result.used_stub_data,
      });
    } catch {
      setErrorMessage(translations.connectionFailed);
    } finally {
      setVoiceState('idle');
    }
  };

  const handleSelectQuickQuestion = (qq: QuickQuestion) => {
    void processQuestion(qq.question);
  };

  const handleActionNavigate = (route: 'find-fish' | 'safety' | 'sea-today' | 'alerts') => {
    onNavigateRoute?.(route);
  };

  const handleReset = () => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setActiveConversation(null);
    setHeardTranscript(null);
    setErrorMessage(null);
    setVoiceState('idle');
  };

  return (
    <div
      className="relative w-full min-h-[100svh] min-h-[100dvh] overflow-x-hidden bg-[#F7FAFC] text-[#062A43]"
      id="orca-ask-page"
    >
      {/* 
        ===================================================================
        TOP-RIGHT SCENIC WATERCOLOR BACKGROUND IMAGE
        - Reuses the existing /assets/orca_safety_background.avif asset
        - Positioned primarily toward the upper-right portion of the page
        - Left side remains clean and light so typography is 100% legible
        ===================================================================
      */}
      <div
        className="pointer-events-none absolute top-0 right-0 z-0 w-[240px] min-[390px]:w-[310px] sm:w-[440px] md:w-[520px] max-w-[68%] h-[290px] min-[390px]:h-[360px] sm:h-[420px] overflow-hidden select-none"
        aria-hidden="true"
      >
        <img
          src={BACKGROUND_IMAGE}
          alt=""
          className="w-full h-full object-cover object-top-right opacity-85 mix-blend-multiply"
          loading="eager"
          decoding="async"
        />
        {/* Soft edge feathering overlays to keep left side clean */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#F7FAFC] via-[#F7FAFC]/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#F7FAFC]/40 to-[#F7FAFC]" />
      </div>

      {/* 
        ===================================================================
        PAGE CONTAINER
        - Centered column, max-width 640px
        - Safe area padding for bottom navigation
        - Flow:
          1. Header: Back + ORCA logo + Location
          2. Title: "Ask ORCA" (Cormorant Garamond) + "“Ask anything about the sea.”"
          3. Main Voice Area / Conversational Answer Card
          4. Quick Questions: 🎣 Where should I fish? 🛡️ Is it safe? 🌊 How is sea? ⚠️ Warnings?
          5. Bottom Text Input: "Type your question..."
        ===================================================================
      */}
      <main className="relative z-10 w-full max-w-[640px] mx-auto px-4 min-[390px]:px-5 sm:px-6 pb-28 min-[390px]:pb-32 sm:pb-36 flex flex-col items-stretch">
        {/* 
          1. TOP HEADER:
          ←  ORCA       📍 Digha, West Bengal
        */}
        <OrcaAskHeader
          onBackClick={onNavigateHome}
          currentLanguage={currentLanguage}
          locationName={locationName}
        />

        {/* 
          2. TITLE:
          - Cormorant Garamond heading: "Ask ORCA"
          - "“Ask anything about the sea.”"
        */}
        <div className="w-full mt-3 sm:mt-4 flex flex-col items-start select-none">
          <h1
            className="font-display font-bold text-[34px] min-[390px]:text-[38px] sm:text-[44px] text-[#062A43] leading-[1.05] tracking-tight"
            id="ask-orca-page-title"
          >
            {translations.pageTitle}
          </h1>

          <p className="font-ui font-normal text-[14px] min-[390px]:text-[15px] sm:text-[16px] text-[#274A62] leading-[1.35] mt-1.5 sm:mt-2 max-w-[90%]">
            “{translations.pageSubtitle}”
          </p>
        </div>

        {/* 
          3. MAIN VOICE AREA OR ACTIVE CONVERSATION CARD
          If user has asked, show the clear conversational card.
          Otherwise, show the large white/very-light-blue voice card with large microphone!
        */}
        {/* Error state — replaces the old silent fake answer. */}
        {errorMessage && (
          <div
            className="w-full mt-4 flex items-start gap-2.5 rounded-2xl border border-[#FCA5A5] bg-[#FEF2F2] px-4 py-3"
            role="alert"
          >
            <AlertCircle size={18} className="mt-0.5 shrink-0 text-[#DC2626]" />
            <p className="font-ui text-[13.5px] leading-snug text-[#991B1B]">{errorMessage}</p>
          </div>
        )}

        {/* What ORCA heard, shown while it is still thinking. */}
        {voiceState === 'thinking' && heardTranscript && (
          <div className="w-full mt-4 rounded-2xl border border-[#BCD8EC] bg-white/80 px-4 py-3">
            <span className="font-ui text-[11px] font-extrabold uppercase tracking-wider text-[#71869A]">
              {translations.youAsked}
            </span>
            <p className="font-ui text-[15px] text-[#062A43] mt-0.5">{heardTranscript}</p>
          </div>
        )}

        <div className="w-full mt-4 sm:mt-5">
          {activeConversation ? (
            <OrcaAnswerCard
              userQuestion={activeConversation.question}
              orcaAnswer={activeConversation.answer}
              actionLabel={activeConversation.actionLabel}
              actionRoute={activeConversation.actionRoute}
              whyExplanation={activeConversation.whyExplanation}
              onNavigateAction={handleActionNavigate}
              onReset={handleReset}
              translations={translations}
              answerAudioUrl={activeConversation.audioUrl}
              answerLanguage={activeConversation.language}
            />
          ) : (
            <OrcaVoiceCard
              voiceState={voiceState}
              onMicClick={handleMicClick}
              translations={translations}
            />
          )}
        </div>

        {/* 
          4. QUICK QUESTIONS:
          Try asking
          🎣 “Where should I fish?”
          🛡️ “Is it safe today?”
          🌊 “How is the sea?”
          ⚠️ “Any warnings?”
        */}
        <div className="w-full mt-5 sm:mt-6">
          <OrcaQuickQuestions
            questions={quickQuestions}
            onSelectQuestion={handleSelectQuickQuestion}
            title={translations.tryAsking}
          />
        </div>

        {/* 
          5. TEXT INPUT:
          At bottom of content area:
          “Type your question…” with send button
          (Voice remains the primary interaction)
        */}
        <div className="w-full mt-5 sm:mt-6">
          <OrcaTextInput
            placeholder={translations.typeQuestionPlaceholder}
            onSubmit={processQuestion}
            disabled={voiceState !== 'idle'}
          />
        </div>
      </main>

      {/* 
        6. PERSISTENT 5-ITEM BOTTOM NAVIGATION:
        Home, Map, Ask, Alerts, Profile
        ASK must be the active item!
      */}
      <OrcaBottomNav
        activeTab="ask"
        currentLanguage={currentLanguage}
        onTabChange={handleTabChange}
      />
    </div>
  );
};
