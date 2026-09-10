export type AlertSeverity = 'high' | 'caution' | 'update' | 'none';

export interface AlertItem {
  id: string;
  severity: 'high' | 'caution' | 'update';
  badgeLabel: string;
  title: string;
  message: string;
  timeAgo: string;
  actionRequired?: string;
}

export interface RecentAlertItem {
  id: string;
  title: string;
  action: string;
  time: string;
}

export interface AlertsPageData {
  location: string;
  severity: AlertSeverity;
  mainAlert: AlertItem | null;
  activeAlerts: AlertItem[];
  recentAlerts: RecentAlertItem[];
  whatShouldIDo: string;
  whatShouldIDoTitle: string;
  noAlertsTitle: string;
  noAlertsSubtitle: string;
}

export interface AlertsTranslations {
  pageTitle: string;
  pageSubtitle: string;
  highAlertBadge: string;
  cautionBadge: string;
  updateBadge: string;
  activeAlertsTitle: string;
  recentAlertsTitle: string;
  viewAll: string;
  whatShouldIDoTitle: string;
  whatShouldIDoHigh: string;
  whatShouldIDoNormal: string;
  noAlertsTitle: string;
  noAlertsSubtitle: string;
  askOrcaTitle: string;
  askOrcaPrompt: string;
  askOrcaChip: string;
  askOrcaAnswer: string;
  stateSimulatorLabel: string;
}

