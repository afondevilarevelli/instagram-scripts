# Instagram Following Manager

A parallelized toolkit for managing your Instagram following. Extensible — add new scripts under `scripts/` and register a subparser in `main.py`.

## Scripts

| Command | Description |
|---|---|
| `unfollow-inactive` | Unfollow users who haven't posted in N months |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your Instagram credentials
```

## Usage

```bash
# Preview who would be unfollowed
python main.py unfollow-inactive --dry-run

# Unfollow users inactive for 12+ months
python main.py unfollow-inactive

# Custom period and parallelism
python main.py unfollow-inactive --months 6 --workers 8

# Also unfollow mutuals (default: only non-followers)
python main.py unfollow-inactive --no-only-non-followers
```

## Project Structure

```
├── main.py                     # Entry point with subcommand CLI
├── scripts/                    # One file per command
│   └── unfollow_inactive.py
├── utils/                      # Shared infrastructure
│   ├── config.py               # Env-based settings
│   └── instagram_client.py     # API wrapper with rate limiting
└── storage/                    # Session cache (gitignored)
```

## Adding a New Script

1. Create `scripts/my_command.py` with a `run(settings, **kwargs)` function
2. Add a subparser in `main.py` under the `subparsers` block
3. Call your script's `run()` in the command dispatch section
