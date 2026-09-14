# Status

Last updated: 2026-09-14

## Where things stand

Image Preview 0.3.0, installed and working: an IMAGES dock in luvus, a loopback
HTTP gallery for the pixels. It is a **stopgap** and the README says to delete it
the day luvus can show a PNG itself.

Nothing is outstanding in the module. The open work is upstream, and this
session moved it along by arguing the case rather than by writing code.

## What changed today

- Removed `[[events]] on = "pane.focused"` from `luvus-module.toml`. There is no
  such event — luvus documents `pane.created`, `pane.closed`,
  `pane.agent_status_changed` and the workspace, tab, task and lease lifecycles,
  and none of them fire on focus. The hook had never run; the 0.4s
  `workspace list` poll was already doing the whole job. `d268496`.
- Corrected the README, which said "module hooks do not run `pane.focused`" —
  that reads as a hook being ignored, when the truth is there is nothing to
  subscribe to.

## Upstream, as of 2026-09-14

| Thing | State | Why we care |
|---|---|---|
| [#207](https://github.com/RizRiyz/luvus/issues/207) image protocols in panes | open, asking for direction | commented with our findings — [issue comment](https://github.com/RizRiyz/luvus/issues/207#issuecomment-5668610014), the first reply it had since 30 August |
| [#324](https://github.com/RizRiyz/luvus/pull/324) kitty graphics in panes | open, mergeable, no milestone, last touched 14 Sep | retires the in-pane half of this module |
| [#236](https://github.com/RizRiyz/luvus/pull/236) open a file in the desktop app | open, last touched 12 Sep | retires **all** of this module, and is the smaller change |

Both PRs are by rsaulo, who also filed #207.

## What we told #207, and why it is worth keeping here

Each of these is a measurement, not an opinion, and each one is the reason a
piece of this module looks the way it does.

- **Luvus eats sixel, and it is not the host terminal.** Linux/Omarchy, Ghostty
  1.3.1, luvus 0.14.1: `img2sixel` in a pane exits 0 and paints nothing, on a
  terminal that supports both sixel and kitty graphics. Confirmed in the source
  on luvus main `7e70fcb`: the vendored parser routes APC into
  `State::SosPmApcString` and drops it, and `src/terminal/` contains no sixel or
  kitty handling at all.
- **Half-blocks are not a fallback for choosing.** An 800px ComfyUI contact
  sheet rendered as half-block cells tells you an image exists and nothing else.
  Our question is "which of these nine", so the blocky in-pane view is a
  different feature, not a degraded one. That is why the browser exists.
- **A loopback URL has no viewport problem.** #207 worries about per-client
  viewports, remote thin clients and replayed sessions. A page served over HTTP
  sidesteps every one of them for the *viewing* case — which is the argument for
  not making "look at this file" wait on in-pane graphics.
- **There is no FILES context for modules.** `contexts` takes `pane`,
  `workspace` or `agent` (`tab` is reserved). Clicking an image in the file tree
  is the natural gesture and a module cannot be offered there, which is why this
  dock keeps its own parallel list of the same files in the same order.
- **There is no focus event.** Hence the 0.4s poll. Subscribing is no help
  either: while idle the stream is almost entirely `terminal.output_ready`.
- **#324 will look broken to its first user.** It implements the Unicode
  placeholder path and silently drops direct placements carrying no pixel or
  cell dimensions — which is exactly what a bare `icat foo.png` sends, and
  exactly what anyone will type first to test it.

## Retire this module when

Either upstream change is enough to delete most of it, and both together delete
all of it:

- **#236 lands** → the gallery goes. Clicking a PNG in FILES opens the desktop
  viewer, which is all the dock was ever standing in for.
- **#324 lands and can place an image with cell size set** → the half-block
  fallback goes, and `view.py` with it.

Check both before doing any more work here. Adding a feature to a module whose
README says to delete it is how a stopgap becomes permanent.

## Next time

- If #324 gets a Linux tester, that is us: we have the contact-sheet workload,
  Ghostty 1.3.1, and the offer is already made in the #207 comment.
- Watch for a focus event or a FILES context appearing upstream. Either would
  let the dock drop its poll or its parallel list, and both are small next to
  the engine work — worth a separate issue if #207 lands on "modules can cover
  the viewing case".
