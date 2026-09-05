export interface QuickQuestion {
  id: string;
  icon: string;
  question: string;
  answerTitle: string;
  answer: string;
  actionLabel: string;
  actionRoute: 'find-fish' | 'safety' | 'sea-today' | 'alerts';
  whyExplanation: string;
}

export interface AskTranslations {
  pageTitle: string;
  pageSubtitle: string;
  whatDoYouWantToKnow: string;
  tapToSpeak: string;
  listening: string;
  speakNow: string;
  thinking: string;
  checkingConditions: string;
  tryAsking: string;
  typeQuestionPlaceholder: string;
  viewSpot: string;
  checkSafety: string;
  seaDetails: string;
  viewAlerts: string;
  whyThisSpot: string;
  whyExplanationLabel: string;
  askAnother: string;
  listenAnswer: string;
  orcaLabel: string;
  youLabel: string;
  micDenied: string;
  micUnsupported: string;
  micNotFound: string;
  micBusy: string;
  couldNotHear: string;
  connectionFailed: string;
  youAsked: string;
  poweredNote: string;
  quickQuestions: {
    findFish: string;
    findFishAnswer: string;
    findFishWhy: string;
    safety: string;
    safetyAnswer: string;
    safetyWhy: string;
    seaToday: string;
    seaTodayAnswer: string;
    seaTodayWhy: string;
    alerts: string;
    alertsAnswer: string;
    alertsWhy: string;
  };
}

