#!/usr/bin/env bash
set -euo pipefail

# Install Oh My Zsh + Powerlevel10k (and helpful fonts) on macOS or Debian/Ubuntu.
# Usage:
#   chmod +x setup-zsh-p10k.sh
#   ./setup-zsh-p10k.sh
#
# Notes:
# - This script will:
#   1) Install prerequisites (git, zsh, curl/wget)
#   2) Install Oh My Zsh (unattended)
#   3) Install Powerlevel10k theme
#   4) Set ZSH_THEME="powerlevel10k/powerlevel10k"
#   5) Optionally install MesloLGS Nerd Font (best for Powerlevel10k)

log() { printf "\n==> %s\n" "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"

log "Checking prerequisites..."
if [[ "$OS" == "Darwin" ]]; then
  if ! have brew; then
    log "Homebrew not found. Installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c \
      "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # shellcheck disable=SC2016
    if [[ -x /opt/homebrew/bin/brew ]]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
    if [[ -x /usr/local/bin/brew ]]; then eval "$(/usr/local/bin/brew shellenv)"; fi
  fi

  log "Installing packages (zsh, git, curl, wget)..."
  brew update
  brew install zsh git curl wget || true

elif [[ "$OS" == "Linux" ]]; then
  if have apt-get; then
    log "Installing packages via apt (zsh, git, curl, wget)..."
    sudo apt-get update
    sudo apt-get install -y zsh git curl wget
  else
    echo "Unsupported Linux distro (need apt-get). Install zsh, git, curl first and re-run."
    exit 1
  fi
else
  echo "Unsupported OS: $OS"
  exit 1
fi

# Choose downloader
DL="curl -fsSL"
if ! have curl && have wget; then
  DL="wget -qO-"
fi
if ! have curl && ! have wget; then
  echo "Neither curl nor wget is installed. Please install one and re-run."
  exit 1
fi

log "Ensuring zsh is installed..."
if ! have zsh; then
  echo "zsh not found after installing prerequisites. Aborting."
  exit 1
fi

# Set zsh as default shell (best-effort)
log "Setting zsh as default shell (may prompt for password)..."
ZSH_PATH="$(command -v zsh)"
if [[ "${SHELL:-}" != "$ZSH_PATH" ]]; then
  if have chsh; then
    # Ensure zsh is in /etc/shells (Linux)
    if [[ "$OS" == "Linux" ]] && ! grep -qE "^${ZSH_PATH}$" /etc/shells 2>/dev/null; then
      echo "$ZSH_PATH" | sudo tee -a /etc/shells >/dev/null
    fi
    chsh -s "$ZSH_PATH" || true
  fi
fi

# Install Oh My Zsh
if [[ -d "${HOME}/.oh-my-zsh" ]]; then
  log "Oh My Zsh already installed at ~/.oh-my-zsh (skipping)."
else
  log "Installing Oh My Zsh (unattended)..."
  # Official installer supports RUNZSH=no and CHSH=no for unattended installs.
  RUNZSH=no CHSH=no sh -c "$($DL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
fi

# Install Powerlevel10k
P10K_DIR="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"
if [[ -d "$P10K_DIR" ]]; then
  log "Powerlevel10k already installed at $P10K_DIR (skipping)."
else
  log "Cloning Powerlevel10k..."
  git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$P10K_DIR"
fi

# Set theme in ~/.zshrc
ZSHRC="${HOME}/.zshrc"
log "Configuring ~/.zshrc to use Powerlevel10k..."
if [[ ! -f "$ZSHRC" ]]; then
  touch "$ZSHRC"
fi

# Backup
cp -a "$ZSHRC" "${ZSHRC}.bak.$(date +%Y%m%d%H%M%S)"

# Replace existing ZSH_THEME or add it
if grep -qE '^[[:space:]]*ZSH_THEME=' "$ZSHRC"; then
  # Replace line
  sed -i'' -e 's|^[[:space:]]*ZSH_THEME=.*$|ZSH_THEME="powerlevel10k/powerlevel10k"|' "$ZSHRC" 2>/dev/null \
    || sed -i -e 's|^[[:space:]]*ZSH_THEME=.*$|ZSH_THEME="powerlevel10k/powerlevel10k"|' "$ZSHRC"
else
  printf '\nZSH_THEME="powerlevel10k/powerlevel10k"\n' >> "$ZSHRC"
fi

# (Optional) Install Meslo Nerd Font (recommended)
log "Optional: Installing MesloLGS Nerd Font (recommended for Powerlevel10k)..."
if [[ "$OS" == "Darwin" ]]; then
  if have brew; then
    brew tap homebrew/cask-fonts >/dev/null 2>&1 || true
    brew install --cask font-meslo-lg-nerd-font || true
    log "Font installed. Set your terminal font to 'MesloLGS NF' in preferences."
  fi
else
  # Linux: download fonts into ~/.local/share/fonts
  FONT_DIR="${HOME}/.local/share/fonts"
  mkdir -p "$FONT_DIR"
  tmpdir="$(mktemp -d)"
  (
    cd "$tmpdir"
    for f in \
      "MesloLGS NF Regular.ttf" \
      "MesloLGS NF Bold.ttf" \
      "MesloLGS NF Italic.ttf" \
      "MesloLGS NF Bold Italic.ttf"
    do
      url="https://github.com/romkatv/powerlevel10k-media/raw/master/${f// /%20}"
      log "Downloading $f..."
      $DL "$url" > "$FONT_DIR/$f"
    done
  )
  rm -rf "$tmpdir"
  if have fc-cache; then
    fc-cache -f "$FONT_DIR" || true
  fi
  log "Fonts downloaded. Set your terminal font to 'MesloLGS NF' in your terminal settings."
fi

log "Done."
cat <<'EOF'

Next steps:
1) Restart your terminal (or log out/in) so the default shell change takes effect.
2) Start zsh:
     zsh
3) Run Powerlevel10k configuration wizard:
     p10k configure

If icons look wrong, set your terminal font to: MesloLGS NF
EOF
