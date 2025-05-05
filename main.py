from flask import Flask, jsonify, render_template_string
import os
import threading
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord_bot')

# Track bot start time
start_time = datetime.now()
bot_status = {"running": False, "error": None}

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-dev-key")

@app.route('/')
def index():
    uptime = datetime.now() - start_time
    hours, remainder = divmod(uptime.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    # Simple status page with HTML
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Roblox Discord Bot - Status</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            .container { max-width: 800px; margin-top: 50px; }
            .status-badge { font-size: 1.1em; }
            .card { border: none; margin-bottom: 20px; }
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container">
            <div class="card shadow">
                <div class="card-body">
                    <h2 class="card-title mb-4">Roblox Discord Bot Status</h2>
                    <div class="d-flex align-items-center mb-3">
                        <h5 class="me-3 mb-0">Bot Status:</h5>
                        <span class="badge bg-{{ 'success' if bot_status['running'] else 'danger' }} status-badge">
                            {{ 'ONLINE' if bot_status['running'] else 'OFFLINE' }}
                        </span>
                    </div>
                    <p class="card-text mb-1"><strong>Uptime:</strong> {{ uptime }}</p>
                    <p class="card-text mb-1"><strong>Start Time:</strong> {{ start_time }}</p>
                    {% if bot_status['error'] %}
                    <div class="alert alert-danger mt-3">
                        <h5>Error:</h5>
                        <pre>{{ bot_status['error'] }}</pre>
                    </div>
                    {% endif %}
                </div>
            </div>
            <div class="card shadow">
                <div class="card-body">
                    <h5 class="card-title">Bot Information</h5>
                    <p class="card-text mb-1"><strong>Application ID:</strong> {{ app_id }}</p>
                    <p class="card-text"><strong>Environment:</strong> {{ environment }}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Application ID (masked for security)
    app_id = os.environ.get("APPLICATION_ID", "Not set")
    if app_id != "Not set":
        app_id = f"{app_id[:4]}...{app_id[-4:]}"
    
    # Determine environment
    environment = "Production" if os.environ.get("PORT") else "Development"
    
    return render_template_string(
        html, 
        bot_status=bot_status,
        uptime=uptime_str,
        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
        app_id=app_id,
        environment=environment
    )

@app.route('/status')
def status():
    uptime = datetime.now() - start_time
    uptime_seconds = uptime.total_seconds()
    
    return jsonify({
        "status": "online" if bot_status["running"] else "offline",
        "bot_name": "Roblox Discord Bot",
        "uptime_seconds": int(uptime_seconds),
        "uptime_formatted": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s",
        "started_at": start_time.isoformat(),
        "environment": "production" if os.environ.get("PORT") else "development"
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    if bot_status["running"]:
        return jsonify({"status": "healthy"}), 200
    else:
        return jsonify({"status": "unhealthy", "error": bot_status["error"]}), 503

def run_flask():
    """Run the Flask web server"""
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)

def run_bot():
    """Import and run the Discord bot"""
    try:
        # Check for required environment variables
        token = os.environ.get("DISCORD_TOKEN")
        app_id = os.environ.get("APPLICATION_ID")
        
        if not token:
            raise ValueError("DISCORD_TOKEN environment variable is not set")
        if not app_id:
            raise ValueError("APPLICATION_ID environment variable is not set")
            
        # Log the start attempt
        logger.info(f"Starting Discord bot with APPLICATION_ID: {app_id[:4]}...{app_id[-4:] if len(app_id) > 8 else ''}")
        
        # Mark the bot as running - this will be set before importing bot
        # because bot.py will start running the bot automatically when imported
        bot_status["running"] = True
        
        # When we import bot.py, it will automatically run the bot
        # The bot is controlled by the bot.py file itself
        import bot
    except Exception as e:
        error_msg = f"Failed to start Discord bot: {e}"
        logger.error(error_msg)
        bot_status["running"] = False
        bot_status["error"] = error_msg
        # Continue running the web server even if the bot fails
        # This way we can see the error in the web interface

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True  # Thread will exit when the main program exits
    flask_thread.start()
    
    # Run the Discord bot in the main thread
    run_bot()