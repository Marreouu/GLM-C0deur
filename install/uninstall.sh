#!/usr/bin/env bash
#
# Desinstallation de GLM Code sur Linux et macOS.
#
# Retire le paquet, la ligne ajoutee au PATH et, avec --purge, la
# configuration et les sessions enregistrees.
#
# Usage :
#     ./install/uninstall.sh [--purge] [--quiet]
#
set -euo pipefail

LOG_FILE="${TMPDIR:-/tmp}/glm-uninstall.log"
PURGE=0
QUIET=0

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_RESET=$'\033[0m'; C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'; C_DIM=$'\033[90m'
else
    C_RESET=""; C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_DIM=""
fi

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >>"$LOG_FILE"; }
say() { log "$1"; [ "$QUIET" -eq 1 ] || printf '%s%s%s\n' "${2:-}" "$1" "$C_RESET"; }
say_step() { say "==> $1" "$C_CYAN"; }
say_ok()   { say "    OK  $1" "$C_GREEN"; }
say_warn() { log "WARN $1"; printf '%s    !   %s%s\n' "$C_YELLOW" "$1" "$C_RESET" >&2; }

while [ $# -gt 0 ]; do
    case "$1" in
        --purge) PURGE=1; shift ;;
        --quiet) QUIET=1; shift ;;
        -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) say_warn "option inconnue : $1"; exit 1 ;;
    esac
done

: >"$LOG_FILE"
say ""
say "  GLM Code - desinstallation"
say ""

# --- 1. Paquet ---------------------------------------------------------------

PYTHON=""
IN_VENV=0

# Un venv actif prime : sinon on desinstallerait le paquet global alors que
# l'utilisateur visait son environnement virtuel.
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
    IN_VENV=1
    say_ok "environnement virtuel actif : ${VIRTUAL_ENV}"
fi
[ -n "$PYTHON" ] || for candidate in python3 python; do
    command -v "$candidate" >/dev/null 2>&1 && { PYTHON="$candidate"; break; }
done

if [ -z "$PYTHON" ]; then
    say_warn "Python introuvable : le paquet ne peut pas etre desinstalle par pip"
else
    say_step "Suppression du paquet"
    if "$PYTHON" -m pip uninstall -y glmcode >>"$LOG_FILE" 2>&1; then
        say_ok "paquet supprime"
    else
        say_warn "pip n'a rien supprime (deja absent ?)"
    fi
fi

# --- 2. PATH -----------------------------------------------------------------

say_step "Nettoyage du PATH"
CLEANED=0
if [ "$IN_VENV" -eq 1 ]; then
    say_ok "venv : fichiers de shell inchanges"
    CLEANED=1
fi
[ "$IN_VENV" -eq 1 ] || 
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    [ -f "$rc" ] || continue
    grep -qF "# GLM Code" "$rc" || continue
    # Retire la ligne marquee, en gardant une sauvegarde horodatee.
    cp "$rc" "$rc.glm-backup-$(date '+%Y%m%d%H%M%S')"
    grep -vF "# GLM Code" "$rc" >"$rc.tmp" && mv "$rc.tmp" "$rc"
    say_ok "ligne retiree de $rc"
    CLEANED=1
done
[ "$CLEANED" -eq 1 ] || say_ok "aucune ligne a retirer"

# --- 3. Lanceurs residuels ---------------------------------------------------

say_step "Recherche de lanceurs residuels"
FOUND=0
if [ -n "$PYTHON" ]; then
    SCRIPTS_DIR="$("$PYTHON" -c 'import sysconfig; print(sysconfig.get_path("scripts", "posix_user"))' 2>/dev/null || true)"
else
    SCRIPTS_DIR="$HOME/.local/bin"
fi
for dir in "$SCRIPTS_DIR" "$HOME/.local/bin" /usr/local/bin; do
    [ -n "$dir" ] && [ -e "$dir/glm" ] || continue
    if rm -f "$dir/glm" 2>/dev/null; then
        say_ok "supprime : $dir/glm"
        FOUND=1
    else
        say_warn "droits insuffisants pour $dir/glm (essaie avec sudo)"
    fi
done
[ "$FOUND" -eq 1 ] || say_ok "aucun lanceur residuel"

# --- 4. Configuration --------------------------------------------------------

CONFIG_DIR="$HOME/.glmcode"
if [ "$PURGE" -eq 1 ]; then
    say_step "Suppression de la configuration"
    if [ -d "$CONFIG_DIR" ]; then
        rm -rf "$CONFIG_DIR"
        say_ok "supprime : $CONFIG_DIR"
    else
        say_ok "rien a supprimer"
    fi
elif [ -d "$CONFIG_DIR" ]; then
    say_warn "configuration conservee : $CONFIG_DIR (relance avec --purge pour l'effacer)"
fi

say ""
say "  Desinstallation terminee." "$C_GREEN"
say "  Ouvre un nouveau terminal pour que le PATH soit rafraichi." "$C_DIM"
say ""
