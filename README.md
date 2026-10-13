# SkillForge

Vite + React frontend preview for self-evolving skill infrastructure. The interface pairs dot-matrix and pixel typography with a moving particle background, stable cards, and dark/light themes.

## Run

```sh
npm install
npm run dev
```

Open http://127.0.0.1:5173/. Production check: `npm run build`.

## Experience

- Product-led landing page with a concrete sales skill repair preview, architecture overview, applications, and guardrails.
- Seven-stage walkthrough stays on the selected step. There is no autoplay or walkthrough pause/resume control.
- The same greyscale particle background and neutral palette continue across every page. Light mode uses silver glass and charcoal text; dark mode uses translucent graphite surfaces and silver accents. Colour is reserved for the pixel characters.
- Workspace includes an overview, skill library, console, activity, contracts, version history, and local draft creation.
- Cursor companions Byte and Scout appear automatically, float at their perch, trail desktop pointers, and sparkle on clicks. They never intercept input. Paused motion, reduced motion, and touch retain a stationary perch.
- Card frames remain steady while title words visibly float and tilt automatically, icons bob, and edge highlights travel. Extra hover responses supplement the continuous motion. Page transitions and button feedback use transforms and opacity, without animated blur or layout changes.
- Offscreen sections and hidden tabs pause decorative motion. Cursor movement is frame-scheduled, and the background is a seamless 60 fps loop. The global motion control and reduced-motion preference are supported.
- The sales demo simulates the revenue/Sales mismatch, repairs the mapping, validates three tests, and saves version 1.1 for reuse.
- Storybook and all particle film playback/download controls have been removed. The MP4 remains an ambient background asset.

## Source map

- `src/App.jsx`: workspace state, routing, demo lifecycle, dialogs, and theme.
- `src/components/Landing.jsx`: product landing page and manual lifecycle explorer.
- `src/components/KineticType.jsx`: letter reveals and hover motion.
- `src/components/MotionText.jsx`: responsive word-level text animation.
- `src/components/MotionVisibility.jsx`: offscreen and hidden-tab animation suspension.
- `src/components/CursorCompanions.jsx`: desktop pointer-following pets.
- `src/components/LivingBackground.jsx`: ambient video surface.
- `src/components/ParticleFilm.jsx`: background video playback lifecycle.
- `src/final-polish.css`: final landing composition, palettes, and dialog refinements.
- `src/workspace-polish.css`: stable responsive workspace surfaces and readable type.
- `src/unified-motion.css`: shared translucent surfaces, route-consistent colours, and smooth motion.
- `src/neutral-theme.css`: graphite/silver colour correction across both themes and every route.
- `src/automatic-motion.css`: continuous floating titles and decorative movement without pointer interaction.
- `public/video/`: 12-second, 60 fps particle loop and poster.

Backend execution, AI calls, validation, and metrics are simulated. Drafts and demo progress reset on reload. Theme preferences persist locally. Fonts and assets are bundled; no backend is needed.
