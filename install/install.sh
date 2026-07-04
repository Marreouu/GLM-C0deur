#!/bin/bash
# ============================================================
#  Installateur avancé de GLM Codeur
#
#  Ce script télécharge et installe directement GLM depuis GitHub :
#    1. Détection automatique de l'environnement
#    2. Vérification des dépendances système
#    3. Installation robuste avec gestion des erreurs
#    4. Configuration post-installation
#
#  USAGE :
#    curl -sSL https://raw.githubusercontent.com/Marreouu/GLM-C0deur/main/install/install.sh | bash
# ============================================================

set -e

# --- Configuration ---
REPO_URL="https://github.com/Marreouu/GLM-C0deur"
INSTALL_DIR="$HOME/.glm-code"
TEMP_DIR="/tmp/glm-install-$(date +%s)"
LOG_FILE="/tmp/glm-install.log"
BACKUP_DIR="/tmp/glm-backup-$(date +%s)"

# --- Couleurs et affichage ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

write_step() { echo -e "${CYAN}==> $1${NC}"; }
write_ok()   { echo -e "    ${GREEN}$1${NC}"; }
write_warn() { echo -e "    ${YELLOW}$1${NC}"; }
write_err()  { echo -e "    ${RED}$1${NC}"; }
write_log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

# --- Barre de progression ---
show_progress() {
    local duration=${1:-10}
    local width=40
    local completed=0
    local percent=0
    
    printf "\r["
    for ((i=0; i<width; i++)); do
        if [ $i -lt $((percent * width / 100)) ]; then
            printf "="
        else
            printf " "
        fi
    done
    printf "] %d%%" $percent
    
    while [ $completed -lt $duration ]; do
        sleep 0.1
        completed=$((completed + 1))
        percent=$((completed * 100 / duration))
        
        printf "\r["
        for ((i=0; i<width; i++)); do
            if [ $i -lt $((percent * width / 100)) ]; then
                printf "="
            else
                printf " "
            fi
        done
        printf "] %d%%" $percent
    done
    echo
}

# --- Détection de l'environnement ---
detect_os() {
    write_step "Détection de l'environnement"
    
    # Détection du système d'exploitation
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
        if command -v lsb_release >/dev/null 2>&1; then
            DISTRO=$(lsb_release -d | cut -f2)
        elif [ -f /etc/os-release ]; then
            DISTRO=$(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)
        else
            DISTRO="Linux (distribution inconnue)"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
        DISTRO=$(sw_vers -productVersion 2>/dev/null || echo "macOS (version inconnue)")
    else
        OS=$(uname)
        DISTRO="Système non supporté"
    fi
    
    write_ok "Système détecté : $OS - $DISTRO"
    write_log "OS: $OS - $DISTRO"
    
    # Vérification de la version de bash
    BASH_VERSION=$(bash --version | head -n1 | cut -d' ' -f4 | cut -d'(' -f1)
    MAJOR=$(echo "$BASH_VERSION" | cut -d'.' -f1)
    MINOR=$(echo "$BASH_VERSION" | cut -d'.' -f2)
    
    if [ "$MAJOR" -lt 4 ] || ([ "$MAJOR" -eq 4 ] && [ "$MINOR" -lt 0 ]); then
        write_err "Bash 4.0+ requis (version détectée : $BASH_VERSION)"
        exit 1
    fi
    write_ok "Bash $BASH_VERSION"
    write_log "Bash version: $BASH_VERSION"
}

# --- Vérification de la connectivité Internet ---
check_internet() {
    write_step "Vérification de la connectivité Internet"
    
    if ! ping -c 1 -W 5 github.com >/dev/null 2>&1; then
        write_err "Pas de connexion Internet détectée"
        write_err "Veuillez vérifier votre connexion et réessayer"
        exit 1
    fi
    
    write_ok "Connexion Internet active"
    write_log "Internet connectivity: OK"
}

# --- Vérification des paquets système ---
check_system_packages() {
    write_step "Vérification des paquets système"
    
    local required_packages=("git" "curl" "wget")
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! command -v "$package" >/dev/null 2>&1; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        write_warn "Paquets manquants : ${missing_packages[*]}"
        
        if [[ "$OS" == "Linux" ]]; then
            write_warn "Installation recommandée :"
            if [[ "$DISTRO" == *"Ubuntu"* ]] || [[ "$DISTRO" == *"Debian"* ]]; then
                write_warn "sudo apt update && sudo apt install ${missing_packages[*]}"
            elif [[ "$DISTRO" == *"CentOS"* ]] || [[ "$DISTRO" == *"Red Hat"* ]]; then
                write_warn "sudo yum install ${missing_packages[*]}"
            fi
            write_err "Veuillez installer les paquets manquants et réessayer"
            exit 1
        else
            write_err "Veuillez installer les paquets manquants et réessayer"
            exit 1
        fi
    else
        write_ok "Tous les paquets système requis sont présents"
    fi
    
    write_log "System packages check completed"
}

