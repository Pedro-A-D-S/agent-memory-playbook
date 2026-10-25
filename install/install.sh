#!/usr/bin/env bash
# agent-memory-playbook installer (Linux, macOS, Git-Bash on Windows)
#
# Installs the full 5-layer memory skill set for every requested tool at once.
# The skills are interdependent - install them as a set, not individually.
#
# VERIFIED: hermes       -> <HERMES_HOME>/skills/memory   (hermes-agent docs)
# VERIFIED: claude-code  -> <CLAUDE_HOME>/skills          (claude code docs)
# VERIFIED: antigravity  -> <workspace>/.agent/skills + <workspace>/AGENTS.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$ROOT/skills"

MODE="copy"
DRY_RUN=0
TARGETS=()

usage() {
  cat <<'EOF'
Usage: install.sh [--target NAME]... [--symlink] [--dry-run]

  --target NAME  hermes | claude-code | antigravity | all   (repeatable, default: all)
  --symlink      Link skills instead of copying (needs Developer Mode on Windows)
  --dry-run      Print what would happen; touch nothing
  -h, --help     Show this help

Environment overrides:
  HERMES_HOME            default: $HOME/.hermes, else $HOME/AppData/Local/hermes
  CLAUDE_HOME            default: $HOME/.claude
  ANTIGRAVITY_WORKSPACE  default: current directory
EOF
}

log() { printf '%s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target)  [ $# -ge 2 ] || { log "error: --target needs a value"; exit 2; }
               TARGETS+=("$2"); shift 2 ;;
    --symlink) MODE="symlink"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)         log "error: unknown argument: $1"; usage; exit 2 ;;
  esac
done
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("all")

hermes_home() {
  if [ -n "${HERMES_HOME:-}" ]; then printf '%s' "$HERMES_HOME"
  elif [ -d "$HOME/.hermes" ]; then printf '%s' "$HOME/.hermes"
  else printf '%s' "$HOME/AppData/Local/hermes"; fi
}

expand_targets() {
  local want
  for want in "$@"; do
    case "$want" in
      all)         printf '%s\n' hermes claude-code antigravity ;;
      hermes|claude-code|antigravity) printf '%s\n' "$want" ;;
      *)           log "error: unknown target: $want"; exit 2 ;;
    esac
  done
}

skills_dir_for() {
  case "$1" in
    hermes)      printf '%s' "$(hermes_home)/skills/memory" ;;
    claude-code) printf '%s' "$(printf '%s' "${CLAUDE_HOME:-$HOME/.claude}")/skills" ;;
    antigravity) printf '%s' "${ANTIGRAVITY_WORKSPACE:-$PWD}/.agent/skills" ;;
  esac
}

install_skills() {
  local tool="$1" dest="$2" skill_dir name target backup
  log "== $tool -> $dest"
  if [ "$DRY_RUN" = 1 ]; then
    local n=0
    for skill_dir in "$SKILLS_SRC"/*/; do n=$((n + 1)); done
    log "   (dry-run) would install $n skills ($MODE)"
    return 0
  fi
  mkdir -p "$dest"
  for skill_dir in "$SKILLS_SRC"/*/; do
    name="$(basename "$skill_dir")"
    target="$dest/$name"
    if [ -e "$target" ] || [ -L "$target" ]; then
      backup="$target.bak-$(date +%Y%m%d%H%M%S)"
      log "   backup: $name -> $(basename "$backup")"
      mv "$target" "$backup"
    fi
    if [ "$MODE" = "symlink" ]; then
      ln -s "$skill_dir" "$target"
    else
      cp -R "$skill_dir" "$target"
    fi
    log "   installed $name"
  done
}

write_agents_md() {
  local workspace="$1"
  local target="$workspace/AGENTS.md"
  local skill_dir name
  if [ "$DRY_RUN" = 1 ]; then
    log "   (dry-run) would write $target"
    return 0
  fi
  {
    printf '# Agent Memory - 5-Layer Playbook\n\n'
    printf 'This workspace has persistent agent memory installed.\n\n'
    printf 'Before any task: query episodic memory, load semantic facts, check for a procedural skill.\n'
    printf 'After any task: save the outcome, extract new facts, propose a skill after 3 successes.\n\n'
    printf '## Skills\n\n'
    for skill_dir in "$SKILLS_SRC"/*/; do
      name="$(basename "$skill_dir")"
      printf -- '- `%s` - %s\n' "$name" "$(grep -m1 '^description:' "$skill_dir/SKILL.md" | sed 's/^description:[[:space:]]*//')"
    done
    printf '\n## Savings audit\n\n'
    printf '```bash\npython skills/memory-savings-check/scripts/savings_check.py --memory-dir ./memory --format table\n```\n'
  } > "$target"
  log "   wrote $target"
}

mapfile -t SELECTED < <(expand_targets "${TARGETS[@]}")
log "agent-memory-playbook installer"
log "  source : $SKILLS_SRC"
log "  mode   : $MODE"
log "  targets: ${SELECTED[*]}"
log ""

for tool in "${SELECTED[@]}"; do
  install_skills "$tool" "$(skills_dir_for "$tool")"
  if [ "$tool" = "antigravity" ]; then
    write_agents_md "${ANTIGRAVITY_WORKSPACE:-$PWD}"
  fi
done

log ""
if [ "$DRY_RUN" = 1 ]; then
  log "Dry run complete. Nothing was written."
else
  log "Done. Restart the target tool so it re-scans its skills directory."
fi
