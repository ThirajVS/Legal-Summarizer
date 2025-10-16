import React, { useState, useEffect } from "react";

/** ---------------- Helpers ---------------- */
const pick = (reArr, text, group = 1, fb = "N/A") => {
  for (const re of reArr) {
    const m = text.match(re);
    if (m && m[group]) return String(m[group]).trim();
  }
  return fb;
};

const short = (v, n = 120) => (v && v.length > n ? v.slice(0, n) + "…" : v || "N/A");

/** ---------------- Robust FIR Parser ----------------
 * - Captures values with proper boundaries (comma/period/newline)
 * - Handles headings on same line as Name (e.g., "1. Complainant Details Name: ...")
 * - Avoids giant text in entity boxes
 */
function parseFIR(raw = "") {
  const empty = {
    overview: "FIR summary not available.",
    keyPoints: [],
    entities: {
      firNumber: "N/A",
      policeStation: "N/A",
      date: "N/A",
      time: "N/A",
      complainant: "N/A",
      accused: "N/A",
      witnesses: [],
      sections: [],
      location: "N/A",
      investigatingOfficer: "N/A",
    },
    timeline: [],
  };
  if (!raw || !raw.trim()) return empty;

  // Keep newlines for block parsing; also have a flattened copy for inline matches
  const text = raw.replace(/\r\n?/g, "\n");
  const flat = text.replace(/[ \t]+/g, " ").trim();

  // Tight single-line captures (stop at comma/period/newline)
  const policeStation = pick(
  [
    // do NOT stop on periods; stop only at comma/newline/end
    /\bPolice\s*Station\s*[:\-]?\s*([A-Za-z0-9 .,&'_-]+?)(?=,|\n|$)/i,
  ],
  flat
);


  const firNumber = pick(
    [/\bFIR\s*(?:No\.?|Number)\s*[:\-]?\s*([A-Za-z0-9\/\-]+)/i,
     /\bFIR\s*registered\s*No\.?\s*([A-Za-z0-9\/\-]+)/i],
    flat
  );

  const date = pick(
    [/\bDate\s*[:\-]?\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})/i],
    flat
  );

  const time = pick(
    [/\bTime\s*[:\-]?\s*([0-9]{1,2}[:.][0-9]{2}\s*(?:AM|PM|am|pm)?)/i,
     /\b(?:at|around)\s*([0-9]{1,2}[:.][0-9]{2}\s*(?:AM|PM|am|pm)?)/i,
     /\b([0-9]{1,2}[:.][0-9]{2})\s*(?:hrs|Hrs|hours)?/i],
    flat
  );

  // Slice between numeric headings (works even if Name is on same line)
  const sliceBetween = (startRe, endRe) => {
    const s = text.search(startRe);
    if (s === -1) return "";
    const rest = text.slice(s);
    const e = rest.search(endRe);
    return e === -1 ? rest : rest.slice(0, e);
  };

  // Complainant: catch 'Name:' anywhere in the block, stop before Age/Address/.,,/newline
  const complainantBlock = sliceBetween(/1\.\s*Complainant\s*Details/i, /2\./i);
const complainant =
  (
    complainantBlock.match(
      /Name\s*:\s*([A-Za-z .'_-]+?)(?=\s+(?:Age|Address|Designation|Contact|Mobile|Phone|Email|Police|Station|FIR|Date|Time)\b|,|\n|$)/i
    )?.[1]
    ||
    pick(
      [/\bComplainant(?:\s*Name|\s*Details)?\s*:\s*([A-Za-z .'_-]+)/i],
      flat
    )
    ||
    "N/A"
  ).trim();

  // Accused: same approach
  const accusedBlock = sliceBetween(/2\.\s*Accused\s*Details/i, /3\./i);
const accused =
  (
    accusedBlock.match(
      /Name\s*:\s*([A-Za-z .@'_-]+?)(?=\s+(?:Age|Address|Designation|Contact|Mobile|Phone|Email|Police|Station|FIR|Date|Time)\b|,|\n|$)/i
    )?.[1]
    ||
    pick(
      [/\bAccused(?:\s*Name|\s*Details)?\s*:\s*([A-Za-z .@'_-]+)/i],
      flat
    )
    ||
    "N/A"
  ).trim();

  // Witnesses: list lines (bullets or numbered). Also try inline "Witnesses: a, b, c"
  // ---- Witnesses: list in section 5; stop before Designation/PS/etc.; strip ranks like SI/ASI/Inspector ----
const witnessesBlock = sliceBetween(/5\.\s*Witness(?:es)?/i, /6\./i);

// helper to trim ranks + tidy spaces
const cleanPerson = (s) =>
  (s || "")
    .replace(/^\s*(?:Name\s*:\s*)?/i, "")
    .replace(/^(?:SI|ASI|HC|PC|Ct|Inspector|Sub-Inspector)\.?\s+/i, "") // drop police ranks at start
    .replace(/\s+/g, " ")
    .trim();

let witnesses = [];

// 5.a bullet/numbered lines inside the block
for (const line of witnessesBlock.split("\n")) {
  const m = line.match(
    /^\s*(?:-|\d+\.)?\s*([A-Za-z .'-]+?)(?=,|\.|\s+(?:Designation|Rank|Police\s*Station|Address|Age|Contact|Mobile|Phone|Email)\b|$)/i
  );
  if (m && m[1]) {
    const name = cleanPerson(m[1]);
    if (name) witnesses.push(name);
  }
}

// 5.b inline "Witnesses: a, b, c" fallback
if (witnesses.length === 0) {
  const inline = flat.match(/\bWitness(?:es)?[^:]*:\s*([^.\n]+)/i)?.[1] || "";
  if (inline) {
    for (const chunk of inline.split(/,| and /i)) {
      const name = cleanPerson(
        (chunk || "").match(
          /^\s*([A-Za-z .'-]+?)(?=,|\.|\s+(?:Designation|Rank|Police\s*Station|Address|Age|Contact|Mobile|Phone|Email)\b|$)/
        )?.[1] || ""
      );
      if (name) witnesses.push(name);
    }
  }
}

// de-duplicate
witnesses = Array.from(new Set(witnesses));


  // Investigating Officer (IO)
  // --- keep sliceBetween as-is above ---

// Replace your current IO extraction with this:
const ioBlock = sliceBetween(/7\.\s*Investigating\s*Officer/i, /8\./i);

// inline fallbacks anywhere in the text (tight end boundaries)
const ioInline = pick(
  [
    /\bInvestigating\s*Officer\s*Name\s*:\s*([A-Za-z .'-]+?)(?=,|\.|\n|$)/i,
    /\bIO\s*Name\s*:\s*([A-Za-z .'-]+?)(?=,|\.|\n|$)/i,
    /assigned\s+to\s*([A-Za-z .'-]+?)\s*,\s*Investigating\s*Officer/i,
  ],
  flat,
  1,
  ""
);

let investigatingOfficer =
  (
    ioBlock.match(
      /Name\s*:\s*([A-Za-z .'-]+?)(?=\s+(?:Age|Address|Designation|Contact|Mobile|Phone|Email|Police|Station|FIR|Date|Time)\b|,|\n|$)/i
    )?.[1] ||
    ioInline ||
    "N/A"
  ).trim();


  // Sections: “IPC Section 441” and “Section 447 IPC”
  const sectionsSet = new Set();
  for (const m of text.matchAll(/\bIPC\s*Section\s*(\d+)/gi)) sectionsSet.add(`IPC ${m[1]}`);
  for (const m of text.matchAll(/\bSection\s*(\d+)\s*IPC\b/gi)) sectionsSet.add(`IPC ${m[1]}`);
  const sections = Array.from(sectionsSet);

  // Location: explicit Location: … else a known locality in text; else PS
  // ✅ Final robust location extraction (dot-aware + FIR-safe)
let location =
  pick(
    [
      // 1) Explicit "Location:" (do NOT stop on periods—only comma/newline/end)
      /\bLocation\s*[:\-]?\s*([A-Za-z0-9 .,&'_-]+?)(?=,|\n|$)/i,

      // 2) Sub-locality in parentheses after Police Station, e.g. "(Bharathi Nagar)"
      /\bPolice\s*Station.*?\(\s*([A-Za-z0-9 .,&'_-]+?)\s*\)/i,

      // 3) Fallback to "Police Station: …" main area
      /\bPolice\s*Station\s*[:\-]?\s*([A-Za-z0-9 .,&'_-]+?)(?=,|\n|$)/i,

      // 4) Conservative "at/in ..." but ignore property & report words up front
      /\b(?:at|in)\s+(?!Survey\s*No\b|FIR\b|First\b|Information\b|Report\b|Police\s*Station\b)([A-Za-z0-9 .,&'_-]+?)(?=,|\n|$)/i,
    ],
    flat,
    1,
    ""
  ) || "";

// If we accidentally caught something starting with report words, try a stricter second pass
if (!location || /\b(FIR|First|Information|Report)\b/i.test(location)) {
  const m = flat.match(
    /\b(?:at|in)\s+(?!Survey\s*No\b|FIR\b|First\b|Information\b|Report\b|Police\s*Station\b)([A-Za-z .,&'_-]+?(?:Puram|Nagar|Colony|Road|Street|Layout|Block|Area|District|City))(?=,|\n|$)/i
  );
  location = (m?.[1] || "").trim();
}

// Cleanup & normalization
location = (location || "")
  .replace(/\bSurvey\s*No\b.*$/i, "")      // drop trailing property refs
  .replace(/\s+/g, " ")                    // collapse spaces
  .replace(/\b([A-Z])\s*\.\s*([A-Z])\s*\./g, "$1.$2.")  // "R . S ." -> "R.S."
  .trim();

// Fallbacks: explicit localities present in text, else Police Station, else N/A
if (!location) {
  const rs = flat.match(/\bR\.?\s*S\.?\s*Puram\b/i)?.[0];
  const bn = flat.match(/\bBharathi\s*Nagar\b/i)?.[0];
  location = (bn || rs || policeStation || "N/A").trim();
}


  // Overview
  const overviewParts = ["FIR registered"];
  if (policeStation && policeStation !== "N/A") overviewParts.push(`at ${policeStation}`);
  if (location && location !== "N/A" && location !== policeStation) overviewParts.push(`(${location})`);
  if (firNumber && firNumber !== "N/A") overviewParts.push(`FIR No: ${firNumber}`);
  if (date && date !== "N/A") overviewParts.push(`Date: ${date}`);
  if (time && time !== "N/A") overviewParts.push(`Time: ${time}`);
  const overview = overviewParts.join(" ").replace(/\s+/g, " ").trim();

  const keyPoints = [
    `Complainant – ${complainant || "N/A"}`,
    `Accused – ${accused || "N/A"}`,
    `Location – ${location || "N/A"}`,
    `Sections – ${sections.length ? sections.join(", ") : "N/A"}`,
    `Investigating Officer – ${investigatingOfficer || "N/A"}`,
  ];

  const timeline = [];
  if (date !== "N/A" || time !== "N/A") {
    timeline.push({
      time: [date !== "N/A" ? date : "", time !== "N/A" ? time : ""].filter(Boolean).join(" "),
      event: "FIR registered",
    });
  }

  return {
    overview,
    keyPoints,
    entities: {
      firNumber: firNumber || "N/A",
      policeStation: policeStation || "N/A",
      date: date || "N/A",
      time: time || "N/A",
      complainant: complainant || "N/A",
      accused: accused || "N/A",
      witnesses,
      sections,
      location: location || "N/A",
      investigatingOfficer: investigatingOfficer || "N/A",
    },
    timeline,
  };
}

/** ---------------- Presentation ---------------- */
function SummaryCard({ summaryText }) {
  const parsed = parseFIR(summaryText);

  return (
    <div className="space-y-6 text-gray-100">
      {/* Overview */}
      <section>
        <h3 className="text-blue-400 font-semibold mb-2">Overview</h3>
        <p className="text-slate-300 leading-relaxed">{parsed.overview}</p>
      </section>

      {/* Key Points */}
      <section>
        <h3 className="text-purple-400 font-semibold mb-3">Key Points</h3>
        <ul className="list-decimal pl-5 text-slate-300 space-y-1">
          {parsed.keyPoints.map((b, i) => <li key={i}>{b}</li>)}
        </ul>
      </section>

      {/* Extracted Entities */}
      <section>
        <h3 className="text-green-400 font-semibold mb-3">Extracted Entities</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Complainant:</b> {short(parsed.entities.complainant)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Accused:</b> {short(parsed.entities.accused)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Sections:</b> {parsed.entities.sections.length ? parsed.entities.sections.join(", ") : "N/A"}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Location:</b> {short(parsed.entities.location)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Police Station:</b> {short(parsed.entities.policeStation)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>FIR No:</b> {short(parsed.entities.firNumber, 40)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Date:</b> {short(parsed.entities.date, 40)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2"><b>Time:</b> {short(parsed.entities.time, 40)}</div>
          <div className="bg-slate-700/40 rounded-lg p-2 col-span-2"><b>Investigating Officer:</b> {short(parsed.entities.investigatingOfficer)}</div>
          {parsed.entities.witnesses.length > 0 && (
            <div className="bg-slate-700/40 rounded-lg p-2 col-span-2">
              <b>Witnesses:</b> {parsed.entities.witnesses.join(", ")}
            </div>
          )}
        </div>
      </section>

      {/* Timeline */}
      {parsed.timeline.length > 0 && (
        <section>
          <h3 className="text-yellow-400 font-semibold mb-3">Timeline</h3>
          <div className="space-y-2">
            {parsed.timeline.map((t, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="bg-yellow-600 text-white text-xs font-bold rounded px-2 py-1">
                  {short(t.time, 24)}
                </span>
                <span className="text-slate-300">{t.event}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default function CaseSummaryView() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  // Load all processed cases
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/cases")
      .then((res) => res.json())
      .then((data) => setCases(data.cases || []))
      .catch((err) => console.error("Error loading cases:", err));
  }, []);

  // When user selects a case, fetch its summary
  const handleSelectCase = async (caseId) => {
    setSelectedCase(caseId);
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/result/${caseId}`);
      const data = await res.json();
      setSummary(data.summary || "No summary found.");
    } catch (_) {
      setSummary("No summary found.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 text-white p-6">
      <div className="max-w-7xl mx-auto flex gap-6">
        {/* Sidebar */}
        <div className="w-1/4 bg-slate-800/50 backdrop-blur-md rounded-2xl p-4 shadow-lg">
          <h2 className="text-lg font-semibold mb-4">Case Files</h2>
          <ul className="space-y-3">
            {cases.map((c) => (
              <li
                key={c.case_id}
                onClick={() => handleSelectCase(c.case_id)}
                className={`p-3 rounded-xl cursor-pointer transition ${
                  selectedCase === c.case_id
                    ? "bg-blue-700/70"
                    : "bg-slate-700/40 hover:bg-blue-700/50"
                }`}
              >
                {c.case_id}
                <br />
                <span className="text-xs text-gray-300">{c.file_name}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Summary Panel */}
        <div className="flex-1 bg-slate-800/60 rounded-2xl p-6 shadow-lg">
          {!selectedCase ? (
            <div className="text-gray-400 text-center mt-20 text-lg">
              Select a case file to view its summary.
            </div>
          ) : loading ? (
            <div className="text-gray-400 text-center mt-20 text-lg">
              Loading summary…
            </div>
          ) : (
            <>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">{selectedCase}</h2>
                <button className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700">
                  Download PDF
                </button>
              </div>

              <div className="text-gray-200 leading-relaxed">
                <SummaryCard summaryText={summary} />
              </div>

              {/* Ask AI Section (UI placeholder) */}
              <div className="mt-8 bg-slate-900/60 rounded-2xl p-4 border border-blue-800/30">
                <h3 className="text-lg font-semibold mb-2">Ask AI About This Case</h3>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., 'Show witness info' or 'Extract FIR number'"
                    className="flex-1 px-4 py-2 rounded-lg bg-slate-800/50 text-white border border-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 transition">
                    Ask
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
