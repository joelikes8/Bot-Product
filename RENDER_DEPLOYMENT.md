# Render Deployment Guide

This guide explains how to deploy your Discord bot on Render's hosting platform.

## Prerequisites

1. A [Render](https://render.com) account
2. Your Discord bot token and application ID
3. A PostgreSQL database (you can create one on Render or use another provider)

## Deployment Steps

### 1. Create a New Web Service

1. Go to your Render dashboard
2. Click "New" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service with these settings:
   - **Name**: roblox-discord-bot (or your preferred name)
   - **Environment**: Python
   - **Build Command**: `pip install -r render-requirements.txt`
   - **Start Command**: `python main.py`

### 2. Add Environment Variables

Add the following environment variables in the Render dashboard:

- `DISCORD_TOKEN`: Your Discord bot token
- `APPLICATION_ID`: Your Discord application ID
- `DATABASE_URL`: Your PostgreSQL database URL
- `SESSION_SECRET`: A random string for Flask session security

### 3. Database Setup

If you don't already have a PostgreSQL database:

1. Go to your Render dashboard
2. Click "New" and select "PostgreSQL"
3. Configure your database
4. Once created, copy the Internal Database URL to use as your `DATABASE_URL` environment variable

### 4. Deploy

1. Click "Create Web Service"
2. Wait for the build and deployment process to complete
3. Your Discord bot should now be running!

## Monitoring and Logs

- View logs in the Render dashboard
- The web interface will be available at your Render service URL
- Check bot status at `https://your-service-url/status`

## Troubleshooting

- If the bot doesn't start, check the logs in the Render dashboard
- Verify all environment variables are set correctly
- Ensure your database is accessible from the service

## Render Blueprint

This project includes a `render.yaml` file that you can use with Render Blueprint for one-click deployment.