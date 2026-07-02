# DataCollector browser extension

The Chrome extension used to gather the keystroke and mouse data for the thesis
(Chapter 5). It listens for keyboard and mouse events on every page the signed-
in user visits and uploads them to a collection server. This is the research
prototype, archived here as a record of the tool - **not** something to install
for everyday browsing.

## Files

| File               | Role                                                         |
|--------------------|--------------------------------------------------------------|
| `manifest.json`    | extension manifest (Manifest V2)                             |
| `contentscript.js` | captures key/mouse events, sends them to the background page |
| `background.js`    | relays messages and uploads data to the server              |
| `popup.html/.js`   | login / logout / status UI                                  |
| `reg.html/.js`     | participant registration form                               |

## How it works

A content script runs on every page and attaches six listeners: `mousemove`,
`mousedown`, `mouseup`, `wheel`, `keydown`, `keyup`. Each event is packaged and
sent via `chrome.runtime.sendMessage` to the background script, which (because
a content script cannot make cross-origin requests directly) forwards it to the
server over HTTP. Recording only happens while the participant is logged in, so
they can pause collection at any time by logging out - important because the
tool captures **everything typed**, including passwords (thesis Section 5.5).

- Keystrokes are recorded as key code + down/up timestamps + modifier state.
- Mouse events are recorded as action type + coordinates + timestamp.

See [`docs/data-format.md`](../docs/data-format.md) for the exact fields.

## Changes made for release

- The collection server host is replaced with a placeholder
  (`SERVER_BASE_URL` in `background.js`). The server-side ASP code is not part
  of this repository, so the extension will not upload anywhere as shipped.
- Fixed a bug where holding **Alt** set the Ctrl field instead of the Alt field
  (`contentscript.js`). The thesis analysis used only the Shift and CapsLock
  columns, so published results are unaffected.
- Fixed a `clientY` typo in the old-browser fallback path.
- Removed an unused jQuery dependency (the code is plain DOM JavaScript).

## Status

This is **Manifest V2**, which Chrome has deprecated in favour of Manifest V3.
It is kept as-is to faithfully represent the tool used in the experiments; it
is not maintained for current Chrome releases.

## Ethics

Collection was covered by RHUL ISG ethics approval, with written informed
consent from every participant (thesis Appendices A and B). Anyone reusing this
must obtain their own ethics approval and informed consent before collecting
data. The gathered dataset was never published.
