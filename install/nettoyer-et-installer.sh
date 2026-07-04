#!/bin/bash
# ============================================================
#  Remise a zero + installation propre de glm
#
#  A EXECUTER SUR LA MACHINE OU glm EST CASSE.
#  Ce script :
#    1. Desinstalle glmcode de TOUS les Python trouves
#    2. Supprime tous les lanceurs glm residuels
#    3. Telecharge et reinstalle proprement glm depuis GitHub
#
#  USAGE :
#    curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/nettoyer-et-installer.sh | bash
# ============================================================

set -e

# Fonctions pour l'affichage
write_step() { echo -e "\e[36m==> $1\e[0m"; }
write_ok()   { echo -e "    \e[32m$1\e[0m"; }
write_warn() { echo -e "    \e[33m$1\e[0m"; }
write_err()  { echo -e "    \e[31m$1\e[0m"; }

# --- Configuration ---
REPO_URL="https://github.com/Marreouu/GLM-C0deur"
INSTALL_DIR="$HOME/.glm-code"
TEMP_DIR="/tmp/glm-install"

echo ""
echo "  Remise a zero de glm" -e "\e[35m"
echo "  Source : $REPO_URL" -e "\e[90m"
echo ""

# ------------------------------------------------------------ 
# 0. Recenser tous les interpreteurs Python de la machine
# ------------------------------------------------------------
write_step "Recherche des Python installes"
PYTHONS=()

# via "which python3" et "which python"
for cmd in "python3" "python"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHONS+=($(command -v "$cmd"))
    fi
done

# Uniquer les chemins
PYTHONS=($(printf "%s\n" "${PYTHONS[@]}" | sort -u))

