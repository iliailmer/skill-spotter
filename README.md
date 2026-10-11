# skill-spotter

A Claude Code plugin. It notices when a prompt repeats earlier prompts from other
sessions and suggests a fix:

| Kind | What you get |
| --- | --- |
| `skill` | a drafted `SKILL.md` for a repeated multi-step procedure |
| `rule` | one line for your instructions file (`CLAUDE.md`) for a repeated correction |
| `hook` | an idea for a check a script could do automatically |
| `alias` | a shell alias or function for a repeated command |

## How it works

1. On each prompt, an async hook (`check`) updates a SQLite full-text index of past
   prompts (`~/.claude/projects/*/*.jsonl`) and looks for similar prompts in at least
   two other sessions. No match: stop. No model call. About 4% of prompts pass.
2. On a match, one `claude -p --model haiku` call decides the kind and drafts the
   content. About 4 s, in the background. It uses your normal Claude Code login.
3. At your next prompt a sync hook (`show`) prints the idea once as a message.
4. You choose: `skill-spotter accept <name>` or `skill-spotter dismiss <name>`.

Accepting never applies or commits anything:

- `skill`: writes `<skills dir>/<name>/SKILL.md`.
- `rule`: appends a line under `## Added by skill-spotter` in your instructions file.
- `hook`, `alias`: saves the text to `~/.cache/skill-spotter/accepted-ideas.md`.

## Install

In Claude Code:

    /plugin install skill-spotter --marketplace iliailmer/skill-spotter

To try it from a clone without installing:

    git clone https://github.com/iliailmer/skill-spotter && claude --plugin-dir ./skill-spotter

Put `bin/skill-spotter` on your PATH to run the commands below. Python 3.11+, no
dependencies.

## Commands

    skill-spotter list | accept <name> | dismiss <name> | status | replay

`replay` runs the gate over your history and prints how often it would fire.
`status` prints a short string you can show in a statusline.

## Where files go

If `chezmoi` is installed and its source tree has `dot_claude/`, accepted files go
into that tree. Otherwise they go to `~/.claude/`. Override with:

- `SKILL_SPOTTER_SKILLS_DIR`
- `SKILL_SPOTTER_RULES_FILE`
- `SKILL_SPOTTER_HOME` (state, default `~/.cache/skill-spotter`)
- `SKILL_SPOTTER_PROJECTS` (transcripts, default `~/.claude/projects`)

## Notes

- The model subprocess runs with `SKILL_SPOTTER_ACTIVE=1`, so its own hooks do nothing.
- A topic is suggested at most once per 7 days. Any error means no suggestion.
- Every model decision is appended to `decisions.jsonl` in the state folder. It
  contains your prompts. It is not in this repo. It is the training data for a
  later logistic-regression gate.
- The model reads your prompts and your instructions file (to avoid repeats). They go
  to Anthropic, as your prompts already do.
- `claude -p --bare` is not used: it ignores your login and needs an API key.

## Tests

    uv run pytest