export const ASK_TRANSLATIONS: Record<string, AskTranslations> = {
  en: {
    pageTitle: 'Ask ORCA',
    pageSubtitle: 'Ask anything about the sea.',
    whatDoYouWantToKnow: 'What do you want to know?',
    tapToSpeak: 'Tap to speak',
    listening: 'Listening…',
    speakNow: 'Speak now',
    thinking: 'ORCA is thinking…',
    checkingConditions: "I'm checking the sea, weather and fishing conditions…",
    tryAsking: 'Try asking',
    typeQuestionPlaceholder: 'Type your question…',
    viewSpot: 'View spot →',
    checkSafety: 'Check safety →',
    seaDetails: 'Sea details →',
    viewAlerts: 'View alerts →',
    whyThisSpot: 'Why this spot?',
    whyExplanationLabel: 'Why?',
    askAnother: 'Ask another question',
    listenAnswer: 'Listen',
    orcaLabel: 'ORCA',
    youLabel: 'Fisherman',
    micDenied: 'Microphone permission is blocked. Allow it in your browser settings.',
    micUnsupported: 'Voice recording is not supported on this browser.',
    micNotFound: 'No microphone found. Connect one and try again.',
    micBusy: 'Your microphone is being used by another app. Close it and try again.',
    couldNotHear: 'I could not hear anything. Please try again.',
    connectionFailed: 'Could not reach ORCA. Check your connection and try again.',
    youAsked: 'You asked',
    poweredNote: 'Answer based on live marine data',
    quickQuestions: {
      findFish: 'Where should I fish?',
      findFishAnswer: 'Try the green area, 12 km offshore. Sea conditions are safe.',
      findFishWhy: 'Water temperature is 27.5°C with high chlorophyll and moderate currents, attracting mackerel and hilsa.',
      safety: 'Is it safe today?',
      safetyAnswer: 'Conditions are safe until 2 PM. Avoid going far offshore after 2 PM due to strong winds.',
      safetyWhy: 'Wind speeds will exceed 38 km/h after 2 PM with 2.2m swell offshore.',
      seaToday: 'How is the sea?',
      seaTodayAnswer: 'Calm waters right now. Waves 0.8m, wind 12 km/h. Good day for fishing.',
      seaTodayWhy: 'Gentle south-westerly breeze with favorable tide cycles until late afternoon.',
      alerts: 'Any warnings?',
      alertsAnswer: 'High alert: Strong winds expected after 2 PM. Avoid going far offshore.',
      alertsWhy: 'IMD coastal squall warning active for Digha-Midnapore maritime belt from 2 PM.',
    },
  },
  bn: {
    pageTitle: 'ORCA-কে জিজ্ঞাসা করুন',
    pageSubtitle: 'সমুদ্র সম্পর্কে যা কিছু জানতে চান বলুন।',
    whatDoYouWantToKnow: 'আপনি কী জানতে চান?',
    tapToSpeak: 'কথা বলতে চাপুন',
    listening: 'শুনছি…',
    speakNow: 'এখন বলুন',
    thinking: 'ORCA তথ্য যাচাই করছে…',
    checkingConditions: 'আমি সমুদ্র, আবহাওয়া এবং মাছের পরিস্থিতি দেখছি…',
    tryAsking: 'এগুলি জিজ্ঞাসা করতে পারেন',
    typeQuestionPlaceholder: 'আপনার প্রশ্ন লিখুন…',
    viewSpot: 'জায়গা দেখুন →',
    checkSafety: 'নিরাপত্তা দেখুন →',
    seaDetails: 'সমুদ্রের তথ্য →',
    viewAlerts: 'সতর্কতা দেখুন →',
    whyThisSpot: 'কেন এই স্থান?',
    whyExplanationLabel: 'কারণ কী?',
    askAnother: 'অন্য প্রশ্ন করুন',
    listenAnswer: 'শুনুন',
    orcaLabel: 'ORCA',
    youLabel: 'মৎস্যজীবী',
    micDenied: 'মাইক্রোফোনের অনুমতি বন্ধ আছে। ব্রাউজার সেটিংসে অনুমতি দিন।',
    micUnsupported: 'এই ব্রাউজারে ভয়েস রেকর্ডিং সমর্থিত নয়।',
    micNotFound: 'কোনো মাইক্রোফোন পাওয়া যায়নি। একটি সংযুক্ত করে আবার চেষ্টা করুন।',
    micBusy: 'অন্য একটি অ্যাপ মাইক্রোফোন ব্যবহার করছে। সেটি বন্ধ করে আবার চেষ্টা করুন।',
    couldNotHear: 'আমি কিছু শুনতে পাইনি। আবার চেষ্টা করুন।',
    connectionFailed: 'ORCA-র সাথে সংযোগ করা যায়নি। ইন্টারনেট দেখে আবার চেষ্টা করুন।',
    youAsked: 'আপনি জিজ্ঞাসা করেছেন',
    poweredNote: 'সরাসরি সামুদ্রিক তথ্যের ভিত্তিতে উত্তর',
    quickQuestions: {
      findFish: 'আজ কোথায় মাছ ধরতে যাব?',
      findFishAnswer: 'তীর থেকে ১২ কিমি দূরে সবুজ চিহ্নিত এলাকায় যান। সমুদ্র শান্ত ও অনুকূল।',
      findFishWhy: 'পানির তাপমাত্রা ২৭.৫°C এবং ক্লোরোফিলের মাত্রা বেশি হওয়ায় ইলিশ ও ম্যাকেরেল পাওয়ার সম্ভাবনা বেশি।',
      safety: 'আজ সমুদ্রে যাওয়া কি নিরাপদ?',
      safetyAnswer: 'দুপুর ২টা পর্যন্ত পরিস্থিতি নিরাপদ। ২টার পর তীব্র বাতাসের কারণে দূরে যাবেন না।',
      safetyWhy: 'দুপুর ২টার পর বাতাসের গতি ৩৮ কিমি/ঘণ্টা ছাড়িয়ে যেতে পারে এবং ঢেউ ২.২ মিটারে উঠবে।',
      seaToday: 'আজ সমুদ্র কেমন আছে?',
      seaTodayAnswer: 'এখন সমুদ্র শান্ত রয়েছে। ঢেউ ০.৮ মিটার, বাতাস ১২ কিমি/ঘণ্টা। মাছ ধরার ভালো দিন।',
      seaTodayWhy: 'দক্ষিণ-পশ্চিম দিকের হালকা বাতাস এবং ভাটার অনুকূল সময় রয়েছে।',
      alerts: 'কোনো সতর্কতা আছে কি?',
      alertsAnswer: 'জরুরি সতর্কতা: দুপুর ২টার পর তীব্র বাতাস বইবে। দুপুর ২টার আগেই তীরে ফিরুন।',
      alertsWhy: 'দীঘা উপকূলের জন্য দুপুর ২টা থেকে কালবৈশাখীর সতর্কতা জারি রয়েছে।',
    },
  },
  ta: {
    pageTitle: 'ORCA-விடம் கேளுங்கள்',
    pageSubtitle: 'கடல் குறித்து எதையும் கேளுங்கள்.',
    whatDoYouWantToKnow: 'நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?',
    tapToSpeak: 'பேச தட்டவும்',
    listening: 'கேட்கிறது…',
    speakNow: 'இப்போது பேசுங்கள்',
    thinking: 'ORCA யோசிக்கிறது…',
    checkingConditions: 'கடல், வானிலை மற்றும் மீன்பிடி நிலைகளை சரிபார்க்கிறேன்…',
    tryAsking: 'இவற்றைக் கேட்கலாம்',
    typeQuestionPlaceholder: 'உங்கள் கேள்வியை தட்டச்சு செய்யவும்…',
    viewSpot: 'இடத்தை பார்க்க →',
    checkSafety: 'பாதுகாப்பை பார்க்க →',
    seaDetails: 'கடல் விபரம் →',
    viewAlerts: 'எச்சரிக்கைகள் →',
    whyThisSpot: 'ஏன் இந்த இடம்?',
    whyExplanationLabel: 'ஏன்?',
    askAnother: 'மற்றொரு கேள்வி கேளுங்கள்',
    listenAnswer: 'கேட்க',
    orcaLabel: 'ORCA',
    youLabel: 'மீனவர்',
    micDenied: 'ஒலிவாங்கி அனுமதி தடுக்கப்பட்டுள்ளது. உலாவி அமைப்புகளில் அனுமதிக்கவும்.',
    micUnsupported: 'இந்த உலாவியில் குரல் பதிவு ஆதரிக்கப்படவில்லை.',
    micNotFound: 'ஒலிவாங்கி கிடைக்கவில்லை. ஒன்றை இணைத்து மீண்டும் முயற்சிக்கவும்.',
    micBusy: 'வேறு ஒரு செயலி ஒலிவாங்கியைப் பயன்படுத்துகிறது. அதை மூடி மீண்டும் முயற்சிக்கவும்.',
    couldNotHear: 'எதுவும் கேட்கவில்லை. மீண்டும் முயற்சிக்கவும்.',
    connectionFailed: 'ORCA-வை அணுக முடியவில்லை. இணைப்பைச் சரிபார்க்கவும்.',
    youAsked: 'நீங்கள் கேட்டது',
    poweredNote: 'நேரடி கடல் தரவின் அடிப்படையில் பதில்',
    quickQuestions: {
      findFish: 'எங்கு மீன்பிடிக்க செல்லலாம்?',
      findFishAnswer: 'கரையிலிருந்து 12 கி.மீ தொலைவில் உள்ள பச்சை மண்டலத்திற்கு செல்லுங்கள். கடல் பாதுகாப்பானது.',
      findFishWhy: 'நீர் வெப்பநிலை 27.5°C மற்றும் சிறந்த குளோரோபில் உள்ளதால் மீன்கள் அதிகம் உள்ளன.',
      safety: 'இன்று செல்வது பாதுகாப்பானதா?',
      safetyAnswer: 'மதியம் 2 மணி வரை பாதுகாப்பானது. அதற்கு மேல் ஆழ்கடலுக்கு செல்வதை தவிர்க்கவும்.',
      safetyWhy: 'மதியம் 2 மணிக்கு மேல் காற்று 38 கி.மீ/மணிக்கு மேல் அதிகரிக்கும்.',
      seaToday: 'கடல் நிலைமை எப்படி உள்ளது?',
      seaTodayAnswer: 'தற்போது கடல் அமைதியாக உள்ளது. அலை 0.8 மீ, காற்று 12 கி.மீ/மணி. மீன்பிடிக்க நல்லது.',
      seaTodayWhy: 'தென்மேற்கு மிதமான காற்று மற்றும் சாதகமான அலை உள்ளது.',
      alerts: 'ஏதேனும் எச்சரிக்கைகள் உள்ளதா?',
      alertsAnswer: 'அதி தீவிர எச்சரிக்கை: மதியம் 2 மணிக்கு மேல் பலத்த காற்று வீசும். கரை திரும்புங்கள்.',
      alertsWhy: 'வானிலை மையம் மதியம் 2 மணிக்கு புயல் காற்று எச்சரிக்கை விடுத்துள்ளது.',
    },
  },
  te: {
    pageTitle: 'ORCA ను అడగండి',
    pageSubtitle: 'సముద్రం గురించి ఏదైనా అడగండి.',
    whatDoYouWantToKnow: 'మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?',
    tapToSpeak: 'మాట్లాడటానికి నొక్కండి',
    listening: 'వింటున్నాను…',
    speakNow: 'ఇప్పుడు మాట్లాడండి',
    thinking: 'ORCA ఆలోచిస్తోంది…',
    checkingConditions: 'సముద్రం, వాతావరణ పరిస్థితులను తనిఖీ చేస్తున్నాను…',
    tryAsking: 'ఇవి అడగవచ్చు',
    typeQuestionPlaceholder: 'మీ ప్రశ్నను టైప్ చేయండి…',
    viewSpot: 'ప్రదేశం చూడండి →',
    checkSafety: 'భద్రత చూడండి →',
    seaDetails: 'సముద్ర వివరాలు →',
    viewAlerts: 'హెచ్చరికలు →',
    whyThisSpot: 'ఈ ప్రాంతం ఎందుకు?',
    whyExplanationLabel: 'ఎందుకు?',
    askAnother: 'మరొక ప్రశ్న అడగండి',
    listenAnswer: 'వినండి',
    orcaLabel: 'ORCA',
    youLabel: 'మత్స్యకారుడు',
    micDenied: 'మైక్రోఫోన్ అనుమతి నిరోధించబడింది. బ్రౌజర్ సెట్టింగ్‌లలో అనుమతించండి.',
    micUnsupported: 'ఈ బ్రౌజర్‌లో వాయిస్ రికార్డింగ్ మద్దతు లేదు.',
    micNotFound: 'మైక్రోఫోన్ కనుగొనబడలేదు. ఒకదాన్ని కనెక్ట్ చేసి మళ్లీ ప్రయత్నించండి.',
    micBusy: 'మరొక యాప్ మైక్రోఫోన్‌ను ఉపయోగిస్తోంది. దాన్ని మూసివేసి మళ్లీ ప్రయత్నించండి.',
    couldNotHear: 'నాకు ఏమీ వినిపించలేదు. మళ్లీ ప్రయత్నించండి.',
    connectionFailed: 'ORCAని చేరుకోలేకపోయాము. కనెక్షన్ తనిఖీ చేయండి.',
    youAsked: 'మీరు అడిగినది',
    poweredNote: 'ప్రత్యక్ష సముద్ర డేటా ఆధారంగా సమాధానం',
    quickQuestions: {
      findFish: 'ఎక్కడ వేటకు వెళ్ళాలి?',
      findFishAnswer: 'తీరానికి 12 కి.మీ దూరంలో ఉన్న ఆకుపచ్చ ప్రాంతానికి వెళ్ళండి. పరిస్థితులు అనుకూలం.',
      findFishWhy: 'నీటి ఉష్ణోగ్రత 27.5°C మరియు క్లోరోఫిల్ ఎక్కువగా ఉండటం వల్ల చేపలు లభ్యమవుతాయి.',
      safety: 'ఈరోజు వేట సురక్షితమేనా?',
      safetyAnswer: 'మధ్యాహ్నం 2 గంటల వరకు సురక్షితం. ఆ తర్వాత గాలుల తీవ్రత వల్ల లోతుకు వెళ్లవద్దు.',
      safetyWhy: 'మధ్యాహ్నం 2 గంటల తర్వాత గాలి వేగం 38 కిమీ/గం దాటవచ్చు.',
      seaToday: 'సముద్రం ఎలా ఉంది?',
      seaTodayAnswer: 'ప్రస్తుతం సముద్రం ప్రశాంతంగా ఉంది. అలలు 0.8 మీ, గాలి 12 కిమీ/గం. వేటకు అనుకూలం.',
      seaTodayWhy: 'నైరుతి వైపు నుండి మందకొడిగా వీచే గాలులు మరియు అనుకూలమైన పోటు ఉన్నాయి.',
      alerts: 'ఏవైనా హెచ్చరికలు ఉన్నాయా?',
      alertsAnswer: 'తీవ్ర హెచ్చరిక: మధ్యాహ్నం 2 గంటల తర్వాత తీవ్ర గాలులు. ఒడ్డుకు చేరుకోండి.',
      alertsWhy: 'వాతావరణ శాఖ నుండి మధ్యాహ్నం 2 గంటలకు గాలుల హెచ్చరిక జారీ చేయబడింది.',
    },
  },
  hi: {
    pageTitle: 'ORCA से पूछें',
    pageSubtitle: 'समुद्र के बारे में कुछ भी पूछें।',
    whatDoYouWantToKnow: 'आप क्या जानना चाहते हैं?',
    tapToSpeak: 'बोलने के लिए दबाएं',
    listening: 'सुन रहे हैं…',
    speakNow: 'अब बोलें',
    thinking: 'ORCA सोच रहा है…',
    checkingConditions: 'मैं समुद्र, मौसम और मछली पकड़ने की स्थिति देख रहा हूँ…',
    tryAsking: 'यह पूछकर देखें',
    typeQuestionPlaceholder: 'अपना प्रश्न लिखें…',
    viewSpot: 'स्थान देखें →',
    checkSafety: 'सुरक्षा देखें →',
    seaDetails: 'समुद्र विवरण →',
    viewAlerts: 'चेतावनियाँ →',
    whyThisSpot: 'यही जगह क्यों?',
    whyExplanationLabel: 'क्यों?',
    askAnother: 'दूसरा प्रश्न पूछें',
    listenAnswer: 'सुनें',
    orcaLabel: 'ORCA',
    youLabel: 'मछुआरा',
    micDenied: 'माइक्रोफ़ोन की अनुमति बंद है। ब्राउज़र सेटिंग्स में अनुमति दें।',
    micUnsupported: 'इस ब्राउज़र पर वॉइस रिकॉर्डिंग समर्थित नहीं है।',
    micNotFound: 'कोई माइक्रोफ़ोन नहीं मिला। एक जोड़कर फिर कोशिश करें।',
    micBusy: 'कोई दूसरा ऐप माइक्रोफ़ोन इस्तेमाल कर रहा है। उसे बंद करके फिर कोशिश करें।',
    couldNotHear: 'मुझे कुछ सुनाई नहीं दिया। कृपया फिर से कोशिश करें।',
    connectionFailed: 'ORCA से संपर्क नहीं हो सका। कनेक्शन जाँचें।',
    youAsked: 'आपने पूछा',
    poweredNote: 'सीधे समुद्री आंकड़ों पर आधारित उत्तर',
    quickQuestions: {
      findFish: 'आज कहाँ मछली पकड़ने जाऊँ?',
      findFishAnswer: 'तट से 12 किमी दूर हरे क्षेत्र में जाएं। समुद्र की स्थिति सुरक्षित है।',
      findFishWhy: 'पानी का तापमान 27.5°C और क्लोरोफिल की मात्रा अच्छी है, जिससे मछली मिलने की संभावना अधिक है।',
      safety: 'क्या आज जाना सुरक्षित है?',
      safetyAnswer: 'दोपहर 2 बजे तक सुरक्षित है। 2 बजे के बाद तेज हवाओं के कारण दूर जाने से बचें।',
      safetyWhy: 'दोपहर 2 बजे के बाद हवा की रफ्तार 38 किमी/घंटा से अधिक हो जाएगी।',
      seaToday: 'समुद्र कैसा है?',
      seaTodayAnswer: 'अभी समुद्र शांत है। लहरें 0.8 मीटर, हवा 12 किमी/घंटा। मछली पकड़ने के लिए अच्छा दिन।',
      seaTodayWhy: 'हल्की दक्षिणी-पश्चिमी हवा और अनुकूल ज्वार की स्थिति बनी हुई है।',
      alerts: 'क्या कोई चेतावनी है?',
      alertsAnswer: 'गंभीर चेतावनी: दोपहर 2 बजे के बाद तेज हवाएं चलेंगी। 2 बजे से पहले तट पर लौटें।',
      alertsWhy: 'दीघा तट के लिए दोपहर 2 बजे से आंधी की चेतावनी जारी की गई है।',
    },
  },
  ml: {
    pageTitle: 'ORCA-യോട് ചോദിക്കുക',
    pageSubtitle: 'കടലിനെക്കുറിച്ച് എന്തും ചോദിക്കാം.',
    whatDoYouWantToKnow: 'നിങ്ങൾക്ക് എന്താണ് അറിയേണ്ടത്?',
    tapToSpeak: 'സംസാരിക്കാൻ തൊടുക',
    listening: 'കേൾക്കുന്നു…',
    speakNow: 'ഇപ്പോൾ സംസാരിക്കുക',
    thinking: 'ORCA പരിശോധിക്കുന്നു…',
    checkingConditions: 'കടൽ, കാലാവസ്ഥ, മത്സ്യബന്ധന സാധ്യതകൾ പരിശോധിക്കുന്നു…',
    tryAsking: 'ഇവ ചോദിച്ചുനോക്കൂ',
    typeQuestionPlaceholder: 'ചോദ്യം ടൈപ്പ് ചെയ്യുക…',
    viewSpot: 'സ്ഥലം കാണുക →',
    checkSafety: 'സുരക്ഷ നോക്കുക →',
    seaDetails: 'കടൽ വിവരങ്ങൾ →',
    viewAlerts: 'മുന്നറിയിപ്പുകൾ →',
    whyThisSpot: 'എന്തുകൊണ്ട് ഈ സ്ഥലം?',
    whyExplanationLabel: 'കാരണം?',
    askAnother: 'മറ്റൊരു ചോദ്യം ചോദിക്കുക',
    listenAnswer: 'കേൾക്കുക',
    orcaLabel: 'ORCA',
    youLabel: 'മത്സ്യത്തൊഴിലാളി',
    micDenied: 'മൈക്രോഫോൺ അനുമതി തടഞ്ഞിരിക്കുന്നു. ബ്രൗസർ ക്രമീകരണങ്ങളിൽ അനുവദിക്കുക.',
    micUnsupported: 'ഈ ബ്രൗസറിൽ വോയ്‌സ് റെക്കോർഡിംഗ് പിന്തുണയ്ക്കുന്നില്ല.',
    micNotFound: 'മൈക്രോഫോൺ കണ്ടെത്തിയില്ല. ഒന്ന് ബന്ധിപ്പിച്ച് വീണ്ടും ശ്രമിക്കുക.',
    micBusy: 'മറ്റൊരു ആപ്പ് മൈക്രോഫോൺ ഉപയോഗിക്കുന്നു. അത് അടച്ച് വീണ്ടും ശ്രമിക്കുക.',
    couldNotHear: 'എനിക്ക് ഒന്നും കേൾക്കാനായില്ല. വീണ്ടും ശ്രമിക്കുക.',
    connectionFailed: 'ORCA-യുമായി ബന്ധപ്പെടാനായില്ല. കണക്ഷൻ പരിശോധിക്കുക.',
    youAsked: 'നിങ്ങൾ ചോദിച്ചത്',
    poweredNote: 'തത്സമയ സമുദ്ര ഡാറ്റ അടിസ്ഥാനമാക്കിയ ഉത്തരം',
    quickQuestions: {
      findFish: 'എവിടെയാണ് മീൻ പിടിക്കേണ്ടത്?',
      findFishAnswer: 'തീരത്തുനിന്ന് 12 കി.മീ അകലെയുള്ള പച്ച ഭാഗത്തേക്ക് പോകുക. കടൽ സുരക്ഷിതമാണ്.',
      findFishWhy: 'വെള്ളത്തിന് 27.5°C താപനിലയും ക്ലോറോഫിൽ കൂടുതലുമുള്ളതിനാൽ കൂടുതൽ മീൻ ലഭിക്കും.',
      safety: 'ഇന്ന് കടലിൽ പോകുന്നത് സുരക്ഷിതമാണോ?',
      safetyAnswer: 'ഉച്ചയ്ക്ക് 2 മണി വരെ സുരക്ഷിതമാണ്. അതിനുശേഷം ശക്തമായ കാറ്റുള്ളതിനാൽ ദൂരേക്ക് പോകരുത്.',
      safetyWhy: 'ഉച്ചയ്ക്ക് 2 മണിക്ക് ശേഷം കാറ്റ് 38 കി.മീ/മണിക്കൂറിലധികം വേഗത കൈവരിക്കും.',
      seaToday: 'ഇന്ന് കടൽ എങ്ങനെ കാണുന്നു?',
      seaTodayAnswer: 'ഇപ്പോൾ കടൽ ശാന്തമാണ്. തിരമാല 0.8 മീറ്റർ, കാറ്റ് 12 കി.മീ/മണിക്കൂർ. അനുകൂല സമയം.',
      seaTodayWhy: 'ശാന്തമായ തെക്കുപടിഞ്ഞാറൻ കാറ്റും അനുകൂലമായ വേലിയേറ്റവുമാണ് ഉള്ളത്.',
      alerts: 'എന്തെങ്കിലും മുന്നറിയിപ്പുകൾ ഉണ്ടോ?',
      alertsAnswer: 'തീവ്ര ജാഗ്രത: ഉച്ചയ്ക്ക് 2 മണിക്ക് ശേഷം ശക്തമായ കാറ്റ്. 2 മണിക്ക് മുൻപായി തിരിച്ചെത്തുക.',
      alertsWhy: 'ഉച്ചയ്ക്ക് 2 മണി മുതൽ തീരദേശത്ത് ശക്തമായ കാറ്റിന് സാധ്യതയുണ്ട്.',
    },
  },
};

