# Installing Prerequisites — Python and Git

Before you can install and run College Compass, you need two free tools on your computer: **Python** and **Git**. If you already have them, skip to the relevant Quickstart.

---

## Do you already have them?

Open a terminal (Mac: **Terminal** app, Windows: **Command Prompt**) and run:

```bash
python --version
```

```bash
git --version
```

If both commands print a version number (e.g. `Python 3.11.4`, `git version 2.41.0`), you're ready — go straight to the Quickstart:

- [Quickstart — Free path (Ollama)](Quickstart-free.md)
- [Quickstart — Pro path (API key)](Quickstart-pro.md)

If either command says "not found" or "not recognized", follow the steps below.

---

## 1. Install Python

College Compass requires **Python 3.9 or higher**.

### macOS

macOS may have an old Python 2 pre-installed. Install the current version via the official installer:

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click **Download Python 3.x.x** (latest stable)
3. Open the downloaded `.pkg` file and follow the installer
4. Open a new Terminal window and verify:

```bash
python3 --version
```

### Windows

> ⚠️ **Critical:** During install, check **"Add Python to PATH"** on the first screen. If you miss this, Python won't be found from the command line.

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Click **Download Python 3.x.x**
3. Run the installer — **tick "Add Python to PATH"** before clicking Install Now
4. Open a **new** Command Prompt window and verify:

```bat
python --version
```

### Linux

Most Linux distributions include Python 3. Check first:

```bash
python3 --version
```

If not installed:

```bash
# Ubuntu / Debian
sudo apt update && sudo apt install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3
```

---

## 2. Install Git

Git is used to download the College Compass code from GitHub.

### macOS

```bash
brew install git
```

No Homebrew? Get it from [brew.sh](https://brew.sh/) or download Git directly from [git-scm.com/download/mac](https://git-scm.com/download/mac).

### Windows

1. Go to [git-scm.com/download/win](https://git-scm.com/download/win) — the download starts automatically
2. Run the installer — default options are fine for all steps
3. Open a **new** Command Prompt and verify:

```bat
git --version
```

> **Tip:** Git installs "Git Bash" on Windows — a Unix-style terminal. You can use either Git Bash or Command Prompt for all College Compass commands.

### Linux

```bash
# Ubuntu / Debian
sudo apt install git

# Fedora
sudo dnf install git
```

---

## 3. Verify both are installed

Open a **new** terminal window (important — existing windows won't see newly installed tools) and run:

```bash
python --version
git --version
```

Both should print version numbers. If one still says "not found":

- **Windows:** Make sure you opened a **new** Command Prompt after installing
- **Python on Windows:** Re-run the Python installer, choose "Modify", and tick "Add Python to PATH"
- **Mac:** Try `python3 --version` instead of `python`

---

## 4. Now install College Compass

Once Python and Git are confirmed, return to the Quickstart for your chosen path:

- [Quickstart — Free path (Ollama, no API key)](Quickstart-free.md)
- [Quickstart — Pro path (OpenAI or Anthropic API key)](Quickstart-pro.md)
