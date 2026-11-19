# Changelog

## [1.0.0](https://github.com/TimeToAlign/TimeToShare/compare/v0.1.0...v1.0.0) (2026-11-19)


### ⚠ BREAKING CHANGES

* `font_path()` is replaced by `font_paths()` and `FONT_FILES` (JS `FONT_FILES`); `fonts/LICENSE` is now `fonts/DejaVuSans-LICENSE`, with `fonts/NotoMusic-LICENSE` beside it; the metrics file is now `fonts/dejavu-sans-2.37+noto-music-2.004.metrics.json`; drawings name both fonts and their coordinate labels change.
* the root start/end wedge and label addresses (`{"id": T, "part": ["start"|"end"]}` and their labels) no longer address anything; address the `origin`/`length` timestamps instead.

### Features

* a catalogue of identifier systems, verbs and types replaces the scheme registry ([4923d67](https://github.com/TimeToAlign/TimeToShare/commit/4923d671e64619f1ddd92945f9c80b5cb4aabe7f))
* add a margin placement input for containers with one content ([97bab9c](https://github.com/TimeToAlign/TimeToShare/commit/97bab9c106c2f0cb332f8bb7f759d4e1ffe2e6c8))
* check the description layer alone and store each identified fact once ([71d7a64](https://github.com/TimeToAlign/TimeToShare/commit/71d7a64aefbc92e5ceb8d90bebc608b62e6151f0))
* child_ends is public API with its rule documented ([edf7491](https://github.com/TimeToAlign/TimeToShare/commit/edf7491547daba99f3be7696b5c1a61b908ccea8))
* css_pixels and user_units graphical units ([b7b915e](https://github.com/TimeToAlign/TimeToShare/commit/b7b915e408f50a65aed1e354632908c189763eee))
* draw what DejaVu Sans lacks in Noto Music and label coordinates with their pretty text ([0970f7f](https://github.com/TimeToAlign/TimeToShare/commit/0970f7fa112709df90283b4d0d27cce282763972))
* export the walk of a manifest's statement subjects ([dc27deb](https://github.com/TimeToAlign/TimeToShare/commit/dc27debb877c05bf588e301d372d407d0bc4f4a5))
* helpers between bare IDs and the file's #id form ([f6a7c5a](https://github.com/TimeToAlign/TimeToShare/commit/f6a7c5ada5f47aa3c251b2db1f14bdb0d32cc4b7))
* infer a manifest file's form and write it back in both packages ([0d59382](https://github.com/TimeToAlign/TimeToShare/commit/0d593825bf2a6349b829f226d7a0c176ee3c68ed))
* **js:** validate links, recognise catalogue URLs and build links from URLs ([ea57a00](https://github.com/TimeToAlign/TimeToShare/commit/ea57a00893a1d0e4bf667b6617b5494a9f30963f))
* **js:** write canonical YAML, pretty JSON and RFC 8785 JSON, read all three ([ec0c990](https://github.com/TimeToAlign/TimeToShare/commit/ec0c990a56c7645b0e7e6296f2c7ba4f843574f0))
* lay out conversion maps by row and round float labels to three decimals ([816c2d4](https://github.com/TimeToAlign/TimeToShare/commit/816c2d430808e2808fb6aff6fb3d78743f84ab1d))
* let named timestamps state what is drawn of them; drop the root's start and end markers ([dacc08f](https://github.com/TimeToAlign/TimeToShare/commit/dacc08f23f4f14c8679880193d703f6854d91609))
* name timestamps in a manifest and draw their cross-section lines ([aa9e6be](https://github.com/TimeToAlign/TimeToShare/commit/aa9e6be19e3f4dbb1c91de77b613792904f76372))
* property–value statements, provenance and an inline JSON-LD context replace links and schemes ([0edf747](https://github.com/TimeToAlign/TimeToShare/commit/0edf747c699099061412ed5d8de1da7e7704080e))
* **python:** validate links, recognise catalogue URLs and model the description layer ([7cca289](https://github.com/TimeToAlign/TimeToShare/commit/7cca2897482e340defbe4fbfc46dfa8e3356b345))
* **python:** write canonical YAML, pretty JSON and RFC 8785 JSON, and read all three ([900a744](https://github.com/TimeToAlign/TimeToShare/commit/900a744ebbfc388fa66a140be695e2443f0dd1dd))
* **python:** write the minimal form by default in to_dict ([183e848](https://github.com/TimeToAlign/TimeToShare/commit/183e848a01f0cec4588135ba0c1b442d71f5f6c5))
* refuse assertion dates the Gregorian calendar lacks ([f97444e](https://github.com/TimeToAlign/TimeToShare/commit/f97444efbce7621942cd9398c2f0ff85cef7eec2))
* refuse values nested deeper than 256 levels in every serialization ([d57a2a5](https://github.com/TimeToAlign/TimeToShare/commit/d57a2a58b4a005b04de7bc54cfa87d9460b115c1))
* **registry:** recognise YouTube video addresses ([05c2757](https://github.com/TimeToAlign/TimeToShare/commit/05c275786fd5f0e96de155e5df06dff8e2a04b18))
* rename and drop element references in statements; compact an IRI by its prefix ([6827930](https://github.com/TimeToAlign/TimeToShare/commit/68279303adbd1d696e5f0c2441c7e17ecf721483))
* **schema:** add description links, schemes and part readings ([029c924](https://github.com/TimeToAlign/TimeToShare/commit/029c924fbe93186d91fc32bd38a952daa959aab7))
* statements, provenance and the catalogue in the npm package ([d38b98f](https://github.com/TimeToAlign/TimeToShare/commit/d38b98f3e1f1cae09ec45c8e106c0e6690164975))
* statements, provenance and the catalogue in the Python package ([9bfad96](https://github.com/TimeToAlign/TimeToShare/commit/9bfad96672a51d6437b7e1807421945035970b77))
* write every ID in a manifest file as #id; graphical.rules ([c531361](https://github.com/TimeToAlign/TimeToShare/commit/c531361d58fd8e3f30d2130666cc412f337a9832))


### Bug Fixes

* containment on float axes follows double arithmetic ([39f6f92](https://github.com/TimeToAlign/TimeToShare/commit/39f6f92f411949254e7ee6d901e20340669fa36a))
* **js:** keep huge float-axis integers, pair surrogates by kind, walk YAML with a stack ([335ec49](https://github.com/TimeToAlign/TimeToShare/commit/335ec49d9afe0a861c14e10298a74887d2912318))
* name YAML tag, anchor and empty-key refusals alike in both readers ([00e2f06](https://github.com/TimeToAlign/TimeToShare/commit/00e2f0631bca50a400f0095e399117a09ec05525))
* one reading of pairs, paths and catalogue matches in the npm package ([0e94c0c](https://github.com/TimeToAlign/TimeToShare/commit/0e94c0ce33ca58f8d56ccbfa6c5549e6dcf55a92))
* one reading of paths and catalogue matches in the Python package ([a2bebe0](https://github.com/TimeToAlign/TimeToShare/commit/a2bebe007b539db78b016f82186d06899b9174c8))
* **python:** refuse YAML nested beyond the recursion limit with a position ([c1b922e](https://github.com/TimeToAlign/TimeToShare/commit/c1b922ec35974ea1c49121cf02cf4659aea1a98f))
* read YAML through PyYAML's event API and refuse every tag ([3cd161f](https://github.com/TimeToAlign/TimeToShare/commit/3cd161f19225e140c94fef2c97d9a21f8869be49))
* refuse bare scheme references in the description check; one message for every bare ID ([bdd4b26](https://github.com/TimeToAlign/TimeToShare/commit/bdd4b26c3be836544b9d2a729da05af197221356))
* refuse the first YAML fault at its token in both readers ([6c811cc](https://github.com/TimeToAlign/TimeToShare/commit/6c811cceb02a140968d073f7abe005ec82c0ad97))
* **registry:** class the YouTube video ID as a manifestation ([7c44048](https://github.com/TimeToAlign/TimeToShare/commit/7c44048bf056533c39eadded20f67ad2bb0122b8))
* **registry:** keep playlist embeds out of the YouTube video scheme ([b3b0b24](https://github.com/TimeToAlign/TimeToShare/commit/b3b0b24774550c73ebb8b31f5d8f0366d9e5dfd1))
* **registry:** refuse YouTube live-stream embeds and read legacy /v/ addresses ([f76301a](https://github.com/TimeToAlign/TimeToShare/commit/f76301aa6e65b2284161cda5d0121377a8914d28))
* **registry:** write the YouTube video scheme in the pretty JSON layout ([5245f0d](https://github.com/TimeToAlign/TimeToShare/commit/5245f0d1045cb4e33b21b883df45851952f1ce79))
* **schema:** refuse a trailing newline in IDs and paints in both validators ([6324cac](https://github.com/TimeToAlign/TimeToShare/commit/6324cac08085870d3e002b2c0c34cc01576b8396))
* **scripts:** write emitted fixtures with LF line endings on every platform ([97a26d2](https://github.com/TimeToAlign/TimeToShare/commit/97a26d217003a46411ffa46ba6dc80ad952f07e2))
* segment lines on float axes follow double arithmetic ([3362a3c](https://github.com/TimeToAlign/TimeToShare/commit/3362a3cfac3d50775f011a41911d2680b0153eed))
* **serialization:** refuse the first fault in document order in every reader ([d6128f3](https://github.com/TimeToAlign/TimeToShare/commit/d6128f3415aac0eea671a2148487718215065678))

## 0.1.0 (2026-10-21)


### Features

* TimeToShare! 0.1.0, an exchange format for the structures of musical timelines ([128d432](https://github.com/TimeToAlign/TimeToShare/commit/128d43248c2be717271fca7ae19256e310a0b093))
