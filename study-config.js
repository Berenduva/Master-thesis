/* ==========================================================================
   STUDY CONTENT
   --------------------------------------------------------------------------
   Everything a participant reads in the app lives in this file (texts) and in
   questions.js (the 30 questions with all model answers), so you can change
   them without touching the app logic in index.html.
   The questionnaires (GAAIS-10, Jian, extra questions), consent and debrief
   are done in Qualtrics.

   Design: two blocks of 15 questions. At the start the researcher chooses the
   participant's group (Group 1–4), which fixes the order of the conditions and
   which question set (A or B) goes with which condition:

       group   block 1          block 2
       1       Base, set A      Conf, set B
       2       Base, set B      Conf, set A
       3       Conf, set A      Base, set B
       4       Conf, set B      Base, set A

   Base = without confidence score, Conf = with confidence score.
   Within a block the 15 questions are shown in a FIXED order (the order in
   questions.js), the same for every participant (see randomizeOrder below).
   The setup screen only shows "Group 1"–"Group 4", not what each group means, so a
   participant who sees it learns nothing about the design.
   ========================================================================== */

const STUDY = {
  title: "Answers from an AI assistant",
  researcher: "Berend de Vries",
  supervisor: "Katja Rogers",
  institution: "University of Amsterdam",
  contactEmail: "berend.de.vries@student.uva.nl",
  estimatedMinutes: 25,                            // TODO: update after the pilot
  completionCode: "",                              // optional, e.g. for SONA / Prolific

  // >>> BETA SWITCH <<<  true = EVERYONE sees the researcher view (live log + measures)
  // next to the study, e.g. for a demo on GitHub Pages. MUST be false for real participants.
  // With beta: false the researcher can still open the view with ?debug=1 in the address.
  beta: false,

  // Consent and debrief are done in Qualtrics. Set to true to show them in the app as well.
  showConsent: false,
  showDebrief: false,

  // Each model was asked every question this many times.
  answersPerModel: 20,

  // false = every participant gets the questions of a set in the same, fixed order
  // (the order in questions.js). true = a new random order per participant.
  randomizeOrder: false,

  // Which questions are used, by ID. Leave the list empty ([]) to use ALL questions.
  activeQuestions: [],

  // "AI is thinking" animation before each answer, then the answer is typed out.
  // Same for every question, so the delay never hints at whether an answer is right.
  thinkingMs: 1500,      // how long the thinking dots show (ms)
  typingMsPerChar: 25,   // typing speed (ms per character); 0 = show the answer at once

  // Hovers on a model (or on its answer list) shorter than this are logged as "short"
  // but not counted as "looked at" in the trial summary.
  hoverThresholdMs: 400
};

/* The four groups: [condition, question set] for block 1 and block 2.
   The key ("1"–"4") is the group number shown on the setup screen as "Group 1" etc.
   and stored in the "group" column of every CSV file.
   "baseline" = without confidence score, "confidence" = with confidence score. */
const GROUPS = {
  "1": [["baseline", "A"], ["confidence", "B"]],
  "2": [["baseline", "B"], ["confidence", "A"]],
  "3": [["confidence", "A"], ["baseline", "B"]],
  "4": [["confidence", "B"], ["baseline", "A"]]
};

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
    decide whether to accept or decline it. You will also fill in short questionnaires about AI and about your trust in the assistant; the researcher
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

  // Instructions before a block WITHOUT confidence score.
  introBase: `
      <p>You will see a series of questions about news and politics. For each one, an AI assistant gives an answer.</p>
      <ul>
        <li><strong>Accept</strong> the answer if you think it is correct.</li>
        <li><strong>Decline</strong> the answer if you think it is wrong.</li>
      </ul>
      <p>Answer as you would when using generative AI in daily life. There is no time limit.</p>`,

  // Instructions before a block WITH confidence score.
  introConf: `
      <p>You will see a series of questions about news and politics. For each one, an AI assistant gives an answer.</p>
      <p>In this part, every answer comes with a <strong>confidence score</strong>. Five different AI models were each
      asked the same question ${STUDY.answersPerModel} times. The score shows how many of all these answers agree with the
      answer shown. Click <strong>Show details</strong> to see the answers per model, and point at a model to read
      everything it answered.</p>
      <ul>
        <li><strong>Accept</strong> the answer if you think it is correct.</li>
        <li><strong>Decline</strong> the answer if you think it is wrong.</li>
      </ul>
      <p>Answer as you would when using generative AI in daily life. There is no time limit.</p>`,

  // Shown after block 1.
  breakScreen: `
      <p>You have finished Part 1. Thank you!</p>
      <p><strong>Please go back to the questionnaire now</strong> and leave this window open.
      When the questionnaire tells you to, come back here and continue with Part 2.</p>`,

  // Shown after block 2 (when showDebrief is false).
  endScreen: `
      <p>You have finished Part 2. Thank you!</p>
      <p><strong>Please go back to the questionnaire</strong> to complete the last questions.</p>`,

  debrief: `
    <p>Thank you for taking part! Here is what the study was about.</p>
    <p>We are investigating whether a <strong>numeric confidence score</strong> helps people trust AI answers
    <em>appropriately</em>: accepting answers that are correct and declining answers that are wrong. That is why one
    part of the study showed a confidence score and the other part did not.</p>
    <p>The AI answers were real answers from five AI models: the answer shown was the answer most models gave, and the
    confidence score showed how many of their answers agreed with it. Not all of these answers were correct. The score
    was based on how often the models agreed with each other, not on whether the answer was actually true. The
    incorrect answers you saw are listed below with the correct answer, so you don’t leave with wrong information.</p>
    <p>Please don’t tell other possible participants about the incorrect answers, as this would affect the results.
    Questions or want your data removed? Contact ${STUDY.contactEmail} and mention your participant number.</p>`
};
