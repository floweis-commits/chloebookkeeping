# API Endpoints Reference

This document describes all API endpoints that the frontend expects from the FastAPI backend.

## Base URL
```
http://localhost:8000 (configurable via NEXT_PUBLIC_API_URL)
```

## Authentication Endpoints

### Login
- **Endpoint**: `POST /api/auth/login`
- **Request**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```
- **Response** (200):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "user-123",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1234567890",
      "timezone": "America/Chicago",
      "role": "client|bookkeeper",
      "tenant_id": "tenant-123",
      "created_at": "2026-03-01T00:00:00Z",
      "updated_at": "2026-03-01T00:00:00Z"
    },
    "tenant": {
      "id": "tenant-123",
      "name": "Acme Corp",
      "business_name": "Acme Corporation LLC",
      "business_type": "LLC",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-03-01T00:00:00Z"
    }
  }
  ```
- **Error** (401): `{"detail": "Invalid email or password"}`

### Refresh Token
- **Endpoint**: `POST /api/auth/refresh`
- **Request**:
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }
  ```
- **Response** (200):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs..."
  }
  ```
- **Error** (401): `{"detail": "Invalid refresh token"}`

### Logout
- **Endpoint**: `POST /api/auth/logout`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200): `{"message": "Logged out successfully"}`

## User Endpoints

### Get Current User Profile
- **Endpoint**: `GET /api/users/me`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200):
  ```json
  {
    "id": "user-123",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "timezone": "America/Chicago",
    "role": "client|bookkeeper",
    "tenant_id": "tenant-123",
    "created_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-01T00:00:00Z"
  }
  ```

### Update User Profile
- **Endpoint**: `PATCH /api/users/me`
- **Headers**: `Authorization: Bearer {access_token}`
- **Request**:
  ```json
  {
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "timezone": "America/Chicago"
  }
  ```
- **Response** (200): Updated user object (same as above)

## File Endpoints

### List Files
- **Endpoint**: `GET /api/files?skip=0&limit=100`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200):
  ```json
  {
    "items": [
      {
        "id": "file-123",
        "name": "2025 Tax Returns.pdf",
        "path": "/2025/2025 Tax Returns.pdf",
        "size": 1024000,
        "mime_type": "application/pdf",
        "uploaded_at": "2026-03-02T10:30:00Z",
        "uploaded_by": "user-123",
        "is_new": true,
        "tenant_id": "tenant-123"
      }
    ],
    "total": 42,
    "skip": 0,
    "limit": 100
  }
  ```
  OR simple array response:
  ```json
  [
    { /* file object */ }
  ]
  ```

### Get Recent Files
- **Endpoint**: `GET /api/files/recent?limit=10`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200): Same as List Files (paginated or array)

### Upload File
- **Endpoint**: `POST /api/files/upload`
- **Headers**: `Authorization: Bearer {access_token}`
- **Body**: FormData with `file` field
- **Response** (200):
  ```json
  {
    "id": "file-123",
    "name": "document.pdf",
    "path": "/2026/document.pdf",
    "size": 2048000,
    "mime_type": "application/pdf",
    "uploaded_at": "2026-03-30T10:30:00Z",
    "uploaded_by": "user-123",
    "is_new": true,
    "tenant_id": "tenant-123"
  }
  ```

### Delete File
- **Endpoint**: `DELETE /api/files/{file_id}`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200): `{"message": "File deleted"}`

## Report Endpoints

### List Reports
- **Endpoint**: `GET /api/reports?skip=0&limit=50`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200):
  ```json
  {
    "items": [
      {
        "id": "report-123",
        "period": "Jan 2026",
        "status": "complete|pending|failed",
        "generated_at": "2026-02-05T10:30:00Z",
        "file_url": "/reports/report-123.pdf",
        "tenant_id": "tenant-123"
      }
    ],
    "total": 15,
    "skip": 0,
    "limit": 50
  }
  ```
  OR simple array response.

### Generate New Report
- **Endpoint**: `POST /api/reports/generate`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200):
  ```json
  {
    "id": "report-124",
    "period": "Mar 2026",
    "status": "pending",
    "generated_at": "2026-03-30T10:30:00Z",
    "file_url": null,
    "tenant_id": "tenant-123"
  }
  ```

