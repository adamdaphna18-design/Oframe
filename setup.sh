#!/bin/bash
pip install -r requirements.txt
mkdir -p ~/.oframe/plugins
cp -r oframe/plugins/* ~/.oframe/plugins/ 2>/dev/null || true
echo "O‑Frame setup complete."
