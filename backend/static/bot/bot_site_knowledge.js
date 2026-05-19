const NS_KNOWLEDGE = {
  fairness_checker: {
    trigger_phrases: ["am i being treated fairly", "check my rights", "rights violation", "treated unfairly", "is this legal", "can they do this", "fairness check"],
    title: "Fairness Checker",
    what_it_does: "Detects possible legal rights violations in your situation. Tells you which rights may have been violated, which acts and sections apply, and what to do next.",
    how_to_use: ["Click 'Fairness Check' in the top navigation", "Describe your situation in plain English - be as specific as possible", "Example: 'My employer has not paid me for 2 months and threatened to fire me if I complain'", "Click 'Check My Rights'", "Review the violations detected, applicable acts, and suggested next steps"],
    example_queries: ["My landlord entered my home without notice", "Police held me for 3 days without informing my family", "I was denied a job because of my religion"],
    chips: ["Try Fairness Checker ->", "Show me an example situation", "What counts as a rights violation?"],
    nav: "/ai-legal-tools"
  },
  rights_card: {
    trigger_phrases: ["rights card", "know my rights", "what are my rights", "arrest rights", "employment rights", "consumer rights", "tenant rights", "education rights", "printable rights"],
    title: "Rights Card Generator",
    what_it_does: "Generates a structured, printable Know Your Rights card. Choose a category and get a legally grounded card listing your rights, the law behind each right, and what authorities cannot do to you.",
    how_to_use: ["Click 'Rights Cards' in the top navigation", "Select a category: Arrest, Employment, Consumer, Tenant, or Education", "Click 'Generate My Rights Card'", "Each right shows its legal basis (act + section)", "Use the Print button to save or share the card"],
    categories: {
      arrest_rights: "Rights during police arrest and detention - Articles 20, 21, 22",
      employment_rights: "Workplace rights - Industrial Disputes Act, Payment of Wages Act, Shops & Establishments Act",
      consumer_rights: "Consumer protection rights - Consumer Protection Act 2019",
      tenant_rights: "Tenant and housing rights - Rent Control Acts, Transfer of Property Act",
      education_rights: "Right to Education - Article 21A, RTE Act 2009"
    },
    chips: ["Generate Arrest Rights Card", "Generate Employment Rights Card", "What does each category include?"],
    nav: "/ai-legal-tools"
  },
  scenario_simulator: {
    trigger_phrases: ["scenario", "simulate", "fired", "evicted", "step by step", "legal walkthrough", "what happens if", "notice period", "terminated", "dismissed", "wrongful", "what should i do"],
    title: "Scenario Simulator",
    what_it_does: "Describe any legal situation in plain English and get a complete step-by-step legal walkthrough - which laws apply, what the other party cannot legally do, what evidence to preserve, and what remedies are available.",
    how_to_use: ["Click 'Simulate Scenario' in the top navigation", "Describe what happened - e.g. 'I was fired without notice after 4 years at my company'", "Click 'Simulate'", "Review each step of the walkthrough, your rights, and how to proceed"],
    example_queries: ["I was fired without notice", "My landlord is refusing to return my security deposit", "A shopkeeper sold me a defective product and refuses a refund", "My employer is forcing me to work overtime without extra pay"],
    chips: ["Simulate: fired without notice", "Simulate: landlord deposit dispute", "What evidence should I gather?"],
    nav: "/ai-legal-tools"
  },
  translator: {
    trigger_phrases: ["translate", "legal translator", "legal jargon", "plain english", "what does this mean", "legal notice", "contract", "decode", "understand this document", "layman", "simple words", "legal language", "confusing document", "what does it say"],
    title: "Legal Translator",
    what_it_does: "Converts legal jargon into plain English, or plain English into precise legal terminology. Paste any legal notice, contract clause, or court document and get an accurate explanation with every legal term defined.",
    how_to_use: ["Click 'Legal Translator' in the top navigation", "Choose direction: 'Legal -> Plain English' or 'Plain English -> Legal'", "Paste or type the text you want translated", "Click 'Translate'", "Each legal term is explained with its source act and section"],
    example_queries: ["What does 'suo motu cognizance' mean?", "Translate this clause: 'The party of the first part shall hereinafter...'", "Translate to legal: 'My boss fired me without telling me why'"],
    chips: ["Translate a legal notice", "What does suo motu mean?", "Translate plain English to legal terms"],
    nav: "/ai-legal-tools"
  },
  amendment_tracker: {
    trigger_phrases: ["amendment", "constitution changed", "article amended", "how many times amended", "constitutional history", "amendment timeline", "42nd amendment", "44th amendment", "when was article changed", "constitutional amendment"],
    title: "Amendment Tracker",
    what_it_does: "Shows the complete history of how the Indian Constitution has been amended - 106 amendments so far. Search by article number to see every amendment that affected it, with summaries of what changed and why.",
    how_to_use: ["Click 'Amendment Tracker' in the navigation", "Browse the full timeline of all constitutional amendments", "Or search for a specific article - e.g. type '21' to see all amendments affecting Article 21", "Click any amendment card to read a detailed summary"],
    example_queries: ["Which amendments affected Article 21?", "What did the 44th Amendment change?", "When was the right to education added to the Constitution?"],
    chips: ["Show Article 21 amendment history", "What did the 44th Amendment do?", "How many amendments has India had?"],
    nav: "/ai-legal-tools"
  },
  article_comparator: {
    trigger_phrases: ["compare article", "difference between article", "article 14 and 21", "similar articles", "conflict between", "article 19", "how are they related", "article 32", "article 226"],
    title: "Article Comparison Tool",
    what_it_does: "Compare any two articles of the Indian Constitution side by side - similarities, differences, legal conflicts, how they relate to each other, and landmark cases where courts interpreted them together.",
    how_to_use: ["Click 'Compare Articles' in the navigation", "Enter the first article number (e.g. 14)", "Enter the second article number (e.g. 21)", "Click 'Compare'", "Review similarities, differences, conflicts, and the relationship between them"],
    popular_comparisons: [{ a: "14", b: "21", label: "Equality vs Right to Life" }, { a: "19", b: "21", label: "Freedom of Speech vs Personal Liberty" }, { a: "32", b: "226", label: "Supreme Court vs High Court remedies" }],
    chips: ["Compare Article 14 and 21", "Compare Article 19 and 21", "Compare Article 32 and 226"],
    nav: "/ai-legal-tools"
  },
  general: {
    trigger_phrases: ["how does this work", "what can you do", "help", "confused", "getting started", "tour", "show me around", "what is this page"],
    title: "Getting Started",
    overview: "Welcome to NyayaSetu! Here is what I can help you with:",
    tools_summary: [
      { name: "Legal Questions", use: "Ask any legal question in plain English" },
      { name: "Site Guide", use: "Ask me how to use tools or navigate the site" }
    ],
    chips: ["About NyayaSetu", "Tools of NyayaSetu", "How to use correctly", "Common Questions"]
  },
  about_nyayasetu: {
    trigger_phrases: ["what is nyayasetu", "about nyayasetu", "info about nyaysetu", "nyayasetu project", "who made nyayasetu", "purpose of nyayasetu"],
    title: "About NyayaSetu",
    overview: "NyayaSetu is an AI-powered legal assistance platform designed to bridge the gap between Indian citizens and the legal system.",
    faqs: [
      { q: "Who is it for?", a: "Indian citizens looking to understand their legal rights and options." },
      { q: "Is it a substitute for a lawyer?", a: "No, NyayaSetu provides informational guidance, not formal legal advice." },
      { q: "What domains does it cover?", a: "Constitutional law, consumer protection, tenant rights, employment, and more." }
    ],
    chips: ["Tools of NyayaSetu", "How to use correctly", "Common Questions"]
  },
  how_to_use_correctly: {
    trigger_phrases: ["how to use nyayasetu correctly", "guide to use nyayasetu", "how to use nyayasetu", "nyayasetu site guide", "how to use the site", "best practices"],
    title: "How to Use NyayaSetu Correctly",
    overview: "To get the best and most accurate results from NyayaSetu, follow these guidelines:",
    how_to_use: [
      "Be specific: Provide details like dates, amounts, and actions taken.",
      "Use plain English: You don't need to use legal jargon.",
      "Provide context: State the relationship (e.g., 'my landlord', 'my employer').",
      "Verify with a lawyer: Always confirm AI-generated advice with a qualified legal professional before taking formal action."
    ],
    chips: ["Common Questions", "Tools of NyayaSetu"]
  },
  common_questions: {
    trigger_phrases: ["common questions", "faq", "frequently asked questions", "clear common qns", "common queries"],
    title: "Common Questions (FAQ)",
    overview: "Here are some common questions about using NyayaSetu:",
    faqs: [
      { q: "Is my data safe?", a: "Yes, your queries are processed securely." },
      { q: "Can NyayaSetu represent me in court?", a: "No, NyayaSetu cannot provide legal representation." },
      { q: "How accurate is the information?", a: "It is grounded in the Indian Constitution and key acts, but AI can sometimes make mistakes. Always verify." }
    ],
    chips: ["How to use correctly", "About NyayaSetu"]
  },
  nyayasetu_tools: {
    trigger_phrases: ["tools of nyayasetu", "what tools", "nyayasetu features", "show me tools", "list tools", "site features"],
    title: "Tools of NyayaSetu",
    overview: "NyayaSetu provides 6 specialized tools to help you navigate the legal system:",
    tools_summary: [
      { name: "Fairness Checker", use: "Detect possible rights violations" },
      { name: "Rights Card Generator", use: "Get printable rights for specific scenarios" },
      { name: "Scenario Simulator", use: "Step-by-step walkthrough of legal options" },
      { name: "Legal Translator", use: "Convert legal jargon to plain English" },
      { name: "Amendment Tracker", use: "Explore constitutional changes" },
      { name: "Article Comparator", use: "Compare constitutional articles side-by-side" }
    ],
    chips: ["How to use correctly", "About NyayaSetu"]
  }
};

globalThis.NS_KNOWLEDGE = NS_KNOWLEDGE;
