# Changelog

## Unreleased

### Changes

* An elision's `display` defaults to `["ellipsis", "name"]`, and the initial value of the property `elision-display` is `ellipsis name`: every gap shows its ellipsis with the name of its timeline unless its `display` says otherwise. A stated `["ellipsis"]` is kept and draws the ellipsis alone.
* A gap draws exactly one ellipsis, centred in the gap and on the card (across a frame, on its member cards together), with its labels centred below it, their room still taken in the markers band of the elision's timeline; continuations stay on every row crossing the gap.
* An ancestor card behind a frame has a seam at each end of its member's span, as wide as the frame's room on that side, so that what lies outside the member's span lies outside the frame; the automatic proportion of its derived elisions reads the card's reach from the frame's edges. The drawing specification defines the seam once: a jump of a card's axis that leaves nothing out and draws nothing, a row crossing it drawn whole. The seam between two groups along a root drawn once follows the same definition, its rows no longer drawn as continuations.
* The defaults no longer cut the manifest's title at 160 canvas units.

## 0.1.0 (2026-10-21)


### Features

* TimeToShare! 0.1.0, an exchange format for the structures of musical timelines ([128d432](https://github.com/TimeToAlign/TimeToShare/commit/128d43248c2be717271fca7ae19256e310a0b093))
