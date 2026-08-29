# Kiosk setup (for caregivers)

The app is designed to run locked to one device so the child stays in User Mode
and can't leave it. Caregiver Mode is reachable only by entering the 4-digit PIN.

## iPad / iPadOS — Guided Access

1. Settings → Accessibility → Guided Access → **on**. Set a Guided Access
   passcode (different from the app PIN).
2. Open the app (installed from Safari: Share → **Add to Home Screen**).
3. Triple-click the side/home button → **Start**.
4. To exit: triple-click → enter the Guided Access passcode.

For an always-on shared device, consider **Single App Mode** via Apple
Configurator or an MDM.

## Android — Screen Pinning

1. Settings → Security → **App pinning** → on ("Ask for PIN before unpinning").
2. Open the installed app → Recents → tap the app icon → **Pin**.
3. To exit: hold Back + Overview, then enter the device PIN.

For a dedicated device, use a launcher/MDM lock-task mode.

## Notes

- Install the app first (Add to Home Screen / Install) so it runs full-screen
  and works offline.
- The app session does not expire — sign in once.
- The Caregiver PIN protects configuration; the OS lock above protects against
  leaving the app entirely. Use both.
