#!/bin/zsh
# Double-click to start Reel Studio (opens http://127.0.0.1:8765). Close this window to stop it.
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"
[ -s "$HOME/.nvm/nvm.sh" ] && source "$HOME/.nvm/nvm.sh" >/dev/null
if curl -s -o /dev/null http://127.0.0.1:8765/api/jobs; then
  open http://127.0.0.1:8765; exit 0
fi
(sleep 1.5 && open http://127.0.0.1:8765) &
exec python3 reel_editor/app/server.py --port 8765