# --- Téléchargement du dépôt GitHub ---
download_repo() {
    write_step "Téléchargement du dépôt GitHub"
    
    # Nettoyage des anciens téléchargements
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR" 2>/dev/null || true
    fi
    
    # Sauvegarde de l'installation existante si elle existe
    if [ -d "$INSTALL_DIR" ]; then
        write_warn "Installation existante détectée, sauvegarde en cours..."
        mkdir -p "$BACKUP_DIR"
        mv "$INSTALL_DIR" "$BACKUP_DIR/"
        write_ok "Installation sauvegardée dans : $BACKUP_DIR"
        write_log "Backup created: $BACKUP_DIR"
    fi
    
    # Téléchargement avec git
    write_ok "Clonage du dépôt..."
    if ! git clone --depth=1 "$REPO_URL" "$TEMP_DIR" 2>&1 | while read line; do
        echo "    $line"
        write_log "Git clone: $line"
    done; then
        write_err "Échec du clonage du dépôt"
        write_err "Vérifiez votre connexion Internet et l'URL du dépôt"
        exit 1
    fi
    
    write_ok "Dépôt téléchargé avec succès"
    write_log "Repository downloaded successfully"
}

# --- Détection et vérification de Python ---
detect_python() {
    write_step "Détection de Python"
    
    local python_commands=("python3" "python")
    local available_pythons=()
    
    # Recherche des installations Python disponibles
    for cmd in "${python_commands[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            if $cmd --version >/dev/null 2>&1; then
                available_pythons+=("$cmd")
            fi
        fi
    done
    
    if [ ${#available_pythons[@]} -eq 0 ]; then
        write_err "Python introuvable. Installez Python 3.11+ depuis https://python.org"
        exit 1
    fi
    
    # Si plusieurs versions disponibles, proposer un choix
    if [ ${#available_pythons[@]} -gt 1 ]; then
        write_warn "Plusieurs installations de Python détectées :"
        for i in "${!available_pythons[@]}"; do
            version=$(${available_pythons[$i]} --version 2>&1)
            echo "    $((i+1)). $version (${{available_pythons[$i]}})"
        done
        echo -n "    Choisissez une version (1-${#available_pythons[@]}): "
        read -r choice
        
        if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#available_pythons[@]} ]; then
            write_err "Choix invalide"
            exit 1
        fi
        
        PYTHON_CMD="${available_pythons[$((choice-1))]}"
    else
        PYTHON_CMD="${available_pythons[0]}"
    fi
    
    # Vérification de la version
    VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    MAJOR=$(echo "$VERSION" | cut -d'.' -f1)
    MINOR=$(echo "$VERSION" | cut -d'.' -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
        write_err "Python 3.11+ requis (version détectée : $VERSION)"
        exit 1
    fi
    
    write_ok "Python $VERSION ($PYTHON_CMD) sélectionné"
    write_log "Python selected: $PYTHON_CMD $VERSION"
}

# --- Installation des dépendances ---
install_dependencies() {
    write_step "Installation des dépendances"
    
    cd "$TEMP_DIR"
    
    # Mise à jour de pip
    write_ok "Mise à jour de pip..."
    if ! $PYTHON_CMD -m pip install --upgrade pip >/dev/null 2>&1; then
        write_warn "Échec de la mise à jour de pip, tentative avec --user"
        if ! $PYTHON_CMD -m pip install --upgrade pip --user >/dev/null 2>&1; then
            write_err "Échec de la mise à jour de pip"
            exit 1
        fi
    fi
    
    # Installation des dépendances
    write_ok "Installation des dépendances depuis requirements.txt..."
    if [ -f "requirements.txt" ]; then
        if ! $PYTHON_CMD -m pip install -r "requirements.txt" 2>&1 | while read line; do
            echo "    $line"
            write_log "Pip install: $line"
        done; then
            write_err "Échec de l'installation des dépendances"
            exit 1
        fi
        write_ok "Dépendances installées"
    else
        write_warn "Fichier requirements.txt non trouvé"
    fi
    
    write_log "Dependencies installed"
}

# --- Installation finale ---
install_glm() {
    write_step "Installation finale"
    
    # Déplacement vers le dossier d'installation final
    write_ok "Déplacement vers $INSTALL_DIR..."
    if ! mv "$TEMP_DIR" "$INSTALL_DIR"; then
        write_err "Échec du déplacement vers $INSTALL_DIR"
        exit 1
    fi
    
    write_ok "Installé dans : $INSTALL_DIR"
    write_log "Installation directory: $INSTALL_DIR"
}

# --- Création du lanceur ---
create_launcher() {
    write_step "Création de la commande glm"
    
    BIN_DIR="$INSTALL_DIR/bin"
    mkdir -p "$BIN_DIR"
    
    # Lanceur .sh : ajoute la racine au PYTHONPATH puis lance le module glmcode
    cat > "$BIN_DIR/glm" << 'EOF'
#!/bin/bash
# Lanceur glm
export PYTHONPATH="$(dirname "$(dirname "$(realpath "$0")")"):$PYTHONPATH"
exec python3 -m glmcode "$@"
EOF
    
    chmod +x "$BIN_DIR/glm"
    write_ok "Lanceur créé : $BIN_DIR/glm"
    write_log "Launcher created: $BIN_DIR/glm"
}

# --- Ajout au PATH ---
add_to_path() {
    write_step "Ajout de glm au PATH"
    
    BIN_DIR="$INSTALL_DIR/bin"
    SHELL_RC=""
    
    # Détection du fichier de configuration du shell
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.profile" ]; then
        SHELL_RC="$HOME/.profile"
    fi
    
    if [ -n "$SHELL_RC" ]; then
        if grep -q "export PATH=\"$BIN_DIR:\$PATH\"" "$SHELL_RC" 2>/dev/null; then
            write_ok "Déjà dans le PATH : $BIN_DIR"
        else
            echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
            write_ok "Ajouté au PATH : $BIN_DIR"
            write_log "Added to PATH in: $SHELL_RC"
        fi
    else
        write_warn "Aucun fichier de shell trouvé. Ajoutez manuellement :"
        write_warn "export PATH=\"$BIN_DIR:\$PATH\""
    fi
    
    # Disponible aussi dans la session courante
    export PATH="$BIN_DIR:$PATH"
}

# --- Installation de la configuration ---
install_config() {
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
            write_ok "Config déjà présente : $CFG_DST (conservée)"
        else
            cp "$CFG_SRC" "$CFG_DST"
            write_ok "Config installée : $CFG_DST"
        fi
    else
        write_warn "Aucun config.toml/config.example.toml à copier"
    fi
    
    write_log "Configuration handled"
}

# --- Vérification de l'installation ---
verify_installation() {
    write_step "Vérification de l'installation"
    
    if command -v glm >/dev/null 2>&1; then
        if glm --version >/dev/null 2>&1; then
            write_ok "glm opérationnel"
            write_log "Installation verified successfully"
        else
            write_warn "La vérification n'a pas abouti dans cette session."
            write_warn "Redémarrez votre terminal puis tapez : glm --version"
        fi
    else
        write_warn "glm n'est pas dans le PATH."
        write_warn "Redémarrez votre terminal ou exécutez : source ~/.bashrc (ou ~/.zshrc)"
    fi
}

# --- Nettoyage ---
cleanup() {
    write_step "Nettoyage"
    
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    write_ok "Fichiers temporaires supprimés"
    write_log "Cleanup completed"
}

# --- Fonction de rollback ---
rollback() {
    write_err "Erreur lors de l'installation. Restauration en cours..."
    write_log "Rollback initiated"
    
    # Restaurer l'installation précédente si elle existe
    if [ -d "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR/$(basename "$INSTALL_DIR")" ]; then
        rm -rf "$INSTALL_DIR" 2>/dev/null || true
        mv "$BACKUP_DIR/$(basename "$INSTALL_DIR")" "$INSTALL_DIR"
        write_ok "Installation précédente restaurée"
        write_log "Previous installation restored"
    fi
    
    # Nettoyer les fichiers temporaires
    rm -rf "$TEMP_DIR" 2>/dev/null || true
    rm -rf "$BACKUP_DIR" 2>/dev/null || true
    
    write_err "Restauration terminée. Veuillez vérifier l'état du système."
    exit 1
}

# --- Gestion des erreurs ---
set_error_trap() {
    set -E
    trap 'rollback' ERR
}

# --- Main ---
main() {
    echo ""
    echo "  Installation avancée de GLM Codeur" | sed 's/./=/g'
    echo "  Installation avancée de GLM Codeur"
    echo "  Source : $REPO_URL"
    echo "  Log : $LOG_FILE"
    echo "" | sed 's/./=/g'
    
    # Initialisation du fichier de log
    echo "=== Installation GLM Codeur ===" > "$LOG_FILE"
    echo "Date : $(date)" >> "$LOG_FILE"
    echo "==============================" >> "$LOG_FILE"
    
    # Configuration de la gestion d'erreurs
    set_error_trap
    
    # Exécution des étapes
    detect_os
    check_internet
    check_system_packages
    download_repo
    detect_python
    install_dependencies
    install_glm
    create_launcher
    add_to_path
    install_config
    verify_installation
    cleanup
    
    echo ""
    echo "  Installation terminée avec succès !" | sed 's/./=/g'
    echo "  Pour utiliser glm, redémarrez votre terminal"
    echo "  ou exécutez : source ~/.bashrc (ou ~/.zshrc)"
    echo "  Ensuite, tapez : glm --version"
    echo "  Installé dans : $INSTALL_DIR"
    echo "  Logs : $LOG_FILE"
    echo "" | sed 's/./=/g'
}

# Exécution du script
main