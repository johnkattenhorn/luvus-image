# Image Preview

**Stopgap.** Luvus cannot show a PNG in its own file viewer yet. This module
is a workaround, not the long-term answer.

Retire it once these land and actually paint pixels in a pane (or open the
file from FILES):

- [RizRiyz/luvus#324](https://github.com/RizRiyz/luvus/pull/324) — kitty
  graphics in panes (open, parked for 0.15, conflicts with main as of
  2026-09-13)
- [RizRiyz/luvus#236](https://github.com/RizRiyz/luvus/pull/236) — open a
  file in the desktop's own application

Until then: an **IMAGES** dock in Luvus, click a row, a **local browser**
tab shows the real pixels.

## Why a browser

Luvus's file viewer is a text viewer. It detects binaries and says so.
Markdown and Mermaid are the only rich previews it ships. A module pane
is an ordinary terminal: Luvus ate sixel (probed 2026-09-13, `img2sixel`
exit 0, blank pane). Half-blocks of an 800px sheet are unreadable.

So the readable view is a loopback page (`127.0.0.1`) that serves the file
bytes. The dock still lives in Luvus.

It does **not** replace the FILES click. Module actions can hang off panes,
workspaces and agents, not the file tree.

## Install

Needs Python 3 and either [Pillow](https://pypi.org/project/Pillow/) or
ImageMagick (`magick` / `convert`).

```sh
luvus module install johnkattenhorn/luvus-image
```

From a checkout:

```sh
luvus module link /path/to/luvus-image
```

## Use

- Click a row in the **IMAGES** dock — that opens the browser gallery
  on **the same list, same order**. Dock row `3  photos/hero.png` is
  thumb 3, and the URL is `/?n=3`.
- In the page: arrows or `n`/`p` walk that list, `1`–`9` jump to dock
  row 1–9.
- Switching workspaces: the watcher polls `workspace list` every 0.4s
  and rescans when `active` cwd changes. Module hooks do not run
  `pane.focused`, and `luvus events` while idle is almost only
  `terminal.output_ready`. The header is `IMAGES · scanning <folder>…`
  then `IMAGES · <folder>`; a bottom-bar **IMG** chip shows working
  then done. `runs/` is skipped so generate output does not bury sheets.
- Right-click a WORKSPACES row → Refresh image list.
- Select a path in a pane → right-click → View selected path in the browser.
- **Open image in a Luvus pane** is the blocky half-block fallback.

The server binds `127.0.0.1` only and serves only files currently in the
gallery list, and only if they still look like images. It is not a file
server for the rest of the disk.

## Settings

Under **Settings → Modules → Image Preview**:

- **Scan depth** (default 4)
- **Images in the dock** (default 40, newest first)

## What this is not

It is not Luvus's image viewer. It is not a hex dump and not an editor.
When #324 can display a PNG with cell size set, and/or #236 can open one
from FILES, delete this module.
