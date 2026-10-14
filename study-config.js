/* ==========================================================================
   STUDY CONTENT
   --------------------------------------------------------------------------
   Everything a participant reads in the app lives in this file, so you can
   change the questions and texts without touching the app logic in
   index.html. (The questionnaires — GAAIS-10, Jian — are done in Qualtrics.)

   ⚠ The questions below are EXAMPLES so the full flow can be tested.
     Replace them with your 40 ChainForge questions (~80% correct AI answers).
     Which questions get the confidence score is randomised per participant
     in index.html (planTrials), balanced over correct and incorrect answers.
   ========================================================================== */

const STUDY = {
  title: "Answers from an AI assistant",
  researcher: "Berend de Vries",
  supervisor: "Katja Rogers",
  institution: "University of Amsterdam",
  contactEmail: "Berend2000devries@gmail.com",   // TODO
  estimatedMinutes: 25,                            // TODO: update after the pilot
  completionCode: "",                              // optional, e.g. for SONA / Prolific

  // BETA: true = show the researcher view (live log + measures) next to the study,
  // e.g. to demo it to your supervisor. Set to false before real data collection.
  beta: true,

  // Each model was asked every question this many times (ChainForge runs).
  answersPerModel: 20,

  // Which questions are used, by ID. Leave the list empty ([]) to use ALL questions below.
  // Now: a short 4-question demo for the supervisor (2 correct, 2 incorrect AI answers).
  activeQuestions: ["A01", "A02", "A03", "B03"],

  // "AI is thinking" animation before each answer, then the answer is typed out.
  // Same for every question, so the delay never hints at whether an answer is right.
  thinkingMs: 1500,      // how long the thinking dots show (ms)
  typingMsPerChar: 25,   // typing speed (ms per character); 0 = show the answer at once

  // Hovers on a model shorter than this are logged but not counted as "looked at".
  hoverThresholdMs: 300
};

/* --------------------------------------------------------------------------
   QUESTIONS
   id        unique ID, stored in every CSV row
   q         the question
   a         the answer the AI assistant shows
   correct   true if that answer is correct (never shown to participants)
   alt       only used when `a` is incorrect: the correct answer, shown in the debrief
   models    per AI model, the short answers it gave over its answersPerModel (20) runs:
               ModelName: [[count, "short answer", agrees], ...]
             - count   how many of the 20 runs gave this answer (counts per model add up to 20)
             - agrees  true if this answer means the same as `a`
             The model's score = share of its runs that agree; the overall confidence
             score = share of ALL runs (5 models x 20) that agree with `a`.
             Its most frequent answer is shown under its name in "Show details".
   article   the fact-check text
   -------------------------------------------------------------------------- */
