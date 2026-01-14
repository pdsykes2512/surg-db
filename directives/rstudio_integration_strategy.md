# RStudio Integration Strategy for IMPACT

## Executive Summary

This document outlines the strategy for integrating RStudio Server into the IMPACT application to enable advanced statistical analysis, data visualization, and reporting capabilities for clinical audit data.

**Goal:** Provide clinicians and data analysts with a familiar R environment for:
- Complex statistical analysis of surgical outcomes
- Custom data visualizations beyond the built-in dashboard
- Ad-hoc querying and exploratory data analysis
- Generation of publication-ready reports and figures
- Advanced predictive modeling and risk stratification

---

## Architecture Overview

### Integration Approach: **Embedded RStudio Server with Secure API Bridge**

```
┌─────────────────────────────────────────────────────────────┐
│                    IMPACT Frontend (React)                   │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ Dashboard  │  │   Reports    │  │  RStudio Portal  │    │
│  │   Page     │  │     Page     │  │   (New Page)     │    │
│  └────────────┘  └──────────────┘  └──────────────────┘    │
│                                            │                 │
│                                            ▼                 │
│                              ┌──────────────────────┐       │
│                              │  Embedded RStudio    │       │
│                              │  (iframe with SSO)   │       │
│                              └──────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│              IMPACT Backend (FastAPI - Port 8000)           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            New: RStudio API Gateway                   │  │
│  │  • POST /api/rstudio/auth      (SSO token exchange)  │  │
│  │  • GET  /api/rstudio/session   (Create R session)    │  │
│  │  • GET  /api/rstudio/datasets  (List available data) │  │
│  │  • POST /api/rstudio/export    (Export datasets)     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│           RStudio Server (Port 8787 - Internal Only)        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • RStudio IDE with R 4.x                            │  │
│  │  • Pre-installed packages: mongolite, tidyverse,     │  │
│  │    survival, caret, plotly, rmarkdown                │  │
│  │  • Reverse proxy authentication (no separate login)  │  │
│  │  • User workspace isolation (per-user directories)   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│               MongoDB (Port 27017 - Localhost)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  impact (clinical data)                              │  │
│  │  • Read-only access for RStudio users                │  │
│  │  • Connection via mongolite R package                │  │
│  │  • Pre-configured helper functions in R environment  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Approach

### Option 1: **Embedded RStudio Server** (RECOMMENDED)

**Description:** Install RStudio Server on the same VPS, configure reverse proxy authentication via nginx, embed in frontend via iframe with SSO token passing.

**Pros:**
- Seamless user experience (single login, embedded IDE)
- Full control over R environment and packages
- Direct MongoDB access (localhost connection, fast)
- User workspace persistence
- No additional infrastructure costs
- Can restrict access via IMPACT role-based permissions

**Cons:**
- Additional server resource usage (RAM/CPU)
- Requires RStudio Server installation and configuration
- Need to manage R package dependencies

**Best for:** Organizations wanting integrated, seamless analytics without external dependencies.

---

### Option 2: **RStudio Connect with API-Based Data Export**

**Description:** Use RStudio Connect or standalone RStudio Server with API endpoints that export data from IMPACT on-demand.

**Pros:**
- RStudio runs independently (can be on separate server)
- Easier to scale horizontally
- Clear separation of concerns
- Users can use local RStudio Desktop if preferred

**Cons:**
- Less seamless UX (separate login, data export steps)
- Data export latency for large datasets
- Need to manage exported files (.csv/.rds)
- Users need to manually refresh data

**Best for:** Organizations with existing RStudio infrastructure or preferring separation.

---

### Option 3: **Jupyter with R Kernel + MongoDB**

**Description:** Alternative approach using JupyterLab with R kernel instead of RStudio.

**Pros:**
- Lighter weight than RStudio Server
- Multi-language support (Python + R in same notebook)
- Modern notebook interface
- Good package ecosystem

**Cons:**
- Not the familiar RStudio IDE (learning curve for R users)
- Less mature R tooling compared to RStudio
- Need to manage Jupyter installation

**Best for:** Teams comfortable with Jupyter or wanting Python + R flexibility.

---

## Recommended Approach: **Option 1 - Embedded RStudio Server**

Based on the IMPACT application requirements, **Option 1** is recommended because:
1. ✅ Provides seamless user experience (embedded in IMPACT UI)
2. ✅ Leverages existing authentication (JWT SSO)
3. ✅ Direct MongoDB access (fast, no data duplication)
4. ✅ Familiar RStudio environment for clinicians
5. ✅ Full control over security and access permissions
6. ✅ User workspaces persist (save scripts, outputs)

---

## Technical Implementation Plan

### Phase 1: RStudio Server Installation & Configuration

#### 1.1 Install RStudio Server on VPS

```bash
# Install R 4.x
sudo apt update
sudo apt install -y r-base r-base-dev

