// In-app camera capture for card-like icons — a caregiver photographs the
// actual object (their child's own cup, school bag, snack) instead of hunting
// for a matching bundled symbol. Modelled on modules/aac/recorder.js's shape:
// a support probe plus one async entry point. Own <dialog> rather than
// dialog.js's confirm/destructive shells (those are text-only; this needs a
// live video feed and a captured-still review step).

import { el, toast } from "./ui.js";
import { scaleForUpload } from "./image-scale.js";

export function isCameraSupported() {
  return !!navigator.mediaDevices?.getUserMedia;
}

// Resolves a File (image/jpeg, already downscaled) or null if the caregiver
// cancelled, denied permission, or no camera exists. Never throws, and never
// triggers a native alert/confirm (those would block the whole tab). Every
// exit path — capture-then-confirm, retake, cancel, backdrop click, Esc — ends
// in the dialog's own "close" event, which is the single place the camera's
// MediaStream tracks are stopped, so the camera indicator light always goes
// out.
export async function capturePhoto() {
  if (!isCameraSupported()) return null;

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 } },
      audio: false,
    });
  } catch {
    toast("אין גישה למצלמה, או שלא נמצאה מצלמה", "error");
    return null;
  }

  let result = null;
  let shotBlob = null;

  const video = el("video", { autoplay: true, playsinline: true, muted: true, class: "camera-video" });
  video.srcObject = stream;
  const shot = el("img", { class: "camera-shot", alt: "", hidden: true });

  const captureBtn = el("button", { type: "button", class: "btn-primary" }, "צלם");
  const retakeBtn = el("button", { type: "button", class: "btn-link", hidden: true }, "צילום מחדש");
  const useBtn = el("button", { type: "button", class: "btn-primary", hidden: true }, "אישור");
  const cancelBtn = el("button", { type: "button", class: "btn-link" }, "ביטול");
  const busy = el("p", { class: "muted", role: "status", hidden: true }, "מעבד…");

  const dialog = el(
    "dialog",
    { class: "dialog camera-dialog" },
    el("div", { class: "dialog-head" }, el("h2", {}, "צילום תמונה")),
    el("div", { class: "camera-frame" }, video, shot),
    busy,
    el("div", { class: "dialog-actions" }, captureBtn, retakeBtn, useBtn, cancelBtn),
  );

  function showLive() {
    shotBlob = null;
    shot.hidden = true;
    video.hidden = false;
    captureBtn.hidden = false;
    retakeBtn.hidden = true;
    useBtn.hidden = true;
  }

  captureBtn.onclick = () => {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        shotBlob = blob;
        shot.src = canvas.toDataURL("image/jpeg", 0.9); // data: — CSP img-src has no blob:
        shot.hidden = false;
        video.hidden = true;
        captureBtn.hidden = true;
        retakeBtn.hidden = false;
        useBtn.hidden = false;
      },
      "image/jpeg",
      0.9,
    );
  };

  retakeBtn.onclick = showLive;

  useBtn.onclick = async () => {
    if (!shotBlob) return;
    busy.hidden = false;
    useBtn.disabled = true;
    retakeBtn.disabled = true;
    try {
      result = await scaleForUpload(shotBlob);
    } catch {
      toast("לא ניתן לעבד את התמונה", "error");
    }
    dialog.close();
  };

  cancelBtn.onclick = () => dialog.close();
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  document.body.append(dialog);
  dialog.showModal();

  return new Promise((resolve) => {
    dialog.addEventListener(
      "close",
      () => {
        stream.getTracks().forEach((t) => t.stop());
        dialog.remove();
        resolve(result);
      },
      { once: true },
    );
  });
}
