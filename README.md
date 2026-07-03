<p align="center">
  <img src="src/assets/banner.png" alt="Pawn Passant" width="100%">
</p>

# Pawn Passant

*A cross-platform chess game built with Flet.*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.85+-orange.svg)](https://flet.dev/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Android-blueviolet)](https://github.com/Sakth1/PawnPassant/releases)
[![Version](https://img.shields.io/badge/version-v0.3.0-blueviolet)](https://github.com/Sakth1/PawnPassant/releases)

---

## Table of Contents

- [Overview](#overview)
- [Download](#download)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Current Limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Pawn Passant is a cross-platform chess application built with [Flet](https://flet.dev/), a Python framework that wraps Flutter for native desktop, mobile, and web UIs. It delivers a polished chess experience with full rules enforcement, move animations, a configurable chess clock, and an AI opponent powered by Leela Chess Zero (Lc0).

The application separates game logic from presentation. The backend uses [`python-chess`](https://python-chess.readthedocs.io/) for move validation and rules enforcement, while the frontend provides a responsive, interactive interface. Components communicate through an event-driven signal bus, keeping the architecture modular and testable.

---

## Download

Grab the latest build for your platform:

| Platform | Format | Link |
|----------|--------|------|
| Windows | Installer (`.exe`) | [Download](https://github.com/Sakth1/PawnPassant/releases/latest) |
| Windows | Portable (`.zip`) | [Download](https://github.com/Sakth1/PawnPassant/releases/latest) |
| Android | APK (`.apk`) | [Download](https://github.com/Sakth1/PawnPassant/releases/latest) |

All assets are built automatically via GitHub Actions and signed for Android. See the [Releases page](https://github.com/Sakth1/PawnPassant/releases) for the full changelog.

---

## Features

- **Full chess rules** — En passant, castling, promotion, check, checkmate, stalemate, insufficient material, 75-move rule, fivefold repetition
- **Configurable chess clock** — Bullet, Blitz, Rapid, and Classical presets with custom time control and millisecond precision at critical time
- **Move animations** — Adjustable speed (off, fast, normal, slow)
- **Drag-and-drop or click-to-move** — Both interaction modes supported
- **Promotion dialog** — Interactive overlay to choose Queen, Rook, Bishop, or Knight
- **Captured pieces panel** — Visual display organized by color
- **Legal move highlighting** — Dots and rings for available destinations
- **Board auto-flip** — Optionally reverse orientation after each move
- **Coordinate labels** — Optional file/rank labels on board edges
- **Draw and resign** — Offer draw or resign with optional confirmation
- **Move confirmation** — Optional dialog before committing each move
- **Responsive layout** — Three breakpoints (mobile, tablet, desktop) with adaptive UI
- **Persistent settings** — Preferences saved across sessions (Android SharedPreferences, Windows JSON)
- **Settings page** — Configure board display, gameplay, and clock preferences
- **Developer mode** — Load test positions for debugging (set `PAWNPASSANT_DEV=true`)

---

## Installation

### Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### From source

```bash
# Clone the repository
git clone https://github.com/Sakth1/PawnPassant.git
cd PawnPassant

# Create and activate a virtual environment with uv (recommended)
uv venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
uv sync
```

If you prefer pip:

```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
source .venv/bin/activate  # macOS/Linux
pip install .
```

### Prebuilt binaries

Prebuilt binaries for Windows (portable ZIP and installer) and Android (APK) are available on the [Releases page](https://github.com/Sakth1/PawnPassant/releases).

---

## Usage

### Running the game

```bash
python src/main.py
```

Or with the Flet CLI:

```bash
flet run
```

### How to play

1. **Start a game** — Select a time control preset (or enter a custom one) and choose to play against the computer or another player.
2. **Move pieces** — Click a piece to select it, then click a destination square. Alternatively, drag and drop pieces.
3. **Promote a pawn** — When a pawn reaches the back rank, choose a piece from the promotion dialog.
4. **Use the clock** — The chess clock runs automatically. When your time runs out, the game ends.
5. **Draw or resign** — Use the buttons below the clock to offer a draw or resign.

### Developer mode

Set the `PAWNPASSANT_DEV` environment variable to `true` to expose a test position selector:

```bash
# Windows PowerShell
$env:PAWNPASSANT_DEV = "true"

# macOS / Linux
export PAWNPASSANT_DEV=true
```

---

## Configuration

Settings are persisted automatically. On Windows they are stored at `%APPDATA%\pawnpassant\settings.json`; on Android they use the platform SharedPreferences.

| Category | Setting | Options |
|----------|---------|---------|
| Board | Legal move hints | On / Off |
| Board | Tap feedback | On / Off |
| Board | Auto-flip board | On / Off |
| Board | Coordinate labels | On / Off |
| Board | Move animation speed | Off / Fast / Normal / Slow |
| Gameplay | Confirm moves | On / Off |
| Gameplay | Default promotion | Ask / Queen / Rook / Bishop / Knight |
| Clock | Critical time threshold | Seconds (default: 10) |
| Clock | Show milliseconds | On / Off |
| Clock | Confirm draw / resign | On / Off |

---

## Current Limitations

- **Draw agreement** — Only the current player can offer a draw; the opponent cannot accept or reject it yet.
- **AI opponent** — The Lc0 integration is scaffolded but the bot does not yet make moves automatically.
- **Local multiplayer** — The "Play someone" option is marked as a work in progress.
- **Online multiplayer** — The game state defines an `ONLINE` mode, but no networking implementation exists.
- **Captured piece drag feedback** — Placeholder hooks exist but the drag interaction is not functional.

---

## Roadmap

### Completed

- [x] Promotions
- [x] Time control (clock backend and UI)
- [x] Move animations
- [x] Captured pieces display
- [x] App icon
- [x] Drag-and-drop piece movement
- [x] APK signing and CI/CD pipeline
- [x] Responsive UI
- [x] Draw and resign options
- [x] Home page with time control presets
- [x] Chess game page
- [x] Settings page

### Planned

- [ ] **AI opponent** — Complete Lc0 integration so the computer plays moves with time-aware decision making
- [ ] **"Play someone" mode** — Local two-player (pass-and-play) mode
- [ ] **Draw agreement flow** — Allow the opposing player to accept or reject a draw offer
- [ ] **Online multiplayer** — Networked play against remote opponents
- [ ] **Captured piece interaction** — Drag feedback and interaction from the captured pieces panel

---

## Contributing

Contributions are welcome! To contribute:

1. **Fork** the repository.
2. **Create a branch** (`git checkout -b feature/my-feature`).
3. **Make your changes** and ensure tests pass (`pytest`).
4. **Commit** with a descriptive message.
5. **Push** to your fork and submit a pull request.

The project includes a comprehensive test suite with unit tests, property-based tests, and fuzz tests. Please add tests for new functionality.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