# Install RStudio Server (open source edition)
wget https://download2.rstudio.org/server/jammy/amd64/rstudio-server-2024.12.0-467-amd64.deb
sudo dpkg -i rstudio-server-2024.12.0-467-amd64.deb
sudo apt install -f  # Fix dependencies if needed

# Configure RStudio to listen on localhost only (not exposed to internet)
sudo sh -c 'echo "www-address=127.0.0.1" >> /etc/rstudio/rserver.conf'

# Enable reverse proxy authentication (no separate RStudio login)
sudo sh -c 'echo "auth-proxy=1" >> /etc/rstudio/rserver.conf'
sudo sh -c 'echo "auth-proxy-sign-in-url=http://localhost:3000/login" >> /etc/rstudio/rserver.conf'

# Restart RStudio Server
sudo systemctl restart rstudio-server
sudo systemctl enable rstudio-server
```

#### 1.2 Install Essential R Packages

```bash
# Create R package installation script
sudo su - -c "R -e \"install.packages(c(
  'mongolite',      # MongoDB connector
  'tidyverse',      # Data manipulation (dplyr, ggplot2, etc.)
  'survival',       # Survival analysis (Kaplan-Meier, Cox models)
  'caret',          # Machine learning
  'plotly',         # Interactive plots
  'rmarkdown',      # Report generation
  'knitr',          # Dynamic documents
  'DT',             # Interactive tables
  'lubridate',      # Date handling
  'stringr',        # String manipulation
  'scales',         # Axis formatting
  'patchwork',      # Combine plots
  'broom',          # Tidy model outputs
  'glmnet',         # Regularized regression
  'randomForest',   # Random forests
  'pROC',           # ROC curves
  'tableone'        # Table 1 generation
), repos='https://cloud.r-project.org/')\""
```

#### 1.3 Create IMPACT R Helper Library

Create `/usr/local/lib/R/site-library/impactdb/R/impact_helpers.R`:

```r
# IMPACT Database Connection Helper Functions
library(mongolite)

# Global connection settings (read from environment)
MONGO_URI <- Sys.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME <- "impact"

#' Connect to IMPACT MongoDB Database
#'
#' @param collection_name Name of collection (patients, episodes, treatments, tumours)
#' @return mongolite connection object
#' @export
impact_connect <- function(collection_name) {
  mongo(
    collection = collection_name,
    db = DB_NAME,
    url = MONGO_URI
  )
}

#' Get all patients with demographics
#'
#' @param fields Optional character vector of fields to include
#' @return data.frame of patient data
#' @export
get_patients <- function(fields = NULL) {
  conn <- impact_connect("patients")

  # Define query and fields
  query <- '{}'
  field_spec <- if (!is.null(fields)) {
    paste0('{"', paste(fields, collapse = '":1,"'), '":1}')
  } else {
    '{}'
  }

  # Fetch data
  data <- conn$find(query = query, fields = field_spec)
  conn$disconnect()

  return(data)
}

#' Get all episodes with optional filtering
#'
#' @param condition_type Optional filter: "cancer", "ibd", "benign"
#' @param cancer_type Optional filter: "bowel", "kidney", etc.
#' @return data.frame of episode data
#' @export
get_episodes <- function(condition_type = NULL, cancer_type = NULL) {
  conn <- impact_connect("episodes")

  # Build query
  query_parts <- list()
  if (!is.null(condition_type)) {
    query_parts <- c(query_parts, paste0('"condition_type":"', condition_type, '"'))
  }
  if (!is.null(cancer_type)) {
    query_parts <- c(query_parts, paste0('"cancer_type":"', cancer_type, '"'))
  }

  query <- if (length(query_parts) > 0) {
    paste0('{', paste(query_parts, collapse = ','), '}')
  } else {
    '{}'
  }

  # Fetch data
  data <- conn$find(query = query)
  conn$disconnect()

  return(data)
}