if [ ${#PYTHONS[@]} -eq 0 ]; then
    write_err "Aucun Python trouve. Installez Python 3.11+ depuis https://python.org"
    exit 1
fi

for p in "${PYTHONS[@]}"; do
    write_ok "$p"
done

# ------------------------------------------------------------ 
# 1. Desinstaller glmcode de chaque Python
# ------------------------------------------------------------
write_step "Desinstallation de glmcode (tous les Python)"
for py in "${PYTHONS[@]}"; do
    $py -m pip uninstall glmcode -y >/dev/null 2>&1 || true
    $py -m pip uninstall glm -y >/dev/null 2>&1 || true
done
write_ok "Paquets glmcode/glm desinstalles"

# ------------------------------------------------------------ 
# 2. Supprimer tous les lanceurs glm residuels
# ------------------------------------------------------------
write_step "Suppression des lanceurs glm residuels"

# Trouver tous les dossiers dans le PATH
PATH_DIRS=()
IFS=':' read -ra ADDR <<< "$PATH"
for dir in "${ADDR[@]}"; do
    if [ -d "$dir" ]; then
        PATH_DIRS+=("$dir")
    fi
done

# Ajouter les dossiers de scripts Python
for py in "${PYTHONS[@]}"; do
    if [ -x "$py" ]; then
        SCRIPT_DIR=$($py -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>/dev/null || true)
        if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR" ]; then
            PATH_DIRS+=("$SCRIPT_DIR")
        fi
    fi
done

# Uniquer les dossiers
PATH_DIRS=($(printf "%s\n" "${PATH_DIRS[@]}" | sort -u))

REMOVED=0

for d in "${PATH_DIRS[@]}"; do
    # On ne supprime pas notre futur lanceur
    if [[ "$(realpath "$d" 2>/dev/null || echo "$d")" == "$(realpath "$INSTALL_DIR" 2>/dev/null || echo "$INSTALL_DIR")" ]]; then
        continue
    fi
    
    # Supprimer tous les fichiers glm.*
    for name in "glm" "glm.sh" "glm.py"; do
        f="$d/$name"
        if [ -f "$f" ]; then
            rm -f "$f" 2>/dev/null || true
            if [ ! -f "$f" ]; then
                ((REMOVED++))
                write_ok "supprime : $f"
            else
                write_warn "impossible de supprimer : $f"
            fi
        fi
    done
done

if [ $REMOVED -eq 0 ]; then
    write_ok "aucun lanceur residuel"
fi

# supprimer l'ancien dossier d'installation s'il existe
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
fi

echo ""
echo "  Nettoyage termine. Installation propre..." -e "\e[35m"
echo ""

# ------------------------------------------------------------ 
# 3. Telecharger le depot GitHub
# ------------------------------------------------------------
write_step "Telechargement du depot GitHub"
if ! command -v git >/dev/null 2>&1; then
    write_err "Git est requis mais non installe. Installez Git d'abord."
    exit 1
fi

# Supprimer les anciens telechargements
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR" 2>/dev/null || true
fi

# Telecharger avec git
git clone "$REPO_URL" "$TEMP_DIR"
if [ $? -ne 0 ]; then
    write_err "Echec du clonage du depot"
    write_err "Verifiez votre connexion Internet et l'URL du depot"
    exit 1
fi
write_ok "Depot telecharge avec succes"

# ------------------------------------------------------------ 
# 4. Choisir un Python 3.11+ pour l'installation propre
# ------------------------------------------------------------
write_step "Selection d'un Python 3.11+"
PYTHON_CMD=""
for py in "${PYTHONS[@]}"; do
    if [ -x "$py" ]; then
        VERSION=$($py --version 2>&1 | cut -d' ' -f2)
        MAJOR=$(echo $VERSION | cut -d'.' -f1)
        MINOR=$(echo $VERSION | cut -d'.' -f2)
        
        if [ "$MAJOR" -gt 3 ] || [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_CMD="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    write_err "Aucun Python 3.11+ trouve. Installez-le depuis https://python.org"
    exit 1
fi
write_ok "Python retenu : $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

# ------------------------------------------------------------ 
# 5. Installer les dependances
# ------------------------------------------------------------
write_step "Installation des dependances"
cd "$TEMP_DIR"
$PYTHON_CMD -m pip install --upgrade pip >/dev/null 2>&1
$PYTHON_CMD -m pip install -r "requirements.txt"
if [ $? -ne 0 ]; then
    write_err "Echec de l'installation des dependances"
    exit 1
fi
write_ok "Dependances installees"

# ------------------------------------------------------------ 
# 6. Deplacer vers le dossier d'installation final
# ------------------------------------------------------------
write_step "Installation finale"
mv "$TEMP_DIR" "$INSTALL_DIR"
write_ok "Installe dans : $INSTALL_DIR"

# ------------------------------------------------------------ 
# 7. Creer le lanceur glm unique
# ------------------------------------------------------------
write_step "Creation de la commande glm"
BIN_DIR="$INSTALL_DIR/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/glm" << 'EOF'
#!/bin/bash
# Lanceur glm
export PYTHONPATH="$(dirname "$(dirname "$(realpath "$0")")"):$PYTHONPATH"
exec python3 -m glmcode "$@"
EOF
chmod +x "$BIN_DIR/glm"
write_ok "Lanceur cree : $BIN_DIR/glm"

# ------------------------------------------------------------ 
# 8. Ajouter bin au PATH utilisateur (une seule fois)
# ------------------------------------------------------------
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

export PATH="$BIN_DIR:$PATH"

# ------------------------------------------------------------ 
# 9. Installer la config globale (~/.glmcode/config.toml)
# ------------------------------------------------------------
write_step "Installation de la configuration"
CFG_DIR="$HOME/.glmcode"
mkdir -p "$CFG_DIR"
CFG_DST="$CFG_DIR/config.toml"
CFG_SRC="$INSTALL_DIR/config.toml"

if [ ! -f "$CFG_SRC" ]; then
    CFG_SRC="$INSTALL_DIR/config.example.toml"
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

# ------------------------------------------------------------ 
# 10. Verification
# ------------------------------------------------------------
write_step "Verification"
if "$BIN_DIR/glm" --version >/dev/null 2>&1; then
    write_ok "glm operationnel"
else
    write_warn "Verification non aboutie dans cette session."
    write_warn "Redemarrez votre terminal puis tapez : glm --version"
fi

# Nettoyer les fichiers temporaires
write_step "Nettoyage"
rm -rf "$TEMP_DIR" 2>/dev/null || true

echo ""
echo "  Termine ! Une seule commande glm est maintenant installee." -e "\e[32m"
echo "  Redemarrez votre terminal et tapez : glm" -e "\e[32m"
echo "  Installe dans : $INSTALL_DIR" -e "\e[90m"
echo ""