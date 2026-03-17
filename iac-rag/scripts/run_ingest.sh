#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=$(pwd)
python ingestion/ingest.py
