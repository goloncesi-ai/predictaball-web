# QA Test Matrix

## Devices / OS
- iPhone 15 / iOS 18+
- iPhone SE / iOS 18+
- iPad / iPadOS 18+

## Core flows
- [ ] Cold start -> tabs load without crash.
- [ ] Pull-to-refresh works in all tabs.
- [ ] Relaunch restores selected team/round/player state.
- [ ] Network off: cached GET data renders where available.

## Analysis
- [ ] Team pickers populate.
- [ ] Metrics render.
- [ ] Goal trend chart renders.
- [ ] H2H and recent matches sections render.

## Simulation
- [ ] League/team/formations selectable.
- [ ] Formation pitch preview updates live.
- [ ] Run prediction returns result.
- [ ] Probability chart + scoreline bars render.
- [ ] Adjustment details render.

## Upcoming Games
- [ ] Round stepper loads requested round.
- [ ] Confidence labels and probability bars render.
- [ ] Top scoreline rows render when available.

## Player Lab
- [ ] Team filter narrows player list.
- [ ] Single profile metrics render.
- [ ] Compare mode chart and delta rows render.

## Non-functional
- [ ] No UI blocking hangs during API failures.
- [ ] Error messages are user-readable.
- [ ] Scrolling performance is acceptable on older device.
