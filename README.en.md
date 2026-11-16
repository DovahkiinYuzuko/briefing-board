# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

An agent skill that turns discussion topics and options organized by an AI agent into a local web dashboard before implementation, collecting your decisions and comments through a browser UI.

It fits design or architecture discussions where long chat threads make topics hard to track or you want to hold off implementation until every item is agreed upon. For single-fact questions or straightforward edits, regular chat responses are faster.

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

Python 3.11 or higher is required (uses the standard library `tomllib`, requiring no external Python packages).

### Installation

Install with the command matching your environment:

**With Agent Skills Compatible Tools**

```bash
npx skills add DovahkiinYuzuko/briefing-board
```

**As an Antigravity Plugin**

```bash
agy plugin install https://github.com/DovahkiinYuzuko/briefing-board
```

### Triggering

Invoke the skill in conversation with your agent using the slash command or natural-language phrases:

- `/briefing-board`
- Phrases requesting a briefing or strategy session before implementation (such as "let's do a briefing", "open the briefing board", or "help me decide the approach").

---

## How It Works

1. **Start a Session**: When you invoke the skill, the AI agent organizes the discussion topics and options, starts the local server, and presents the dashboard URL (`http://localhost:<PORT>/wip/<session-folder>/`).
2. **Review and Save in Browser**: Open the URL in your browser, select a decision per topic (Pending, Approve, Revise, Investigate, or Cancel) and choose options. Add comments or propose new topics as needed, then save.
3. **Iterate on Open Items**: While saved as a draft or while any topic remains pending, marked for revision, or under investigation, the AI agent does not proceed with implementation or issue creation. It updates the board with answers or investigation results, and resolved items can be hidden with the "Hide Resolved" switch.
4. **Complete and Archive**: Once all topics are approved or cancelled, the agent confirms whether to create tasks or issues, moves the session to `done/`, and stops the server.

---

## Key Features

- **Isolated Git Footprint**: On first generation of the output directory (`briefing-board/`), a `.gitignore` file containing `*` and `!.gitignore` is automatically created so session files do not pollute your repository's Git history.
- **Deterministic Per-Project Ports and LAN Access**: A project-specific port in `8899..8998` is derived from the CRC32 hash of the output directory path (probing up to `+20` if occupied). Because the server binds to `0.0.0.0`, sessions can also be reviewed from smartphones or tablets on the same LAN.
- **Multilingual UI and Summary Output**: Switch the display language from the header, and the `summary.md` generated on save matches the selected language. Japanese and English are included by default, and additional languages can be added by placing JSON files in `skills/briefing-board/locales/`.
- **Settings Persistence**: UI language and view mode are saved globally across projects in `skills/briefing-board/user_settings.json`, while session list sort order and search queries are saved per project in `portal_settings.json`.

---

## Runtime Environment and Constraints

- **CDN Dependency for Math, Code Highlighting, and Fonts**: KaTeX (0.16.8), Prism.js (1.29.0), and Google Fonts (Noto Sans JP / Noto Sans Mono) are loaded via CDN. This choice keeps the repository free of external Python dependencies and frontend build steps. In offline environments, formulas and code blocks fall back to plain text, while option selection and saving continue to function.
- **Limitations in `file://` Fallback Mode**: Static assets are copied into each session folder so the dashboard can still be viewed and `decision.toml` can be downloaded even when a local server cannot run. However, auto-saving (`POST /api/save`), `summary.md` generation, and settings persistence (`/api/settings`) do not work over `file://`; accessing the HTTP URL served by `server.py` enables those features.
- **Static Session List Generation**: The session list (`briefing-board/index.html`) is built when sessions are created, updated, or archived. Because there is no background database or file-watcher daemon, `new_briefing.py --rebuild-portal` is only needed if session folders are moved manually.

---

## Internal Architecture and References

<details>
<summary>Expand directory and script responsibilities and specification links</summary>

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