export const ALERTS_TRANSLATIONS: Record<string, AlertsTranslations> = {
  en: {
    pageTitle: 'Alerts',
    pageSubtitle: 'Stay informed. Stay safe.',
    highAlertBadge: 'HIGH ALERT',
    cautionBadge: 'CAUTION',
    updateBadge: 'UPDATE',
    activeAlertsTitle: 'Active alerts',
    recentAlertsTitle: 'Recent alerts',
    viewAll: 'View all →',
    whatShouldIDoTitle: 'What should I do?',
    whatShouldIDoHigh: 'Stay close to shore and avoid going far offshore after 2 PM.',
    whatShouldIDoNormal: "You're good for now. Check again before you leave.",
    noAlertsTitle: 'No important alerts',
    noAlertsSubtitle: 'Sea conditions look normal near you.',
    askOrcaTitle: 'Ask ORCA',
    askOrcaPrompt: 'Want to know what this alert means?',
    askOrcaChip: 'What time will winds get dangerous?',
    askOrcaAnswer: 'Winds will start picking up after 1:30 PM and exceed 38 km/h by 2 PM. High swell is expected 8–12 km offshore. Return to shore before 2 PM.',
    stateSimulatorLabel: 'Alert state:',
  },
  bn: {
    pageTitle: 'সতর্কতা',
    pageSubtitle: 'তথ্য জানুন। নিরাপদে থাকুন।',
    highAlertBadge: 'জরুরি সতর্কতা',
    cautionBadge: 'সতর্কতা',
    updateBadge: 'হালনাগাদ',
    activeAlertsTitle: 'সক্রিয় সতর্কতা',
    recentAlertsTitle: 'সাম্প্রতিক সতর্কতা',
    viewAll: 'সব দেখুন →',
    whatShouldIDoTitle: 'আমার কী করা উচিত?',
    whatShouldIDoHigh: 'তটের কাছাকাছি থাকুন এবং দুপুর ২টার পর গভীর সমুদ্রে যাওয়া এড়িয়ে চলুন।',
    whatShouldIDoNormal: 'বর্তমানে পরিস্থিতি অনুকূল। বের হওয়ার আগে আবার দেখে নিন।',
    noAlertsTitle: 'কোনো জরুরি সতর্কতা নেই',
    noAlertsSubtitle: 'আপনার কাছে সমুদ্রের অবস্থা স্বাভাবিক রয়েছে।',
    askOrcaTitle: 'ORCA-কে জিজ্ঞাসা করুন',
    askOrcaPrompt: 'এই সতর্কতার অর্থ জানতে চান?',
    askOrcaChip: 'কখন থেকে বাতাস বিপজ্জনক হবে?',
    askOrcaAnswer: 'দুপুর ১:৩০ থেকে বাতাস বাড়বে এবং দুপুর ২টার মধ্যে ৩৮ কিমি/ঘণ্টা ছাড়িয়ে যেতে পারে। দুপুর ২টার আগেই তীরে ফিরে আসুন।',
    stateSimulatorLabel: 'সতর্কতার অবস্থা:',
  },
  ta: {
    pageTitle: 'எச்சரிக்கைகள்',
    pageSubtitle: 'விழிப்புடன் இருங்கள். பாதுகாப்பாக இருங்கள்.',
    highAlertBadge: 'அதி தீவிர எச்சரிக்கை',
    cautionBadge: 'கவனம்',
    updateBadge: 'தகவல்',
    activeAlertsTitle: 'செயலில் உள்ள எச்சரிக்கைகள்',
    recentAlertsTitle: 'முந்தைய எச்சரிக்கைகள்',
    viewAll: 'அனைத்தையும் பார்க்க →',
    whatShouldIDoTitle: 'நான் என்ன செய்ய வேண்டும்?',
    whatShouldIDoHigh: 'கரைக்கு அருகிலேயே இருங்கள், மதியம் 2 மணிக்கு மேல் ஆழ்கடலுக்குச் செல்வதைத் தவிர்க்கவும்.',
    whatShouldIDoNormal: 'தற்போது நிலைமை சாதாரணமாக உள்ளது. புறப்படும் முன் மீண்டும் சரிபார்க்கவும்.',
    noAlertsTitle: 'முக்கிய எச்சரிக்கைகள் இல்லை',
    noAlertsSubtitle: 'உங்கள் பகுதியில் கடல் நிலை இயல்பாக உள்ளது.',
    askOrcaTitle: 'ORCA-விடம் கேளுங்கள்',
    askOrcaPrompt: 'இந்த எச்சரிக்கையின் அர்த்தம் தெரிய வேண்டுமா?',
    askOrcaChip: 'காற்று எப்போது தீவிரமடையும்?',
    askOrcaAnswer: 'மதியம் 1:30 மணிக்கு மேல் காற்று அதிகரித்து 2 மணிக்கு தீவிரமடையும். மதியம் 2 மணிக்கு முன் கரை திரும்புங்கள்.',
    stateSimulatorLabel: 'எச்சரிக்கை நிலை:',
  },
  te: {
    pageTitle: 'హెచ్చరికలు',
    pageSubtitle: 'సమాచారం తెలుసుకోండి. సురక్షితంగా ఉండండి.',
    highAlertBadge: 'తీవ్ర హెచ్చరిక',
    cautionBadge: 'జాగ్రత్త',
    updateBadge: 'సమాచారం',
    activeAlertsTitle: 'ప్రస్తుత హెచ్చరికలు',
    recentAlertsTitle: 'ఇటీవలి హెచ్చరికలు',
    viewAll: 'అన్నీ చూడండి →',
    whatShouldIDoTitle: 'నేను ఏమి చేయాలి?',
    whatShouldIDoHigh: 'ఒడ్డుకు దగ్గరగానే ఉండండి, మధ్యాహ్నం 2 గంటల తర్వాత సముద్రంలోకి వెళ్లవద్దు.',
    whatShouldIDoNormal: 'ప్రస్తుతానికి అంతా సాధారణంగా ఉంది. బయలుదేరే ముందు మళ్ళీ చూడండి.',
    noAlertsTitle: 'ముఖ్యమైన హెచ్చరికలు లేవు',
    noAlertsSubtitle: 'మీ సమీపంలో సముద్ర పరిస్థితులు సాధారణంగా ఉన్నాయి.',
    askOrcaTitle: 'ORCA ను అడగండి',
    askOrcaPrompt: 'ఈ హెచ్చరిక అర్థం తెలుసుకోవాలా?',
    askOrcaChip: 'గాలి ఎప్పుడు ఎక్కువవుతుంది?',
    askOrcaAnswer: 'మధ్యాహ్నం 1:30 నుండి గాలులు పెరిగి 2 గంటలకు ప్రమాదకర స్థాయికి చేరవచ్చు. 2 గంటల లోపే ఒడ్డుకు రండి.',
    stateSimulatorLabel: 'హెచ్చరిక స్థితి:',
  },
  hi: {
    pageTitle: 'चेतावनी',
    pageSubtitle: 'सूचित रहें। सुरक्षित रहें।',
    highAlertBadge: 'गंभीर चेतावनी',
    cautionBadge: 'सावधानी',
    updateBadge: 'अपडेट',
    activeAlertsTitle: 'सक्रिय चेतावनियाँ',
    recentAlertsTitle: 'हाल की चेतावनियाँ',
    viewAll: 'सभी देखें →',
    whatShouldIDoTitle: 'मुझे क्या करना चाहिए?',
    whatShouldIDoHigh: 'तट के पास रहें और दोपहर 2 बजे के बाद गहरे समुद्र में जाने से बचें।',
    whatShouldIDoNormal: 'अभी स्थिति सामान्य है। जाने से पहले फिर से जांच लें।',
    noAlertsTitle: 'कोई गंभीर चेतावनी नहीं',
    noAlertsSubtitle: 'आपके निकट समुद्र की स्थिति सामान्य दिख रही है।',
    askOrcaTitle: 'ORCA से पूछें',
    askOrcaPrompt: 'इस चेतावनी का अर्थ जानना चाहते हैं?',
    askOrcaChip: 'हवा कब खतरनाक होगी?',
    askOrcaAnswer: 'दोपहर 1:30 के बाद हवा की गति बढ़ेगी और 2 बजे तक 38 किमी/घंटा हो सकती है। 2 बजे से पहले तट पर लौटें।',
    stateSimulatorLabel: 'चेतावनी स्तर:',
  },
  ml: {
    pageTitle: 'മുന്നറിയിപ്പുകൾ',
    pageSubtitle: 'അറിഞ്ഞിരിക്കുക. സുരക്ഷിതരായിരിക്കുക.',
    highAlertBadge: 'തീവ്ര ജാഗ്രത',
    cautionBadge: 'ശ്രദ്ധിക്കുക',
    updateBadge: 'അപ്ഡേറ്റ്',
    activeAlertsTitle: 'സജീവ മുന്നറിയിപ്പുകൾ',
    recentAlertsTitle: 'സമീപകാല മുന്നറിയിപ്പുകൾ',
    viewAll: 'എല്ലാം കാണുക →',
    whatShouldIDoTitle: 'ഞാൻ എന്ത് ചെയ്യണം?',
    whatShouldIDoHigh: 'തീരത്തോട് ചേർന്ന് നിൽക്കുക, ഉച്ചയ്ക്ക് 2 മണിക്ക് ശേഷം ദൂരേക്ക് പോകുന്നത് ഒഴിവാക്കുക.',
    whatShouldIDoNormal: 'ഇപ്പോൾ കുഴപ്പമില്ല. ഇറങ്ങുന്നതിന് മുൻപ് വീണ്ടും നോക്കുക.',
    noAlertsTitle: 'പ്രധാന മുന്നറിയിപ്പുകളില്ല',
    noAlertsSubtitle: 'കടൽ സാധാരണ നിലയിലാണെന്ന് കാണുന്നു.',
    askOrcaTitle: 'ORCA-യോട് ചോദിക്കുക',
    askOrcaPrompt: 'ഈ മുന്നറിയിപ്പിന്റെ അർത്ഥം അറിയണോ?',
    askOrcaChip: 'കാറ്റ് എപ്പോഴാണ് ശക്തമാവുക?',
    askOrcaAnswer: 'ഉച്ചയ്ക്ക് 1:30 ന് ശേഷം കാറ്റ് കൂടും. 2 മണിക്ക് മുൻപായി തിരികെ തീരത്ത് എത്തുക.',
    stateSimulatorLabel: 'മുന്നറിയിപ്പ് നില:',
  },
};

