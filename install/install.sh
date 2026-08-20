#!/usr/bin/env bash
#
# Installation de GLM Code sur Linux et macOS.
#
# Installe le paquet avec pip, puis ajoute le dossier des scripts Python au
# PATH du shell pour que la commande `glm` soit disponible partout.
#
# Usage :
#     ./install/install.sh [--quiet] [--no-path] [--source CHEMIN]
#
set -euo pipefail

LOG_FILE="${TMPDIR:-/tmp}/glm-install.log"
QUIET=0
NO_PATH=0
SOURCE=""

# --- Journalisation et affichage --------------------------------------------

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_RESET=$'\033[0m'; C_CYAN=$'\033[36m'; C_GREEN=$'\033[32m'
    C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_DIM=$'\033[90m'
else
    C_RESET=""; C_CYAN=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_DIM=""
fi

log() { printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${2:-INFO}" "$1" >>"$LOG_FILE"; }
say() { log "$1"; [ "$QUIET" -eq 1 ] || printf '%s%s%s\n' "${2:-}" "$1" "$C_RESET"; }

say_step() { say "==> $1" "$C_CYAN"; }
say_ok()   { say "    OK  $1" "$C_GREEN"; }
say_warn() { log "$1" WARN; printf '%s    !   %s%s\n' "$C_YELLOW" "$1" "$C_RESET" >&2; }

abort() {
    log "$1" ERROR
    printf '%s    X   %s%s\n' "$C_RED" "$1" "$C_RESET" >&2
    [ $# -gt 1 ] && printf '%s        %s%s\n' "$C_YELLOW" "$2" "$C_RESET" >&2
    printf '\n%sJournal complet : %s%s\n' "$C_DIM" "$LOG_FILE" "$C_RESET" >&2
    exit 1
}

# --- Options ----------------------------------------------------------------

while [ $# -gt 0 ]; do
    case "$1" in
        --quiet)   QUIET=1; shift ;;
        --no-path) NO_PATH=1; shift ;;
        --source)  SOURCE="${2:-}"; shift 2 ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) abort "option inconnue : $1" "Voir $0 --help" ;;
    esac
done

: >"$LOG_FILE"

say ""
say "  GLM Code - installation"
say "  -----------------------" "$C_DIM"
say ""

# --- 1. Environnement -------------------------------------------------------

say_step "Verification de l'environnement"
log "uname   : $(uname -a)"

case "$(uname -s)" in
    Linux)
        DISTRO="Linux"
        if [ -r /etc/os-release ]; then
            # shellcheck disable=SC1091
            DISTRO="$(. /etc/os-release && printf '%s %s' "${NAME:-Linux}" "${VERSION_ID:-}")"
        fi
        say_ok "$DISTRO" ;;
    Darwin) say_ok "macOS $(sw_vers -productVersion 2>/dev/null || echo '')" ;;
    *) say_warn "systeme non teste : $(uname -s)" ;;
esac

# --- 2. Python --------------------------------------------------------------

say_step "Recherche de Python 3.11 ou plus recent"

PYTHON=""
IN_VENV=0

# Un environnement virtuel actif prime : `pip install --user` y est refuse, et
# l'utilisateur attend une installation dans son venv.
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
    IN_VENV=1
    say_ok "environnement virtuel actif : ${VIRTUAL_ENV} (Python $("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])'))"
fi

[ -n "$PYTHON" ] || for candidate in python3.14 python3.13 python3.12 python3.11 python3 python; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || continue
    log "candidat : $candidate -> $version"
    major="${version%%.*}"
    minor="${version##*.}"
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
        PYTHON="$candidate"
        say_ok "Python $version ($(command -v "$candidate"))"
        break
    fi
done

[ -n "$PYTHON" ] || abort "aucun Python 3.11+ trouve." \
    "Installe-le, par exemple : sudo apt install python3 python3-pip"

if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    say_warn "pip absent, tentative via ensurepip"
    "$PYTHON" -m ensurepip --upgrade >>"$LOG_FILE" 2>&1 \
        || abort "impossible d'installer pip." "Essaie : sudo apt install python3-pip"
fi
say_ok "pip disponible"

# --- 3. Sources -------------------------------------------------------------

say_step "Localisation des sources"

if [ -z "$SOURCE" ]; then
    # Ce script vit dans install/, le depot est le dossier parent.
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SOURCE="$(dirname "$SCRIPT_DIR")"
fi

