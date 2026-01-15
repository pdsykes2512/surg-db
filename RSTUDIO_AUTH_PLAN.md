# RStudio Authentication Integration Plan

## Overview
Integrate RStudio authentication with IMPACT's user management system using a single PAM user with per-user directories.

## Architecture

### Current State
- ✅ IMPACT users stored in MongoDB with JWT authentication
- ✅ User roles: admin, surgeon, data_entry, viewer
- ✅ RStudio Server running with PAM auth (single test user)
- ✅ Nginx reverse proxy configured at `/rstudio-server/`
- ✅ Frontend RStudio page with role-based access (surgeon/admin only)

### Target State
- Single PAM user (`rstudio-user`) for all RStudio sessions
- Per-user directories: `/home/rstudio-user/users/<user_email>/`
- RStudio access controlled via IMPACT admin panel (new field: `rstudio_access`)
- Automatic user directory creation/cleanup
- Auth-proxy integration for seamless SSO

---

## Implementation Steps

### Phase 1: Database Schema Update

#### 1.1 Add `rstudio_access` field to User model

**File:** `backend/app/models/user.py`

```python
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = Field(default=UserRole.VIEWER)
    is_active: bool = Field(default=True)
    department: Optional[str] = Field(None, max_length=100)
    job_title: Optional[str] = Field(None, max_length=100)
    rstudio_access: bool = Field(default=False)  # NEW FIELD

class UserUpdate(BaseModel):
    # ... existing fields ...
    rstudio_access: Optional[bool] = None  # NEW FIELD
```

#### 1.2 Update existing users in database

**Script:** `execution/add_rstudio_access_field.py`

```python
"""Add rstudio_access field to all existing users (default: False)"""
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv

async def migrate():
    load_dotenv()
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('SYSTEM_DB_NAME', 'impact_system')]

    # Add rstudio_access=False to all users that don't have it
    result = await db.users.update_many(
        {'rstudio_access': {'$exists': False}},
        {'$set': {'rstudio_access': False}}
    )
    print(f"Updated {result.modified_count} users")

    # Optionally enable for admins and surgeons
    result = await db.users.update_many(
        {'role': {'$in': ['admin', 'surgeon']}},
        {'$set': {'rstudio_access': True}}
    )
    print(f"Enabled RStudio access for {result.modified_count} admin/surgeon users")

    client.close()

if __name__ == '__main__':
    asyncio.run(migrate())
```

---

### Phase 2: RStudio User Directory Management

#### 2.1 Directory Structure

```
/home/rstudio-user/
├── .Rprofile              # Global R startup (loads impactdb library)
├── .Renviron             # Environment variables (MongoDB connection)
└── users/
    ├── admin@impact.local/
    │   ├── .RData
    │   ├── .Rhistory
    │   └── projects/
    ├── surgeon1@hospital.nhs.uk/
    │   └── ...
    └── surgeon2@hospital.nhs.uk/
        └── ...
```

#### 2.2 Directory Management Script

**File:** `execution/manage_rstudio_directories.py`

```python
"""
Manage RStudio user directories - create, cleanup, set permissions
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from dotenv import load_dotenv

RSTUDIO_HOME = Path("/home/rstudio-user")
USERS_DIR = RSTUDIO_HOME / "users"

async def get_rstudio_users() -> List[str]:
    """Get list of users with rstudio_access=True"""
    load_dotenv()
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client[os.getenv('SYSTEM_DB_NAME', 'impact_system')]

    users = await db.users.find(
        {'rstudio_access': True, 'is_active': True},
        {'email': 1}
    ).to_list(None)

    client.close()
    return [u['email'] for u in users]

def create_user_directory(email: str):
    """Create directory for user if it doesn't exist"""
    user_dir = USERS_DIR / email

    if not user_dir.exists():
        user_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {user_dir}")

        # Set ownership to rstudio-user
        subprocess.run(['chown', '-R', 'rstudio-user:rstudio-user', str(user_dir)])

        # Set permissions (rwx for owner, rx for group, no access for others)
        subprocess.run(['chmod', '750', str(user_dir)])
    else:
        print(f"  Directory already exists: {user_dir}")

def cleanup_orphaned_directories(authorized_users: List[str]):
    """Remove directories for users who no longer have RStudio access"""
    if not USERS_DIR.exists():
        return

    existing_dirs = [d.name for d in USERS_DIR.iterdir() if d.is_dir()]
    orphaned = set(existing_dirs) - set(authorized_users)

    for email in orphaned:
        user_dir = USERS_DIR / email
        print(f"⚠️  Archiving orphaned directory: {email}")

        # Archive before deleting (safety measure)
        archive_dir = RSTUDIO_HOME / "archives"
        archive_dir.mkdir(exist_ok=True)

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = archive_dir / f"{email}_{timestamp}.tar.gz"

        subprocess.run(['tar', '-czf', str(archive_path), '-C', str(USERS_DIR), email])
        shutil.rmtree(user_dir)
        print(f"  Archived to: {archive_path}")

async def sync_directories():
    """Sync directories with authorized users"""
    print("Syncing RStudio user directories...")

    # Get authorized users
    authorized_users = await get_rstudio_users()
    print(f"Found {len(authorized_users)} users with RStudio access")

    # Create directories for authorized users
    for email in authorized_users:
        create_user_directory(email)

    # Cleanup orphaned directories
    cleanup_orphaned_directories(authorized_users)

    print("✓ Directory sync complete")

if __name__ == '__main__':
    asyncio.run(sync_directories())
```

