---
name: Serene Path
colors:
  surface: '#FFFFFF'
  surface-dim: '#dad9de'
  surface-bright: '#faf9fd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f7'
  surface-container: '#eeedf2'
  surface-container-high: '#e8e8ec'
  surface-container-highest: '#e2e2e6'
  on-surface: '#1a1c1f'
  on-surface-variant: '#43474f'
  inverse-surface: '#2f3034'
  inverse-on-surface: '#f1f0f5'
  outline: '#737780'
  outline-variant: '#c3c6d0'
  surface-tint: '#3d608e'
  primary: '#3a5d8b'
  on-primary: '#ffffff'
  primary-container: '#5476a6'
  on-primary-container: '#fdfcff'
  inverse-primary: '#a6c8fd'
  secondary: '#3e6658'
  on-secondary: '#ffffff'
  secondary-container: '#c0ecda'
  on-secondary-container: '#446c5e'
  tertiary: '#79550e'
  on-tertiary: '#ffffff'
  tertiary-container: '#956e27'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d4e3ff'
  primary-fixed-dim: '#a6c8fd'
  on-primary-fixed: '#001c3a'
  on-primary-fixed-variant: '#234875'
  secondary-fixed: '#c0ecda'
  secondary-fixed-dim: '#a5d0be'
  on-secondary-fixed: '#002117'
  on-secondary-fixed-variant: '#264e41'
  tertiary-fixed: '#ffdeac'
  tertiary-fixed-dim: '#efbf70'
  on-tertiary-fixed: '#281900'
  on-tertiary-fixed-variant: '#604100'
  background: '#faf9fd'
  on-background: '#1a1c1f'
  surface-variant: '#e2e2e6'
  bg: '#F7F9F9'
  text: '#2D3436'
  text-muted: '#636E72'
  success: '#7FB069'
  warning: '#E6A23C'
  danger: '#D66853'
  focus: '#4A90E2'
  border: '#DCDFE6'
typography:
  display-user:
    fontFamily: Rubik
    fontSize: 2.6rem
    fontWeight: '500'
    lineHeight: '1.15'
  heading-caregiver:
    fontFamily: Rubik
    fontSize: 1.9rem
    fontWeight: '500'
    lineHeight: '1.2'
  subheading:
    fontFamily: Rubik
    fontSize: 1.4rem
    fontWeight: '500'
    lineHeight: '1.3'
  body:
    fontFamily: Rubik
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: '1.4'
  caption:
    fontFamily: Rubik
    fontSize: 0.9rem
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  '1': 0.25rem
  '2': 0.5rem
  '3': 0.75rem
  '4': 1rem
  '6': 1.5rem
  '8': 2rem
  '12': 3rem
---

## Brand & Style

The design system is engineered for neurodivergent accessibility, prioritizing a **low-arousal, compassionate, and predictable** environment. The brand personality is that of a "steady hand"—reliable, professional, and calm. It avoids all forms of sensory friction, such as flashing, rapid motion, or high-saturation triggers.

### Design Style: Minimalism & Tactile Logic
The system employs a refined **Minimalist** approach with **Tactile** influences. 
- **Predictable Hierarchy:** Information is organized through clear surfacing rather than complex decoration.
- **Physical Metaphor:** In the "User Mode," elements behave like physical tiles, providing strong visual and press-down feedback to assist children in understanding cause and effect.
- **Cognitive Load Reduction:** Heavy whitespace and a strict avoidance of neon or pure black/white ensure the interface remains non-threatening and easy to process.

## Colors

The palette is strictly **muted and low-saturation** to prevent sensory overload. All color pairings are validated for WCAG AA compliance.

- **Primary & Secondary:** Soft blues and sage greens provide a calming, non-clinical aesthetic.
- **Semantic Usage:** 
    - `Success` (Calm Green) is used for positive reinforcement and completion.
    - `Warning` and `Danger` are strictly reserved for **Caregiver Mode** to prevent the child from experiencing "failure states" or anxiety-inducing red UI.
