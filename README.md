<div align="center">
  <img src="frontend/public/rehearsed-logo.png" alt="Rehearsed Logo" width="300"/>
</div>
<div align="center">
<b>A Teacher Simuation Platform</b>
</div>


## Overview

Rehearsed is a teacher simulation platform that enables educators to practice their teaching skills in a safe, AI-powered environment. The platform uses conversational AI agents to simulate classroom scenarios, allowing teachers to rehearse and receive feedback on their teaching interactions.

### Architecture

Rehearsed follows a modern, full-stack architecture:

**Frontend:**
- **Angular 20** - A modern TypeScript-based web framework providing a responsive, single-page application interface
- Material Design components for consistent UI/UX
- Real-time chat interface for interacting with AI student agents

**Backend:**
- **FastAPI** - High-performance Python web framework providing RESTful API endpoints
- **LangGraph** - Orchestrates multi-agent AI conversations simulating classroom scenarios
- **PostgreSQL** - Relational database for storing users, scenarios, agents, and conversation history
- **Langfuse** - Observability and monitoring for LLM interactions
- **Google Cloud Speech-to-Text & Text-to-Speech** - Enables voice interactions with AI agents
- **Prometheus & Grafana** - Metrics collection and visualization

The system uses a state graph architecture where AI agents (representing students) can participate in simulated classroom discussions, with the platform providing real-time feedback and scenario-specific guidance.

## Getting Started

### Prerequisites

**Backend:**
- Python 3.13+
- `uv` package manager (`pip install uv`)
- PostgreSQL database
- Environment variables configured (see backend configuration)

**Frontend:**
- Node.js 18+ and npm
- Angular CLI 20+

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   # Ideally in new python env
   pip install uv 
   uv sync
   ```

3. Set up environment variables:
   - Create a `.env.development` file in the `backend/` directory
   - Configure database connection, API keys, and other required settings
   - See `backend/app/core/config.py` for all configuration options

4. Ensure PostgreSQL is running and accessible

5. Run the backend server:

   ```bash
   # or manually:
   cd backend
   source .venv/bin/activate
   uv run fastapi dev app/main.py     
   ```


The backend API will be available at `http://localhost:8000`.  API documentation is available at `http://localhost:8000/docs`.

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment:
   - Copy `src/environments/environment-example.ts` to `src/environments/environment.development.ts`
   - Update the `baseUrl` to point to your backend API (default: `http://localhost:8000`)
   - Configure Firebase settings if using Firebase authentication

4. Run the development server:
   ```bash
   ng serve
   # or:
   npm start
   ```

5. Open your browser and navigate to `http://localhost:4200`

The application will automatically reload when you make changes to the source files.

**Building for production:**
```bash
ng build
# or:
npm run build
```

The production build will be output to the `dist/frontend/browser` directory.

## Deployment

### Backend Deployment (Google Cloud Run)

Deploy the FastAPI backend to Google Cloud Run:

1. **Prerequisites**:
   - Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
   - Authenticate: `gcloud auth login`
   - Set your project: `gcloud config set project YOUR_PROJECT_ID`
   - Enable required APIs:
     ```bash
     gcloud services enable cloudbuild.googleapis.com
     gcloud services enable run.googleapis.com
     gcloud services enable sqladmin.googleapis.com
     ```

2. **Set up Cloud SQL (PostgreSQL)**:
   ```bash
   # Create Cloud SQL instance
   gcloud sql instances create rehearsed-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1 \
     --root-password=YOUR_ROOT_PASSWORD
   
   # Create database
   gcloud sql databases create rehearsed \
     --instance=rehearsed-db
   
   # Create database user
   gcloud sql users create rehearsed-user \
     --instance=rehearsed-db \
     --password=YOUR_USER_PASSWORD
   ```

3. **Build and push Docker image to Artifact Registry**:
   ```bash
   cd backend
   
   # Create Artifact Registry repository (first time only)
   gcloud artifacts repositories create rehearsed-backend \
     --repository-format=docker \
     --location=us-central1 \
     --description="Rehearsed backend Docker images"
   
   # Configure Docker authentication
   gcloud auth configure-docker us-central1-docker.pkg.dev
   
   # Build and push image
   gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rehearsed-backend/rehearsed-backend:latest
   ```

4. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy rehearsed-backend \
     --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rehearsed-backend/rehearsed-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars <use .env.production> \
     --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:rehearsed-db \
     --set-env-vars POSTGRES_HOST=/cloudsql/YOUR_PROJECT_ID:us-central1:rehearsed-db \
     --set-env-vars POSTGRES_DB=rehearsed \
     --set-env-vars POSTGRES_USER=rehearsed-user \
     --set-env-vars POSTGRES_PASSWORD=YOUR_USER_PASSWORD \
     --set-env-vars LLM_API_KEY=YOUR_LLM_API_KEY \
     --set-env-vars JWT_SECRET_KEY=YOUR_JWT_SECRET \
     --set-env-vars LANGFUSE_PUBLIC_KEY=YOUR_LANGFUSE_PUBLIC_KEY \
     --set-env-vars LANGFUSE_SECRET_KEY=YOUR_LANGFUSE_SECRET \
     --memory 4Gi \
     --cpu 2 \
     --timeout 300 \
     --min-instances 1 \
     --max-instances 4
   ```

   Or use a `.env` file or Secret Manager for sensitive values:
   ```bash
   # Store secrets in Secret Manager
   echo -n "your-secret-value" | gcloud secrets create jwt-secret-key --data-file=-
   echo -n "your-secret-value" | gcloud secrets create llm-api-key --data-file=-
   
   # Deploy with secrets
   gcloud run deploy rehearsed-backend \
     --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/rehearsed-backend/rehearsed-backend:latest \
     --platform managed \
     --region us-central1 \
     --update-secrets JWT_SECRET_KEY=jwt-secret-key:latest,LLM_API_KEY=llm-api-key:latest
   ```

6. **Verify deployment**:
   ```bash
   # Get service URL
   gcloud run services describe rehearsed-backend --region us-central1 --format 'value(status.url)'
   
   # Test health endpoint
   curl https://your-service-url/health
   ```

**Environment Variables to Set:**
- `APP_ENV=production`
- `POSTGRES_HOST` - Cloud SQL connection string or IP
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `LLM_API_KEY` - Your LLM API key
- `JWT_SECRET_KEY` - Secret for JWT token signing
- `LANGFUSE_PUBLIC_KEY` - Langfuse public key (if using)
- `LANGFUSE_SECRET_KEY` - Langfuse secret key (if using)
- `ALLOWED_ORIGINS` - Comma-separated list of allowed frontend origins
- Any other required environment variables from `backend/app/core/config.py`

**Note:** For production, consider using [Secret Manager](https://cloud.google.com/secret-manager) for sensitive values instead of environment variables.

### Frontend Deployment (Firebase)

Deploy the Angular frontend to Firebase Hosting:

1. **Update environment configuration with backend Cloud Run URL**:
   - Get your Cloud Run service URL:
     ```bash
     gcloud run services describe rehearsed-backend --region us-central1 --format 'value(status.url)'
     ```
   - Update `src/environments/environment.ts` with the backend URL:
     ```typescript
     export const environment = {
         baseUrl: 'https://your-cloud-run-service-url',
         firebaseConfig: {
             // ... your Firebase config
         }
     };
     ```

2. **Install Firebase CLI** (if not already installed):
   ```bash
   npm install -g firebase-tools
   ```

3. **Login to Firebase**:
   ```bash
   firebase login
   ```

4. **Initialize Firebase** (if not already initialized):
   ```bash
   cd frontend
   firebase init hosting
   ```
   - Select your Firebase project
   - Set public directory to `dist/frontend/browser`
   - Configure as single-page app: `Yes`
   - Set up automatic builds: `No` (or `Yes` if using GitHub Actions)

5. **Build the production bundle**:
   ```bash
   npm run build
   ```
   This creates the production build in `dist/frontend/browser/`.

6. **Deploy to Firebase Hosting**:
   ```bash
   firebase deploy --only hosting
   ```

   Or deploy to a specific hosting site:
   ```bash
   firebase deploy --only hosting:<site-id>
   ```

7. **Verify deployment**:
   - Check the Firebase Console: https://console.firebase.google.com
   - Visit your Firebase Hosting URL (e.g., `https://your-project.web.app`)


## Contributors 


We gratefully acknowledge the following key contributors:
- [Leticia De Bortoli](https://www.linkedin.com/in/leticiadebortoli/): Lead Designer. Contributed UI/UX concepts, design assets, and frontend conceptualization.
- [Megan De Bortoli Zinka](https://www.linkedin.com/in/megandbz/) Lead Developer, contributed architectural ideas and backend conceptualization


## License

This project is dual-licensed:

1.  **The Source Code** is licensed under the [MIT License](./LICENSE).
2.  **The Design Assets** (images, logos, UI concepts) created by [Leticia De Bortoli](https://www.linkedin.com/in/leticiadebortoli/) are licensed under the [Creative Commons Attribution 4.0 International License (CC BY 4.0)](./LICENSE-ASSETS).