---

### Phase 3: RStudio Auth-Proxy Configuration

#### 3.1 Authentication Verification Script

**File:** `/home/rstudio-user/auth-verify.sh`

```bash
#!/bin/bash
# RStudio auth-proxy verification script
# Called by RStudio to verify user authentication

# Get user email from HTTP header passed by nginx
USER_EMAIL="$1"

# Log authentication attempts
echo "$(date): Auth attempt for user: $USER_EMAIL" >> /var/log/rstudio/auth-proxy.log

# Check if user directory exists (meaning they have access)
if [ -d "/home/rstudio-user/users/$USER_EMAIL" ]; then
    echo "$(date): Access granted for: $USER_EMAIL" >> /var/log/rstudio/auth-proxy.log
    exit 0  # Success
else
    echo "$(date): Access denied for: $USER_EMAIL" >> /var/log/rstudio/auth-proxy.log
    exit 1  # Denied
fi
```

**Setup:**
```bash
chmod +x /home/rstudio-user/auth-verify.sh
chown rstudio-user:rstudio-user /home/rstudio-user/auth-verify.sh
mkdir -p /var/log/rstudio
touch /var/log/rstudio/auth-proxy.log
chown rstudio-user:rstudio-user /var/log/rstudio/auth-proxy.log
```

#### 3.2 Update RStudio Server Config

**File:** `/etc/rstudio/rserver.conf`

```conf
# Server Configuration File

# Listen on localhost only (not exposed to internet)
www-address=127.0.0.1

# Port (default is 8787)
www-port=8787

# Root path for nginx reverse proxy
www-root-path=/rstudio-server

# Auth-proxy configuration
auth-proxy=1
auth-proxy-user-header=X-RStudio-User
auth-proxy-sign-in-url=http://impact.vps/login

# Custom working directory per user
rsession-which-r=/usr/bin/R
rsession-ld-library-path=/usr/local/lib/R/site-library

# Allow iframe embedding
www-frame-origin=same
www-enable-origin-check=0
```

#### 3.3 Update RSession Config

**File:** `/etc/rstudio/rsession.conf`

```conf
# R Session Configuration File

# Session timeout settings (in minutes)
session-timeout-minutes=0
session-timeout-suspend=0

# Working directory per user
# RStudio will use: /home/rstudio-user/users/<email>/
session-default-working-dir=/home/rstudio-user/users
session-default-new-project-dir=/home/rstudio-user/users

# Increase session stability
session-save-action-default=no
```

---

### Phase 4: Nginx Configuration Update

#### 4.1 Update nginx RStudio location block

**File:** `/etc/nginx/sites-enabled/default`

Add to the `/rstudio-server/` location block:

```nginx
location /rstudio-server/ {
    # ... existing config ...

    # Pass IMPACT user email to RStudio for auth-proxy
    # This header is set by the backend API
    proxy_set_header X-RStudio-User $http_x_impact_user;

    # ... rest of config ...
}
```

---

### Phase 5: Backend API Updates

#### 5.1 Update RStudio Auth Endpoint

**File:** `backend/app/routes/rstudio.py`

Update the `/api/rstudio/auth` endpoint:

