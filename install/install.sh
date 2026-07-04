#!/bin/bash
# ============================================================
#  Installateur de glm (glmcode)
#
#  A executer par la personne qui recoit le code source :
#    1. Verifie Python 3.11+
#    2. Installe les dependances (requirements.txt)
#    3. Cree un lanceur "glm" et l'ajoute au PATH utilisateur
#       -> la commande "glm" devient utilisable depuis n'importe ou
#
#  IMPORTANT : ne pas deplacer / supprimer le dossier du projet
#  apres l'installation (le lanceur pointe vers ce dossier).
# ============================================================

set -e

# Fonctions pour l'affichage
write_step() { echo -e "\e[36m==> $1\e[0m"; }
write_ok()   { echo -e "    \e[32m$1\e[0m"; }
write_warn() { echo -e "    \e[33m$1\e[0m"; }
write_err()  { echo -e "    \e[31m$1\e[0m"; }

# --- Racine du projet (dossier parent de ce script) ---------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "  Installation de glm" -e "\e[35m"
echo "  Source : $PROJECT_ROOT" -e "\e[90m"
echo ""

# --- 1. Verifier Python -------------------------------------
write_step "Verification de Python"
PYTHON_CMD=""
for cmd in "python3" "python"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if $cmd --version >/dev/null 2>&1; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    write_err "Python introuvable. Installez Python 3.11+ depuis https://python.org"
    exit 1
fi

# Vérifier la version
VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
MAJOR=$(echo $VERSION | cut -d'.' -f1)
MINOR=$(echo $VERSION | cut -d'.' -f2)

if [ "$MAJOR" -lt 3 ] || [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; then
    write_err "Python 3.11+ requis (version detectee : $VERSION)"
    exit 1
fi

write_ok "Python $VERSION ($PYTHON_CMD)"

# --- 2. Installer les dependances ---------------------------
write_step "Installation des dependances (requirements.txt)"
$PYTHON_CMD -m pip install --upgrade pip >/dev/null 2>&1
$PYTHON_CMD -m pip install -r "$PROJECT_ROOT/requirements.txt"
if [ $? -ne 0 ]; then
    write_err "Echec de l'installation des dependances"
    exit 1
fi
write_ok "Dependances installees"

# --- 3. Creer le lanceur "glm" ------------------------------
write_step "Creation de la commande glm"
BIN_DIR="$PROJECT_ROOT/bin"
mkdir -p "$BIN_DIR"

# Lanceur .sh : ajoute la racine au PYTHONPATH puis lance le module glmcode
cat > "$BIN_DIR/glm" << 'EOF'
#!/bin/bash
# Lanceur glm
export PYTHONPATH="$(dirname "$(dirname "$(realpath "$0")")"):$PYTHONPATH"
exec python3 -m glmcode "$@"
EOF
chmod +x "$BIN_DIR/glm"
write_ok "Lanceur cree : $BIN_DIR/glm"

# --- 4. Ajouter le dossier bin au PATH utilisateur ----------
write_step "Ajout de glm au PATH"
SHELL_RC=""
if [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.profile" ]; then
    SHELL_RC="$HOME/.profile"
fi

if [ -n "$SHELL_RC" ]; then
    if grep -q "export PATH=\"$BIN_DIR:\$PATH\"" "$SHELL_RC" 2>/dev/null; then
        write_ok "Deja dans le PATH : $BIN_DIR"
    else
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
        write_ok "Ajoute au PATH : $BIN_DIR"
    fi
else
    write_warn "Aucun fichier de shell trouve. Ajoutez manuellement :"
    write_warn "export PATH=\"$BIN_DIR:\$PATH\""
fi

# Disponible aussi dans la session courante
export PATH="$BIN_DIR:$PATH"

# --- 4b. Installer la config globale (~/.glmcode/config.toml)
write_step "Installation de la configuration"
CFG_DIR="$HOME/.glmcode"
mkdir -p "$CFG_DIR"
CFG_DST="$CFG_DIR/config.toml"
CFG_SRC="$PROJECT_ROOT/config.toml"

if [ ! -f "$CFG_SRC" ]; then
    CFG_SRC="$PROJECT_ROOT/config.example.toml"
fi

if [ -f "$CFG_SRC" ]; then
    if [ -f "$CFG_DST" ]; then
        write_ok "Config deja presente : $CFG_DST (conservee)"
    else
        cp "$CFG_SRC" "$CFG_DST"
        write_ok "Config installee : $CFG_DST"
    fi
else
    write_warn "Aucun config.toml/config.example.toml a copier"
fi

# --- 5. Verification ----------------------------------------
write_step "Verification"
if "$BIN_DIR/glm" --version >/dev/null 2>&1; then
    write_ok "glm operationnel"
else
    write_warn "La verification n'a pas abouti dans cette session."
    write_warn "Redemarrez votre terminal puis tapez : glm --version"
fi

echo ""
echo "  Installation terminee !" -e "\e[32m"
echo "  Redemarrez votre terminal puis tapez : glm" -e "\e[32m"
echo "  (ne deplacez pas ce dossier, le lanceur pointe dessus)" -e "\e[90m"
echo ""