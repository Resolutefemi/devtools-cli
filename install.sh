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

# 2. Install in editable mode
echo -e "${CYAN}📦 Installing dependencies...${NC}"
$PY -m pip install -e .

# 3. Run Setup for PATH configuration
echo -e "${CYAN}⚙️ Configuring system PATH...${NC}"
$PY -m dt_cli.cli setup

echo -e "\n${GREEN}✅ Installation complete!${NC}"
echo -e "${YELLOW}💡 Please restart your terminal or run 'source ~/.bashrc' (or your shell config) to use 'dt' globally.${NC}"
echo -e "${CYAN}💡 You can run 'dt help' to see all available commands.${NC}"
