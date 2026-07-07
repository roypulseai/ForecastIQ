#!/usr/bin/env bash
# ForecastIQ - Quick Start (macOS / Linux)
# Convenience wrapper around start-with-docker.sh
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
exec bash ./start-with-docker.sh "$@"