const QUESTIONS = [
  {
    id: "A01",
    q: "How many member states does the European Union have?",
    a: "The European Union has 27 member states.",
    correct: true, alt: "28 member states",
    models: {
      ChatGPT: [[14, "27 member states", true], [6, "There are 27 EU countries.", true]],
      Claude: [[20, "The EU has 27 member states.", true]],
      Gemini: [[15, "27 countries", true], [4, "27 since Brexit (2020)", true], [1, "28 member states", false]],
      Copilot: [[20, "27 member states", true]],
      Grok: [[12, "27", true], [6, "27 member states", true], [2, "28, including the UK", false]]
    },
    article: { title: "EU membership after Brexit", src: "Example article",
      text: "Since the United Kingdom left on 31 January 2020, the European Union has consisted of 27 member states. Several countries, including Ukraine and Moldova, are candidates for membership." }
  },
  {
    id: "A02",
    q: "What is the minimum voting age for national elections in the Netherlands?",
    a: "You can vote in Dutch national elections from the age of 18.",
    correct: true, alt: "16 years",
    models: {
      ChatGPT: [[13, "18 years old", true], [7, "16 years old", false]],
      Claude: [[18, "From age 18", true], [2, "From age 16", false]],
      Gemini: [[10, "18", true], [10, "16 years", false]],
      Copilot: [[16, "You must be 18.", true], [4, "16 years old", false]],
      Grok: [[2, "18", true], [18, "16 years old", false]]
    },
    article: { title: "Who can vote in the Netherlands?", src: "Example article",
      text: "Dutch citizens aged 18 or older on election day may vote for the House of Representatives. Proposals to lower the voting age to 16 have been discussed, but have not been adopted." }
  },
  {
    id: "A03",
    q: "In which city does the Dutch government have its seat?",
    a: "The Dutch government has its seat in Amsterdam.",
    correct: false, alt: "The Hague",
    models: {
      ChatGPT: [[17, "The Hague", false], [3, "Amsterdam", true]],
      Claude: [[19, "The Hague (Den Haag)", false], [1, "Amsterdam", true]],
      Gemini: [[14, "The Hague", false], [6, "Amsterdam, the capital", true]],
      Copilot: [[16, "The Hague", false], [4, "Amsterdam", true]],
      Grok: [[11, "The Hague", false], [9, "Amsterdam", true]]
    },
    article: { title: "Capital versus seat of government", src: "Example article",
      text: "Amsterdam is the constitutional capital of the Netherlands, but the government, parliament and most ministries are located in The Hague." }
  },
  {
    id: "A04",
    q: "How many seats does the Dutch House of Representatives have?",
    a: "The House of Representatives (Tweede Kamer) has 150 seats.",
    correct: true, alt: "75 seats",
    models: {
      ChatGPT: [[20, "150 seats", true]],
      Claude: [[20, "150", true]],
      Gemini: [[17, "150 seats", true], [3, "75 seats", false]],
      Copilot: [[19, "150 members", true], [1, "225 seats", false]],
      Grok: [[16, "150", true], [4, "75", false]]
    },
    article: { title: "How the Dutch parliament is organised", src: "Example article",
      text: "The House of Representatives has 150 members, elected by proportional representation. The Senate (Eerste Kamer) has 75 members." }
  },
  {
    id: "A05",
    q: "Where is the official seat of the European Parliament?",
    a: "The official seat of the European Parliament is in Strasbourg.",
    correct: true, alt: "Brussels",
    models: {
      ChatGPT: [[15, "Strasbourg", true], [5, "Brussels", false]],
      Claude: [[17, "Strasbourg, France", true], [3, "Brussels", false]],
      Gemini: [[12, "Strasbourg", true], [8, "Brussels", false]],
      Copilot: [[14, "Strasbourg", true], [6, "Brussels, Belgium", false]],
      Grok: [[11, "Strasbourg", true], [7, "Brussels", false], [2, "Luxembourg", false]]
    },
    article: { title: "Three cities, one parliament", src: "Example article",
      text: "The EU treaties make Strasbourg the official seat of the European Parliament, where its monthly plenary sessions take place. Committee meetings are mostly held in Brussels, and the secretariat is based in Luxembourg." }
  },
  {
    id: "B01",
    q: "How often are elections for the European Parliament held?",
    a: "European Parliament elections are held every five years.",
    correct: true, alt: "Every four years",
    models: {
      ChatGPT: [[20, "Every 5 years", true]],
      Claude: [[19, "Every five years", true], [1, "Every four years", false]],
      Gemini: [[18, "Every 5 years", true], [2, "Every 4 years", false]],
      Copilot: [[20, "Once every five years", true]],
      Grok: [[17, "Every 5 years", true], [3, "Every 4 years", false]]
    },
    article: { title: "Europe goes to the polls", src: "Example article",
      text: "Members of the European Parliament are elected for a five-year term. The most recent elections took place in June 2024." }
  },
  {
    id: "B02",
    q: "How many members does the UN Security Council have?",
    a: "The UN Security Council has 15 members.",
    correct: true, alt: "5 members",
    models: {
      ChatGPT: [[18, "15 members", true], [2, "5 members", false]],
      Claude: [[20, "15 (5 permanent, 10 elected)", true]],
      Gemini: [[14, "15", true], [6, "5 permanent members", false]],
      Copilot: [[16, "15 members", true], [4, "5", false]],
      Grok: [[12, "15", true], [8, "5 members", false]]
    },
    article: { title: "Who sits on the Security Council?", src: "Example article",
      text: "The Security Council has 15 members: five permanent members with a veto (China, France, Russia, the United Kingdom and the United States) and ten members elected for two-year terms." }
  },
  {
    id: "B03",
    q: "In which city is the International Court of Justice located?",
    a: "The International Court of Justice is located in Geneva.",
    correct: false, alt: "The Hague",
    models: {
      ChatGPT: [[18, "The Hague", false], [2, "Geneva", true]],
      Claude: [[20, "The Hague (Peace Palace)", false]],
      Gemini: [[15, "The Hague", false], [5, "Geneva", true]],
      Copilot: [[17, "The Hague, Netherlands", false], [3, "Geneva", true]],
      Grok: [[13, "The Hague", false], [7, "Geneva", true]]
    },
    article: { title: "The UN's highest court", src: "Example article",
      text: "The International Court of Justice, the principal judicial organ of the United Nations, sits in the Peace Palace in The Hague." }
  },
  {
    id: "B04",
    q: "Which currency is used in Denmark?",
    a: "Denmark uses the Danish krone.",
    correct: true, alt: "The euro",
    models: {
      ChatGPT: [[20, "The Danish krone", true]],
      Claude: [[20, "Danish krone (DKK)", true]],
      Gemini: [[20, "Krone", true]],
      Copilot: [[19, "Danish krone", true], [1, "The euro", false]],
      Grok: [[18, "Danish krone", true], [2, "Euro", false]]
    },
    article: { title: "Denmark and the euro", src: "Example article",
      text: "Denmark is an EU member but has an opt-out from the euro. Its currency is the Danish krone, which is pegged to the euro." }
  },
  {
    id: "B05",
    q: "In which city is NATO's headquarters located?",
    a: "NATO's headquarters is located in Brussels.",
    correct: true, alt: "Mons",
    models: {
      ChatGPT: [[17, "Brussels", true], [3, "Mons, Belgium", false]],
      Claude: [[19, "Brussels, Belgium", true], [1, "Mons", false]],
      Gemini: [[13, "Brussels", true], [7, "Mons", false]],
      Copilot: [[15, "Brussels", true], [5, "Mons", false]],
      Grok: [[14, "Brussels", true], [4, "Mons", false], [2, "The Hague", false]]
    },
    article: { title: "Where NATO meets", src: "Example article",
      text: "NATO's political headquarters is in Brussels. Its military command for operations (SHAPE) is located near Mons, also in Belgium." }
  }
];

