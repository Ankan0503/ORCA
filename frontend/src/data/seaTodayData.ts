/**
 * `unknown` exists so the screen has somewhere honest to sit while the forecast
 * is still loading. It used to default to `calm`, which painted a green "Good
 * conditions" badge next to the words "CHECKING…" — an all-clear issued before
 * anything had been read.
 */
export type SeaStatus = 'calm' | 'moderate' | 'rough' | 'unknown';

export interface SeaTodayCondition {
  id: 'wind' | 'waves' | 'rain' | 'visibility';
  name: string;
  value: string;
  unit?: string;
  status: string;
  statusType: 'good' | 'caution' | 'alert';
  icon: 'wind' | 'waves' | 'rain' | 'visibility';
}

export interface ForecastHour {
  time: string;
  icon: string;
  temp: string;
  condition: string;
  /**
   * How the safety grader judged this hour — the same verdict the rest of ORCA
   * uses. Carried here because colouring the strip by matching words in the
   * condition text got thunderstorms wrong: "Thunderstorm" contains none of
   * "Rough", "High", "waves" or "Choppy", so lightning fell through to the
   * green branch and was drawn as calmly as "Cloudy".
   */
  status: 'safe' | 'caution' | 'unsafe' | 'unknown';
}

export interface SeaTodayData {
  location: string;
  seaStatus: SeaStatus;
  statusTitle: string;
  statusDescription: string;
  statusBadge: string;
  updatedAgo: string;
  conditions: SeaTodayCondition[];
  forecast: ForecastHour[];
  advice: {
    title: string;
    quote: string;
    type: 'good' | 'caution' | 'danger';
  };
}

export interface SeaTodayTranslations {
  pageTitle: string;
  pageSubtitle: string;
  calmTitle: string;
  calmDescription: string;
  calmBadge: string;
  moderateTitle: string;
  moderateDescription: string;
  moderateBadge: string;
  roughTitle: string;
  roughDescription: string;
  roughBadge: string;
  conditionsTitle: string;
  windLabel: string;
  wavesLabel: string;
  rainLabel: string;
  visibilityLabel: string;
  forecastTitle: string;
  adviceCalmTitle: string;
  adviceCalmQuote: string;
  adviceModerateTitle: string;
  adviceModerateQuote: string;
  adviceRoughTitle: string;
  adviceRoughQuote: string;
  askOrcaTitle: string;
  askOrcaPrompt: string;
  askOrcaChip: string;
  updatedPrefix: string;
  testToggleLabel: string;
}

