export type SafetyStatus = 'safe' | 'caution' | 'danger';

export interface ConditionItem {
  id: string;
  name: string;
  value: string;
  status: string;
  statusType: 'good' | 'neutral' | 'warning' | 'danger';
  iconType: 'wind' | 'waves' | 'rain' | 'visibility' | 'warning' | 'temperature';
  note?: string;
}

export interface SafetyWarning {
  title: string;
  summary: string;
  advisory: string;
  activeFrom?: string;
}

export interface SafetyData {
  status: SafetyStatus;
  statusLabel: string;
  riskSubtitle: string;
  explanation: string;
  whyExplanation: string;
  evidenceChips: string[];
  adviceText: string;
  actionSteps: string[];
  warning: SafetyWarning | null;
  conditions: ConditionItem[];
  lastUpdated: string;
  safeZoneRadiusKm: number;
}

export interface SafetyTranslations {
  pageTitleLine1: string;
  pageTitleLine2: string;
  pageSubtitle: string;
  lastUpdatedPrefix: string;
  whyTitle: string;
  conditionsTitle: string;
  warningTitle: string;
  noWarningTitle: string;
  noWarningSubtitle: string;
  mapTitle: string;
  mapSubtext: string;
  viewFullMap: string;
  safeZoneLegend: string;
  cautionZoneLegend: string;
  dangerZoneLegend: string;
  adviceTitle: string;
  askTitle: string;
  askSubtext: string;
  askPrompt1: string;
  askPrompt2: string;
  backToHome: string;
  testToggleLabel: string;
}