#' Get all treatments with optional filtering
#'
#' @param treatment_type Optional filter: "surgery_primary", "chemotherapy", etc.
#' @param surgeon Optional surgeon name filter
#' @return data.frame of treatment data
#' @export
get_treatments <- function(treatment_type = NULL, surgeon = NULL) {
  conn <- impact_connect("treatments")

  # Build query
  query_parts <- list()
  if (!is.null(treatment_type)) {
    query_parts <- c(query_parts, paste0('"treatment_type":"', treatment_type, '"'))
  }
  if (!is.null(surgeon)) {
    query_parts <- c(query_parts, paste0('"surgeon":"', surgeon, '"'))
  }

  query <- if (length(query_parts) > 0) {
    paste0('{', paste(query_parts, collapse = ','), '}')
  } else {
    '{}'
  }

  # Fetch data
  data <- conn$find(query = query)
  conn$disconnect()

  return(data)
}

#' Get surgical outcomes dataset (joined patients + episodes + treatments)
#'
#' @param condition_type Optional filter: "cancer", "ibd", "benign"
#' @return data.frame with joined data
#' @export
get_surgical_outcomes <- function(condition_type = NULL) {
  library(dplyr)

  # Get data from collections
  patients <- get_patients()
  episodes <- get_episodes(condition_type = condition_type)
  treatments <- get_treatments(treatment_type = "surgery_primary")

  # Join datasets
  outcomes <- treatments %>%
    left_join(episodes, by = c("episode_id" = "episode_id")) %>%
    left_join(patients, by = c("patient_id.x" = "patient_id"))

  # Calculate additional fields
  outcomes <- outcomes %>%
    mutate(
      # Calculate age at surgery
      age_at_surgery = ifelse(
        !is.na(admission_date) & !is.na(date_of_birth),
        as.numeric(difftime(admission_date, date_of_birth, units = "days")) / 365.25,
        NA
      ),

      # Binary outcome flags
      had_complication = ifelse(is.na(complications), FALSE, complications),
      had_readmission = ifelse(is.na(readmission_30day), FALSE, readmission_30day),
      had_mortality_30day = ifelse(is.na(mortality_30day), FALSE, mortality_30day),
      had_mortality_90day = ifelse(is.na(mortality_90day), FALSE, mortality_90day),
      had_rtt = ifelse(is.na(return_to_theatre), FALSE, return_to_theatre),
      had_icu = ifelse(is.na(icu_admission), FALSE, icu_admission),

      # Calculate length of stay
      los_days = ifelse(
        !is.na(admission_date) & !is.na(discharge_date),
        as.numeric(difftime(discharge_date, admission_date, units = "days")),
        NA
      )
    )

  return(outcomes)
}

#' Get tumour staging data
#'
#' @param cancer_type Optional filter: "bowel", "kidney", etc.
#' @return data.frame of tumour data
#' @export
get_tumours <- function(cancer_type = NULL) {
  conn <- impact_connect("tumours")

  # Fetch tumours
  tumours <- conn$find(query = '{}')
  conn$disconnect()

  # Join with episodes to get cancer type filter
  if (!is.null(cancer_type)) {
    episodes <- get_episodes(cancer_type = cancer_type)
    tumours <- tumours %>%
      inner_join(episodes %>% select(episode_id), by = "episode_id")
  }

  return(tumours)
}

#' Calculate summary statistics for surgical outcomes
#'
#' @param data data.frame from get_surgical_outcomes()
#' @return data.frame with summary metrics
#' @export
calculate_outcome_summary <- function(data) {
  library(dplyr)

  summary <- data %>%
    summarise(
      total_surgeries = n(),
      complication_rate = mean(had_complication, na.rm = TRUE) * 100,
      readmission_rate = mean(had_readmission, na.rm = TRUE) * 100,
      mortality_30day_rate = mean(had_mortality_30day, na.rm = TRUE) * 100,
      mortality_90day_rate = mean(had_mortality_90day, na.rm = TRUE) * 100,
      rtt_rate = mean(had_rtt, na.rm = TRUE) * 100,
      icu_rate = mean(had_icu, na.rm = TRUE) * 100,
      median_los = median(los_days, na.rm = TRUE)
    )

  return(summary)
}

