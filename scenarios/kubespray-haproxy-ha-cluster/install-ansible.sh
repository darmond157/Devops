#!/bin/bash
set -e

echo "Updating package lists..."
sudo apt update

echo "Installing software-properties-common..."
sudo apt install -y software-properties-common

echo "Adding Ansible PPA repository..."
sudo add-apt-repository --yes --update ppa:ansible/ansible

echo "Installing Ansible..."
sudo apt install -y ansible

echo "Ansible version installed:"
ansible --version
