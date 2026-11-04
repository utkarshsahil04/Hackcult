# Raahein

## Product purpose
Raahein helps a visitor standing at an Indian monument identify it from a photo and immediately reach a sourced story in English or Hindi. The core promise is to bridge the gap between the structure in front of the visitor and trustworthy context without an account or typed input.

## Audience and moment
- Primary visitor: a domestic or international traveller using one hand at a heritage site, often on patchy mobile data.
- Critical moment: open the PWA, frame or choose a photo, identify the monument, and continue to its story in under thirty seconds.
- Primary action: photograph a monument.

## Product language
- Say `monuments`, `heritage sites`, `guides`, `storytellers`, `visitors`, and `story`.
- Never use `spots`, `attractions`, `vendors`, or `content` in visitor-facing labels.
- Never expose percentages or confidence scores. A later recognition result may say `Likely match` or explain that Raahein is not sure.
- Every main screen supports English and Hindi. Hindi copy must wrap without clipping.

## Experience constraints
- No login or sign-up in the visitor flow. My journey works without an account and stays on the device.
- Identifying a monument requires no typing.
- Camera and gallery access are the two entry paths.
- Main navigation contains Scan, Explore, Plan, and My journey.
- Every interactive target is at least 48px and works by keyboard and touch.
- Visitor photos go directly to recognition and are not retained by the client beyond the active session.

## Platform and implementation
- Mobile-first PWA built with Next.js App Router, React, and strict TypeScript.
- The scan and device-access flow is a client component.
- The backend recognition contract is `POST /api/recognition/identify`; this screen does not change that API.
- The repository's existing Indian-monuments dataset has unconfirmed image licensing and must not be used as a public UI gallery.

## Brand commitments
- One light sandstone visual world only; no dark mode.
- Sandstone `#EADBC0`, ivory `#FBF6EC`, ink `#1F1A14`, secondary ink `#5A4E3F`, Agra Red `#B5452B`, and restrained Marigold `#E8A317` highlights.
- Fraunces for the wordmark and headings, Inter for Latin body text, and Noto Sans Devanagari for Hindi.
- Thin line icons, warm shadows, and rounded surfaces. The central capture action remains unmistakable and Agra Red.

## Confirmed first surface
The Scan home screen leads with a large rounded camera viewfinder, four corner brackets, a short framing hint, a central capture button, a gallery action, a Browse monuments link, a bilingual language toggle, and the three-tab bottom navigation.