- **Neutrality:** Pure `#000000` and `#FFFFFF` are avoided in favor of off-whites and charcoal-grays to reduce screen glare and visual fatigue.

## Typography

This is a **Hebrew-first** system. All text is aligned to the right (RTL). The typeface **Rubik** is selected for its friendly, rounded terminals which are highly legible for children and provide a soft, approachable feel.

- **Line Height:** Increased leading (~1.4 for body) is utilized to prevent "crowding" of Hebrew characters, which can often appear denser than Latin scripts.
- **User Mode (Display):** Uses the `display-user` (2.6rem) level for screen titles to ensure maximum legibility and focus for the child.
- **Caregiver Mode:** Uses standard density typography to facilitate efficient management of schedules and cards.

## Layout & Spacing

The layout adapts between two distinct density modes using a 12-column fluid grid for the caregiver and a simplified, sparse grid for the user.

- **User Mode (`data-mode="user"`):** 
    - Sparse layout with high whitespace.
    - Minimalist grids (2–3 columns max on mobile).
    - Touch targets are prioritized at a minimum of **60x60px**.
- **Caregiver Mode (`data-mode="caregiver"`):** 
    - Standard density for list management and data entry.
- **RTL Integrity:** Margins and paddings are mapped to `start` and `end` values. A `margin-right` in a standard system becomes `margin-inline-start: var(--space-4)` here.

## Elevation & Depth

Depth is used sparingly to indicate interactivity without creating visual "noise." 

- **Tonal Layers:** The primary method of separation is the use of `--color-surface` against the slightly darker `--color-bg`.
- **Shadows:** 
    - **Level 1:** A very light, diffused shadow for resting tiles and cards, providing a subtle "lift" from the background.
    - **Level 2:** Reserved for modals, dialogs, and the "Sentence Bar" (the active construction area in AAC), signifying that these elements are atop the primary navigation layer.
- **Zero Gradients:** Surfaces are flat to maintain visual predictability and clarity.

## Shapes

The shape language is rounded and organic to evoke safety. 

- **Standard Elements:** Inputs and chips use `--radius-sm` (6px) for subtle definition.
- **Interactive Elements:** Buttons and AAC cards use `--radius-md` (12px), creating a friendly, approachable corner.
- **Kiosk Elements:** Large tiles and modals in User Mode use `--radius-lg` (20px) to emphasize their tactile, toy-like nature.
- **Keypads:** Security PIN keys must be perfectly circular or have high roundedness to distinguish them from content tiles.

## Components

### Buttons & Inputs
- **Primary Buttons:** High contrast (using `--color-primary` and `--color-primary-contrast`) with 12px rounded corners. In User Mode, these must scale to 60px height.
- **Active State:** All buttons must have a distinct "press-down" (scale 0.98) feedback to confirm the interaction.
- **Input Fields:** Use `--color-border` for outlines; on focus, a 3px solid `--color-focus` ring appears with a 2px offset.

### AAC Tiles (Cards)
- **Visuals:** Tiles display a central emoji or stroke icon with a label underneath.
- **Feedback:** Upon selection, the tile should flash the primary color or show a bold border to confirm the choice before the icon "moves" to the sentence bar.

### Lists & Containers
- **Caregiver Lists:** Standardized rows with 16px padding and hairline dividers (`--color-border`).
- **User Mode Containers:** Extreme padding (`--space-8`) to prevent accidental taps of adjacent elements.

### Specialized Components
- **The Sentence Bar:** A persistent, elevated (`--shadow-2`) horizontal area where selected AAC tiles are collected. It must support drag-and-drop reordering with clear visual handles.
- **PIN Keypad:** A 3x4 grid of large, circular keys for exiting User Mode, designed to be accessible for caregivers but visually distinct from the child's interface.