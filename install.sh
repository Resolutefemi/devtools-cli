#!/bin/bash

# Renance DevTools Unix Installer
# Supports: Linux, macOS, Termux

# Colors for output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Installing Renance DevTools...${NC}"

# 1. Detect Termux specific needs
if [[ "$PREFIX" == *"/com.termux/"* ]]; then
    echo -e "${CYAN}📱 Termux environment detected.${NC}"
    if ! command -v termux-battery-status &>/dev/null; then
        echo -e "${YELLOW}💡 Tip: To use phone commands (torch, sms, etc.), please run:${NC}"
        echo -e "${GREEN}   pkg install termux-api${NC}"
        echo -e "${YELLOW}   And install the 'Termux:API' app from F-Droid.${NC}\n"
    fi
fi

# 2. Detect Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo -e "${RED}❌ Python not found. Please install Python 3.${NC}"
    exit 1
fi

# 3. Install in editable mode
echo -e "${CYAN}📦 Installing dependencies...${NC}"
$PY -m pip install -e . --quiet 2>/dev/null || $PY -m pip install -e .

# 4. Run Setup for PATH configuration
echo -e "${CYAN}⚙️ Configuring system PATH...${NC}"
$PY -m dt_cli.cli setup 2>/dev/null

# 5. Auto-apply PATH in current session (no restart needed)
if [[ "$PREFIX" == *"/com.termux/"* ]]; then
    export PATH="$PATH:$PREFIX/bin"
else
    # Add all common Python user bin directories
    export PATH="$HOME/.local/bin:$PATH"
    [ -d "$HOME/.pyenv/shims" ] && export PATH="$HOME/.pyenv/shims:$PATH"
    [ -d "$HOME/.cargo/bin" ] && export PATH="$HOME/.cargo/bin:$PATH"
    export PATH="$(python3 -c 'import site; print(site.getuserbase())' 2>/dev/null)/bin:$PATH" 2>/dev/null
fi

# 6. Verify
if command -v dt &>/dev/null; then
    DT_PATH=$(which dt 2>/dev/null || command -v dt 2>/dev/null)
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo -e "${GREEN}   dt command available at: ${DT_PATH}${NC}"
    echo -e "${CYAN}🚀 Run 'dt help' to see all available commands.${NC}"
else
    echo -e "\n${GREEN}✅ Installation complete!${NC}"
    echo -e "${YELLOW}💡 The 'dt' command is installed. Close and reopen your terminal to use it.${NC}"
    echo -e "${CYAN}   Or run this now:  export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
fi