export const SAFETY_TRANSLATIONS: Record<string, SafetyTranslations> = {
  en: {
    pageTitleLine1: 'Is it safe',
    pageTitleLine2: 'to go fishing today?',
    pageSubtitle: 'We check sea and weather conditions before you go.',
    lastUpdatedPrefix: 'Updated',
    whyTitle: 'Why?',
    conditionsTitle: 'Current conditions',
    warningTitle: 'WEATHER WARNING',
    noWarningTitle: 'No active warnings',
    noWarningSubtitle: 'All clear across Digha coastal waters.',
    mapTitle: 'Safe area near you',
    mapSubtext: 'Stay within the green area for safe navigation',
    viewFullMap: 'View full map →',
    safeZoneLegend: 'Safe zone (0–15 km)',
    cautionZoneLegend: 'Caution zone (15–30 km)',
    dangerZoneLegend: 'Danger zone (>30 km)',
    adviceTitle: 'What should I do?',
    askTitle: 'Ask ORCA',
    askSubtext: 'Want to know why?',
    askPrompt1: '“Can I go farther offshore?”',
    askPrompt2: '“When will the waves get higher?”',
    backToHome: 'Back to Home',
    testToggleLabel: 'Safety Simulator:',
  },
  bn: {
    pageTitleLine1: 'আজ কি মাছ ধরতে',
    pageTitleLine2: 'যাওয়া নিরাপদ?',
    pageSubtitle: 'যাওয়ার আগে আমরা সমুদ্র ও আবহাওয়ার পরিস্থিতি যাচাই করি।',
    lastUpdatedPrefix: 'আপডেট হয়েছে',
    whyTitle: 'কেন?',
    conditionsTitle: 'বর্তমান পরিস্থিতি',
    warningTitle: 'আবহাওয়া সতর্কতা',
    noWarningTitle: 'কোনো সক্রিয় সতর্কতা নেই',
    noWarningSubtitle: 'দিঘা উপকূলবর্তী সমুদ্রে পরিস্থিতি স্বাভাবিক।',
    mapTitle: 'আপনার কাছের নিরাপদ অঞ্চল',
    mapSubtext: 'নিরাপদ যাত্রার জন্য সবুজ অঞ্চলের মধ্যে থাকুন',
    viewFullMap: 'সম্পূর্ণ মানচিত্র দেখুন →',
    safeZoneLegend: 'নিরাপদ অঞ্চল (০–১৫ কিমি)',
    cautionZoneLegend: 'সতর্ক অঞ্চল (১৫–৩০ কিমি)',
    dangerZoneLegend: 'বিপজ্জনক অঞ্চল (>৩০ কিমি)',
    adviceTitle: 'আমার কী করা উচিত?',
    askTitle: 'ORCA-কে জিজ্ঞাসা করুন',
    askSubtext: 'কারণ জানতে চান?',
    askPrompt1: '“আমি কি আরও দূরে যেতে পারি?”',
    askPrompt2: '“কখন ঢেউ বাড়বে?”',
    backToHome: 'হোমে ফিরে যান',
    testToggleLabel: 'নিরাপত্তা সিমুলেটর:',
  },
  or: {
    pageTitleLine1: 'ଆଜି ମାଛ ଧରିବାକୁ',
    pageTitleLine2: 'ଯିବା ନିରାପଦ କି?',
    pageSubtitle: 'ଯିବା ପୂର୍ବରୁ ଆମେ ସମୁଦ୍ର ଓ ପାଣିପାଗ ଯାଞ୍ଚ କରୁ।',
    lastUpdatedPrefix: 'ଅଦ୍ୟତନ ହୋଇଛି',
    whyTitle: 'କାହିଁକି?',
    conditionsTitle: 'ବର୍ତ୍ତମାନର ସ୍ଥିତି',
    warningTitle: 'ପାଣିପାଗ ଚେତାବନୀ',
    noWarningTitle: 'କୌଣସି ସକ୍ରିୟ ଚେତାବନୀ ନାହିଁ',
    noWarningSubtitle: 'ଦିଘା ଉପକୂଳରେ ସ୍ଥିତି ସମ୍ପୂର୍ଣ୍ଣ ସ୍ୱାଭାବିକ।',
    mapTitle: 'ଆପଣଙ୍କ ନିକଟରେ ନିରାପଦ ଅଞ୍ଚଳ',
    mapSubtext: 'ନିରାପଦ ରହିବା ପାଇଁ ସବୁଜ ଅଞ୍ଚଳ ଭିତରେ ରୁହନ୍ତୁ',
    viewFullMap: 'ପୂରା ମାନଚିତ୍ର ଦେଖନ୍ତୁ →',
    safeZoneLegend: 'ନିରାପଦ ଅଞ୍ଚଳ (୦–୧୫ କିମି)',
    cautionZoneLegend: 'ସତର୍କ ଅଞ୍ଚଳ (୧୫–୩୦ କିମି)',
    dangerZoneLegend: 'ବିପଦ ଅଞ୍ଚଳ (>୩୦ କିମି)',
    adviceTitle: 'ମୁଁ କ’ଣ କରିବା ଉଚିତ୍?',
    askTitle: 'ORCA କୁ ପଚାରନ୍ତୁ',
    askSubtext: 'କାରଣ ଜାଣିବାକୁ ଚାହାଁନ୍ତି କି?',
    askPrompt1: '“ମୁଁ ଆହୁରି ଦୂରକୁ ଯାଇପାରିବି କି?”',
    askPrompt2: '“ଢେଉ କେତେବେଳେ ବଢ଼ିବ?”',
    backToHome: 'ହୋମ୍ କୁ ଫେରନ୍ତୁ',
    testToggleLabel: 'ସୁରକ୍ଷା ପରୀକ୍ଷଣ:',
  },
  hi: {
    pageTitleLine1: 'क्या आज मछली पकड़ने',
    pageTitleLine2: 'जाना सुरक्षित है?',
    pageSubtitle: 'निकलने से पहले हम समुद्र और मौसम की स्थिति जांचते हैं।',
    lastUpdatedPrefix: 'अपडेट किया गया',
    whyTitle: 'क्यों?',
    conditionsTitle: 'वर्तमान स्थिति',
    warningTitle: 'मौसम चेतावनी',
    noWarningTitle: 'कोई सक्रिय चेतावनी नहीं',
    noWarningSubtitle: 'दीघा तटीय क्षेत्र में स्थिति सामान्य है।',
    mapTitle: 'आपके पास का सुरक्षित क्षेत्र',
    mapSubtext: 'सुरक्षित नेविगेशन के लिए हरे क्षेत्र में रहें',
    viewFullMap: 'पूरा मैप देखें →',
    safeZoneLegend: 'सुरक्षित क्षेत्र (0–15 किमी)',
    cautionZoneLegend: 'सावधानी क्षेत्र (15–30 किमी)',
    dangerZoneLegend: 'खतरे का क्षेत्र (>30 किमी)',
    adviceTitle: 'मुझे क्या करना चाहिए?',
    askTitle: 'ORCA से पूछें',
    askSubtext: 'कारण जानना चाहते हैं?',
    askPrompt1: '“क्या मैं समुद्र में और आगे जा सकता हूँ?”',
    askPrompt2: '“लहरें कब बढ़ेंगी?”',
    backToHome: 'होम पर वापस जाएं',
    testToggleLabel: 'सुरक्षा स्थिति चुनें:',
  },
  ta: {
    pageTitleLine1: 'இன்று மீன்பிடிக்கச்',
    pageTitleLine2: 'செல்வது பாதுகாப்பானதா?',
    pageSubtitle: 'நீங்கள் புறப்படுவதற்கு முன் கடல் மற்றும் வானிலை நிலையை சரிபார்க்கிறோம்.',
    lastUpdatedPrefix: 'புதுப்பிக்கப்பட்டது',
    whyTitle: 'ஏன்?',
    conditionsTitle: 'தற்போதைய நிலைமைகள்',
    warningTitle: 'வானிலை எச்சரிக்கை',
    noWarningTitle: 'செயலில் உள்ள எச்சரிக்கைகள் இல்லை',
    noWarningSubtitle: 'திகா கடலோரப் பகுதியில் நிலைமை சீராக உள்ளது.',
    mapTitle: 'அருகிலுள்ள பாதுகாப்பான பகுதி',
    mapSubtext: 'பாதுகாப்பான பயணத்திற்கு பச்சை பகுதிக்குள் இருங்கள்',
    viewFullMap: 'முழு வரைபடத்தைப் பார்க்க →',
    safeZoneLegend: 'பாதுகாப்பான பகுதி (0–15 கி.மீ)',
    cautionZoneLegend: 'எச்சரிக்கை பகுதி (15–30 கி.மீ)',
    dangerZoneLegend: 'ஆபத்து பகுதி (>30 கி.மீ)',
    adviceTitle: 'நான் என்ன செய்ய வேண்டும்?',
    askTitle: 'ORCA-விடம் கேளுங்கள்',
    askSubtext: 'காரணம் அறிய வேண்டுமா?',
    askPrompt1: '“நான் இன்னும் ஆழக்கடலுக்கு செல்லலாமா?”',
    askPrompt2: '“அலைகள் எப்போது அதிகரிக்கும்?”',
    backToHome: 'முகப்புக்குத் திரும்பு',
    testToggleLabel: 'பாதுகாப்பு நிலை:',
  },
  te: {
    pageTitleLine1: 'ఈ రోజు వేటకు',
    pageTitleLine2: 'వెళ్లడం సురక్షితమేనా?',
    pageSubtitle: 'మీరు బయలుదేరే ముందు సముద్రం మరియు వాతావరణాన్ని పరిశీలిస్తాము.',
    lastUpdatedPrefix: 'నవీకరించబడింది',
    whyTitle: 'ఎందుకు?',
    conditionsTitle: 'ప్రస్తుత పరిస్థితులు',
    warningTitle: 'వాతావరణ హెచ్చరిక',
    noWarningTitle: 'ఎలాంటి హెచ్చరికలు లేవు',
    noWarningSubtitle: 'దిఘా తీరంలో పరిస్థితులు ప్రశాంతంగా ఉన్నాయి.',
    mapTitle: 'మీ సమీప సురక్షిత ప్రాంతం',
    mapSubtext: 'సురక్షిత ప్రయాణం కోసం ఆకుపచ్చ ప్రాంతంలోనే ఉండండి',
    viewFullMap: 'పూర్తి మ్యాప్ చూడండి →',
    safeZoneLegend: 'సురక్షిత ప్రాంతం (0–15 కి.మీ)',
    cautionZoneLegend: 'జాగ్రత్త ప్రాంతం (15–30 కి.మీ)',
    dangerZoneLegend: 'ప్రమాదకర ప్రాంతం (>30 కి.మీ)',
    adviceTitle: 'నేను ఏమి చేయాలి?',
    askTitle: 'ORCAను అడగండి',
    askSubtext: 'కారణం తెలుసుకోవాలా?',
    askPrompt1: '“నేను మరింత లోతుకు వెళ్లవచ్చా?”',
    askPrompt2: '“అలలు ఎప్పుడు పెరుగుతాయి?”',
    backToHome: 'హోమ్‌కు తిరిగి వెళ్లండి',
    testToggleLabel: 'సురక్షిత స్థాయి:',
  },
  ml: {
    pageTitleLine1: 'ഇന്ന് മീൻപിടിക്കാൻ',
    pageTitleLine2: 'പോകുന്നത് സുരക്ഷിതമാണോ?',
    pageSubtitle: 'പുറപ്പെടുന്നതിന് മുൻപ് ഞങ്ങൾ കാലാവസ്ഥയും കടലും പരിശോധിക്കുന്നു.',
    lastUpdatedPrefix: 'അപ്ഡേറ്റ് ചെയ്തത്',
    whyTitle: 'എന്തുകൊണ്ട്?',
    conditionsTitle: 'നിലവിലെ അവസ്ഥകൾ',
    warningTitle: 'കാലാവസ്ഥാ മുന്നറിയിപ്പ്',
    noWarningTitle: 'മുന്നറിയിപ്പുകൾ ഒന്നും തന്നെയില്ല',
    noWarningSubtitle: 'ദിഘ തീരക്കടലിൽ സ്ഥിതിഗതികൾ ശാന്തമാണ്.',
    mapTitle: 'അടുത്തുള്ള സുരക്ഷിത മേഖല',
    mapSubtext: 'സുരക്ഷിതമായ യാത്രയ്ക്ക് പച്ച മേഖലയിൽ തുടരുക',
    viewFullMap: 'മുഴുവൻ മാപ്പ് കാണുക →',
    safeZoneLegend: 'സുരക്ഷിത മേഖല (0–15 കി.മീ)',
    cautionZoneLegend: 'ജാഗ്രതാ മേഖല (15–30 കി.മീ)',
    dangerZoneLegend: 'അപകട മേഖല (>30 കി.മീ)',
    adviceTitle: 'ഞാൻ എന്താണ് ചെയ്യേണ്ടത്?',
    askTitle: 'ORCA യോട് ചോദിക്കൂ',
    askSubtext: 'കാരണം അറിയണമെന്നുണ്ടോ?',
    askPrompt1: '“എനിക്ക് കൂടുതൽ ഉള്ളിലേക്ക് പോകാമോ?”',
    askPrompt2: '“തിരമാലകൾ എപ്പോൾ ഉയരും?”',
    backToHome: 'ഹോമിലേക്ക് മടങ്ങുക',
    testToggleLabel: 'സുരക്ഷാ നില പരിശോധന:',
  },
  mr: {
    pageTitleLine1: 'आज मासेमारीला',
    pageTitleLine2: 'जाणे सुरक्षित आहे का?',
    pageSubtitle: 'जाण्यापूर्वी आम्ही समुद्र आणि हवामानाची स्थिती तपासतो.',
    lastUpdatedPrefix: 'अपडेट केले',
    whyTitle: 'का?',
    conditionsTitle: 'सद्य परिस्थिती',
    warningTitle: 'हवामान इशारा',
    noWarningTitle: 'कोणताही इशारा नाही',
    noWarningSubtitle: 'दिघा किनारपट्टी भागात वातावरण अनुकूल आहे.',
    mapTitle: 'तुमच्या जवळील सुरक्षित क्षेत्र',
    mapSubtext: 'सुरक्षित प्रवासासाठी हिरव्या क्षेत्रात राहा',
    viewFullMap: 'पूर्ण नकाशा पहा →',
    safeZoneLegend: 'सुरक्षित क्षेत्र (०–१५ किमी)',
    cautionZoneLegend: 'सावधगिरीचे क्षेत्र (१५–३० किमी)',
    dangerZoneLegend: 'धोकादायक क्षेत्र (>३० किमी)',
    adviceTitle: 'मी काय करावे?',
    askTitle: 'ORCA ला विचारा',
    askSubtext: 'कारण जाणून घ्यायचे आहे?',
    askPrompt1: '“मी अधिक खोल समुद्रात जाऊ शकतो का?”',
    askPrompt2: '“लाटा कधी वाढतील?”',
    backToHome: 'मुख्यपृष्ठावर परत जा',
    testToggleLabel: 'सुरक्षा चाचणी:',
  },
  gu: {
    pageTitleLine1: 'શું આજે માછીમારી કરવા',
    pageTitleLine2: 'જવું સલામત છે?',
    pageSubtitle: 'નીકળતા પહેલાં અમે દરિયા અને હવામાનની સ્થિતિ તપાસીએ છીએ.',
    lastUpdatedPrefix: 'અપડેટ થયેલ',
    whyTitle: 'કેમ?',
    conditionsTitle: 'હાલની પરિસ્થિતિ',
    warningTitle: 'હવામાન ચેતવણી',
    noWarningTitle: 'કોઈ સક્રિય ચેતવણી નથી',
    noWarningSubtitle: 'દીઘા દરિયાકાંઠે સ્થિતિ સામાન્ય છે.',
    mapTitle: 'તમારી નજીકનો સલામત વિસ્તાર',
    mapSubtext: 'સલામત રહેવા લીલા વિસ્તારની અંદર રહો',
    viewFullMap: 'સંપૂર્ણ નકશો જુઓ →',
    safeZoneLegend: 'સલામત વિસ્તાર (0–15 કિમી)',
    cautionZoneLegend: 'સાવધાની વિસ્તાર (15–30 કિમી)',
    dangerZoneLegend: 'જોખમી વિસ્તાર (>30 કિમી)',
    adviceTitle: 'મારે શું કરવું જોઈએ?',
    askTitle: 'ORCA ને પૂછો',
    askSubtext: 'કારણ જાણવું છે?',
    askPrompt1: '“શું હું વધારે ઊંડા દરિયામાં જઈ શકું?”',
    askPrompt2: '“મોજાં ક્યારે વધશે?”',
    backToHome: 'હોમ પર પાછા જાઓ',
    testToggleLabel: 'સલામતી સ્થિતિ:',
  },
};

