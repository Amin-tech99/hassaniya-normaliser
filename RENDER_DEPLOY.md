# Render Deployment Guide

This guide will help you deploy the Hassaniya Normalizer project to Render.

## Quick Deploy (3 Steps)

### 1. Connect to Render
1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository

### 2. Configure Service
Render will automatically detect the `render.yaml` configuration file and set up:
- **Build Command**: `pip install --upgrade pip && pip install -e .`
- **Start Command**: `hassy-web`
- **Environment**: Python
- **Port**: 10000 (automatically configured)

### 3. Deploy
1. Click "Create Web Service"
2. Wait for build and deployment (usually 2-5 minutes)
3. Your app will be available at: `https://your-service-name.onrender.com`

## Files Added for Render

- `render.yaml` - Render service configuration
- `src/hassy_normalizer/web_ui/server.py` - Entry point for hassy-web command
- `src/hassy_normalizer/web_ui/__init__.py` - Package initialization
- `RENDER_DEPLOY.md` - This deployment guide

## Environment Variables

The following environment variables are automatically configured:
- `PORT=10000` - Render's default port
- `HOST=0.0.0.0` - Listen on all interfaces
- `PYTHONUNBUFFERED=1` - Real-time logs
- `PYTHONDONTWRITEBYTECODE=1` - Faster startup

## Local Testing

Test the Render configuration locally:

```bash
# Install in development mode
pip install -e .

# Test the hassy-web command
hassy-web

# Or test with custom port
PORT=8080 hassy-web
```

## Features

✅ **Automatic Builds** - Deploys on every git push  
✅ **Free Tier** - 750 hours/month free  
✅ **Custom Domain** - Add your own domain  
✅ **SSL Certificate** - Automatic HTTPS  
✅ **Environment Variables** - Secure config management  
✅ **Logs & Monitoring** - Real-time application logs  

## Troubleshooting

### Build Fails
- Check the build logs in Render dashboard
- Ensure all dependencies are in `requirements.txt`
- Verify `pyproject.toml` is properly configured

### App Won't Start
- Check if `hassy-web` command works locally
- Verify the entry point in `pyproject.toml`
- Check application logs for errors

### Import Errors
- Ensure the project structure matches the import paths
- Check that `src/hassy_normalizer/web_ui/server.py` exists
- Verify the package is installed correctly

### Port Issues
- Render automatically sets the PORT environment variable
- Don't hardcode ports in your application
- Use `os.environ.get("PORT", default_port)`

## Support

- [Render Documentation](https://render.com/docs)
- [Python on Render](https://render.com/docs/deploy-python)
- [Environment Variables](https://render.com/docs/environment-variables)

## Next Steps

After deployment:
1. Test all functionality on the live site
2. Set up custom domain (optional)
3. Configure monitoring and alerts
4. Set up database if needed (PostgreSQL available)