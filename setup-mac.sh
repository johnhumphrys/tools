#!/bin/bash

casks=(
    bitwarden
    obsidian
    google-chrome
    iterm2
    postman
    visual-studio-code
    brave-browser
    vlc
    caffeine
    firefox
    spotify
    font-iosevka
    meetingbar
    tableplus
    fontbase
    hiddenbar
    ngrok
    the-unarchiver
)

check_command() {
    if ! command -v "$1" &> /dev/null
    then
        echo "$1 is not installed. Please install it first."
        exit 1
    else
        echo "$1 is installed."
    fi
}

check_command brew
check_command zsh


echo "Installing packages.."
brew install curl fzf git grep htop lazydocker lazygit pwgen vim 

echo "Installing casks.."
for cask in "${casks[@]}"
do
    echo "Installing $cask..."
    brew install --cask "$cask"
done
