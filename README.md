# claude-plugins

Xiangyu's plugin marketplace for [Claude Code](https://code.claude.com/docs/en/plugins).

## Install

In Claude Code:

```
/plugin marketplace add xiangyumou/claude-plugins
/plugin install research-figures@xiangyumou
```

Or from a shell:

```bash
claude plugin marketplace add xiangyumou/claude-plugins
claude plugin install research-figures@xiangyumou
```

Update later with `/plugin marketplace update xiangyumou`.

## Plugins

| Plugin | What it does | License |
|--------|--------------|---------|
| [research-figures](plugins/research-figures) | 科研画图. Skill `scientific-figure-making`: publication-ready matplotlib figures (venue-sized layouts, semantic palette, TrueType PDF export, automatic layout checks via `pubfig.py`) plus a [gallery](plugins/research-figures/skills/scientific-figure-making/gallery/README.md) of 25 reviewed figure scripts from published papers | CC BY-NC 4.0, adapted from [figures4papers](https://github.com/ChenLiu-1996/figures4papers) |

## Using a skill outside Claude Code

Each skill is a plain folder under `plugins/<plugin>/skills/<skill>/` (`SKILL.md` +
`references/` + `scripts/`). Other agents that read skill folders (e.g. Codex, via
`~/.codex/skills/`) can use it through a symlink:

```bash
ln -s ~/Projects/claude-plugins/plugins/research-figures/skills/scientific-figure-making ~/.codex/skills/scientific-figure-making
```

## Adding a skill

Plugins are grouped by purpose: one plugin per category (e.g. `research-figures`), holding any
number of skills. Skills must sit directly under `skills/<skill>/SKILL.md` (no deeper nesting).

1. Add the skill to the matching plugin as `plugins/<plugin>/skills/<skill>/SKILL.md`, or create a new
   category with `plugins/<plugin>/.claude-plugin/plugin.json`.
2. For a new plugin, add an entry to `.claude-plugin/marketplace.json`.
3. Run `claude plugin validate .` and bump `version` when changing an existing plugin.

## License

Each plugin carries its own license in its folder.
