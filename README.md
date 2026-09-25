# claude-plugins

Xiangyu's plugin marketplace for [Claude Code](https://code.claude.com/docs/en/plugins).

## Install

In Claude Code:

```
/plugin marketplace add xiangyumou/claude-plugins
/plugin install scientific-figure-making@xiangyumou
```

Or from a shell:

```bash
claude plugin marketplace add xiangyumou/claude-plugins
claude plugin install scientific-figure-making@xiangyumou
```

Update later with `/plugin marketplace update xiangyumou`.

## Plugins

| Plugin | What it does | License |
|--------|--------------|---------|
| [scientific-figure-making](plugins/scientific-figure-making) | Publication-ready matplotlib figures: venue-sized layouts, semantic palette, TrueType PDF export, automatic layout checks (`pubfig.py` helper + recipes) | CC BY-NC 4.0, adapted from [figures4papers](https://github.com/ChenLiu-1996/figures4papers) |

## Using a skill outside Claude Code

Each skill is a plain folder under `plugins/<plugin>/skills/<skill>/` (`SKILL.md` +
`references/` + `scripts/`). Other agents that read skill folders (e.g. Codex, via
`~/.codex/skills/`) can use it through a symlink:

```bash
ln -s ~/Projects/claude-plugins/plugins/scientific-figure-making/skills/scientific-figure-making ~/.codex/skills/scientific-figure-making
```

## Adding a plugin

1. Create `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/skills/<skill>/SKILL.md`.
2. Add an entry to `.claude-plugin/marketplace.json`.
3. Run `claude plugin validate .` and bump `version` when changing an existing plugin.

## License

Each plugin carries its own license in its folder.
