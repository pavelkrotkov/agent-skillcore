# Codex adapter

Skillfleet exposes the active runtime with managed links under
`~/.agents/skills/`. The location follows the current [Codex skills
documentation](https://developers.openai.com/codex/skills/). The adapter does
not install a second copy and does not claim that Codex has semantically loaded
the skill; `skill-doctor` verifies only filesystem links.
