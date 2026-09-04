import React, { useState, useRef } from 'react';
import { OrcaAskHeader } from '../components/ask/OrcaAskHeader';
import { OrcaVoiceCard, VoiceState } from '../components/ask/OrcaVoiceCard';
import { OrcaQuickQuestions } from '../components/ask/OrcaQuickQuestions';
import { OrcaAnswerCard } from '../components/ask/OrcaAnswerCard';
import { OrcaTextInput } from '../components/ask/OrcaTextInput';
import { OrcaBottomNav, NavTabId } from '../components/OrcaBottomNav';
import { LanguageOption } from '../types';
import {
  QuickQuestion,
  getAskTranslations,
  getQuickQuestionsList,
  answerCustomQuestion,
} from '../data/askData';

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
}

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

  const timerRef = useRef<NodeJS.Timeout | null>(null);

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

  /**
   * Voice Interaction flow:
   * 1. Click mic -> Listening... ("Speak now")
   * 2. After 2.5s simulated or real speech -> Thinking... ("Checking sea, weather...")
   * 3. After 1.2s -> Displays crisp answer card!
   */
  const handleMicClick = () => {
    if (voiceState === 'listening') {
      // User tapped again to stop listening
      triggerThinkingAndAnswer(quickQuestions[0]);
      return;
    }

    if (voiceState === 'thinking') {
      return;
    }

    // Start listening
    setVoiceState('listening');

    // Check if browser Web Speech API is supported
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as unknown as { SpeechRecognition?: any }).SpeechRecognition ||
        (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognition.lang = langCode === 'bn' ? 'bn-BD' : langCode === 'hi' ? 'hi-IN' : 'en-US';
          recognition.interimResults = false;
          recognition.maxAlternatives = 1;

          recognition.onresult = (event: any) => {
            const transcript = event.results[0][0].transcript;
            processQuestion(transcript);
          };

          recognition.onerror = () => {
            // Fallback gracefully on permission or timeout
            fallbackSimulatedVoice();
          };

          recognition.start();
          return;
        } catch {
          fallbackSimulatedVoice();
          return;
        }
      }
    }

    fallbackSimulatedVoice();
  };

  const fallbackSimulatedVoice = () => {
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      triggerThinkingAndAnswer(quickQuestions[0]);
    }, 2400);
  };

  const triggerThinkingAndAnswer = (qq: QuickQuestion) => {
    setVoiceState('thinking');
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      setVoiceState('idle');
      setActiveConversation({
        question: qq.question,
        answer: qq.answer,
        actionLabel: qq.actionLabel,
        actionRoute: qq.actionRoute,
        whyExplanation: qq.whyExplanation,
      });
    }, 1200);
  };

  const processQuestion = (queryText: string) => {
    setVoiceState('thinking');
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      setVoiceState('idle');
      const res = answerCustomQuestion(queryText, langCode);
      setActiveConversation({
        question: queryText,
        answer: res.answer,
        actionLabel: res.actionLabel,
        actionRoute: res.actionRoute,
        whyExplanation: res.whyExplanation,
      });
    }, 1000);
  };

  // When a quick question is clicked, answer immediately!
  const handleSelectQuickQuestion = (qq: QuickQuestion) => {
    setVoiceState('thinking');
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      setVoiceState('idle');
      setActiveConversation({
        question: qq.question,
        answer: qq.answer,
        actionLabel: qq.actionLabel,
        actionRoute: qq.actionRoute,
        whyExplanation: qq.whyExplanation,
      });
    }, 450);
  };

  const handleActionNavigate = (route: 'find-fish' | 'safety' | 'sea-today' | 'alerts') => {
    onNavigateRoute?.(route);
  };

  const handleReset = () => {
    setActiveConversation(null);
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
