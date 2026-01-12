# Session Timeout Implementation

## Overview

This document describes the session timeout and automatic token refresh implementation for the IMPACT application.

## Features

### 1. Automatic Session Timeout
- Sessions expire after **30 minutes** of user inactivity
- Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable
- Tracks mouse, keyboard, touch, and scroll events as activity

### 2. Warning Dialog
- Users receive a warning **5 minutes** before session expiration
- Shows countdown timer with remaining time
- Provides options to:
  - **Continue Session**: Refreshes the token and extends the session
  - **Logout Now**: Immediately ends the session

### 3. Automatic Token Refresh
- Access tokens are automatically refreshed when 10 minutes or less remain
- Uses refresh tokens with 7-day validity
- Implements token rotation for enhanced security

### 4. Intended Destination Redirect
- Saves the current page when session expires
- Automatically redirects to the intended page after re-login
- Provides seamless user experience

### 5. Session Expired Message
- Login page displays a notification when users are redirected due to timeout
- Clear messaging explains why they need to log in again

## Configuration

### Backend (backend/app/config.py)
```python
access_token_expire_minutes: int = 30  # Session timeout (default: 30 min)
refresh_token_expire_days: int = 7     # Refresh token validity (default: 7 days)
session_warning_minutes: int = 5       # Warning before timeout (default: 5 min)
```

Set via environment variables:
```bash
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
SESSION_WARNING_MINUTES=5
```

### Frontend (contexts/AuthContext.tsx)
```typescript
const manager = getSessionManager({
  timeoutMinutes: 30,              // Match backend ACCESS_TOKEN_EXPIRE_MINUTES
  warningMinutes: 5,               // Warning 5 min before expiry
  refreshThresholdMinutes: 10      // Auto-refresh when 10 min remain
})
```

## Security Features

- **Token Rotation**: Refresh tokens are rotated on every refresh, invalidating old tokens
- **Token Type Validation**: Access and refresh tokens have different types and cannot be interchanged
- **Secure Storage**: Tokens stored in localStorage with expiry timestamps
- **Activity Tracking**: Comprehensive event tracking (mouse, keyboard, touch, scroll)

## User Experience Flow

### Normal Usage
1. User logs in → 30-minute session starts
2. User interacts → Timer resets on each activity
3. Session remains active while user is active

### Inactivity Timeout
1. User inactive for 25 minutes → Warning modal appears
2. Modal shows 5-minute countdown
3. User clicks "Continue" → Token refreshes, session extends
4. Or countdown reaches 0 → Automatic logout

### Session Expired
1. Session expires → Redirect to login page
2. "Session Expired" message displayed
3. User logs in → Redirected to original page

## API Endpoints

### POST /api/auth/login
Returns access token, refresh token, and expiry time

### POST /api/auth/refresh  
Accepts refresh token, returns new access and refresh tokens

## Testing

For development testing, reduce timeouts:

```typescript
// Frontend: AuthContext.tsx
timeoutMinutes: 2,  // 2 min instead of 30
warningMinutes: 1,  // 1 min warning
```

```python
# Backend: config.py  
access_token_expire_minutes: int = 2  # 2 min instead of 30
```

## Files Modified

### Backend
- `backend/app/config.py` - Added session timeout configuration
- `backend/app/auth.py` - Added refresh token creation and validation
- `backend/app/routes/auth.py` - Added `/refresh` endpoint
- `backend/app/models/user.py` - Updated Token model for refresh tokens

### Frontend
- `frontend/src/contexts/AuthContext.tsx` - Integrated session management
- `frontend/src/pages/LoginPage.tsx` - Added session expired message
- `frontend/src/utils/sessionManager.ts` - Session tracking utility (NEW)
- `frontend/src/components/modals/SessionWarningModal.tsx` - Warning dialog (NEW)

## Troubleshooting

**Session expires too quickly**: Check `ACCESS_TOKEN_EXPIRE_MINUTES` setting

**Warning doesn't appear**: Verify SessionManager is initialized and user is authenticated

**Token refresh fails**: Check refresh token validity and `/api/auth/refresh` endpoint

**Redirect fails**: Verify `intendedPath` is stored in localStorage
