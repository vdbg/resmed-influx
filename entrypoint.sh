#!/bin/bash
if [ ! -f "/app/config.toml" ]; then
    touch /app/config.toml
fi

# Execute the main application
exec "$@"
