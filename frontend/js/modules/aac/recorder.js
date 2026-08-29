// Short in-browser voice recording for a card, via MediaRecorder.
// Gated on voice consent by the caller (editor.js).

export function isSupported() {
  return typeof MediaRecorder !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
}

export async function recordClip({ maxMs = 8000 } = {}) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
  const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);

  const done = new Promise((resolve) => {
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      resolve(new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
    };
  });

  rec.start();
  const stop = () => rec.state !== "inactive" && rec.stop();
  const timer = setTimeout(stop, maxMs);

  return {
    stop: () => {
      clearTimeout(timer);
      stop();
      return done;
    },
    done,
  };
}