DOWNLOADED=0
if [ ! -f "$SOURCE/pyproject.toml" ]; then
    # Execution hors du depot (par exemple via `curl ... | bash`) : on clone.
    say_warn "sources introuvables dans $SOURCE"
    REPO="https://github.com/Marreouu/GLM-C0deur.git"
    SOURCE="${HOME}/.glmcode/src"
    say "    telechargement depuis $REPO"

    command -v git >/dev/null 2>&1 \
        || abort "git est introuvable et les sources ne sont pas locales." \
                 "Installe git, ou clone le depot puis relance install/install.sh"

    rm -rf "$SOURCE"
    mkdir -p "$(dirname "$SOURCE")"
    git clone --depth 1 "$REPO" "$SOURCE" >>"$LOG_FILE" 2>&1 \
        || abort "le clone a echoue (depot prive ou reseau indisponible)." \
                 "Clone le depot manuellement, puis relance install/install.sh"
    DOWNLOADED=1
fi
say_ok "sources : $SOURCE"

# --- 4. Installation --------------------------------------------------------

say_step "Installation du paquet"

PIP_ARGS="--upgrade"
[ "$IN_VENV" -eq 1 ] || PIP_ARGS="$PIP_ARGS --user"   # refuse a l'interieur d'un venv
[ "$DOWNLOADED" -eq 1 ] || PIP_ARGS="$PIP_ARGS --editable"

# Les distributions recentes protegent l'environnement systeme (PEP 668).
if ! "$PYTHON" -m pip install $PIP_ARGS "$SOURCE" >>"$LOG_FILE" 2>&1; then
    if grep -q 'externally-managed-environment' "$LOG_FILE"; then
        say_warn "environnement Python gere par la distribution, nouvelle tentative"
        "$PYTHON" -m pip install $PIP_ARGS --break-system-packages "$SOURCE" >>"$LOG_FILE" 2>&1 \
            || abort "l'installation pip a echoue." "Details dans $LOG_FILE"
    else
        abort "l'installation pip a echoue." "Details dans $LOG_FILE"
    fi
fi
say_ok "paquet installe"

# --- 5. PATH ----------------------------------------------------------------

if [ "$IN_VENV" -eq 1 ]; then
    SCRIPTS_DIR="$("$PYTHON" -c 'import sysconfig; print(sysconfig.get_path("scripts"))')"
else
    SCRIPTS_DIR="$("$PYTHON" -c 'import sysconfig; print(sysconfig.get_path("scripts", "posix_user"))')"
fi
log "dossier des scripts : $SCRIPTS_DIR"

[ -x "$SCRIPTS_DIR/glm" ] || say_warn "glm absent de $SCRIPTS_DIR"

if [ "$NO_PATH" -eq 1 ]; then
    say_step "PATH inchange (--no-path)"
    say "    ajoute ce dossier toi-meme : $SCRIPTS_DIR"
else
    say_step "Configuration du PATH"
    case ":${PATH}:" in
        *":${SCRIPTS_DIR}:"*)
            say_ok "deja present dans le PATH" ;;
        *)
            # On ecrit dans le fichier du shell courant, plus ~/.profile pour
            # les shells de connexion.
            RC_FILES=""
            case "$(basename "${SHELL:-/bin/bash}")" in
                zsh)  RC_FILES="$HOME/.zshrc" ;;
                bash) RC_FILES="$HOME/.bashrc" ;;
                *)    RC_FILES="$HOME/.profile" ;;
            esac
            [ "$RC_FILES" = "$HOME/.profile" ] || RC_FILES="$RC_FILES $HOME/.profile"

            LINE="export PATH=\"\$PATH:$SCRIPTS_DIR\"  # GLM Code"
            for rc in $RC_FILES; do
                touch "$rc"
                if grep -qF "# GLM Code" "$rc"; then
                    say_ok "deja configure dans $rc"
                else
                    printf '\n%s\n' "$LINE" >>"$rc"
                    say_ok "ajoute au PATH dans $rc"
                fi
            done
            say_warn "lance 'source $HOME/.profile' ou ouvre un nouveau terminal"
            export PATH="$PATH:$SCRIPTS_DIR" ;;
    esac
fi

# --- 6. Verification --------------------------------------------------------

say_step "Verification"
if [ -x "$SCRIPTS_DIR/glm" ]; then
    VERSION_OUT="$("$SCRIPTS_DIR/glm" --version 2>&1 || true)"
    log "glm --version -> $VERSION_OUT"
    say_ok "$VERSION_OUT"
else
    say_warn "commande glm introuvable, essaie : $PYTHON -m glmcode"
fi

say ""
say "  Installation terminee." "$C_GREEN"
say ""
say "  Etapes suivantes :"
say "    1. copie config.example.toml vers config.toml" "$C_DIM"
say "    2. renseigne ta cle API Z.ai dans [zai].api_key" "$C_DIM"
say "    3. lance : glm" "$C_DIM"
say ""
say "  Journal : $LOG_FILE" "$C_DIM"
say ""
