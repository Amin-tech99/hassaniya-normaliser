# Railway Deployment Guide

## Quick Deploy to Railway

1. **Connect to Railway**
   - Go to [railway.app](https://railway.app)
   - Sign up/login with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select this repository

2. **Automatic Configuration**
   - Railway will automatically detect this as a Python project
   - It will use the `Procfile` to start the application
   - The `railway.toml` provides additional configuration
   - Dependencies will be installed from `requirements.txt`

3. **Environment Variables**
   - `PORT` - Automatically set by Railway
   - `PYTHONUNBUFFERED=1` - For proper logging
   - `PYTHONDONTWRITEBYTECODE=1` - For performance

4. **Access Your App**
   - Railway will provide a public URL
   - Your app will be available at `https://your-app-name.railway.app`
   - The dashboard will be at `https://your-app-name.railway.app/dashboard`

## Files Added for Railway

- `Procfile` - Tells Railway how to start the app
- `railway.toml` - Railway-specific configuration
- `requirements.txt` - Python dependencies
- `RAILWAY_DEPLOY.md` - This deployment guide

## Local Testing

To test the Railway-ready version locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run with environment variable
PORT=8002 python server.py

# Or use default port
python server.py
```

## Troubleshooting

- If deployment fails, check the Railway logs
- Ensure all dependencies are in `requirements.txt`
- The app should start on the PORT environment variable
- Data persistence: Railway provides ephemeral storage by default