export const getAlertsTranslations = (langCode = 'en'): AlertsTranslations => {
  // Hand-written table first, then the generated catalogue for the languages
  // it never covered, then English. The English fallback stays last and is
  // deliberate: a missing string should show a word the reader may not know
  // rather than nothing at all.
  return (
    ALERTS_TRANSLATIONS[langCode] ||
    (GENERATED_TRANSLATIONS.alertsData?.[langCode] as AlertsTranslations | undefined) ||
    ALERTS_TRANSLATIONS.en
  );
};

/**
 * Returns mock data strictly matching the prompt specifications:
 *
 * Location: Digha, West Bengal
 * Main alert:
 *   HIGH ALERT
 *   Strong winds expected after 2 PM
 *   “Avoid going far offshore after 2 PM.”
 *   Time: 2 hours ago
 *
 * Second alert:
 *   CAUTION
 *   Moderate waves today
 *   “Be careful in open waters.”
 *   Time: 6 hours ago
 *
 * Third update:
 *   UPDATE
 *   No heavy rain expected
 *   “Light rainfall possible in the evening.”
 *   Time: 12 hours ago
 *
 * Recent:
 *   High tide at 4:30 PM — “Plan your return accordingly.”
 *   Wind increasing tomorrow — “Expected 20–25 km/h.”
 */
