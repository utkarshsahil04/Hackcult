# Raahein Offline Demo Dataset (Issue #17)

This directory contains the version-controlled demo package for running Raahein's offline demonstrations without live external dependencies.

## Contents

- `images/`: Five representative, high-resolution demo photos covering canonical monuments in Agra and Delhi:
  1. `taj_mahal.jpg` (`taj-mahal`, Agra) — SHA-256: `5a7f69bdbcd2a7c1193d368617769a85aaa22449b0a9c28e90ad2fb1d96db965`
  2. `qutb_minar.jpg` (`qutb-minar`, Delhi) — SHA-256: `419b6920da37e72d7790bf85bf5a6286f3394be5bab21186defb84c5afafa066`
  3. `humayuns_tomb.jpg` (`humayuns-tomb`, Delhi) — SHA-256: `5a0a3e69c30b99e83de2e47711f24e5c2754a0f1d44851a631274746c4ecd687`
  4. `red_fort.jpg` (`red-fort`, Delhi) — SHA-256: `3eb1a427a85d9a17c13941a3ee5022aa33f9f7cc685e6c3863949cd3e5c58302`
  5. `agra_fort.jpg` (`agra-fort`, Agra) — SHA-256: `162ef044912e27449c61cfb144c6631db43c7bf5fca354a375c9e015d237b015`
- `cached_responses.json`: Structured, frozen recognition candidate outputs for each photo.

## Lookup Behavior

1. Uploading any of the 5 demo photos yields an exact SHA-256 hash match and returns the frozen candidate ranking with `source: "demo_cache"`.
2. Any arbitrary or unknown photo not matching the demo set is processed honestly by the inference engine (or returns `status: "uncertain"` when GPU models are offline). Demo responses are **never** silently served for non-demo uploads.

