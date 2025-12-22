# Flask Flood Hazard App - Vercel Deployment

This Flask application is configured for deployment on Vercel as a serverless function.

## Project Structure
```
FloodApp/
├── api/
│   └── index.py          # Main Flask app (serverless function)
├── templates/
│   └── index.html        # Frontend template
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel configuration
├── revised_map_data.gpkg # Flood hazard data (not included in repo)
└── README.md            # This file
```

## Setup Instructions

### 1. Update Google Drive Link
Before deploying, update the `DATA_URL` in `api/index.py`:
```python
DATA_URL = "YOUR_GOOGLE_DRIVE_DIRECT_LINK_HERE"
```

### 2. Install Vercel CLI (optional for local testing)
```bash
npm install -g vercel
```

### 3. Deploy to Vercel

#### Option A: Deploy via GitHub
1. Push this project to GitHub
2. Connect your GitHub repository to Vercel at https://vercel.com
3. Vercel will automatically detect the configuration and deploy

#### Option B: Deploy via CLI
```bash
vercel
```

## Important Notes

- **Data File**: The `revised_map_data.gpkg` file should be accessible via a direct download link (Google Drive, Dropbox, etc.)
- **Cold Starts**: The first request may be slow as the data file is downloaded
- **File Size Limits**: Vercel has file size limitations. Large data files may cause issues
- **IP Detection**: The app uses `X-Forwarded-For` header to get the real client IP on Vercel

## Environment Considerations

Vercel serverless functions have limitations:
- 50MB deployment size limit
- 250MB memory limit (can be increased with Pro plan)
- 10-second execution timeout (can be increased with Pro plan)

If your `revised_map_data.gpkg` file is large, consider:
1. Hosting it on external storage (S3, GCS, etc.)
2. Using a smaller/compressed version
3. Using a database service instead

## Local Development

To run locally:
```bash
pip install -r requirements.txt
python "map test.py"
```

## Testing

After deployment, visit your Vercel URL to test the application.
