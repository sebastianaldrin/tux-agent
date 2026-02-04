# TuxAgent

A Linux desktop AI assistant. Ask questions, attach screenshots, get help with your system.

> "I know what I want to do, just not how to do it on Linux" — TuxAgent helps with that.

**Status:** Early beta. Tested on Ubuntu 22.04 + GNOME. Should work on other distros but not verified yet. Bug reports welcome.

## What it does

- **Screenshot analysis** - Take a screenshot, ask "what is this?" or "how do I close this?"
- **System tools** - 50+ built-in tools for files, network, processes, etc.
- **Native Linux app** - GTK4 interface, runs as a background service, integrates with Nautilus

## Install

```bash
git clone https://github.com/sebastianaldrin/tux-agent.git
cd tux-agent
./scripts/install.sh
```

The script auto-detects your distro:
- **Ubuntu** - Tested ✓
- **Linux Mint** - Should work (Ubuntu-based)
- **Pop!_OS** - Should work (Ubuntu-based)
- **Zorin OS** - Should work (Ubuntu-based)
- **Fedora** - Should work, not tested
- **Manjaro** - Should work, not tested
- **Arch** - Should work, not tested

Not tested on other distros yet. If you try it, let us know!

### Setup your API key

TuxAgent needs an LLM API key to work. Get one from [Together.ai](https://api.together.xyz/signin) (free tier available) or use OpenAI.

1. Run `tuxagent-overlay`
2. Click the gear icon (Settings)
3. Enter your API key
4. Click "Test Connection"

## Usage

**GUI:** Press `Super+Shift+A` or run `tuxagent-overlay`

**CLI:**
```bash
tux ask "How do I install Chrome?"
tux ask --screenshot "What app is this?"
tux interactive
```

**Nautilus:** Right-click any file → "Ask TuxAgent about this file"

## How it works

```
┌──────────────────────────────────────────────────────────┐
│  Kimi K2.5 / GPT-5.2 (vision + tools)                    │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  TuxAgent Daemon (D-Bus service)                         │
│  - Screenshot capture                                    │
│  - Tool execution (files, network, system info, etc.)    │
└──────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    GTK4 Overlay      CLI (tux)     Nautilus Extension
```

## Security

TuxAgent runs with your user permissions. To help you, it can:

- **Execute shell commands** - with safety checks for obviously dangerous operations
- **Read/write files** - anywhere you have access
- **Network operations** - ping, DNS lookups, port scanning

**What this means:**
- TuxAgent can't do anything you can't already do in a terminal
- It can't access root/system files unless you run it as root (don't do that)
- Dangerous commands like `rm -rf /` are blocked, but the AI makes decisions about what to run

**Best practices:**
- Don't run as root
- Review the conversation if you're unsure what it did
- Be cautious with files from untrusted sources (they could try to manipulate the AI)

## Uninstall

```bash
./scripts/uninstall.sh
```

## Config

- Preferences: `~/.config/tuxagent/preferences.json`
- Conversations: `~/.local/share/tuxagent/conversations/`

## License

MIT
