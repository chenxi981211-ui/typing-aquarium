# Changelog

## 1.1.1 — 2026-08-20

### Changed

**A gentler sound when a fish arrives.** The old one built to its loudest point
1.76 seconds after the fish had already appeared and peaked at 0.85 — a sting,
at a volume that made a background app feel like it wanted attention. It is now
a short excerpt of a real water recording: 0.75 seconds, peaking at 0.26, cut
just before the droplet so the attack survives and faded at both ends so there
is no click.

**Quieter out of the box.** The default master volume drops from 70 to 45. This
sound fires on every catch, so it should still be pleasant on the twentieth one.
Existing installs keep whatever volume you have already set.

---

## 1.1.0 — 2026-08-20

All four of these were found by testing the 1.0.0 build the way someone
downloading it would, rather than against a save that already had history in it.

### Fixed

**Streaks never advanced if you left the app running.** The streak was only
recalculated when the app started. Since this app is meant to sit open in the
background, anyone typing every day kept whatever streak they had when they last
quit — four consecutive days of typing left it unchanged. That made the three
fish gated on streaks (Dwarf Gouramis, Opah, Devil Pupfish) impossible to earn
without quitting and reopening every night.

The streak is now counted back through your daily record each time, so it cannot
drift however the app is used.

**Coming back after a break gave you a streak you had not earned.** Opening the
app after several days away set the streak to 1 before a single key was pressed.

**The all-time character count was missing days.** It was a running counter and
nothing else, so any day it did not personally witness never made it in — history
recovered from logs, a restored save, a reset. It could read a few thousand under
a history holding ninety thousand. It is now reconciled against the daily record.

**"Total typing time" counted your coffee breaks.** The card on the tank was fed
the time-at-keyboard measure, which counts any gap shorter than two minutes. It
reported 18 minutes for 5 minutes of real work. It now shows time actually spent
typing. Statistics still reports the session figure separately under "At
keyboard", which is what that measure honestly is.

### Added

- **Send Test Notification** in the menu bar, which posts one on demand and
  reports which identity macOS filed it under. Useful because notifications from
  an app run from source are attributed to Python rather than Typing Aquarium.

---

## 1.0.0 — 2026-08-08

First release.

- A desktop tank that fills up as you type
- 30 fish, each with its own unlock condition: characters typed, peak speed,
  sustained focus, day streaks, four times of day, and one lifetime total
- Locked fish show only a silhouette until you catch them
- Statistics: daily counts, calendar week and month, activity by hour
- A menu bar fish — closing the window does not quit the app
- Ambient generated soundtrack, four tank themes, full-screen mode
- Notifications when you catch something, and an optional evening reminder

### Known issues

- **Updating may reset the Accessibility permission.** The app is ad-hoc signed,
  so its signature changes with every build, and macOS ties that permission to
  the signature. After replacing the app, check
  System Settings → Privacy & Security → Accessibility if typing stops counting.
- **Apple Silicon only.** There is no Intel build.
- **The app does not check for updates.** Watch the releases page.

### Your data is safe across updates

Everything lives in `~/Library/Application Support/Typing Aquarium/`, never
inside the app itself. Replacing the app keeps every fish, every statistic and
every setting. Verified by deleting the app entirely, installing a fresh copy,
and confirming progress was intact.
