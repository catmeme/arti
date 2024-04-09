#!/usr/bin/env sh
set -e

. /app/venv/bin/activate

if [ -n "$LAMBDA_HANDLER" ]; then
    /app/venv/bin/python -m awslambdaric $LAMBDA_HANDLER
else
    arti "$@"
fi
