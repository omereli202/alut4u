// Spoken breathing cues (שאיפה / החזקה / נשיפה).
//
// This does NOT go through modules/aac/speech.js: that path plays audio that
// the backend pre-generates once when a caregiver saves a card, and it has no
// runtime text-to-speech. These three words are fixed app strings, so the
// browser's speechSynthesis is the right tool — no server round-trip, works
// offline. If the device has no Hebrew voice the engine spells the letters out
// as nonsense, so cuesAvailable() stays false and the caller stays silent.

let heVoice = null;
let checked = false;

function findHebrewVoice() {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => /^he\b|^he-|iw/i.test(v.lang)) || null;
}

function refresh() {
  heVoice = findHebrewVoice();
  checked = true;
}

if ("speechSynthesis" in window) {
  refresh();
  // Chrome populates voices asynchronously — re-check once they arrive.
  window.speechSynthesis.addEventListener("voiceschanged", refresh);
}

export function cuesAvailable() {
  if (!checked) refresh();
  return heVoice !== null;
}

export function speakCue(text) {
  if (!cuesAvailable()) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "he-IL";
  u.voice = heVoice;
  u.rate = 0.85;
  u.volume = 0.9;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

export function stopCues() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}