```python
@router.get("/auth")
async def rstudio_auth(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_system_database)
):
    """
    Create authenticated session for RStudio Server.
    Returns redirect URL and user info for RStudio access.

    Checks both role-based access AND rstudio_access flag.
    """
    # Check if user has rstudio_access enabled
    user_doc = await db.users.find_one({'email': current_user['email']})
    if not user_doc or not user_doc.get('rstudio_access', False):
        raise HTTPException(
            status_code=403,
            detail="RStudio access has not been enabled for your account. Please contact an administrator."
        )

    # Check if user is active
    if not user_doc.get('is_active', False):
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive."
        )

    # Construct RStudio URL for nginx proxy
    host = request.headers.get("host", "localhost")
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", host)

    if ":8000" in forwarded_host:
        forwarded_host = forwarded_host.split(":")[0]

    rstudio_url = f"{forwarded_proto}://{forwarded_host}{RSTUDIO_PROXY_PATH}"

    # Return RStudio URL with custom header for auth-proxy
    return {
        "redirect_url": rstudio_url,
        "username": current_user["email"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "rstudio_access": True,
        "message": "RStudio Server is available.",
        "headers": {
            "X-Impact-User": current_user["email"]  # Used by nginx for auth-proxy
        }
    }
```

#### 5.2 Add Directory Management Endpoint

**File:** `backend/app/routes/rstudio.py`

```python
@router.post("/sync-directories")
async def sync_rstudio_directories(
    current_user: dict = Depends(require_admin)
):
    """
    Sync RStudio user directories (admin only).
    Creates directories for users with access, archives orphaned directories.
    """
    import subprocess

    result = subprocess.run(
        ['python3', '/root/impact/execution/manage_rstudio_directories.py'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        return {
            "status": "success",
            "message": "RStudio directories synced successfully",
            "output": result.stdout
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync directories: {result.stderr}"
        )
```

---

### Phase 6: Frontend Admin Panel Updates

#### 6.1 Update User Interface

**File:** `frontend/src/pages/AdminPage.tsx`

Add RStudio access toggle to user management:

```typescript
// Add to User interface
interface User {
  _id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  department?: string
  job_title?: string
  rstudio_access: boolean  // NEW FIELD
  created_at: string
}

// Add toggle function
const toggleRStudioAccess = async (userId: string, currentAccess: boolean) => {
  try {
    await axios.put(
      `${API_URL}/api/admin/users/${userId}`,
      { rstudio_access: !currentAccess },
      { headers: { Authorization: `Bearer ${token}` } }
    )

    // Sync directories after toggling access
    await axios.post(
      `${API_URL}/api/rstudio/sync-directories`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    )

    fetchUsers() // Refresh user list
  } catch (err: any) {
    setError(err.response?.data?.detail || 'Failed to update RStudio access')
  }
}

// Add column to user table
<TableCell>
  <button
    onClick={() => toggleRStudioAccess(user._id, user.rstudio_access)}
    className={`px-3 py-1 rounded text-sm font-medium ${
      user.rstudio_access
        ? 'bg-green-100 text-green-700 hover:bg-green-200'
        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
    }`}
  >
    {user.rstudio_access ? '✓ Enabled' : '✗ Disabled'}
  </button>
</TableCell>
```

---

### Phase 7: Data Access (IMPLEMENTED ✓)

**Status:** Completed 2026-01-15

Instead of direct MongoDB access, we implemented secure API endpoints for RStudio data access:

#### 7.1 API-Based Data Access (Current Implementation)

**Why:** Direct MongoDB access exposes encrypted fields that RStudio cannot decrypt. API-based access allows the backend to:

- Decrypt sensitive fields
- Perform privacy-preserving transformations (dates → years, DOB → age)
- Strip all encrypted/PII fields before sending to R

**Implementation:**

- Backend endpoints: `/api/rstudio/data/{patients,episodes,treatments,tumours}`
- R helper library: `/home/rstudio-user/R/impactdb/impactdb.R`
- Authentication: JWT tokens from IMPACT login
- Helper script: `execution/setup_rstudio_auth.py`

See `RECENT_CHANGES.md` (2026-01-15 entry) for full details.

#### 7.2 MongoDB Read-Only Setup (Deprecated)

**Note:** Direct MongoDB access is deprecated in favor of API endpoints.

The following script is kept for reference only:

**File:** `execution/setup_rstudio_mongodb_user.py`