/* --------------------------------------------------------------------------
   TEXTS
   -------------------------------------------------------------------------- */
const TEXTS = {
  consent: `
    <p>You are invited to take part in a study by <strong>${STUDY.researcher}</strong> for a master’s thesis at the
    ${STUDY.institution}, supervised by ${STUDY.supervisor}. The study looks at how people decide whether to rely on
    answers given by an AI assistant.</p>
    <h3>What you will do</h3>
    <p>You will see questions about news and politics, each with an answer from an AI assistant. For every answer you
    decide whether to accept or decline it, and you can check a short fact-check article first. You will also fill in short questionnaires about AI and about your trust in the assistant; the researcher
    will tell you when. The study takes about ${STUDY.estimatedMinutes} minutes in total.</p>
    <h3>What we record</h3>
    <p>Your decisions and how you use the screen: which buttons you click, which details you open and point at, and how
    long this takes. We do not record your name, your IP address or anything else that identifies you. Data are stored
    under a participant number and used only for this research.</p>
    <h3>Your rights</h3>
    <p>Participation is voluntary. You can stop at any moment without giving a reason, and you can ask for your data to
    be removed until it has been analysed. Questions? Contact ${STUDY.contactEmail}.</p>`,

  // One checkbox for consent (stored as item "c1" in Pxxx_responses.csv).
  consentChecks: [
    "I have read the information above, I am 18 years or older, and I voluntarily agree to take part and to my anonymous data being used for this research."
  ],

  intro: `
      <p>You will now see a series of questions. For each one, an AI assistant gives an answer.</p>
      <p>Sometimes the answer comes with a <strong>confidence score</strong>. It shows how many answers from five
      different AI models agree with the answer shown. Each model was asked the same question ${STUDY.answersPerModel}
      times. Click <strong>Show details</strong> to see the score per model, and point at a model to see which answers
      it gave. Other answers are shown without a score.</p>
      <ul>
        <li><strong>Accept</strong> the answer if you think it is correct.</li>
        <li><strong>Decline</strong> the answer if you think it is wrong.</li>
        <li>Not sure? Click <strong>Fact-check</strong> to read a short article first, then decide.</li>
      </ul>
      <p>Answer as you would in daily life. There is no time limit, but please don’t look anything up elsewhere.</p>`,

  debrief: `
    <p>Thank you for taking part! Here is what the study was about.</p>
    <p>We are investigating whether a <strong>numeric confidence score</strong> helps people trust AI answers
    <em>appropriately</em>: accepting answers that are correct and declining answers that are wrong. That is why some
    answers were shown with a confidence score and others without.</p>
    <p>Some AI answers in this study were <strong>deliberately incorrect</strong>, in roughly the proportion found in
    research on real AI assistants. The confidence scores were based on how often five AI models agreed with each other,
    not on whether the answer was actually true. The incorrect answers you saw are listed below with the correct answer,
    so you don’t leave with wrong information.</p>
    <p>Please don’t tell other possible participants about the incorrect answers, as this would affect the results.
    Questions or want your data removed? Contact ${STUDY.contactEmail} and mention your participant number.</p>`
};
