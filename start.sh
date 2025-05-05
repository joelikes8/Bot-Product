#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Check if running in Render or local environment
if [ "$PORT" != "" ]; then
  echo "Running in production mode (Render)"
  # Start the application using main.py (both web server and bot)
  python main.py
else
  echo "Running in development mode (local)"
  # Start the bot only
  python bot.py
fi