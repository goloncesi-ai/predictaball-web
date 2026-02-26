# Deployment Guide for PredictaBall AI

Since your application uses a Python backend (Flask) for the simulations, it cannot be hosted directly on Squarespace (which only hosts static websites).

We will deploy the **entire application** (Frontend + Backend) to a cloud provider called **Render**. It is free/cheap and easy to use.

## Architecture

- **Domain**: `predictaballai.com` (Managed by Squarespace)
- **Hosting**: Render (Runs the Python code and serves the website) at `https://your-app-name.onrender.com`
- **Connection**: You will add a DNS record in Squarespace to point your domain to Render.

## Prerequisites

1.  **GitHub Account**: You need to upload this code to a GitHub repository.
2.  **Render Account**: Sign up at [render.com](https://render.com).

## Steps to Deploy

### 1. Structure Change (Already Done)
I have reorganized your project structure to be deployment-ready:
-   Created `requirements.txt` (List of Python libraries).
-   Created `public/` folder for your website files (`index.html`, `style.css`, etc.) to keep them clean.
-   Updated `server.py` to serve the website and use relative paths (so it works on the cloud).
-   Updated `app.js` to talk to the backend correctly.

### 2. Push to GitHub
1.  Create a new repository on GitHub (e.g., `predictaball-web`).
2.  Push this entire folder (`Gol Oncesi`) to that repository.
    *(If you need help with git commands, let me know)*.

### 3. Deploy on Render
1.  Go to the Render Dashboard.
2.  Click **New +** and select **Web Service**.
3.  Connect your GitHub repository.
4.  Configure the service:
    -   **Name**: `predictaball-ai` (or similar)
    -   **Region**: Frankfurt (closest to Turkey) or any preference.
    -   **Runtime**: **Python 3**
    -   **Build Command**: `pip install -r requirements.txt`
    -   **Start Command**: `gunicorn server:app`
5.  Click **Create Web Service**.

### 3.1 Performance Tuning (Render Environment Variables)
For faster simulation responses on low-tier instances, set these in Render:

- `GOLO_SIMULATION_COUNT_DEFAULT=60`
- `GOLO_SIMULATION_COUNT_MIN=20`
- `GOLO_SIMULATION_COUNT_MAX=200`
- `GOLO_SIM_INCLUDE_HEATMAPS=0`
- `GOLO_SIM_INCLUDE_IMAGES=0`
- `GOLO_SIM_INCLUDE_MARKOV=0` (set to `1` if you want Markov panel data returned)
- `GOLO_LOGIT_USE_CV=0`
- `GOLO_RF_TREES=120`
- `GOLO_RF_MAX_DEPTH=16`
- `GOLO_TRAIN_AUX_TARGETS=0`

### 4. Connect Domain
1.  Once the service is live (you'll get a URL like `https://predictaball.onrender.com`), go to the **Settings** tab in Render.
2.  Scroll to **Custom Domains** and click **Add Custom Domain**.
3.  Enter `predictaballai.com`.
4.  Render will verify it and give you DNS settings (an `A` record and `CNAME`).
5.  **Go to Squarespace**:
    -   Navigate to **Settings > Domains**.
    -   Click on `predictaballai.com`.
    -   Go to **DNS Settings**.
    -   Add the records provided by Render.

Wait for propagation (up to 24h, usually fast), and your site will be live!