export const SEA_TODAY_TRANSLATIONS: Record<string, SeaTodayTranslations> = {
  en: {
    pageTitle: 'Sea Today',
    pageSubtitle: 'Know the sea before you go.',
    calmTitle: 'CALM SEA',
    calmDescription: 'Good day for fishing',
    calmBadge: 'Good conditions',
    moderateTitle: 'MODERATE SEA',
    moderateDescription: 'Be a little careful',
    moderateBadge: 'Moderate conditions',
    roughTitle: 'ROUGH SEA',
    roughDescription: 'Avoid going far offshore',
    roughBadge: 'Rough conditions',
    conditionsTitle: 'Today',
    windLabel: 'Wind',
    wavesLabel: 'Waves',
    rainLabel: 'Rain',
    visibilityLabel: 'Visibility',
    forecastTitle: 'Today',
    adviceCalmTitle: 'Good to go',
    adviceCalmQuote: 'Sea conditions look good today.',
    adviceModerateTitle: 'Be careful',
    adviceModerateQuote: 'Waves may increase later today.',
    adviceRoughTitle: 'Stay ashore',
    adviceRoughQuote: 'Rough sea expected. Avoid going out.',
    askOrcaTitle: 'Ask ORCA',
    askOrcaPrompt: 'Want to know more?',
    askOrcaChip: 'Will waves get rougher later today?',
    updatedPrefix: 'Updated',
    testToggleLabel: 'Sea State Simulator:',
  },
  bn: {
    pageTitle: 'আজকের সমুদ্র',
    pageSubtitle: 'সমুদ্রে যাওয়ার আগে অবস্থা জেনে নিন।',
    calmTitle: 'শান্ত সমুদ্র',
    calmDescription: 'মাছ ধরার জন্য অনুকূল দিন',
    calmBadge: 'অনুকূল অবস্থা',
    moderateTitle: 'মাঝারি সমুদ্র',
    moderateDescription: 'কিছুটা সতর্ক থাকুন',
    moderateBadge: 'সতর্ক অবস্থা',
    roughTitle: 'উত্তাল সমুদ্র',
    roughDescription: 'গভীর সমুদ্রে যাওয়া এড়িয়ে চলুন',
    roughBadge: 'উত্তাল অবস্থা',
    conditionsTitle: 'আজকের অবস্থা',
    windLabel: 'বাতাস',
    wavesLabel: 'ঢেউ',
    rainLabel: 'বৃষ্টি',
    visibilityLabel: 'দৃশ্যমানতা',
    forecastTitle: 'আজকের পূর্বাভাস',
    adviceCalmTitle: 'সমুদ্রে যাওয়া নিরাপদ',
    adviceCalmQuote: 'আজ সমুদ্রের অবস্থা শান্ত ও অনুকূল।',
    adviceModerateTitle: 'সাবধানে থাকুন',
    adviceModerateQuote: 'দিনের শেষের দিকে ঢেউ কিছুটা বাড়তে পারে।',
    adviceRoughTitle: 'কূলে থাকুন',
    adviceRoughQuote: 'সমুদ্র উত্তাল হতে পারে। নামবেন না।',
    askOrcaTitle: 'ORCA-কে জিজ্ঞাসা করুন',
    askOrcaPrompt: 'আরও কিছু জানতে চান?',
    askOrcaChip: 'বিকেলে কি ঢেউ বেশি বাড়বে?',
    updatedPrefix: 'আপডেট করা হয়েছে',
    testToggleLabel: 'সমুদ্রের অবস্থা পরীক্ষা করুন:',
  },
  ta: {
    pageTitle: 'இன்றைய கடல்',
    pageSubtitle: 'கடலுக்கு செல்லும் முன் அறிந்து கொள்ளுங்கள்.',
    calmTitle: 'அமைதியான கடல்',
    calmDescription: 'மீன்பிடிக்க நல்ல நாள்',
    calmBadge: 'நல்ல சூழல்',
    moderateTitle: 'மிதமான கடல்',
    moderateDescription: 'சற்று கவனமாக இருங்கள்',
    moderateBadge: 'கவன சூழல்',
    roughTitle: 'சீற்றமான கடல்',
    roughDescription: 'ஆழ்கடலுக்கு செல்வதை தவிர்க்கவும்',
    roughBadge: 'அபாய சூழல்',
    conditionsTitle: 'இன்று',
    windLabel: 'காற்று',
    wavesLabel: 'அலைகள்',
    rainLabel: 'மழை',
    visibilityLabel: 'பார்வைத்திறன்',
    forecastTitle: 'இன்றைய முன்னறிவிப்பு',
    adviceCalmTitle: 'செல்லலாம்',
    adviceCalmQuote: 'இன்று கடல் நிலைமைகள் நன்றாக உள்ளன.',
    adviceModerateTitle: 'கவனமாக இருங்கள்',
    adviceModerateQuote: 'மாலையில் அலைகள் அதிகரிக்கலாம்.',
    adviceRoughTitle: 'கரையில் இருங்கள்',
    adviceRoughQuote: 'கடல் சீற்றமாக இருக்கும். கடலுக்கு செல்ல வேண்டாம்.',
    askOrcaTitle: 'ORCA-விடம் கேளுங்கள்',
    askOrcaPrompt: 'மேலும் அறிய வேண்டுமா?',
    askOrcaChip: 'மாலையில் அலைகள் சீற்றமாகுமா?',
    updatedPrefix: 'புதுப்பிக்கப்பட்டது',
    testToggleLabel: 'கடல் நிலை:',
  },
  te: {
    pageTitle: 'ఈరోజు సముద్రం',
    pageSubtitle: 'వేటకు వెళ్లే ముందు సముద్ర పరిస్థితి తెలుసుకోండి.',
    calmTitle: 'ప్రశాంత సముద్రం',
    calmDescription: 'చేపల వేటకు అనుకూలమైన రోజు',
    calmBadge: 'అనుకూల పరిస్థితులు',
    moderateTitle: 'మధ్యస్థ సముద్రం',
    moderateDescription: 'కొంచెం జాగ్రత్తగా ఉండండి',
    moderateBadge: 'జాగ్రత్త పరిస్థితులు',
    roughTitle: 'అల్లకల్లోల సముద్రం',
    roughDescription: 'దూరంగా వెళ్లవద్దు',
    roughBadge: 'ప్రమాదకర పరిస్థితులు',
    conditionsTitle: 'ఈరోజు',
    windLabel: 'గాలి',
    wavesLabel: 'అలలు',
    rainLabel: 'వర్షం',
    visibilityLabel: 'దృశ్యమానత',
    forecastTitle: 'ఈరోజు సూచన',
    adviceCalmTitle: 'వెళ్ళడానికి అనుకూలం',
    adviceCalmQuote: 'ఈరోజు సముద్ర పరిస్థితులు బాగున్నాయి.',
    adviceModerateTitle: 'జాగ్రత్తగా ఉండండి',
    adviceModerateQuote: 'తరువాత అలలు పెరిగే అవకాశం ఉంది.',
    adviceRoughTitle: 'ఒడ్డునే ఉండండి',
    adviceRoughQuote: 'సముద్రం అల్లకల్లోలంగా ఉంది. వెళ్లకండి.',
    askOrcaTitle: 'ORCA ను అడగండి',
    askOrcaPrompt: 'మరింత సమాచారం కావాలా?',
    askOrcaChip: 'సాయంత్రం అలలు ఎక్కువవుతాయా?',
    updatedPrefix: 'అప్‌డేట్ చేయబడింది',
    testToggleLabel: 'సముద్ర స్థితి:',
  },
  hi: {
    pageTitle: 'आज का समुद्र',
    pageSubtitle: 'समुद्र में जाने से पहले स्थिति जान लें।',
    calmTitle: 'शांत समुद्र',
    calmDescription: 'मछली पकड़ने के लिए अच्छा दिन',
    calmBadge: 'अनुकूल स्थिति',
    moderateTitle: 'मध्यम समुद्र',
    moderateDescription: 'थोड़ी सावधानी बरतें',
    moderateBadge: 'सावधानी स्थिति',
    roughTitle: 'अशांत समुद्र',
    roughDescription: 'दूर समुद्र में जाने से बचें',
    roughBadge: 'खराब स्थिति',
    conditionsTitle: 'आज',
    windLabel: 'हवा',
    wavesLabel: 'लहरें',
    rainLabel: 'बारिश',
    visibilityLabel: 'दृश्यता',
    forecastTitle: 'आज का पूर्वानुमान',
    adviceCalmTitle: 'जाने के लिए सुरक्षित',
    adviceCalmQuote: 'आज समुद्र की स्थिति अनुकूल है।',
    adviceModerateTitle: 'सावधान रहें',
    adviceModerateQuote: 'शाम को लहरें बढ़ सकती हैं।',
    adviceRoughTitle: 'तट पर रहें',
    adviceRoughQuote: 'समुद्र अशांत रहने की संभावना है। न जाएं।',
    askOrcaTitle: 'ORCA से पूछें',
    askOrcaPrompt: 'क्या और जानना चाहते हैं?',
    askOrcaChip: 'क्या शाम को लहरें बढ़ेंगी?',
    updatedPrefix: 'अपडेट किया गया',
    testToggleLabel: 'समुद्र की स्थिति:',
  },
  ml: {
    pageTitle: 'ഇന്നത്തെ കടൽ',
    pageSubtitle: 'കടലിൽ പോകുന്നതിന് മുൻപ് സ്ഥിതി അറിയുക.',
    calmTitle: 'ശാന്തമായ കടൽ',
    calmDescription: 'മീൻപിടുത്തത്തിന് അനുകൂലമായ ദിനം',
    calmBadge: 'നല്ല അവസ്ഥ',
    moderateTitle: 'മിതമായ കടൽ',
    moderateDescription: 'കുറച്ച് ശ്രദ്ധിക്കുക',
    moderateBadge: 'ശ്രദ്ധിക്കുക',
    roughTitle: 'പ്രക്ഷുബ്ധമായ കടൽ',
    roughDescription: 'ദൂരേക്ക് പോകരുത്',
    roughBadge: 'അപകടകരം',
    conditionsTitle: 'ഇന്ന്',
    windLabel: 'കാറ്റ്',
    wavesLabel: 'തിരമാലകൾ',
    rainLabel: 'മഴ',
    visibilityLabel: 'കാഴ്ച',
    forecastTitle: 'ഇന്നത്തെ പ്രവചനം',
    adviceCalmTitle: 'പോകാൻ അനുയോജ്യം',
    adviceCalmQuote: 'ഇന്ന് കടൽ സാഹചര്യങ്ങൾ അനുകൂലമാണ്.',
    adviceModerateTitle: 'ശ്രദ്ധിക്കുക',
    adviceModerateQuote: 'വൈകുന്നേരം തിരമാലകൾ കൂടിയേക്കാം.',
    adviceRoughTitle: 'കരയിൽ തുടരുക',
    adviceRoughQuote: 'കടൽ പ്രക്ഷുബ്ധമായിരിക്കും. പോകരുത്.',
    askOrcaTitle: 'ORCA-യോട് ചോദിക്കുക',
    askOrcaPrompt: 'കൂടുതൽ അറിയണോ?',
    askOrcaChip: 'വൈകുന്നേരം തിര കൂടുമോ?',
    updatedPrefix: 'അപ്ഡേറ്റ് ചെയ്തത്',
    testToggleLabel: 'കടൽ സ്ഥിതി:',
  },
};

