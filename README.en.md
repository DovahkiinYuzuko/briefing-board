# briefing-board

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=flat-square&logo=javascript&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=opensourceinitiative&logoColor=white)](./LICENSE.MIT)

[日本語](./README.md) | [English](./README.en.md)

An agent skill that turns topics and options organized by an AI agent during pre-implementation design discussions into a local interactive web dashboard and Kanban portal, collecting user decisions as structured files (`decision.toml` and `summary.md`).

## Contents

- [briefing-board](#briefing-board)
  - [Contents](#contents)
  - [Installation and Triggering](#installation-and-triggering)
    - [Installation](#installation)
    - [Triggering](#triggering)
  - [Session Workflow](#session-workflow)
  - [Key Features](#key-features)
  - [Runtime Environment and Constraints](#runtime-environment-and-constraints)
  - [Internal Architecture and Detailed References](#internal-architecture-and-detailed-references)
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
- Phrases requesting a briefing or strategy session before implementation (such as "let's do a briefing", "strategy session", or "方針決め").

---

## Session Workflow

Once triggered, each session proceeds through five steps:

1. **Agenda Creation**: The agent writes the discussion topics, options, and background notes (`ai_notes`) into `briefing_input.toml`.
2. **Validation, Build, and Server Launch**: The script validates the input schema, generates the session and Kanban portal under `<project>/briefing-board/`, starts the local HTTP server, and presents the dashboard URL (`http://localhost:<PORT>/wip/<session-folder>/`).
3. **Review and Save in Browser**: The user opens the dashboard in a browser, selects an action per topic (Pending, Approve, Revise, Investigate, or Cancel), chooses options, adds comments or new topics, and saves.
4. **Finalization Check and Iteration**: The agent reads the saved `decision.toml`. While the session is saved as a draft or any topic remains pending, marked for revision, or under investigation, the agent does not start implementation or issue creation; instead, it addresses feedback or investigates further and updates the board via `--update-session`.
5. **Archive and Shutdown**: Once the session is completed and every topic is approved or canceled, the agent confirms task/issue creation preferences with the user, moves the session folder to `done/`, rebuilds the portal, and stops the server.

---

## Key Features

- **Isolated Git Footprint**: On first generation of the output directory (`briefing-board/`), a `.gitignore` file containing `*` and `!.gitignore` is automatically created so session artifacts do not pollute the target repository's Git history.
- **Deterministic Per-Project Ports and LAN Access**: A project-specific port in `8899..8998` is derived from the CRC32 hash of the output directory path (probing up to `+20` if occupied). Because the server binds to `0.0.0.0`, sessions can also be reviewed from smartphones or tablets on the same LAN.
- **Bilingual UI and Output**: The header language selector switches between English (`en`) and Japanese (`ja`). The `summary.md` generated on save is localized to match the selected language.
- **Hybrid Settings Persistence**: UI language and view mode (`auto`, `desktop`, `mobile`) are persisted globally across projects in `user_settings.json` inside the skill directory, while portal sort order and search queries are persisted per project in `portal_settings.json`.

---

## Runtime Environment and Constraints

- **Scope and Non-Ideal Cases**: This skill fits design discussions that compare multiple architectural options or specification tradeoffs and require halting implementation until all topics are finalized. For single-fact questions or trivial edits, standard chat responses avoid the overhead of generating and reviewing a dashboard.
- **CDN Dependency for Math, Code Highlighting, and Fonts**: KaTeX (0.16.8), Prism.js (1.29.0), and Google Fonts (Noto Sans JP / Noto Sans Mono) are loaded via CDN. This choice keeps the repository free of frontend build steps and external Python dependencies. In offline environments, formulas and code blocks fall back to plain text, while option selection and saving continue to function.
- **Limitations in `file://` Fallback Mode**: Static assets are copied into each session directory so the dashboard can still be viewed and `decision.toml` can be downloaded even if a local server cannot run. However, `POST /api/save` auto-saving, `summary.md` generation, and `/api/settings` persistence do not operate over `file://`; accessing the HTTP URL served by `server.py` enables those features.
- **Static Portal Generation**: The Kanban portal (`briefing-board/index.html`) is statically rendered when sessions are created or updated. Because there is no background database or file-watcher daemon, moving session folders manually between `wip/` and `done/` requires running `new_briefing.py --rebuild-portal` to refresh the portal cards.

---

## Internal Architecture and Detailed References

<details>
<summary>Expand directory and script responsibilities and specification links</summary>

### Component Responsibilities

| Path | Responsibility |
| :--- | :--- |
| `plugin.json` | Manifest definition for Antigravity plugin installation. |
| `skills/briefing-board/SKILL.md` | Agent execution protocol (5-step workflow, decision tree, and pre-approval implementation guard). |
| `skills/briefing-board/scripts/new_briefing.py` | Schema validation for input TOML/JSON, session creation and in-place updates (`--update-session`), portal rebuilding (`--rebuild-portal`), and server startup orchestration. |
| `skills/briefing-board/scripts/server.py` | Local HTTP server (`GET /api/decision`, `POST /api/save`, `GET/POST /api/settings`, `POST /api/shutdown`) and `summary.md` generation. |
| `skills/briefing-board/scripts/briefing_common.py` | Shared utilities for TOML/JSON loading, deterministic port calculation, and reading/writing `user_settings.json` and `portal_settings.json`. |
| `skills/briefing-board/resources/` | Frontend assets aligned with DADS design tokens (`index.html`, `portal.html`, `app.js`, `style.css`). |
| `skills/briefing-board/locales/` | Localization bundles (`en.json`, `ja.json`). |
| `skills/briefing-board/references/` | Schema specification, CLI reference, and agenda input template. |

### Reference Documents

- Skill definition: [SKILL.md](./skills/briefing-board/SKILL.md)
- CLI arguments and API endpoints (for development and verification): [cli_reference.md](./skills/briefing-board/references/cli_reference.md)
- Input/output TOML schema (`briefing.toml` / `decision.toml`): [schema_specification.md](./skills/briefing-board/references/schema_specification.md)
- Agenda input template: [agenda_template.toml](./skills/briefing-board/references/agenda_template.toml)

</details>

---

## LICENSE

[MIT](./LICENSE.MIT)

Third-Party → [NOTICE.md](./NOTICE.md)

This skill's UI is an independent implementation referencing the [Digital Agency Design System (DADS)](https://design.digital.go.jp/dads/) specifications and is not created or provided directly by the Digital Agency of Japan.