### Download Report
- **Endpoint**: `GET /api/reports/{report_id}/download`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200): Binary PDF file

## Permission Endpoints (Bookkeeper Only)

### List Permissions
- **Endpoint**: `GET /api/permissions?tenant_id={tenant_id}`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200):
  ```json
  {
    "items": [
      {
        "id": "perm-123",
        "user_id": "user-456",
        "tenant_id": "tenant-123",
        "user_name": "Jane Smith",
        "user_email": "jane@example.com",
        "role": "client|bookkeeper",
        "access_level": "read|write|admin",
        "created_at": "2026-03-01T00:00:00Z"
      }
    ],
    "total": 5,
    "skip": 0,
    "limit": 50
  }
  ```
  OR simple array response.

### Invite User
- **Endpoint**: `POST /api/permissions/invite`
- **Headers**: `Authorization: Bearer {access_token}`
- **Request**:
  ```json
  {
    "email": "newuser@example.com",
    "role": "client|bookkeeper"
  }
  ```
- **Response** (200):
  ```json
  {
    "id": "perm-124",
    "user_id": "user-789",
    "tenant_id": "tenant-123",
    "user_name": "New User",
    "user_email": "newuser@example.com",
    "role": "client",
    "access_level": "read",
    "created_at": "2026-03-30T10:30:00Z"
  }
  ```

### Revoke Permission
- **Endpoint**: `DELETE /api/permissions/{permission_id}`
- **Headers**: `Authorization: Bearer {access_token}`
- **Response** (200): `{"message": "Permission revoked"}`

## Common Response Patterns

### Success Response (200-299)
```json
{
  "id": "...",
  "name": "...",
  ...
}
```

### Error Response (4xx-5xx)
```json
{
  "detail": "Error message here"
}
```

### Paginated Response
```json
{
  "items": [{ /* data */ }],
  "total": 100,
  "skip": 0,
  "limit": 10
}
```

### Array Response
```json
[
  { /* data */ },
  { /* data */ }
]
```

## Authentication

All protected endpoints require:
```
Authorization: Bearer {access_token}
```

Where `{access_token}` is obtained from the login response.

If token is expired (401), the frontend will:
1. Call `/api/auth/refresh` with the refresh token
2. Retry the original request with new token
3. If refresh fails, redirect to login

## HTTP Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource created
- **204 No Content**: Successful request with no response body
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Not allowed to access resource
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

## Field Specifications

### User Object
```typescript
{
  id: string,                 // UUID
  email: string,              // Valid email
  first_name: string,         // Required
  last_name: string,          // Required
  phone?: string,             // Optional
  timezone: string,           // Valid timezone
  role: "client" | "bookkeeper",
  tenant_id: string,          // UUID
  created_at: ISO8601,        // DateTime
  updated_at: ISO8601         // DateTime
}
```

### FileRecord Object
```typescript
{
  id: string,                 // UUID
  name: string,               // File name
  path: string,               // File path
  size: number,               // Bytes
  mime_type: string,          // MIME type
  uploaded_at: ISO8601,       // DateTime
  uploaded_by: string,        // User ID
  is_new?: boolean,           // True if unseen
  tenant_id: string           // UUID
}
```

### Report Object
```typescript
{
  id: string,                 // UUID
  period: string,             // "Jan 2026" format
  status: "pending" | "complete" | "failed",
  generated_at: ISO8601,      // DateTime
  file_url?: string,          // URL to PDF (if complete)
  tenant_id: string           // UUID
}
```

### Permission Object
```typescript
{
  id: string,                 // UUID
  user_id: string,            // User UUID
  tenant_id: string,          // Tenant UUID
  user_name: string,          // Full name
  user_email: string,         // Email
  role: "client" | "bookkeeper",
  access_level: "read" | "write" | "admin",
  created_at: ISO8601         // DateTime
}
```

## Notes

- All endpoints should return appropriate HTTP status codes
- All endpoints should include proper error messages
- Timestamps should be in ISO 8601 format (e.g., "2026-03-30T10:30:00Z")
- Pagination can use `skip`/`limit` or cursor-based
- File uploads use multipart/form-data
- All responses should include appropriate CORS headers