export function getSafetyTranslations(langCode?: string): SafetyTranslations {
  if (!langCode) return SAFETY_TRANSLATIONS.en;
  return SAFETY_TRANSLATIONS[langCode] || SAFETY_TRANSLATIONS.en;
}

/**
 * Returns structured safety data for any of the 3 states:
 * - 'safe' (SAFE TO GO)
 * - 'caution' (BE CAREFUL)
 * - 'danger' (DO NOT GO)
 * localized for the selected language.
 */
export function getSafetyData(status: SafetyStatus = 'safe', langCode: string = 'en'): SafetyData {
  if (status === 'caution') {
    return {
      status: 'caution',
      statusLabel: langCode === 'bn' ? 'সতর্ক থাকুন' : langCode === 'hi' ? 'सावधान रहें' : 'BE CAREFUL',
      riskSubtitle: langCode === 'bn' ? 'আজ মাঝারি ঝুঁকি।' : langCode === 'hi' ? 'आज मध्यम जोखिम।' : 'Moderate risk today.',
      explanation:
        langCode === 'bn'
          ? 'মাছ ধরা সম্ভব, তবে অতিরিক্ত সতর্কতা প্রয়োজন।'
          : langCode === 'hi'
          ? 'मछली पकड़ना संभव है, लेकिन सावधानी आवश्यक है।'
          : 'Fishing is possible, but conditions need caution.',
      whyExplanation:
        langCode === 'bn'
          ? 'বাতাসের গতি বাড়ছে এবং খোলা সমুদ্রে ১.৮ মিটার পর্যন্ত ঢেউ উঠছে।'
          : langCode === 'hi'
          ? 'हवा की गति बढ़ रही है और खुले समुद्र में 1.8 मीटर तक लहरें उठ रही हैं।'
          : 'Wind is picking up and waves are building up to 1.8 m in open coastal waters.',
      evidenceChips:
        langCode === 'bn'
          ? ['⚠️ মাঝারি ঢেউ (১.৮ মি)', '⚠️ ক্রমবর্ধমান বাতাস', '✓ ভালো দৃশ্যমানতা', '⚠️ দুপুরের সতর্কতা']
          : langCode === 'hi'
          ? ['⚠️ मध्यम लहरें (1.8 मी)', '⚠️ तेज़ हवा', '✓ अच्छी दृश्यता', '⚠️ दोपहर की चेतावनी']
          : ['⚠️ Moderate waves (1.8 m)', '⚠️ Rising wind', '✓ Good visibility', '⚠️ Afternoon warning'],
      adviceText:
        langCode === 'bn'
          ? 'উপকূলের কাছাকাছি (১০ কিমি এর মধ্যে) থাকুন। ছোট নৌকা ও ডিঙি নিয়ে দূর সমুদ্রে যাবেন না।'
          : langCode === 'hi'
          ? 'तट के करीब (10 किमी के भीतर) रहें। छोटी नौकाओं को विशेष सावधानी बरतनी चाहिए।'
          : 'Stay close to shore (under 10 km). Small wooden craft and motorized dinghies should exercise caution and return before winds intensify.',
      actionSteps: [
        langCode === 'bn' ? '১০ কিমি উপকূলের ভেতর থাকুন' : 'Stay within 10 km of shore',
        langCode === 'bn' ? 'দুপুর ২টার আগে ফিরে আসুন' : 'Return before 2 PM wind pickup',
        langCode === 'bn' ? 'লাইফ জ্যাকেট পরে থাকুন' : 'Wear life jackets at all times',
      ],
      warning: {
        title: 'WEATHER WARNING',
        summary: 'Strong winds expected after 2 PM.',
        advisory: 'Avoid going far offshore after 2 PM.',
        activeFrom: '2:00 PM',
      },
      conditions: [
        {
          id: 'wind',
          name: langCode === 'bn' ? 'বাতাস' : 'Wind',
          value: '24 km/h',
          status: langCode === 'bn' ? 'মাঝারি' : 'Moderate',
          statusType: 'warning',
          iconType: 'wind',
          note: 'Gusts to 32 km/h',
        },
        {
          id: 'waves',
          name: langCode === 'bn' ? 'ঢেউ' : 'Waves',
          value: '1.8 m',
          status: langCode === 'bn' ? 'উত্তাল' : 'Choppy',
          statusType: 'warning',
          iconType: 'waves',
          note: 'Moderate swell',
        },
        {
          id: 'rain',
          name: langCode === 'bn' ? 'বৃষ্টি' : 'Rain',
          value: '2 mm',
          status: langCode === 'bn' ? 'হালকা বৃষ্টি' : 'Light drizzle',
          statusType: 'neutral',
          iconType: 'rain',
        },
        {
          id: 'visibility',
          name: langCode === 'bn' ? 'দৃশ্যমানতা' : 'Visibility',
          value: '7 km',
          status: langCode === 'bn' ? 'মাঝারি' : 'Moderate',
          statusType: 'neutral',
          iconType: 'visibility',
        },
        {
          id: 'warning',
          name: langCode === 'bn' ? 'সতর্কতা' : 'Weather warning',
          value: langCode === 'bn' ? 'সক্রিয় (২টা)' : 'Active (2 PM)',
          status: langCode === 'bn' ? 'সতর্ক সংকেত' : 'Caution alert',
          statusType: 'warning',
          iconType: 'warning',
        },
        {
          id: 'temperature',
          name: langCode === 'bn' ? 'জলের তাপমাত্রা' : 'Water temperature',
          value: '27°C',
          status: langCode === 'bn' ? 'স্বাভাবিক' : 'Normal',
          statusType: 'good',
          iconType: 'temperature',
        },
      ],
      lastUpdated: '8 mins ago',
      safeZoneRadiusKm: 10,
    };
  }

  if (status === 'danger') {
    return {
      status: 'danger',
      statusLabel: langCode === 'bn' ? 'সমুদ্রে যাবেন না' : langCode === 'hi' ? 'समुद्र में न जाएं' : 'DO NOT GO',
      riskSubtitle: langCode === 'bn' ? 'আজ উচ্চ ঝুঁকি।' : langCode === 'hi' ? 'आज उच्च जोखिम।' : 'High risk today.',
      explanation:
        langCode === 'bn'
          ? 'বিপজ্জনক সমুদ্র পরিস্থিতি। সমুদ্রে যাওয়া এড়িয়ে চলুন।'
          : langCode === 'hi'
          ? 'खतरनाक समुद्री स्थिति। बाहर जाने से बचें।'
          : 'Dangerous sea conditions. Avoid going out.',
      whyExplanation:
        langCode === 'bn'
          ? 'উত্তর বঙ্গোপসাগরে ভারী নিম্নচাপ, ৩.২ মিটারের বেশি উঁচু ঢেউ এবং ৫০ কিমি/ঘন্টা বেগে ঝোড়ো হাওয়া চলছে।'
          : langCode === 'hi'
          ? 'उत्तर बंगाल की खाड़ी में भारी दबाव, 3.2 मीटर से अधिक ऊंची लहरें और 50 किमी/घंटा की तूफानी हवाएं हैं।'
          : 'Heavy storm surge, high swells exceeding 3.2 m, and gale force winds reported in North Bay of Bengal.',
      evidenceChips:
        langCode === 'bn'
          ? ['✕ উচ্চ ঢেউ (>৩ মি)', '✕ ঝোড়ো বাতাস (৫০ কিমি)', '✕ কম দৃশ্যমানতা', '✕ লাল সতর্কতা']
          : langCode === 'hi'
          ? ['✕ ऊंची लहरें (>3 मी)', '✕ तूफानी हवा (50 किमी)', '✕ कम दृश्यता', '✕ रेड अलर्ट']
          : ['✕ High waves (>3.2 m)', '✕ Gale force winds', '✕ Poor visibility', '✕ Red warning active'],
      adviceText:
        langCode === 'bn'
          ? 'কোনো পরিস্থিতিতেই সমুদ্রে যাবেন না। দিঘা শঙ্করপুর মৎস্য বন্দরে সমস্ত ট্রলার ও নৌকা শক্ত করে বেঁধে রাখুন।'
          : langCode === 'hi'
          ? 'किसी भी परिस्थिति में समुद्र में न जाएं। सभी नावों को बंदरगाह पर सुरक्षित बांध कर रखें।'
          : 'Do not venture into the sea. Keep all boats tied securely at Digha Sankarpur fishing harbour until official clearance.',
      actionSteps: [
        langCode === 'bn' ? 'সমুদ্রে যাওয়া পুরোপুরি বন্ধ রাখুন' : 'Do not venture into the sea',
        langCode === 'bn' ? 'নৌকা বন্দরে নিরাপদ স্থানে বাঁধুন' : 'Secure all vessels at harbour',
        langCode === 'bn' ? 'সরকারি সতর্কবার্তা শুনুন' : 'Monitor marine radio & alerts',
      ],
      warning: {
        title: 'SEVERE MARINE WARNING',
        summary: 'Gale wind warning & rough sea alert in effect.',
        advisory: 'Fishermen are strictly advised not to venture into deep sea.',
        activeFrom: 'Current',
      },
      conditions: [
        {
          id: 'wind',
          name: langCode === 'bn' ? 'বাতাস' : 'Wind',
          value: '48 km/h',
          status: langCode === 'bn' ? 'প্রচণ্ড ঝড়' : 'Gale force',
          statusType: 'danger',
          iconType: 'wind',
          note: 'Gusts up to 60 km/h',
        },
        {
          id: 'waves',
          name: langCode === 'bn' ? 'ঢেউ' : 'Waves',
          value: '3.4 m',
          status: langCode === 'bn' ? 'খুব উত্তাল' : 'Rough / High',
          statusType: 'danger',
          iconType: 'waves',
          note: 'Dangerous swell',
        },
        {
          id: 'rain',
          name: langCode === 'bn' ? 'বৃষ্টি' : 'Rain',
          value: '32 mm',
          status: langCode === 'bn' ? 'ভারী বৃষ্টি' : 'Heavy rain',
          statusType: 'danger',
          iconType: 'rain',
        },
        {
          id: 'visibility',
          name: langCode === 'bn' ? 'দৃশ্যমানতা' : 'Visibility',
          value: '2.5 km',
          status: langCode === 'bn' ? 'খুব কম' : 'Poor',
          statusType: 'danger',
          iconType: 'visibility',
        },
        {
          id: 'warning',
          name: langCode === 'bn' ? 'সতর্কতা' : 'Weather warning',
          value: langCode === 'bn' ? 'লাল সতর্কতা' : 'Red Alert',
          status: langCode === 'bn' ? 'বন্দরে অবস্থান' : 'Harbour stay',
          statusType: 'danger',
          iconType: 'warning',
        },
        {
          id: 'temperature',
          name: langCode === 'bn' ? 'জলের তাপমাত্রা' : 'Water temperature',
          value: '25°C',
          status: langCode === 'bn' ? 'উত্তাল সমুদ্র' : 'Rough sea',
          statusType: 'neutral',
          iconType: 'temperature',
        },
      ],
      lastUpdated: '5 mins ago',
      safeZoneRadiusKm: 0,
    };
  }

  // Default: SAFE TO GO
  return {
    status: 'safe',
    statusLabel: langCode === 'bn' ? 'যাত্রা নিরাপদ' : langCode === 'hi' ? 'जाना सुरक्षित है' : 'SAFE TO GO',
    riskSubtitle: langCode === 'bn' ? 'আজ ঝুঁকি কম।' : langCode === 'hi' ? 'आज कम जोखिम।' : 'Low risk today.',
    explanation:
      langCode === 'bn'
        ? 'আপনার এলাকায় মাছ ধরার জন্য সমুদ্র পরিস্থিতি অনুকূল।'
        : langCode === 'hi'
        ? 'आपके क्षेत्र में मछली पकड़ने के लिए समुद्र की स्थिति अनुकूल है।'
        : 'Sea conditions look favourable for fishing in your area.',
    whyExplanation:
      langCode === 'bn'
        ? 'ঢেউ কম, বাতাস মাঝারি, দৃশ্যমানতা পরিষ্কার এবং কোনো সক্রিয় আবহাওয়া সতর্কতা নেই।'
        : langCode === 'hi'
        ? 'लहरें कम हैं, हवा मध्यम है, दृश्यता अच्छी है और कोई मौसम चेतावनी नहीं है।'
        : 'Waves are low, wind is moderate, visibility is good, and there are no active weather warnings.',
    evidenceChips:
      langCode === 'bn'
        ? ['✓ শান্ত ঢেউ (০.৮ মি)', '✓ শান্ত বাতাস (১২ কিমি)', '✓ পরিষ্কার দৃশ্যমানতা', '✓ কোনো সতর্কতা নেই']
        : langCode === 'hi'
        ? ['✓ शांत लहरें (0.8 मी)', '✓ अनुकूल हवा (12 किमी)', '✓ अच्छी दृश्यता', '✓ कोई चेतावनी नहीं']
        : ['✓ Low waves', '✓ Moderate wind', '✓ Good visibility', '✓ No warnings'],
    adviceText:
      langCode === 'bn'
        ? 'এখন পরিস্থিতি ভালো। মাছ ধরতে গেলে সবুজ অঞ্চলের মধ্যে থাকুন এবং গভীর সমুদ্রে যাওয়ার আগে আবহাওয়া যাচাই করুন।'
        : langCode === 'hi'
        ? 'अभी स्थिति अच्छी है। यदि आप जा रहे हैं, तो हरे क्षेत्र में रहें और गहरे समुद्र में जाने से पहले अलर्ट देखें।'
        : 'Good conditions now. If you go fishing, stay within the green area and check alerts before heading farther offshore.',
    actionSteps: [
      langCode === 'bn' ? '১৫ কিমি সবুজ অঞ্চলের মধ্যে থাকুন' : 'Stay within 15 km of shore',
      langCode === 'bn' ? 'সূর্যাস্তের আগে বা বাতাস বদলালে ফিরুন' : 'Return before sunset or if wind shifts',
      langCode === 'bn' ? 'নৌকায় লাইফ জ্যাকেট প্রস্তুত রাখুন' : 'Keep life jackets accessible on board',
    ],
    warning: null, // No active warning
    conditions: [
      {
        id: 'wind',
        name: langCode === 'bn' ? 'বাতাস' : 'Wind',
        value: '12 km/h',
        status: langCode === 'bn' ? 'অনুকূল' : 'Good',
        statusType: 'good',
        iconType: 'wind',
        note: 'Gentle sea breeze',
      },
      {
        id: 'waves',
        name: langCode === 'bn' ? 'ঢেউ' : 'Waves',
        value: '0.8 m',
        status: langCode === 'bn' ? 'শান্ত' : 'Calm',
        statusType: 'good',
        iconType: 'waves',
        note: 'Smooth swell',
      },
      {
        id: 'rain',
        name: langCode === 'bn' ? 'বৃষ্টি' : 'Rain',
        value: '0 mm',
        status: langCode === 'bn' ? 'বৃষ্টি নেই' : 'No rain',
        statusType: 'good',
        iconType: 'rain',
      },
      {
        id: 'visibility',
        name: langCode === 'bn' ? 'দৃশ্যমানতা' : 'Visibility',
        value: '10+ km',
        status: langCode === 'bn' ? 'চমৎকার' : 'Good',
        statusType: 'good',
        iconType: 'visibility',
      },
      {
        id: 'warning',
        name: langCode === 'bn' ? 'আবহাওয়া সতর্কতা' : 'Weather warning',
        value: langCode === 'bn' ? 'কিছু নেই' : 'None',
        status: langCode === 'bn' ? 'সক্রিয় সতর্কতা নেই' : 'No active alerts',
        statusType: 'good',
        iconType: 'warning',
      },
      {
        id: 'temperature',
        name: langCode === 'bn' ? 'জলের তাপমাত্রা' : 'Water temperature',
        value: '28°C',
        status: langCode === 'bn' ? 'স্বাভাবিক' : 'Normal',
        statusType: 'good',
        iconType: 'temperature',
      },
    ],
    lastUpdated: '12 mins ago',
    safeZoneRadiusKm: 15,
  };
}
