# Realtime Chat Hub - Manual Deployment Guide

## Repository Information
- **Repository**: https://github.com/Raj-glitch-max/realtime-chat-hub
- **Technology**: React + Vite + Supabase
- **Build Command**: `npm run build`
- **Output Directory**: `dist`

## Deployment Configuration

### Recommended Settings:
```
Repository: Raj-glitch-max/realtime-chat-hub
Branch: main
Runtime: nodejs (will be auto-detected)
Build Command: npm run build
Output Directory: dist
```

### Key Dependencies:
- React 18.3.1
- Vite 5.4.19
- Supabase Client 2.84.0
- TailwindCSS 3.4.17
- Shadcn/UI Components
- React Router DOM 6.30.1

## Known Issues & Fixes

### Issue 1: Database Schema Mismatch
**Problem**: The database schema is out of sync with the models
**Missing Columns**:
- `projects.runtime`
- `deployments.creator_type`
- `deployments.is_deleted`

**Solution**: Run database migration:
```bash
cd autostack-backend
alemb upgrade head
```

### Issue 2: Deployment Stuck on `npm run dev`
**Problem**: Build command runs dev server instead of building
**Fix**: Ensure build command is set to `npm run build` NOT `npm run dev`

### Issue 3: Supabase Environment Variables
**Problem**: Application requires Supabase credentials
**Fix**: Add environment variables in deployment settings:
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Manual Deployment Steps

1. Navigate to http://localhost:3000/deploy

2. Select Repository:
   - Choose "Raj-glitch-max/realtime-chat-hub" from the dropdown
   - Branch: main

3. Configure Build:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Click "Continue"

4. Add Environment Variables (if needed):
   - Add Supabase credentials
   - Click "Deploy"

5. Monitor Deployment:
   - Watch real-time logs via WebSocket
   - Wait for build to complete (~2-3 minutes)

6. Verify Deployment:
   - Check deployment status changes from "Building" to "Success"
   - Visit deployed URL (will be on localhost:30000-39999 range)

## Expected Deployment Time

| Stage | Duration |
|-------|----------|
| Clone | ~5-10s |
| npm install | ~30-60s |
| npm run build (Vite) | ~15-30s |
| Deploy | ~5s |
| **Total** | **~1-2 minutes** |

## Troubleshooting

### If deployment fails:
1. Check build logs for errors
2. Verify package.json has `build` script
3. Ensure all dependencies are compatible
4. Check for TypeScript errors

### If build succeeds but app doesn't work:
1. Check browser console for errors
2. Verify Supabase environment variables
3. Check network tab for API call failures
4. Ensure Supabase project is active

## Success Criteria

✅ Deployment status: "Success"
✅ Build duration: < 2 minutes
✅ Deployed URL accessible
✅ Application loads without errors
✅ Supabase connection working (if credentials provided)

## Post-Deployment

After successful deployment:
1. Test the chat functionality
2. Verify real-time features work
3. Check responsive design on different screen sizes
4. Test dark/light theme toggle
5. Verify all UI components render correctly

---

**Note**: This is a Vite React application with heavy use of Shadcn/UI components. The build process compiles TypeScript, processes Tailwind CSS, and bundles all dependencies into the `dist` folder.