# Print helper message when library is loaded
.onAttach <- function(libname, pkgname) {
  packageStartupMessage("IMPACT Database Helper Functions Loaded")
  packageStartupMessage("Available functions:")
  packageStartupMessage("  - impact_connect(collection_name)")
  packageStartupMessage("  - get_patients(fields = NULL)")
  packageStartupMessage("  - get_episodes(condition_type = NULL, cancer_type = NULL)")
  packageStartupMessage("  - get_treatments(treatment_type = NULL, surgeon = NULL)")
  packageStartupMessage("  - get_surgical_outcomes(condition_type = NULL)")
  packageStartupMessage("  - get_tumours(cancer_type = NULL)")
  packageStartupMessage("  - calculate_outcome_summary(data)")
  packageStartupMessage("")
  packageStartupMessage("Example usage:")
  packageStartupMessage("  library(impactdb)")
  packageStartupMessage("  outcomes <- get_surgical_outcomes(condition_type = 'cancer')")
  packageStartupMessage("  summary <- calculate_outcome_summary(outcomes)")
}
```

---

### Phase 2: Backend API Integration

#### 2.1 Create RStudio Authentication Bridge

Create `backend/app/routes/rstudio.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from app.auth import get_current_active_user
from app.models.user import User
import httpx
import os

router = APIRouter(prefix="/api/rstudio", tags=["rstudio"])

RSTUDIO_BASE_URL = "http://localhost:8787"  # RStudio Server URL (internal)


@router.get("/auth")
async def rstudio_auth(
    current_user: User = Depends(get_current_active_user)
):
    """
    Create authenticated session for RStudio Server using reverse proxy auth.
    Returns a redirect URL to RStudio with authentication headers.
    """
    # Check if user has permission to use RStudio
    # (e.g., only surgeons and admins)
    allowed_roles = ["admin", "surgeon"]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="RStudio access is restricted to surgeons and administrators"
        )

    # Create RStudio session with user info
    # RStudio will use X-Auth-Username header for authentication
    headers = {
        "X-Auth-Username": current_user.email,
        "X-Auth-Name": current_user.full_name
    }

    # Return redirect URL with authentication info
    # Frontend will open this in iframe with credentials
    return {
        "redirect_url": f"{RSTUDIO_BASE_URL}/",
        "username": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role
    }


@router.get("/datasets")
async def list_available_datasets(
    current_user: User = Depends(get_current_active_user)
):
    """
    List available datasets that can be loaded into RStudio.
    Provides metadata about collections and typical use cases.
    """
    datasets = [
        {
            "name": "patients",
            "description": "Patient demographics and medical history",
            "fields": [
                "patient_id", "mrn", "nhs_number", "date_of_birth",
                "gender", "ethnicity", "bmi", "smoking_status"
            ],
            "row_count_estimate": "~1000",
            "r_function": "get_patients()"
        },
        {
            "name": "episodes",
            "description": "Clinical episodes (cancer, IBD, benign)",
            "fields": [
                "episode_id", "patient_id", "condition_type", "cancer_type",
                "referral_date", "lead_clinician", "episode_status"
            ],
            "row_count_estimate": "~1500",
            "r_function": "get_episodes(condition_type = 'cancer')"
        },
        {
            "name": "treatments",
            "description": "Surgical and oncology treatments",
            "fields": [
                "treatment_id", "episode_id", "treatment_type", "admission_date",
                "surgeon", "asa_score", "complications", "mortality_30day"
            ],
            "row_count_estimate": "~2000",
            "r_function": "get_treatments(treatment_type = 'surgery_primary')"
        },
        {
            "name": "tumours",
            "description": "Tumour staging and pathology",
            "fields": [
                "tumour_id", "episode_id", "tnm_clinical_t", "tnm_clinical_n",
                "tnm_pathological_t", "grade", "crm_status"
            ],
            "row_count_estimate": "~800",
            "r_function": "get_tumours(cancer_type = 'bowel')"
        },
        {
            "name": "surgical_outcomes",
            "description": "Joined dataset: patients + episodes + treatments (surgery only)",
            "fields": [
                "patient_id", "episode_id", "treatment_id", "age_at_surgery",
                "asa_score", "complications", "readmission_30day",
                "mortality_30day", "los_days"
            ],
            "row_count_estimate": "~1000",
            "r_function": "get_surgical_outcomes(condition_type = 'cancer')"
        }
    ]

    return {"datasets": datasets}


