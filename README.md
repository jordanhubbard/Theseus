# ai-template

A project template that enforces consistent conventions, structured development workflows, and a distinctive documentation persona across all AI-assisted repositories.

Repositories cloned from this template automatically inherit rules and skills that guide AI coding assistants — no manual setup or repeated prompting required.

## Behavior Switches (`skills/config.yaml`)

This template now ships with behavior switches so downstream repositories can opt out of conventions they do not want. That includes the README backstory requirement.

Default switches:

```yaml
behavior_switches:
  provenance_story:
    enabled: true
    require_readme_section: true
    update_chronicle: true
  responsible_vibe_workflow:
    enabled: true
```

If a repository built from this template wants a more neutral documentation style, set:

```yaml
behavior_switches:
  provenance_story:
    enabled: false
```

## What It Does

**ai-template** solves the problem of repeating yourself to AI assistants. Instead of explaining your project conventions every session, this template encodes them once and applies them everywhere:

- **Project structure enforcement** — Required directories (`tests/`, `docs/`), Makefile targets (`make`, `make test`, `make start`, `make stop`, `make restart`, `make clean`), and minimum 70% test coverage.
- **Structured development workflows** — Integration with [responsible-vibe-mcp](https://github.com/mrsimpson/responsible-vibe-mcp) for phase-based development (planning, implementation, testing, review) instead of unstructured "vibe coding."
- **Configurable documentation persona** — The PROVENANCE skill can add a humorous serialized origin story (the programmer and Sir Reginald von Fluffington III), but this behavior is controlled by `skills/config.yaml` so downstream repositories can opt out.
- **Security and quality guardrails** — OWASP top-10 awareness, no over-engineering, no scope creep beyond what was requested.

## What's Included

| File / Directory | Purpose |
|-----------------|---------|
| [`CLAUDE.md`](CLAUDE.md) | Project conventions automatically loaded by Claude Code — directory structure, Makefile targets, test coverage, README requirements, code quality rules |
| [`skills/`](skills/) | Reusable AI prompt templates (see [Skills Index](skills/README.md)) |
| [`skills/config.yaml`](skills/config.yaml) | Behavior switches for optional conventions (for example, enabling/disabling PROVENANCE requirements) |
| [`skills/PROVENANCE.md`](skills/PROVENANCE.md) | The origin story skill — style guide, character notes, chronicle chain, and checklist for adding new chapters |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) | Repository issue templates for convention bugs and skill/convention requests |
| [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) | Pull request checklist for skills, conventions, and behavior switch changes |
| `.claude/skills/responsible-vibe/` | Structured development workflow skill for Claude Code |
| `.github/skills/responsible-vibe/` | Structured development workflow skill for GitHub Copilot |
| `.opencode/skills/responsible-vibe/` | Structured development workflow skill for OpenCode |

## Responsible Vibe MCP

The template includes the [responsible-vibe-mcp](https://github.com/mrsimpson/responsible-vibe-mcp) skill across multiple AI assistant platforms. This skill enforces structured development workflows — plan before you code, test what you build, review before you ship — rather than letting the AI jump straight into writing code without a plan.

The skill is installed for:
- **Claude Code** (`.claude/skills/`)
- **GitHub Copilot** (`.github/skills/`)
- **OpenCode** (`.opencode/skills/`)

You can disable expectations around this workflow for downstream repositories by setting `behavior_switches.responsible_vibe_workflow.enabled: false` in `skills/config.yaml`.

## Usage

1. Clone or use this repo as a GitHub template for a new project.
2. Set `skills/config.yaml` switches for your project's preferred conventions.
3. The `CLAUDE.md` will automatically guide AI assistants to follow project conventions.
4. Replace this `README.md` with a project-specific one.
5. If PROVENANCE switches are enabled, use the PROVENANCE skill to write your project's origin story chapter and chain it into the chronicle.

## The Documentation Persona (Optional)

Projects can include a section called "The Totally True and Not At All Embellished History of [Project Name]." Whether this is required depends on `skills/config.yaml`:

- If `behavior_switches.provenance_story.enabled: true` and `require_readme_section: true`, include it.
- If either switch is off, the section is optional and should not be enforced.

When enabled, the section has practical purpose:

- **Provenance tracking** — If a project has this section, an AI was meaningfully involved in its development. If it doesn't, the author worked alone.
- **Serialized narrative** — Each project is a numbered chapter in a continuing chronicle, with navigation links chaining them together across repositories.
- **Consistent voice** — Third-person limited, dry-humorous, mock-historical. The programmer announces things to his cat. The cat does not care.

See [`skills/PROVENANCE.md`](skills/PROVENANCE.md) for the full style guide, character notes, and checklist.

## License

BSD 2-Clause