export const getSeaTodayTranslations = (langCode = 'en'): SeaTodayTranslations => {
  return SEA_TODAY_TRANSLATIONS[langCode] || SEA_TODAY_TRANSLATIONS.en;
};

/**
 * Returns mock data strictly matching the prompt specifications:
 * Location: Digha, West Bengal
 * Sea: CALM SEA
 * Status: Good day for fishing
 * Wind: 12 km/h - Moderate
 * Waves: 0.8 m - Calm
 * Rain: 0 mm - No rain
 * Visibility: 10+ km - Good
 * Forecast:
 *   6 AM — 🌤 — 27° — Calm
 *   9 AM — ☀️ — 28° — Calm
 *   12 PM — 🌤 — 28° — Calm
 *   3 PM — 🌊 — 27° — Slight waves
 *   6 PM — ☀️ — 26° — Calm
 * Advice: “Sea conditions look good today.”
 * Last updated: 12 mins ago
 */
export const getSeaTodayData = (
  status: SeaStatus = 'calm',
  langCode = 'en',
  locationName = 'Digha, West Bengal'
): SeaTodayData => {
  const t = getSeaTodayTranslations(langCode);

  if (status === 'rough') {
    return {
      location: locationName,
      seaStatus: 'rough',
      statusTitle: t.roughTitle,
      statusDescription: t.roughDescription,
      statusBadge: `🔴 ${t.roughBadge}`,
      updatedAgo: `12 mins ago`,
      conditions: [
        {
          id: 'wind',
          name: t.windLabel,
          value: '42 km/h',
          status: 'Strong',
          statusType: 'alert',
          icon: 'wind',
        },
        {
          id: 'waves',
          name: t.wavesLabel,
          value: '2.8 m',
          status: 'High',
          statusType: 'alert',
          icon: 'waves',
        },
        {
          id: 'rain',
          name: t.rainLabel,
          value: '18 mm',
          status: 'Heavy rain',
          statusType: 'alert',
          icon: 'rain',
        },
        {
          id: 'visibility',
          name: t.visibilityLabel,
          value: '3 km',
          status: 'Poor',
          statusType: 'alert',
          icon: 'visibility',
        },
      ],
      forecast: [
        { time: '6 AM', icon: '🌧', temp: '25°', condition: 'Rough waves' , status: 'unsafe' },
        { time: '9 AM', icon: '⛈', temp: '25°', condition: 'High waves' , status: 'unsafe' },
        { time: '12 PM', icon: '⛈', temp: '24°', condition: 'Stormy' , status: 'unsafe' },
        { time: '3 PM', icon: '🌧', temp: '24°', condition: 'High waves' , status: 'unsafe' },
        { time: '6 PM', icon: '🌧', temp: '23°', condition: 'Rough sea' , status: 'unsafe' },
      ],
      advice: {
        title: t.adviceRoughTitle,
        quote: t.adviceRoughQuote,
        type: 'danger',
      },
    };
  }

  if (status === 'moderate') {
    return {
      location: locationName,
      seaStatus: 'moderate',
      statusTitle: t.moderateTitle,
      statusDescription: t.moderateDescription,
      statusBadge: `🟡 ${t.moderateBadge}`,
      updatedAgo: `12 mins ago`,
      conditions: [
        {
          id: 'wind',
          name: t.windLabel,
          value: '24 km/h',
          status: 'Breezy',
          statusType: 'caution',
          icon: 'wind',
        },
        {
          id: 'waves',
          name: t.wavesLabel,
          value: '1.4 m',
          status: 'Moderate',
          statusType: 'caution',
          icon: 'waves',
        },
        {
          id: 'rain',
          name: t.rainLabel,
          value: '2 mm',
          status: 'Light rain',
          statusType: 'caution',
          icon: 'rain',
        },
        {
          id: 'visibility',
          name: t.visibilityLabel,
          value: '7 km',
          status: 'Fair',
          statusType: 'caution',
          icon: 'visibility',
        },
      ],
      forecast: [
        { time: '6 AM', icon: '⛅', temp: '26°', condition: 'Calm' , status: 'safe' },
        { time: '9 AM', icon: '🌤', temp: '27°', condition: 'Calm' , status: 'safe' },
        { time: '12 PM', icon: '🌤', temp: '28°', condition: 'Slight waves' , status: 'caution' },
        { time: '3 PM', icon: '🌊', temp: '27°', condition: 'Choppy' , status: 'caution' },
        { time: '6 PM', icon: '⛅', temp: '26°', condition: 'Moderate' , status: 'safe' },
      ],
      advice: {
        title: t.adviceModerateTitle,
        quote: t.adviceModerateQuote,
        type: 'caution',
      },
    };
  }

  // DEFAULT: 'calm'
  return {
    location: locationName,
    seaStatus: 'calm',
    statusTitle: t.calmTitle,
    statusDescription: t.calmDescription,
    statusBadge: `🟢 ${t.calmBadge}`,
    updatedAgo: `12 mins ago`,
    conditions: [
      {
        id: 'wind',
        name: t.windLabel,
        value: '12 km/h',
        status: 'Moderate',
        statusType: 'good',
        icon: 'wind',
      },
      {
        id: 'waves',
        name: t.wavesLabel,
        value: '0.8 m',
        status: 'Calm',
        statusType: 'good',
        icon: 'waves',
      },
      {
        id: 'rain',
        name: t.rainLabel,
        value: '0 mm',
        status: 'No rain',
        statusType: 'good',
        icon: 'rain',
      },
      {
        id: 'visibility',
        name: t.visibilityLabel,
        value: '10+ km',
        status: 'Good',
        statusType: 'good',
        icon: 'visibility',
      },
    ],
    forecast: [
      { time: '6 AM', icon: '🌤', temp: '27°', condition: 'Calm' , status: 'safe' },
      { time: '9 AM', icon: '☀️', temp: '28°', condition: 'Calm' , status: 'safe' },
      { time: '12 PM', icon: '🌤', temp: '28°', condition: 'Calm' , status: 'safe' },
      { time: '3 PM', icon: '🌊', temp: '27°', condition: 'Slight waves' , status: 'caution' },
      { time: '6 PM', icon: '☀️', temp: '26°', condition: 'Calm' , status: 'safe' },
    ],
    advice: {
      title: t.adviceCalmTitle,
      quote: t.adviceCalmQuote,
      type: 'good',
    },
  };
};