@router.get("/health")
async def rstudio_health_check():
    """
    Check if RStudio Server is running and accessible.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{RSTUDIO_BASE_URL}/", timeout=5.0)
            if response.status_code == 200:
                return {"status": "healthy", "message": "RStudio Server is running"}
            else:
                return {"status": "unhealthy", "message": f"RStudio returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Cannot connect to RStudio: {str(e)}"}
```

#### 2.2 Register RStudio Routes in Main App

Add to `backend/app/main.py`:

```python
from app.routes import rstudio

# Register RStudio routes
app.include_router(rstudio.router)
```

---

### Phase 3: Frontend Integration

#### 3.1 Create RStudio Page Component

Create `frontend/src/pages/RStudioPage.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../utils/api';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import LoadingSpinner from '../components/common/LoadingSpinner';

interface RStudioAuthResponse {
  redirect_url: string;
  username: string;
  full_name: string;
  role: string;
}

interface Dataset {
  name: string;
  description: string;
  fields: string[];
  row_count_estimate: string;
  r_function: string;
}

const RStudioPage: React.FC = () => {
  const { user } = useAuth();
  const [authData, setAuthData] = useState<RStudioAuthResponse | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeRStudio = async () => {
      try {
        // Get RStudio authentication token
        const authResponse = await api.get<RStudioAuthResponse>('/api/rstudio/auth');
        setAuthData(authResponse.data);

        // Get available datasets
        const datasetsResponse = await api.get<{ datasets: Dataset[] }>('/api/rstudio/datasets');
        setDatasets(datasetsResponse.data.datasets);

        setLoading(false);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to initialize RStudio');
        setLoading(false);
      }
    };

    initializeRStudio();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <PageHeader
          title="RStudio Analytics"
          description="Access restricted or RStudio unavailable"
        />
        <Card>
          <div className="text-red-600 p-4">
            <p className="font-semibold">Error:</p>
            <p>{error}</p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6">
      <PageHeader
        title="RStudio Analytics"
        description="Advanced statistical analysis and custom reporting with R"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* RStudio IDE */}
        <div className="lg:col-span-2">
          <Card>
            <div className="p-4 border-b">
              <h3 className="text-lg font-semibold">RStudio IDE</h3>
              <p className="text-sm text-gray-600">
                Connected as {authData?.full_name} ({authData?.username})
              </p>
            </div>
            <div className="relative" style={{ height: '800px' }}>
              <iframe
                src={authData?.redirect_url}
                className="w-full h-full border-0"
                title="RStudio Server"
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
              />
            </div>
          </Card>
        </div>

        {/* Dataset Documentation */}
        <div>
          <Card>
            <div className="p-4 border-b">
              <h3 className="text-lg font-semibold">Available Datasets</h3>
              <p className="text-sm text-gray-600">
                Use these helper functions in your R scripts
              </p>
            </div>
            <div className="p-4 space-y-4 max-h-[760px] overflow-y-auto">
              {datasets.map((dataset) => (
                <div key={dataset.name} className="border-b pb-4 last:border-b-0">
                  <h4 className="font-semibold text-sm text-gray-900">
                    {dataset.name}
                  </h4>
                  <p className="text-xs text-gray-600 mt-1">
                    {dataset.description}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Approx. {dataset.row_count_estimate} records
                  </p>
                  <div className="mt-2 bg-gray-100 p-2 rounded">
                    <code className="text-xs font-mono text-purple-700">
                      {dataset.r_function}
                    </code>
                  </div>
                  <details className="mt-2">
                    <summary className="text-xs text-gray-600 cursor-pointer">
                      View fields ({dataset.fields.length})
                    </summary>
                    <ul className="mt-1 text-xs text-gray-500 pl-4 list-disc">
                      {dataset.fields.slice(0, 10).map((field) => (
                        <li key={field}>{field}</li>
                      ))}
                      {dataset.fields.length > 10 && (
                        <li>...and {dataset.fields.length - 10} more</li>
                      )}
                    </ul>
                  </details>
                </div>
              ))}
            </div>
          </Card>

          {/* Quick Start Guide */}
          <Card className="mt-4">
            <div className="p-4 border-b">
              <h3 className="text-lg font-semibold">Quick Start</h3>
            </div>
            <div className="p-4 text-sm space-y-2">
              <p className="font-semibold">1. Load the IMPACT library:</p>
              <div className="bg-gray-100 p-2 rounded">
                <code className="text-xs font-mono">library(impactdb)</code>
              </div>

              <p className="font-semibold mt-4">2. Fetch surgical outcomes:</p>
              <div className="bg-gray-100 p-2 rounded">
                <code className="text-xs font-mono">
                  outcomes &lt;- get_surgical_outcomes()
                </code>
              </div>

              <p className="font-semibold mt-4">3. Calculate summary stats:</p>
              <div className="bg-gray-100 p-2 rounded">
                <code className="text-xs font-mono">
                  summary &lt;- calculate_outcome_summary(outcomes)
                </code>
              </div>

              <p className="font-semibold mt-4">4. Visualize:</p>
              <div className="bg-gray-100 p-2 rounded">
                <code className="text-xs font-mono">
                  library(ggplot2)<br />
                  ggplot(outcomes, aes(x=asa_score)) + geom_bar()
                </code>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default RStudioPage;
```

#### 3.2 Add Route to Frontend

Update `frontend/src/App.tsx` to include RStudio route:

```typescript
import RStudioPage from './pages/RStudioPage';

// In the Routes section:
<Route
  path="/rstudio"
  element={
    <ProtectedRoute requiredRoles={['admin', 'surgeon']}>
      <RStudioPage />
    </ProtectedRoute>
  }
/>
```

#### 3.3 Add Navigation Link

Update `frontend/src/components/Layout.tsx` to add RStudio nav item:

```typescript
{hasRole(['admin', 'surgeon']) && (
  <NavLink
    to="/rstudio"
    icon={ChartBarIcon}
    label="RStudio Analytics"
  />
)}
```

---

### Phase 4: Nginx Reverse Proxy Configuration

Add to nginx configuration (usually `/etc/nginx/sites-available/impact.vps`):

```nginx
# RStudio Server proxy (requires authentication)
location /rstudio/ {
    # Only accessible to authenticated users (handled by backend)
    proxy_pass http://127.0.0.1:8787/;

    # WebSocket support (required for RStudio)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # Pass authentication headers
    proxy_set_header X-Auth-Username $http_x_auth_username;
    proxy_set_header X-Auth-Name $http_x_auth_name;

    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Timeouts (RStudio sessions can be long)
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

Reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Security Considerations

### 1. **Access Control**
- Only users with `admin` or `surgeon` roles can access RStudio
- Enforced at backend API level (FastAPI route dependencies)
- Frontend hides RStudio nav link for unauthorized users

### 2. **Authentication Flow**
- Users authenticate once via IMPACT login (JWT)
- JWT token verified before RStudio session creation
- RStudio uses reverse proxy authentication (no separate login)
- Session tied to IMPACT user identity

### 3. **Data Access Permissions**
- RStudio has READ-ONLY access to MongoDB
- Create dedicated MongoDB user with read-only permissions:

```javascript
// Run in MongoDB shell
use impact
db.createUser({
  user: "rstudio_reader",
  pwd: "SECURE_PASSWORD_HERE",
  roles: [
    { role: "read", db: "impact" }
  ]
})
```

Update R helper library to use read-only credentials:
```r
MONGO_URI <- "mongodb://rstudio_reader:PASSWORD@localhost:27017/impact"
```

### 4. **Network Isolation**
- RStudio Server listens on localhost only (127.0.0.1:8787)
- NOT exposed to internet directly
- Only accessible via nginx reverse proxy
- nginx enforces authentication headers

### 5. **User Workspace Isolation**
- Each user gets isolated workspace directory
- RStudio Server creates `/home/{username}` directories
- Users cannot access other users' R scripts or outputs

### 6. **Sensitive Data Handling**
- NHS numbers, MRN, DOB, postcodes remain encrypted in MongoDB
- R helper functions should NOT decrypt sensitive fields
- If decryption needed, require additional explicit user consent
- Consider anonymization for non-clinical users

### 7. **Audit Logging**
- Log RStudio access attempts to audit_logs collection:
  - user_id, timestamp, action: "rstudio_access"
  - IP address, session duration
- MongoDB query logging (enable in MongoDB config if needed)

---

## Example Use Cases

### 1. **Kaplan-Meier Survival Analysis**

```r
library(impactdb)
library(survival)
library(survminer)

# Get surgical outcomes for bowel cancer
outcomes <- get_surgical_outcomes(condition_type = "cancer")

# Filter for bowel cancer only
bowel_outcomes <- outcomes %>%
  filter(cancer_type == "bowel")

# Create survival object (90-day mortality)
surv_obj <- Surv(
  time = rep(90, nrow(bowel_outcomes)),  # Follow-up time
  event = bowel_outcomes$had_mortality_90day  # Event indicator
)

# Fit Kaplan-Meier by ASA score
km_fit <- survfit(surv_obj ~ asa_score, data = bowel_outcomes)

# Plot
ggsurvplot(
  km_fit,
  data = bowel_outcomes,
  pval = TRUE,
  risk.table = TRUE,
  title = "90-Day Survival by ASA Score",
  xlab = "Days",
  ylab = "Survival Probability"
)
```

### 2. **Risk Prediction Model (Complications)**

```r
library(impactdb)
library(caret)
library(pROC)

# Get surgical outcomes
outcomes <- get_surgical_outcomes()

# Prepare modeling dataset
model_data <- outcomes %>%
  select(
    had_complication,  # Outcome
    age_at_surgery, bmi, asa_score,
    smoking_status, urgency_classification
  ) %>%
  na.omit()

# Split train/test
set.seed(123)
train_idx <- createDataPartition(model_data$had_complication, p = 0.7, list = FALSE)
train <- model_data[train_idx, ]
test <- model_data[-train_idx, ]

# Train logistic regression
model <- glm(
  had_complication ~ age_at_surgery + bmi + asa_score + urgency_classification,
  data = train,
  family = binomial
)

# Predict on test set
pred_probs <- predict(model, test, type = "response")

# Calculate ROC AUC
roc_obj <- roc(test$had_complication, pred_probs)
auc(roc_obj)

# Plot ROC curve
plot(roc_obj, main = "Complication Risk Prediction Model")
```

### 3. **Surgeon Performance Comparison (Funnel Plot)**

```r
library(impactdb)
library(ggplot2)

# Get treatments by surgeon
treatments <- get_treatments(treatment_type = "surgery_primary")

# Calculate per-surgeon complication rates
surgeon_summary <- treatments %>%
  group_by(surgeon) %>%
  summarise(
    n_surgeries = n(),
    complication_rate = mean(complications, na.rm = TRUE) * 100
  ) %>%
  filter(n_surgeries >= 20)  # Minimum 20 cases

# Calculate control limits (95% and 99.8%)
overall_rate <- mean(treatments$complications, na.rm = TRUE)
surgeon_summary <- surgeon_summary %>%
  mutate(
    expected_rate = overall_rate * 100,
    se = sqrt((overall_rate * (1 - overall_rate)) / n_surgeries) * 100,
    lower_95 = expected_rate - 1.96 * se,
    upper_95 = expected_rate + 1.96 * se,
    lower_99 = expected_rate - 3.09 * se,
    upper_99 = expected_rate + 3.09 * se
  )

# Funnel plot
ggplot(surgeon_summary, aes(x = n_surgeries, y = complication_rate)) +
  geom_point(size = 3) +
  geom_line(aes(y = expected_rate), color = "blue") +
  geom_line(aes(y = lower_95), color = "orange", linetype = "dashed") +
  geom_line(aes(y = upper_95), color = "orange", linetype = "dashed") +
  geom_line(aes(y = lower_99), color = "red", linetype = "dashed") +
  geom_line(aes(y = upper_99), color = "red", linetype = "dashed") +
  labs(
    title = "Surgeon Complication Rate Funnel Plot",
    x = "Number of Surgeries",
    y = "Complication Rate (%)",
    caption = "Orange: 95% CI, Red: 99.8% CI"
  ) +
  theme_minimal()
```

### 4. **Table 1 Generation (Publication-Ready)**

```r
library(impactdb)
library(tableone)

# Get surgical outcomes
outcomes <- get_surgical_outcomes(condition_type = "cancer")

# Define variables for Table 1
vars <- c(
  "age_at_surgery", "gender", "bmi", "asa_score",
  "urgency_classification", "had_complication",
  "readmission_30day", "mortality_30day", "los_days"
)

# Categorical variables
cat_vars <- c("gender", "asa_score", "urgency_classification")

# Create Table 1 stratified by complication status
table1 <- CreateTableOne(
  vars = vars,
  strata = "had_complication",
  data = outcomes,
  factorVars = cat_vars,
  test = TRUE
)

# Print with formatting
print(table1, formatOptions = list(big.mark = ","))

# Export to CSV
write.csv(
  print(table1, printToggle = FALSE),
  file = "table1_complications.csv"
)
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Install R 4.x on VPS
- [ ] Install RStudio Server (open source edition)
- [ ] Install required R packages (mongolite, tidyverse, survival, etc.)
- [ ] Create IMPACT R helper library (`impactdb`)
- [ ] Create MongoDB read-only user (`rstudio_reader`)
- [ ] Configure RStudio Server for reverse proxy auth
- [ ] Set RStudio to listen on localhost only

### Backend Changes
- [ ] Create `backend/app/routes/rstudio.py`
- [ ] Register RStudio routes in `main.py`
- [ ] Add RStudio role permission checks
- [ ] Test `/api/rstudio/auth` endpoint
- [ ] Test `/api/rstudio/datasets` endpoint
- [ ] Test `/api/rstudio/health` endpoint

### Frontend Changes
- [ ] Create `frontend/src/pages/RStudioPage.tsx`
- [ ] Add RStudio route to `App.tsx`
- [ ] Add navigation link to `Layout.tsx`
- [ ] Build frontend with RStudio changes

### Nginx Configuration
- [ ] Add RStudio reverse proxy block to nginx config
- [ ] Test WebSocket support (RStudio requires it)
- [ ] Validate authentication header passing
- [ ] Test nginx config with `nginx -t`
- [ ] Reload nginx

### Services Restart
- [ ] Restart RStudio Server: `sudo systemctl restart rstudio-server`
- [ ] Restart backend: `sudo systemctl restart impact-backend`
- [ ] Restart frontend: `sudo systemctl restart impact-frontend`

### Testing & Validation
- [ ] Log in as surgeon user
- [ ] Navigate to RStudio page
- [ ] Verify iframe loads RStudio IDE
- [ ] Test MongoDB connection in R: `library(mongolite); mongo("patients")$count()`
- [ ] Load impactdb library: `library(impactdb)`
- [ ] Test helper functions: `get_patients()`, `get_surgical_outcomes()`
- [ ] Create test visualization (e.g., `ggplot(outcomes, aes(x=asa_score)) + geom_bar()`)
- [ ] Verify user isolation (create file, log in as different user, verify can't see)
- [ ] Test read-only access (attempt to insert into MongoDB, should fail)

### Security Validation
- [ ] Verify RStudio not accessible via direct port 8787 access
- [ ] Confirm unauthorized users (data_entry, viewer) cannot access
- [ ] Check audit logs for RStudio access events
- [ ] Validate MongoDB read-only user permissions

### Documentation
- [ ] Update `RECENT_CHANGES.md` with RStudio integration notes
- [ ] Create user guide for RStudio features (for surgeons)
- [ ] Document R helper functions (`impactdb` package)
- [ ] Add troubleshooting section for common RStudio issues

---

## Maintenance & Monitoring

### Regular Updates
- **R Packages:** Monthly updates via `update.packages()` as root
- **RStudio Server:** Check for security updates quarterly
- **MongoDB Connector:** Ensure mongolite package is current

### Resource Monitoring
- **CPU/RAM:** RStudio can be resource-intensive (monitor with `htop`)
- **Disk Space:** User workspaces can grow (set quotas if needed)
- **Session Count:** Limit concurrent RStudio sessions if VPS memory limited

### Backup User Workspaces
- RStudio user data stored in `/home/{username}`
- Consider daily backups of workspace directories
- Automated backup script:

```bash
#!/bin/bash
# /usr/local/bin/backup_rstudio_workspaces.sh
BACKUP_DIR="/var/backups/rstudio-workspaces"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/workspaces-$DATE.tar.gz" /home/*/

# Keep only last 7 days
find "$BACKUP_DIR" -name "workspaces-*.tar.gz" -mtime +7 -delete
```

---

## Alternative Lightweight Option: Shiny Server

If RStudio Server proves too resource-intensive, consider **Shiny Server** as a lightweight alternative:

**Pros:**
- Lighter weight (just R + Shiny, no IDE)
- Can create pre-built dashboards/apps
- Users interact via web UI (no R coding needed)
- Easier to secure (no arbitrary R code execution)

**Cons:**
- No interactive R console (users can't write custom analyses)
- Requires pre-building Shiny apps
- Less flexible than full RStudio

**Use case:** Best for deploying pre-built analytics dashboards to non-R users.

---

## Cost-Benefit Analysis

### Resource Requirements
- **CPU:** +1-2 cores for concurrent R sessions
- **RAM:** +2-4 GB (1 GB per concurrent RStudio session)
- **Disk:** +2-5 GB (R packages + user workspaces)

### Benefits
- Advanced statistical capabilities not feasible in JavaScript
- Familiar environment for clinicians trained in R
- Enables publication-quality analyses and figures
- Supports complex modeling (survival analysis, risk prediction)
- Reproducible research (R scripts as documentation)

### Risks
- Increased server resource usage
- Additional maintenance burden (R package updates)
- Potential for slow queries if users write inefficient R code
- Need to train users on R helper functions

---

## Conclusion

The **Embedded RStudio Server** approach provides the most seamless and powerful analytics integration for IMPACT. With proper configuration of reverse proxy authentication, read-only MongoDB access, and role-based permissions, this integration enables clinicians to perform sophisticated statistical analyses while maintaining data security and audit compliance.

**Next Steps:**
1. Review this strategy document with stakeholders
2. Allocate time for implementation (estimated 2-3 days)
3. Test in development environment first
4. Roll out to production with phased access (start with 2-3 power users)
5. Gather feedback and iterate on helper functions

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
**Author:** AI Session (Claude Code)
