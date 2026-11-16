# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

An agent skill that puts AI-organized discussion topics and options onto a local web dashboard before implementation, letting you review and respond in a browser.

Useful when design threads get buried in long chats or when you want to hold off implementation until every item is agreed on (for quick questions or small edits, regular chat is simpler).

## Contents

- [Installation and Triggering](#installation-and-triggering)
  - [Installation](#installation)
  - [Triggering](#triggering)
- [How It Works](#how-it-works)
- [Key Features](#key-features)
- [Runtime Environment and Constraints](#runtime-environment-and-constraints)
- [Internal Architecture and References](#internal-architecture-and-references)
  - [Component Responsibilities](#component-responsibilities)
  - [Reference Documents](#reference-documents)
- [LICENSE](#license)

## Installation and Triggering

Requires Python 3.11 or higher (uses the standard library `tomllib`, so no external packages are needed).

### Installation

**With Agent Skills Compatible Tools**

```bash
npx skills add DovahkiinYuzuko/briefing-board
```

**As an Antigravity Plugin**

```bash
agy plugin install https://github.com/DovahkiinYuzuko/briefing-board
```

### Triggering

Start a session in chat using the slash command or a natural-language prompt:

- `/briefing-board`
- Phrases requesting a briefing or strategy session before implementation (such as "let's do a briefing", "open the briefing board", or "help me decide the approach").

---

## How It Works

1. **Open the board**: Invoke the skill, and the AI organizes topics and options, starts the local server, and shares the URL (`http://localhost:<PORT>/wip/<session-folder>/`).
2. **Review and save**: Pick a status per topic (Pending, Approve, Revise, Investigate, or Cancel), choose options, add comments or new topics if needed, and save.
3. **Iterate on open items**: While saved as a draft or while any item is Pending, Revise, or Investigate, the AI holds off on implementation or issue creation and updates the board. You can hide resolved items with the "Hide Resolved" toggle.
4. **Wrap up and archive**: Once everything is Approved or Cancelled, the AI confirms whether to create tasks or issues, moves the session to `done/`, and shuts down the server.

---

## Key Features

- **Clean Git working tree**: Creates `briefing-board/.gitignore` (`*` and `!.gitignore`) on the first run so session files stay out of Git history.
- **Per-project ports and LAN access**: The local server picks a dedicated port per project (`8899..8998`) and binds to `0.0.0.0`, making it accessible from phones or tablets on the same LAN.
- **Multilingual UI and summary output**: Switch the display language from the header, and `summary.md` is generated in whichever language is active.
- **Persistent settings**: UI language and view mode are shared across all projects, while portal sort order and search filters are kept per project.

---

## Runtime Environment and Constraints

- **Offline fallback**: Math (KaTeX 0.16.8), syntax highlighting (Prism.js 1.29.0), and fonts (Google Fonts: Noto Sans JP / Noto Sans Mono) load from CDNs and fall back to plain text offline (option selection and saving still work).
- **Opening via `file://`**: Even without a local server, you can open the HTML directly to view sessions and download `decision.toml`. Auto-save (`POST /api/save`), `summary.md` generation, and settings persistence (`/api/settings`) require the HTTP URL served by `server.py`.
- **Static session list**: The portal (`briefing-board/index.html`) is rebuilt statically whenever sessions are created, updated, or archived. Run `new_briefing.py --rebuild-portal` only if you move session folders manually.

---

## Internal Architecture and References

<details>
<summary>Directory layout, implementation details, and specification links</summary>

### Implementation Notes

- **Port allocation**: Derived from the CRC32 hash of the output directory path in `8899..8998` (probing up to `+20` if already in use).
- **Adding languages**: Place additional JSON locale files under `skills/briefing-board/locales/`.
- **Settings storage**: UI language and view mode live in `skills/briefing-board/user_settings.json`; per-project portal sort/search state lives in `portal_settings.json`.
- **Why CDNs and static asset copies**: Avoids external Python dependencies and frontend build steps, while keeping basic viewing and `decision.toml` export working even if a local server cannot start.

### Component Responsibilities

| Path | Responsibility |
| :--- | :--- |
| `plugin.json` | Manifest definition for Antigravity plugin installation. |
| `skills/briefing-board/SKILL.md` | Agent execution protocol (5-step workflow, decision tree, and pre-approval implementation guard). |
| `skills/briefing-board/scripts/new_briefing.py` | Schema validation for input TOML/JSON, session creation and in-place updates (`--update-session`), validated archiving (`--archive <session-folder>`, server shutdown is separate), session list rebuilding (`--rebuild-portal`), and server startup orchestration. |
| `skills/briefing-board/scripts/server.py` | Local HTTP server (`GET /api/decision`, `POST /api/save`, `GET/POST /api/settings`, `POST /api/shutdown`) and `summary.md` generation. |
| `skills/briefing-board/scripts/briefing_common.py` | Shared utilities for TOML/JSON loading, deterministic port calculation, and reading/writing `user_settings.json` and `portal_settings.json`. |
| `skills/briefing-board/resources/` | Frontend assets aligned with DADS design tokens (`index.html`, `portal.html`, `app.js`, `style.css`). |
| `skills/briefing-board/locales/` | Localization bundles (`en.json`, `ja.json`). |
| `skills/briefing-board/references/` | Schema specification, CLI reference, and agenda input template. |

### Reference Documents

- Skill definition: [SKILL.md](./skills/briefing-board/SKILL.md)
- CLI arguments and API endpoints (for development and verification): [cli_reference.md](./skills/briefing-board/references/cli_reference.md)
- Input/output TOML schema (`briefing.toml` / `decision.toml`): [schema_specification.md](./skills/briefing-board/references/schema_specification.md)
- Input template: [agenda_template.toml](./skills/briefing-board/references/agenda_template.toml)

</details>

---

## LICENSE

[MIT](./LICENSE.MIT)

Third-Party → [NOTICE.md](./NOTICE.md)

This skill's UI is an independent implementation referencing the [Digital Agency Design System (DADS)](https://design.digital.go.jp/dads/) specifications and is not created or provided directly by the Digital Agency of Japan.
