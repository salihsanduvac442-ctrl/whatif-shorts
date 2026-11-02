#!/bin/sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
LIB=${LIB:-$(cd "$HERE/../.." && pwd)}
export LIB
cd "$LIB"
node core/render/events.mjs "$HERE" --size 1080x1920
node core/render/video.mjs "$HERE" --fps 24 --workers 4 --size 1080x1920 --out "$HERE/out/video.mp4"
"$LIB/.venv/bin/python" "$HERE/mix.py"
sh core/render/mux.sh "$HERE/out/video.mp4" "$HERE/out/mix.wav" "$HERE/sub-dive-drop.mp4" 24 0
