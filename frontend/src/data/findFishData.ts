export interface FindFishTranslations {
  pageTitleLine1: string;
  pageTitleLine2: string;
  pageSubtitle: string;
  bestAreaBadge: string;
  bestDistance: string;
  bestChance: string;
  bestReason: string;
  goHereBtn: string;
  otherOptionsTitle: string;
  otherOption1Distance: string;
  otherOption1Chance: string;
  otherOption1Action: string;
  otherOption2Distance: string;
  otherOption2Chance: string;
  otherOption2Action: string;
  quickTipTitle: string;
  quickTipText: string;
  askOrcaTitle: string;
  askOrcaPrompt: string;
  askOrcaChip: string;
  mapCurrentLocation: string;
  mapBestZone: string;
  mapGoodZone: string;
  mapAvoidZone: string;
  compassHeading: string;
  travelTime: string;
  seaCondition: string;
  modalClose: string;
}

export const FIND_FISH_TRANSLATIONS: Record<string, FindFishTranslations> = {
  en: {
    pageTitleLine1: 'Where should',
    pageTitleLine2: 'I fish today?',
    pageSubtitle: 'ORCA found the best spots near you.',
    bestAreaBadge: 'BEST AREA',
    bestDistance: '12 km offshore',
    bestChance: 'Good fishing chance',
    bestReason: 'Good fish conditions + safe sea',
    goHereBtn: 'GO HERE →',
    otherOptionsTitle: 'Other good options',
    otherOption1Distance: '18 km offshore',
    otherOption1Chance: 'Moderate chance',
    otherOption1Action: 'Still a good option →',
    otherOption2Distance: '25 km offshore',
    otherOption2Chance: 'Moderate chance',
    otherOption2Action: 'Good conditions →',
    quickTipTitle: 'Quick tip',
    quickTipText: 'Try the green area first. Check sea conditions again if you go farther.',
    askOrcaTitle: 'Ask ORCA',
    askOrcaPrompt: 'Want to know why this spot is good?',
    askOrcaChip: 'Why this spot?',
    mapCurrentLocation: 'Digha Harbour',
    mapBestZone: 'Best spot',
    mapGoodZone: 'Good spot',
    mapAvoidZone: 'Avoid',
    compassHeading: '145° South-East (SE)',
    travelTime: '~40–45 mins at 8 knots',
    seaCondition: 'Calm sea (0.8m wave, safe)',
    modalClose: 'Got it',
  },
  bn: {
    pageTitleLine1: 'আজ কোথায়',
    pageTitleLine2: 'মাছ ধরতে যাব?',
    pageSubtitle: 'ORCA আপনার কাছাকাছি সেরা স্থানগুলো খুঁজে পেয়েছে।',
    bestAreaBadge: 'সেরা এলাকা',
    bestDistance: 'উপকূল থেকে ১২ কিমি দূরে',
    bestChance: 'মাছ পাওয়ার ভালো সুযোগ',
    bestReason: 'অনুকূল মাছের পরিবেশ + শান্ত সমুদ্র',
    goHereBtn: 'এখানে যান →',
    otherOptionsTitle: 'অন্যান্য ভালো বিকল্প',
    otherOption1Distance: 'উপকূল থেকে ১৮ কিমি দূরে',
    otherOption1Chance: 'মাঝারি সুযোগ',
    otherOption1Action: 'এখনও ভালো বিকল্প →',
    otherOption2Distance: 'উপকূল থেকে ২৫ কিমি দূরে',
    otherOption2Chance: 'মাঝারি সুযোগ',
    otherOption2Action: 'অনুকূল আবহাওয়া →',
    quickTipTitle: 'দ্রুত পরামর্শ',
    quickTipText: 'প্রথমে সবুজ এলাকায় যান। বেশি দূরে গেলে আবার সমুদ্রের অবস্থা দেখে নিন।',
    askOrcaTitle: 'ORCA-কে জিজ্ঞাসা করুন',
    askOrcaPrompt: 'এই জায়গাটি কেন ভালো জানতে চান?',
    askOrcaChip: 'এই জায়গাটি কেন ভালো?',
    mapCurrentLocation: 'দিঘা মোহনা',
    mapBestZone: 'সেরা জায়গা',
    mapGoodZone: 'ভালো জায়গা',
    mapAvoidZone: 'যাবেন না',
    compassHeading: '১৪৫° দক্ষিণ-পূর্ব',
    travelTime: '~৪০-৪৫ মিনিট (৮ নট)',
    seaCondition: 'শান্ত সমুদ্র (০.৮ মি ঢেউ, নিরাপদ)',
    modalClose: 'বুঝেছি',
  },
  or: {
    pageTitleLine1: 'ଆଜି କେଉଁଠି',
    pageTitleLine2: 'ମାଛ ଧରିବାକୁ ଯିବି?',
    pageSubtitle: 'ORCA ଆପଣଙ୍କ ପାଖରେ ସର୍ବୋତ୍ତମ ସ୍ଥାନ ଖୋଜି ପାଇଛି।',
    bestAreaBadge: 'ସର୍ବୋତ୍ତମ ଅଞ୍ଚଳ',
    bestDistance: 'ଉପକୂଳରୁ ୧୨ କିମି',
    bestChance: 'ମାଛ ମିଳିବାର ଭଲ ସୁଯୋଗ',
    bestReason: 'ଭଲ ମାଛ ଅନୁକୂଳତା + ସୁରକ୍ଷିତ ସମୁଦ୍ର',
    goHereBtn: 'ଏଠାକୁ ଯାଆନ୍ତୁ →',
    otherOptionsTitle: 'ଅନ୍ୟାନ୍ୟ ଭଲ ବିକଳ୍ପ',
    otherOption1Distance: 'ଉପକୂଳରୁ ୧୮ କିମି',
    otherOption1Chance: 'ମଧ୍ୟମ ସୁଯୋଗ',
    otherOption1Action: 'ଏବେ ମଧ୍ୟ ଭଲ ବିକଳ୍ପ →',
    otherOption2Distance: 'ଉପକୂଳରୁ ୨୫ କିମି',
    otherOption2Chance: 'ମଧ୍ୟମ ସୁଯୋଗ',
    otherOption2Action: 'ଭଲ ପାଣିପାଗ →',
    quickTipTitle: 'ଶୀଘ୍ର ପରାମର୍ଶ',
    quickTipText: 'ପ୍ରଥମେ ସବୁଜ ଅଞ୍ଚଳରେ ଚେଷ୍ଟା କରନ୍ତୁ। ଦୂରକୁ ଗଲେ ପୁଣି ସମୁଦ୍ର ଅବସ୍ଥା ଯାଞ୍ଚ କରନ୍ତୁ।',
    askOrcaTitle: 'ORCA କୁ ପଚାରନ୍ତୁ',
    askOrcaPrompt: 'ଏହି ସ୍ଥାନଟି କାହିଁକି ଭଲ ଜାଣିବାକୁ ଚାହାଁନ୍ତି?',
    askOrcaChip: 'ଏହି ସ୍ଥାନଟି କାହିଁକି ଭଲ?',
    mapCurrentLocation: 'ଦିଘା ବନ୍ଦର',
    mapBestZone: 'ସର୍ବୋତ୍ତମ ସ୍ଥାନ',
    mapGoodZone: 'ଭଲ ସ୍ଥାନ',
    mapAvoidZone: 'ଯାଆନ୍ତୁ ନାହିଁ',
    compassHeading: '୧୪୫° ଦକ୍ଷିଣ-ପୂର୍ବ',
    travelTime: '~୪୦–୪୫ ମିନିଟ୍',
    seaCondition: 'ଶାନ୍ତ ସମୁଦ୍ର (୦.୮ମି ତରଙ୍ଗ)',
    modalClose: 'ବୁଝିଲି',
  },
  hi: {
    pageTitleLine1: 'आज मछली पकड़ने',
    pageTitleLine2: 'कहाँ जाऊं?',
    pageSubtitle: 'ORCA ने आपके पास सबसे अच्छे स्थान खोजे हैं।',
    bestAreaBadge: 'सबसे अच्छा क्षेत्र',
    bestDistance: 'तट से 12 किमी दूर',
    bestChance: 'मछली मिलने की अच्छी संभावना',
    bestReason: 'मछलियों के अनुकूल स्थिति + सुरक्षित समुद्र',
    goHereBtn: 'यहाँ जाएँ →',
    otherOptionsTitle: 'अन्य अच्छे विकल्प',
    otherOption1Distance: 'तट से 18 किमी दूर',
    otherOption1Chance: 'मध्यम संभावना',
    otherOption1Action: 'अभी भी अच्छा विकल्प →',
    otherOption2Distance: 'तट से 25 किमी दूर',
    otherOption2Chance: 'मध्यम संभावना',
    otherOption2Action: 'अनुकूल स्थिति →',
    quickTipTitle: 'त्वरित सुझाव',
    quickTipText: 'पहले हरे क्षेत्र में जाएँ। अधिक दूर जाने पर समुद्र की स्थिति दोबारा जाँचें।',
    askOrcaTitle: 'ORCA से पूछें',
    askOrcaPrompt: 'जानना चाहते हैं यह स्थान क्यों अच्छा है?',
    askOrcaChip: 'यह स्थान क्यों अच्छा है?',
    mapCurrentLocation: 'दीघा बंदरगाह',
    mapBestZone: 'सबसे अच्छा स्थान',
    mapGoodZone: 'अच्छा स्थान',
    mapAvoidZone: 'यहाँ न जाएँ',
    compassHeading: '145° दक्षिण-पूर्व',
    travelTime: '~40–45 मिनट (8 समुद्री मील)',
    seaCondition: 'शांत समुद्र (0.8 मी लहर, सुरक्षित)',
    modalClose: 'समझ गया',
  },
  ta: {
    pageTitleLine1: 'இன்று மீன்பிடிக்க',
    pageTitleLine2: 'எங்கு செல்ல வேண்டும்?',
    pageSubtitle: 'ORCA உங்களுக்கு அருகிலுள்ள சிறந்த இடங்களைக் கண்டறிந்துள்ளது.',
    bestAreaBadge: 'சிறந்த பகுதி',
    bestDistance: 'கடற்கரையிலிருந்து 12 கி.மீ',
    bestChance: 'நல்ல மீன்பிடி வாய்ப்பு',
    bestReason: 'நல்ல மீன் நிலை + பாதுகாப்பான கடல்',
    goHereBtn: 'இங்கே செல்லவும் →',
    otherOptionsTitle: 'மற்ற நல்ல தேர்வுகள்',
    otherOption1Distance: 'கடற்கரையிலிருந்து 18 கி.மீ',
    otherOption1Chance: 'மிதமான வாய்ப்பு',
    otherOption1Action: 'இன்னும் நல்ல தேர்வு →',
    otherOption2Distance: 'கடற்கரையிலிருந்து 25 கி.மீ',
    otherOption2Chance: 'மிதமான வாய்ப்பு',
    otherOption2Action: 'நல்ல சூழல் →',
    quickTipTitle: 'விரைவான குறிப்பு',
    quickTipText: 'முதலில் பச்சை பகுதியில் முயற்சிக்கவும். மேலும் தூரம் சென்றால் கடல் நிலையை சரிபார்க்கவும்.',
    askOrcaTitle: 'ORCA-விடம் கேளுங்கள்',
    askOrcaPrompt: 'இந்த இடம் ஏன் சிறந்தது என்று அறிய வேண்டுமா?',
    askOrcaChip: 'இந்த இடம் ஏன் சிறந்தது?',
    mapCurrentLocation: 'திகா துறைமுகம்',
    mapBestZone: 'சிறந்த இடம்',
    mapGoodZone: 'நல்ல இடம்',
    mapAvoidZone: 'தவிர்க்கவும்',
    compassHeading: '145° தென்கிழக்கு',
    travelTime: '~40–45 நிமிடங்கள்',
    seaCondition: 'அமைதியான கடல் (0.8 மீ அலை)',
    modalClose: 'புரிந்தது',
  },
  te: {
    pageTitleLine1: 'నేడు చేపల వేటకు',
    pageTitleLine2: 'ఎక్కడికి వెళ్ళాలి?',
    pageSubtitle: 'ORCA మీ సమీపంలో ఉత్తమమైన ప్రదేశాలను కనుగొంది.',
    bestAreaBadge: 'ఉత్తమ ప్రాంతం',
    bestDistance: 'తీరానికి 12 కి.మీ దూరంలో',
    bestChance: 'మంచి చేపల అవకాశం',
    bestReason: 'అనుకూల పరిస్థితులు + సురక్షిత సముద్రం',
    goHereBtn: 'ఇక్కడికి వెళ్ళండి →',
    otherOptionsTitle: 'ఇతర మంచి ఎంపికలు',
    otherOption1Distance: 'తీరానికి 18 కి.మీ దూరంలో',
    otherOption1Chance: 'మధ్యస్థ అవకాశం',
    otherOption1Action: 'ఇప్పటికీ మంచి ఎంపిక →',
    otherOption2Distance: 'తీరానికి 25 కి.మీ దూరంలో',
    otherOption2Chance: 'మధ్యస్థ అవకాశం',
    otherOption2Action: 'మంచి పరిస్థితులు →',
    quickTipTitle: 'చిన్న చిట్కా',
    quickTipText: 'ముందుగా ఆకుపచ్చ ప్రాంతాన్ని ప్రయత్నించండి. మరింత ముందుకు వెళ్తే సముద్ర స్థితిని మళ్లీ తనిఖీ చేయండి.',
    askOrcaTitle: 'ORCA ని అడగండి',
    askOrcaPrompt: 'ఈ ప్రదేశం ఎందుకు మంచిదో తెలుసుకోవాలా?',
    askOrcaChip: 'ఈ ప్రదేశం ఎందుకు మంచిది?',
    mapCurrentLocation: 'దిఘా హార్బర్',
    mapBestZone: 'ఉత్తమ ప్రదేశం',
    mapGoodZone: 'మంచి ప్రదేశం',
    mapAvoidZone: 'వెళ్ళవద్దు',
    compassHeading: '145° ఆగ్నేయం',
    travelTime: '~40–45 నిమిషాలు',
    seaCondition: 'ప్రశాంత సముద్రం (0.8 మీ అలలు)',
    modalClose: 'అర్థమైంది',
  },
};

export const getFindFishTranslations = (langCode: string): FindFishTranslations => {
  return FIND_FISH_TRANSLATIONS[langCode] || FIND_FISH_TRANSLATIONS['en'];
};