```python
"""Create MongoDB read-only user for RStudio"""
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

client = pymongo.MongoClient(os.getenv('MONGODB_URI'))
admin_db = client.admin
data_db_name = os.getenv('DATA_DB_NAME', 'impact')

# Create read-only user
admin_db.command({
    'createUser': 'rstudio_reader',
    'pwd': os.getenv('RSTUDIO_MONGODB_PASSWORD', 'rstudio_readonly_pass'),
    'roles': [
        {'role': 'read', 'db': data_db_name}
    ]
})

print(f"✓ Created MongoDB read-only user: rstudio_reader")
print(f"  Database: {data_db_name}")
print(f"  Access: read-only")
```

#### 7.2 Configure R Environment

**File:** `/home/rstudio-user/.Renviron`

```bash
# MongoDB connection for IMPACT data (read-only)
IMPACT_MONGODB_URI="mongodb://rstudio_reader:<password>@localhost:27017/impact?authSource=admin"
IMPACT_DB_NAME="impact"
```

---

## Testing Plan

### Test 1: Basic Access Control
1. Log in as admin to IMPACT
2. Navigate to Admin → Users
3. Toggle RStudio access for a test user
4. Verify directory created in `/home/rstudio-user/users/<email>/`
5. Log in as test user
6. Navigate to RStudio page
7. Verify can access RStudio with auto-login

### Test 2: Access Denial
1. Create user without RStudio access
2. Log in as that user
3. Navigate to RStudio page
4. Verify receives 403 error with clear message
5. Toggle access OFF for a user
6. Verify their directory is archived
7. Verify they can no longer access RStudio

### Test 3: Directory Isolation
1. Log in as User A with RStudio access
2. Create a file in RStudio
3. Log out, log in as User B
4. Verify User B cannot see User A's files
5. Verify User B has their own clean workspace

### Test 4: MongoDB Access
1. Log into RStudio
2. Run: `library(mongolite)`
3. Test connection to IMPACT database
4. Verify can read data
5. Verify CANNOT write/modify data

---

## Migration Checklist

- [ ] Phase 1: Update User model with `rstudio_access` field
- [ ] Run migration script to add field to existing users
- [ ] Phase 2: Create directory management script
- [ ] Test directory creation/cleanup manually
- [ ] Phase 3: Configure RStudio auth-proxy
- [ ] Create auth verification script
- [ ] Update rserver.conf and rsession.conf
- [ ] Phase 4: Update nginx configuration
- [ ] Phase 5: Update backend API endpoints
- [ ] Add `/sync-directories` endpoint
- [ ] Update `/auth` endpoint with access checks
- [ ] Phase 6: Update frontend admin panel
- [ ] Add RStudio access toggle to user table
- [ ] Test toggle functionality
- [ ] Phase 7: Set up MongoDB read-only user
- [ ] Configure R environment variables
- [ ] Install R packages (mongolite, tidyverse, etc.)
- [ ] Testing: Run all test scenarios
- [ ] Documentation: Update RECENT_CHANGES.md

---

## Security Considerations

1. **Directory Permissions:**
   - Each user directory has 750 permissions (owner rwx, group rx, others none)
   - Prevents users from accessing each other's directories

2. **MongoDB Access:**
   - RStudio users have read-only access to data
   - Cannot modify, delete, or create records
   - Separate user from application user

3. **Authentication:**
   - Access controlled at two levels: IMPACT user flag + role
   - Nginx validates authentication before passing to RStudio
   - RStudio auth-proxy verifies directory exists

4. **Audit Trail:**
   - All access logged to `/var/log/rstudio/auth-proxy.log`
   - Directory changes logged by management script
   - Orphaned directories archived (not deleted)

---

## Rollback Plan

If issues occur:
1. Revert `/etc/rstudio/rserver.conf` to simple PAM auth
2. Use `rstudio-user` / `rstudio123` for manual login
3. Revert backend API changes
4. Re-deploy frontend
5. Users can still access RStudio (just not auto-login)

---

## Future Enhancements

1. **Workspace Quotas:**
   - Set disk quota per user directory
   - Alert when approaching limit

2. **Usage Analytics:**
   - Track RStudio session duration
   - Monitor R package installations
   - Resource usage metrics

3. **Shared Workspaces:**
   - Create team directories
   - Collaborative R projects

4. **Backup Integration:**
   - Include user RStudio directories in database backups
   - Automatic backup before directory cleanup
