#!/bin/bash
# ============================================================
#  Désinstallateur de glm (glmcode)
#
#  Ce script désinstalle complètement glm :
#    1. Désinstalle glmcode de TOUS les Python trouvés
#    2. Supprime tous les lanceurs glm résiduels
#    3. Supprime le dossier d'installation
#    4. Supprime la configuration
#
#  USAGE :
#    curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/uninstall.sh | bash
# ============================================================

set -e

# Fonctions pour l'affichage
write_step() { echo -e "\e[36m==> $1\e[0m"; }
write_ok()   { echo -e "    \e[32m$1\e[0m"; }
write_warn() { echo -e "    \e[33m$1\e[0m"; }
write_err()  { echo -e "    \e[31m$1\e[0m"; }

# --- Configuration ---
INSTALL_DIR="$HOME/.glm-code"
CONFIG_DIR="$HOME/.glmcode"

echo ""
echo "  Désinstallation de glm" -e "\e[35m"
echo ""

# ------------------------------------------------------------ 
# 1. Recenser tous les interpreteurs Python de la machine
# ------------------------------------------------------------
write_step "Recherche des Python installés"
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
    write_warn "Aucun Python trouvé. Aucune désinstallation de paquets nécessaire."
else
    for p in "${PYTHONS[@]}"; do
        write_ok "$p"
    fi
fi

# ------------------------------------------------------------ 
# 2. Désinstaller glmcode de chaque Python
# ------------------------------------------------------------
write_step "Désinstallation de glmcode (tous les Python)"
for py in "${PYTHONS[@]}"; do
    $py -m pip uninstall glmcode -y >/dev/null 2>&1 || true
    $py -m pip uninstall glm -y >/dev/null 2>&1 || true
done
write_ok "Paquets glmcode/glm désinstalllés"

# ------------------------------------------------------------ 
# 3. Supprimer tous les lanceurs glm résiduels
# ------------------------------------------------------------
write_step "Suppression des lanceurs glm résiduels"

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
    write_ok "aucun lanceur résiduel"
fi

# ------------------------------------------------------------ 
# 4. Supprimer le dossier d'installation
# ------------------------------------------------------------
write_step "Suppression du dossier d'installation"
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR" 2>/dev/null || true
    if [ ! -d "$INSTALL_DIR" ]; then
        write_ok "Dossier d'installation supprimé : $INSTALL_DIR"
    else
        write_warn "Impossible de supprimer le dossier : $INSTALL_DIR"
    fi
else
    write_ok "Aucun dossier d'installation trouvé"
fi

# ------------------------------------------------------------ 
# 5. Supprimer la configuration
# ------------------------------------------------------------
write_step "Suppression de la configuration"
if [ -d "$CONFIG_DIR" ]; then
    rm -rf "$CONFIG_DIR" 2>/dev/null || true
    if [ ! -d "$CONFIG_DIR" ]; then
        write_ok "Configuration supprimée : $CONFIG_DIR"
    else
        write_warn "Impossible de supprimer la configuration : $CONFIG_DIR"
    fi
else
    write_ok "Aucune configuration trouvée"
fi

# ------------------------------------------------------------ 
# 6. Vérifier si glm est encore accessible
# ------------------------------------------------------------ 
write_step "Vérification finale"
if command -v glm >/dev/null 2>&1; then
    write_warn "Attention : glm est encore accessible. Vérifiez votre PATH"
    write_warn "Redémarrez votre terminal pour être sûr"
else
    write_ok "glm a été complètement désinstallé"
fi

echo ""
echo "  Désinstallation terminée !" -e "\e[32m"
echo ""