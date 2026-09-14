# Decisions

Why this module is shaped the way it is. Each entry is dated, and each one is a
choice that would look wrong without its reason — the obvious things are not
here.

## 2026-09-13 — The readable view is a browser, not a pane

Luvus cannot paint pixels. Probed on luvus 0.14.1, Linux/Omarchy, Ghostty 1.3.1:
`img2sixel` inside a pane exits 0 and paints nothing, on a host terminal that
supports both sixel and kitty graphics. Confirmed later in luvus's own source on
main `7e70fcb` — the vendored parser routes APC into `State::SosPmApcString` and
drops it, and `src/terminal/` has no sixel or kitty handling at all. So this is
not a terminfo problem anyone can configure around.

The half-block fallback is the honest alternative and it is not good enough for
the job. An 800px ComfyUI contact sheet drawn as half-block cells answers "an
image exists" and nothing else; the question that sends us to the sheet is
"which of these nine", and half-blocks cannot answer it. A blocky view is a
different feature, not a degraded one.

So the pixels are served over loopback HTTP and shown in a real browser tab, and
only the *list* lives in luvus. It also happens to sidestep what makes in-pane
graphics hard upstream — every client has its own viewport, remote clients get
projected frames, restored sessions replay text — because a URL has no viewport
problem at all.

Reversal condition is in `docs/STATUS.md`: delete this when
[#236](https://github.com/RizRiyz/luvus/pull/236) or
[#324](https://github.com/RizRiyz/luvus/pull/324) lands.

## 2026-09-13 — The half-block pane action stays, despite the above

`open.py` still offers **Open image in a Luvus pane**. Keeping a view we have
just called unreadable looks inconsistent, so: it answers a different question —
*is this file an image at all, and roughly what of* — without leaving the
keyboard or opening a window, which is worth something when the browser is not
where you are. It is offered, never the default, and the README says plainly
what it is.

## 2026-09-13 — The dock and the gallery are one list, in one order

Dock row 3 is thumb 3 and the URL is `/?n=3`; `1`–`9` in the page jump to dock
rows 1–9.

This is not polish, it is compensation. Luvus offers module actions on
`contexts = ["pane" | "workspace" | "agent"]` — there is no FILES context, so a
module cannot be offered when you click an image in the file tree, which is the
natural gesture. The dock has to be a second, parallel list of the same files,
and a parallel list is only bearable if its order is predictable enough to point
at. Retire the parallel list, not the ordering, when a FILES context appears.

## 2026-09-13 — Poll `workspace list` every 0.4s, rather than subscribe

Luvus has no focus event. The documented set is `pane.created`, `pane.closed`,
`pane.agent_status_changed` plus the workspace, tab, task and lease lifecycles —
nothing fires when the thing you are looking at changes. Subscribing is no help
either: while idle, `luvus events` is almost entirely `terminal.output_ready`.

So `watch.py` polls at `POLL = 0.4` and rescans when the active workspace's cwd
changes. A poll in a module is normally a smell; here it is the only mechanism
that exists. Written down because the obvious "fix" is to replace it with a
subscription, and that does not work.

Corollary, 2026-09-14: the manifest carried `[[events]] on = "pane.focused"` for
a while. No such event exists, so it never ran (`d268496`).

## 2026-09-13 — The server binds loopback and serves only the gallery

`http_view.py` binds `127.0.0.1` on an ephemeral port, and a request is answered
only for a path currently in the gallery state that still passes `is_image()`.
Anything else is 404.

The tempting version of this module is a small static file server rooted at the
workspace. That would serve the whole checkout — source, `.env`, keys — to
anything that can reach the port, in exchange for a little convenience. This is
a picture viewer; it gets to see pictures it was asked about.

Binding beyond loopback would make the gallery reachable from a phone, which is
genuinely useful and is exactly why it is not the default.

## 2026-09-13 — `runs/` is skipped when scanning

`SKIP_DIRS` holds the usual suspects (`.git`, `node_modules`, `.venv`, `dist`,
`build`, …) and also `runs`. That one is workload-specific: image generation
writes hundreds of intermediate frames under `runs/`, and a newest-first dock
capped at 40 would be nothing but those, burying the contact sheets the dock
exists to show. Default depth 4, default 40 rows, both settable.

## 2026-09-13 — A module, marked a stopgap, with deletion criteria

Not a patch to luvus and not a fork. The viewing problem is upstream's to solve
properly, and two changes already in flight would solve it; a module that works
today and disappears when they land costs less than a fork that has to be
maintained against a moving parser.

The stopgap framing is deliberate and is repeated in the README, the manifest
`description` and `docs/STATUS.md`, because a workaround that stops calling
itself one is how it becomes permanent.
