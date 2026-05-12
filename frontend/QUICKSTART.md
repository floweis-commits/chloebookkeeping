# Frontend Quick Start Guide

## Prerequisites

- Node.js 16+ (recommended 18 or 20)
- npm or yarn package manager
- FastAPI backend running on `http://localhost:8000`

## Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Create environment file** (if not exists):
   ```bash
   cp .env.example .env.local
   ```

3. **Configure API URL** in `.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

## Development

Start the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Default Layout

The app automatically redirects to `/login`.

**Login Page Features:**
- Split layout (50% blush background, 50% white form)
- Time-aware greeting based on current hour
- Email and password fields
- "Forgot password?" link (placeholder)
- Form validation and error handling

## Test Credentials

Contact your bookkeeper for test credentials to access:
- Dashboard (recent files)
- Files (file browser & upload)
- Reports (view & generate)
- Settings (profile & team management)

## Page Navigation

After login, navigate using the sidebar:

1. **Home** (`/dashboard`)
   - Shows recent files (last 10)
   - Quick action to generate reports
   - File metadata display

2. **Files** (`/files`)
   - Browse all files
   - Search by filename
   - Upload new files (bookkeeper only)
   - View file details (size, upload date)

3. **Reports** (`/reports`)
   - View generated reports
   - Check report status (pending/complete/failed)
   - Download completed reports
   - Generate new reports (bookkeeper only)

4. **Settings** (`/settings`)
   - Update user profile
   - Change password
   - Manage team access (bookkeeper only)
   - Invite new users (bookkeeper only)

## Key Features

### Authentication
- JWT-based authentication
- Automatic token refresh on expiry
- Session persists across page reloads
- Automatic redirect to login on logout

### File Management
- Search and filter files
- Upload multiple files
- View file metadata
- Responsive grid layout

### Reports
- Generate new reports on demand
- Download completed reports
- Track report generation status
- View report history

### User Management (Bookkeeper)
- Invite team members via email
- Assign roles (Client/Bookkeeper)
- Revoke user access
- View all team members

### Notifications
- Toast notifications for actions
- Auto-dismiss after 4 seconds
- Success and error messages
- Manual dismiss button

## Building for Production

1. **Build the app**:
   ```bash
   npm run build
   ```

2. **Start production server**:
   ```bash
   npm start
   ```

The optimized build will be in `.next/`.

## Common Issues

### API Connection Failed
- Ensure FastAPI backend is running on `http://localhost:8000`
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Check browser console for network errors

### Login Not Working
- Verify credentials with bookkeeper
- Check API server logs for authentication errors
- Clear browser cache and try again

### Files Not Loading
- Verify API endpoint `/api/files` is working
- Check user permissions
- Verify token is valid

### TypeScript Errors
- Run `npm install` to update dependencies
- Delete `.next/` folder and rebuild
- Restart development server

## Environment Variables

### Required
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

### Optional
- Add more as needed for deployment (API keys, analytics, etc)

## Project Structure

```
frontend/
├── app/              # Next.js pages and layouts
├── components/       # Reusable React components
├── lib/              # Utilities, API client, types
├── public/           # Static assets
├── middleware.ts     # Route protection
└── [config files]    # TypeScript, Tailwind, etc
```

## Useful Commands

```bash
# Development
npm run dev           # Start dev server on port 3000

# Production
npm run build         # Build optimized bundle
npm start            # Start production server

# Code quality
npm run lint         # Run ESLint

# Development tools
npm run type-check   # Check TypeScript (if configured)
```

## Styling

Uses Tailwind CSS for all styling. Key colors:

- **Accent**: `bg-blush-400` (#C9A99A)
- **Light background**: `bg-blush-50` (#faf5f2)
- **Light border**: `border-blush-200` (#E8D5CF)
- **Text**: `text-gray-700` to `text-gray-900`

Refer to `tailwind.config.ts` for color palette.

## API Integration

The frontend uses a typed API client (`lib/api.ts`) that handles:

- Authentication (login, logout, token refresh)
- File management (upload, download, delete)
- Report generation and download
- User profile updates
- Permission management

All API calls are typed with TypeScript for safety.

## Deployment

For deployment:

1. Set `NEXT_PUBLIC_API_URL` to your production API URL
2. Run `npm run build` to create optimized bundle
3. Use `npm start` or deploy `.next/` folder to hosting

Compatible with:
- Vercel (recommended)
- AWS Lambda
- Docker
- Traditional Node.js servers

## Support

For issues:
1. Check browser console (F12 → Console tab)
2. Check network requests (F12 → Network tab)
3. Check API server logs
4. Review error messages in toast notifications

## Next Steps

- Customize branding (logo, colors)
- Set up CI/CD pipeline
- Configure deployment hosting
- Add more features as needed
- Set up monitoring and error tracking