export const getAskTranslations = (langCode = 'en'): AskTranslations => {
  return ASK_TRANSLATIONS[langCode] || ASK_TRANSLATIONS.en;
};

export const getQuickQuestionsList = (langCode = 'en'): QuickQuestion[] => {
  const t = getAskTranslations(langCode);

  return [
    {
      id: 'where-to-fish',
      icon: '🎣',
      question: t.quickQuestions.findFish,
      answerTitle: t.quickQuestions.findFish,
      answer: t.quickQuestions.findFishAnswer,
      actionLabel: t.viewSpot,
      actionRoute: 'find-fish',
      whyExplanation: t.quickQuestions.findFishWhy,
    },
    {
      id: 'is-it-safe',
      icon: '🛡️',
      question: t.quickQuestions.safety,
      answerTitle: t.quickQuestions.safety,
      answer: t.quickQuestions.safetyAnswer,
      actionLabel: t.checkSafety,
      actionRoute: 'safety',
      whyExplanation: t.quickQuestions.safetyWhy,
    },
    {
      id: 'how-is-sea',
      icon: '🌊',
      question: t.quickQuestions.seaToday,
      answerTitle: t.quickQuestions.seaToday,
      answer: t.quickQuestions.seaTodayAnswer,
      actionLabel: t.seaDetails,
      actionRoute: 'sea-today',
      whyExplanation: t.quickQuestions.seaTodayWhy,
    },
    {
      id: 'any-warnings',
      icon: '⚠️',
      question: t.quickQuestions.alerts,
      answerTitle: t.quickQuestions.alerts,
      answer: t.quickQuestions.alertsAnswer,
      actionLabel: t.viewAlerts,
      actionRoute: 'alerts',
      whyExplanation: t.quickQuestions.alertsWhy,
    },
  ];
};

/**
 * Intelligent response matcher for custom voice / typed questions:
 * Always returns answer first, short 1-2 sentences, no technical jargon.
 */