export const getAlertsData = (
  severity: AlertSeverity = 'high',
  langCode = 'en',
  locationName = 'Digha, West Bengal'
): AlertsPageData => {
  const t = getAlertsTranslations(langCode);

  const defaultRecentAlerts: RecentAlertItem[] = [
    {
      id: 'recent-1',
      title: 'High tide at 4:30 PM',
      action: 'Plan your return accordingly.',
      time: 'Yesterday',
    },
    {
      id: 'recent-2',
      title: 'Wind increasing tomorrow',
      action: 'Expected 20–25 km/h.',
      time: 'Yesterday',
    },
  ];

  if (severity === 'none') {
    return {
      location: locationName,
      severity: 'none',
      mainAlert: null,
      activeAlerts: [],
      recentAlerts: defaultRecentAlerts,
      whatShouldIDo: t.whatShouldIDoNormal,
      whatShouldIDoTitle: t.whatShouldIDoTitle,
      noAlertsTitle: t.noAlertsTitle,
      noAlertsSubtitle: t.noAlertsSubtitle,
    };
  }

  if (severity === 'caution') {
    const mainCaution: AlertItem = {
      id: 'caution-main',
      severity: 'caution',
      badgeLabel: t.cautionBadge,
      title: 'Moderate waves today',
      message: 'Be careful in open waters.',
      timeAgo: '6 hours ago',
      actionRequired: 'Be careful at sea today.',
    };

    const secondaryUpdate: AlertItem = {
      id: 'update-rain',
      severity: 'update',
      badgeLabel: t.updateBadge,
      title: 'No heavy rain expected',
      message: 'Light rainfall possible in the evening.',
      timeAgo: '12 hours ago',
    };

    return {
      location: locationName,
      severity: 'caution',
      mainAlert: mainCaution,
      activeAlerts: [secondaryUpdate],
      recentAlerts: defaultRecentAlerts,
      whatShouldIDo: 'Carry safety gear and stay within 5 km of the coast.',
      whatShouldIDoTitle: t.whatShouldIDoTitle,
      noAlertsTitle: t.noAlertsTitle,
      noAlertsSubtitle: t.noAlertsSubtitle,
    };
  }

  if (severity === 'update') {
    const mainUpdate: AlertItem = {
      id: 'update-main',
      severity: 'update',
      badgeLabel: t.updateBadge,
      title: 'Conditions have changed',
      message: 'Light rainfall possible in the evening.',
      timeAgo: '12 hours ago',
    };

    return {
      location: locationName,
      severity: 'update',
      mainAlert: mainUpdate,
      activeAlerts: [],
      recentAlerts: defaultRecentAlerts,
      whatShouldIDo: t.whatShouldIDoNormal,
      whatShouldIDoTitle: t.whatShouldIDoTitle,
      noAlertsTitle: t.noAlertsTitle,
      noAlertsSubtitle: t.noAlertsSubtitle,
    };
  }

  // DEFAULT: 'high' (The prompt specification)
  const highAlert: AlertItem = {
    id: 'alert-wind',
    severity: 'high',
    badgeLabel: t.highAlertBadge,
    title: 'Strong winds expected after 2 PM',
    message: 'Avoid going far offshore after 2 PM.',
    timeAgo: '2 hours ago',
    actionRequired: 'Dangerous conditions. Avoid going out.',
  };

  const cautionAlert: AlertItem = {
    id: 'alert-waves',
    severity: 'caution',
    badgeLabel: t.cautionBadge,
    title: 'Moderate waves today',
    message: 'Be careful in open waters.',
    timeAgo: '6 hours ago',
  };

  const updateAlert: AlertItem = {
    id: 'alert-rain',
    severity: 'update',
    badgeLabel: t.updateBadge,
    title: 'No heavy rain expected',
    message: 'Light rainfall possible in the evening.',
    timeAgo: '12 hours ago',
  };

  return {
    location: locationName,
    severity: 'high',
    mainAlert: highAlert,
    activeAlerts: [cautionAlert, updateAlert],
    recentAlerts: defaultRecentAlerts,
    whatShouldIDo: t.whatShouldIDoHigh,
    whatShouldIDoTitle: t.whatShouldIDoTitle,
    noAlertsTitle: t.noAlertsTitle,
    noAlertsSubtitle: t.noAlertsSubtitle,
  };
};
import { GENERATED_TRANSLATIONS } from './generatedTranslations';
