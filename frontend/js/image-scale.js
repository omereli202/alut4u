// One image downscale, shared by the camera capture and file-upload paths
// (see camera.js, visual-picker.js). A tablet rear-camera JPEG is routinely
// 3-8MB, well over the server's MAX_IMAGE_BYTES (4MB, checked *before* it
// resizes — backend/app/services/media_processing.py) — so without this, a
// camera photo (and plenty of gallery photos) would 422 before ever reaching
// the resize step. Shrinking client-side also means less of the photo leaves
// the device. The server still re-encodes on top of this (EXIF strip, its own
// 1024px cap) — this is a client-side mirror of that cap, not a replacement.

const MAX_DIM = 1024;
const QUALITY = 0.85;
const SKIP_BELOW_BYTES = 1024 * 1024; // already small — skip a lossy re-encode

export async function scaleForUpload(source, { maxDim = MAX_DIM, quality = QUALITY } = {}) {
  const bitmap = await createImageBitmap(source);
  const { width, height } = bitmap;
  const alreadySmall = width <= maxDim && height <= maxDim && (source.size ?? Infinity) <= SKIP_BELOW_BYTES;
  if (alreadySmall) {
    bitmap.close?.();
    return source instanceof File ? source : new File([source], `photo-${Date.now()}.jpg`, { type: source.type });
  }

  const scale = Math.min(1, maxDim / Math.max(width, height));
  const w = Math.max(1, Math.round(width * scale));
  const h = Math.max(1, Math.round(height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  canvas.getContext("2d").drawImage(bitmap, 0, 0, w, h);
  bitmap.close?.();

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
  return new File([blob], `photo-${Date.now()}.jpg`, { type: "image/jpeg" });
}
