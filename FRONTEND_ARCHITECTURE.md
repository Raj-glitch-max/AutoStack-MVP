# AutoStack Frontend Architecture

## Executive Summary

AutoStack's frontend is a modern, enterprise-grade React application built with TypeScript, providing a comprehensive deployment platform interface. The application leverages cutting-edge technologies and follows industry best practices for scalability, maintainability, and user experience.

## Technology Stack

### Core Technologies
- **React 18.3.1**: Latest React with concurrent features and automatic batching
- **TypeScript 5.8.3**: Type-safe development with advanced type inference
- **Vite 5.4.19**: Next-generation frontend tooling with HMR and optimized builds
- **React Router v6.30.1**: Client-side routing with nested routes and data loading

### UI Framework & Styling
- **TailwindCSS 3.4.17**: Utility-first CSS framework
- **Radix UI**: Unstyled, accessible component primitives
- **shadcn/ui**: Re-usable components built on Radix UI
- **Framer Motion 12.23.24**: Production-ready motion library
- **Lucide React 0.462.0**: Beautiful, consistent icon set

### State Management & Data Fetching
- **TanStack Query (React Query) 5.83.0**: Powerful async state management
  - Automatic caching and background refetching
  - Optimistic updates
  - Request deduplication
  - Pagination and infinite scroll support

### Form Management
- **React Hook Form 7.61.1**: Performant, flexible forms
- **Zod 3.25.76**: TypeScript-first schema validation
- **@hookform/resolvers 3.10.0**: Validation resolver for React Hook Form

### Additional Libraries
- **date-fns 3.6.0**: Modern date utility library
- **recharts 2.15.4**: Composable charting library
- **next-themes 0.3.0**: Theme management (dark/light mode)
- **sonner 1.7.4**: Toast notifications

## Project Structure

\`\`\`
autostack-frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── ui/             # shadcn/ui components (53 components)
│   │   ├── Layout.tsx      # Main layout wrapper
│   │   ├── NavLink.tsx     # Navigation link component
│   │   ├── ProtectedRoute.tsx  # Route protection HOC
│   │   └── GithubConnectionCard.tsx  # GitHub integration UI
│   ├── pages/              # Page components (14 pages)
│   │   ├── Landing.tsx     # Landing page
│   │   ├── Login.tsx       # Login page
│   │   ├── Signup.tsx      # Signup page
│   │   ├── DashboardPage.tsx  # Main dashboard
│   │   ├── DeployPage.tsx  # Deployment creation
│   │   ├── DeploymentsPage.tsx  # Deployments list
│   │   ├── DeploymentDetail.tsx  # Deployment details
│   │   ├── AnalyticsPage.tsx  # Analytics dashboard
│   │   ├── StatusPage.tsx  # System status
│   │   ├── Settings.tsx    # User settings
│   │   └── ...
│   ├── hooks/              # Custom React hooks
│   │   ├── useAuth.tsx     # Authentication hook
│   │   ├── use-toast.ts    # Toast notifications hook
│   │   └── use-mobile.tsx  # Mobile detection hook
│   ├── lib/                # Utility functions
│   │   ├── utils.ts        # General utilities
│   │   └── auth-storage.ts # Auth token management
│   ├── context/            # React context providers
│   │   └── AuthContext.tsx # Authentication context
│   ├── App.tsx             # Root component with routing
│   ├── main.tsx            # Application entry point
│   ├── config.ts           # Configuration constants
│   └── index.css           # Global styles
├── public/                 # Static assets
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite configuration
└── tailwind.config.ts      # Tailwind configuration
\`\`\`

## Application Architecture

### Component Hierarchy

\`\`\`mermaid
graph TD
    A[main.tsx] --> B[App.tsx]
    B --> C[AuthProvider]
    C --> D[Router]
    D --> E[Layout]
    E --> F[Protected Routes]
    F --> G[Dashboard]
    F --> H[Deployments]
    F --> I[Deploy]
    F --> J[Analytics]
    F --> K[Settings]
    D --> L[Public Routes]
    L --> M[Landing]
    L --> N[Login]
    L --> O[Signup]
\`\`\`

### Routing Structure

\`\`\`mermaid
graph LR
    A[/] --> B[Landing Page]
    C[/login] --> D[Login Page]
    E[/signup] --> F[Signup Page]
    G[/dashboard] --> H[Dashboard]
    I[/deployments] --> J[Deployments List]
    K[/deployments/:id] --> L[Deployment Detail]
    M[/deploy] --> N[Deploy Page]
    O[/analytics] --> P[Analytics]
    Q[/settings] --> R[Settings]
    S[/status] --> T[Status Page]
    
    style H fill:#90EE90
    style J fill:#90EE90
    style L fill:#90EE90
    style N fill:#90EE90
    style P fill:#90EE90
    style R fill:#90EE90
    style T fill:#90EE90
\`\`\`

## Key Features & Implementation

### 1. Authentication System

#### Authentication Flow

\`\`\`mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant O as OAuth Provider
    
    U->>F: Click Login
    F->>U: Show login options
    
    alt Email/Password
        U->>F: Enter credentials
        F->>B: POST /api/auth/login
        B->>F: Return JWT tokens
        F->>F: Store tokens
        F->>U: Redirect to dashboard
    else GitHub OAuth
        U->>F: Click GitHub login
        F->>O: Redirect to GitHub
        O->>U: Request authorization
        U->>O: Approve
        O->>F: Redirect with code
        F->>B: POST /api/auth/github/callback
        B->>F: Return JWT tokens
        F->>F: Store tokens
        F->>U: Redirect to dashboard
    else Google OAuth
        U->>F: Click Google login
        F->>O: Redirect to Google
        O->>U: Request authorization
        U->>O: Approve
        O->>F: Redirect with code
        F->>B: POST /api/auth/google/callback
        B->>F: Return JWT tokens
        F->>F: Store tokens
        F->>U: Redirect to dashboard
    end
\`\`\`

#### Implementation Details

**AuthContext.tsx**
- Provides authentication state globally
- Manages JWT tokens (access + refresh)
- Handles token refresh automatically
- Provides \`authorizedRequest\` helper for API calls

**Token Storage** (\`lib/auth-storage.ts\`)
- Stores tokens in localStorage
- Automatic token expiration handling
- Secure token refresh mechanism

**Protected Routes** (\`components/ProtectedRoute.tsx\`)
- Wraps protected pages
- Redirects to login if unauthenticated
- Preserves intended destination

### 2. Deployment Management

#### Deployment Creation Flow

\`\`\`mermaid
graph TD
    A[User on Deploy Page] --> B{Select Source}
    B -->|GitHub Repo| C[Enter Repository URL]
    B -->|Manual| D[Upload Files]
    C --> E[Configure Build Settings]
    D --> E
    E --> F[Set Environment Variables]
    F --> G[Choose Branch]
    G --> H[Submit Deployment]
    H --> I[Backend Creates Deployment]
    I --> J[Redirect to Deployment Detail]
    J --> K[Stream Logs via WebSocket]
\`\`\`

#### Deployment Detail Page Features

**Real-time Log Streaming**
\`\`\`typescript
// WebSocket connection for live logs
const wsUrl = buildLogsWebSocketUrl(deploymentId, accessToken);
const socket = new WebSocket(wsUrl);

socket.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  if (payload.type === "log") {
    setLogs(prev => [...prev, payload.line]);
  }
};
\`\`\`

**Features:**
- Live log streaming with WebSocket
- Auto-scroll with pause/resume
- Color-coded logs (errors in red, success in green)
- Deployment stages visualization
- Container metrics display
- Delete deployment functionality

### 3. Dashboard & Analytics

#### Dashboard Components

\`\`\`mermaid
graph TD
    A[Dashboard Page] --> B[Stats Cards]
    A --> C[Recent Deployments]
    A --> D[Quick Actions]
    A --> E[Activity Timeline]
    
    B --> B1[Total Deployments]
    B --> B2[Success Rate]
    B --> B3[Active Containers]
    B --> B4[Failed Deployments]
    
    C --> C1[Deployment List]
    C --> C2[Status Badges]
    C --> C3[Quick Links]
\`\`\`

#### Analytics Features
- Deployment success/failure trends
- Build duration charts (using Recharts)
- Resource usage metrics
- Time-series analysis
- Filterable date ranges

### 4. State Management with React Query

#### Query Configuration

\`\`\`typescript
// Example: Fetching deployment details
const { data, isLoading, error } = useQuery<DeploymentDetailResponse>({
  queryKey: ["deployment-detail", id],
  enabled: !!id,
  queryFn: async () => {
    const response = await authorizedRequest(\`/api/deployments/\${id}\`);
    if (!response.ok) throw new Error("Failed to load deployment");
    return response.json();
  },
  refetchInterval: 5000, // Auto-refresh every 5 seconds
});
\`\`\`

#### Benefits
- Automatic background refetching
- Cache management
- Loading and error states
- Optimistic updates
- Request deduplication

### 5. UI Components (shadcn/ui)

#### Component Library (53 Components)

**Layout Components:**
- Card, Separator, Tabs, Accordion, Collapsible

**Form Components:**
- Input, Textarea, Select, Checkbox, Radio Group, Switch, Slider

**Feedback Components:**
- Toast, Alert, Dialog, Sheet, Drawer

**Navigation Components:**
- Navigation Menu, Menubar, Breadcrumb, Pagination

**Data Display:**
- Table, Badge, Avatar, Progress, Skeleton

**Overlay Components:**
- Popover, Tooltip, Hover Card, Context Menu, Dropdown Menu

#### Design System

**Colors:**
- Primary: Blue gradient
- Success: Green
- Error: Red
- Warning: Yellow
- Muted: Gray

**Typography:**
- Font Family: System fonts with fallbacks
- Headings: Bold, various sizes
- Body: Regular weight

**Spacing:**
- Consistent spacing scale (4px base)
- Responsive padding and margins

### 6. Theme Management

**Dark/Light Mode:**
- Implemented with \`next-themes\`
- System preference detection
- Persistent theme selection
- Smooth transitions

## Data Flow Architecture

\`\`\`mermaid
graph LR
    A[User Action] --> B[Component]
    B --> C{Type}
    C -->|Query| D[React Query]
    C -->|Mutation| E[React Query Mutation]
    D --> F[API Request]
    E --> F
    F --> G[Backend API]
    G --> H[Response]
    H --> I[Cache Update]
    I --> J[UI Re-render]
    
    style D fill:#FFE4B5
    style E fill:#FFE4B5
    style I fill:#90EE90
\`\`\`

## Performance Optimizations

### 1. Code Splitting
- Route-based code splitting with React.lazy
- Dynamic imports for heavy components
- Reduced initial bundle size

### 2. Memoization
- React.memo for expensive components
- useMemo for computed values
- useCallback for event handlers

### 3. Virtual Scrolling
- Implemented for large lists
- Reduces DOM nodes
- Improves scroll performance

### 4. Image Optimization
- Lazy loading images
- Responsive images
- WebP format support

### 5. Build Optimizations
- Vite's optimized build process
- Tree shaking
- Minification
- Gzip compression

## Security Considerations

### 1. Authentication
- JWT tokens with expiration
- Secure token storage
- Automatic token refresh
- CSRF protection

### 2. XSS Prevention
- React's built-in XSS protection
- Sanitized user inputs
- Content Security Policy headers

### 3. API Security
- HTTPS only in production
- CORS configuration
- Rate limiting (backend)

## Testing Strategy

### Unit Tests
- Component testing with React Testing Library
- Hook testing
- Utility function tests

### Integration Tests
- User flow testing
- API integration tests
- Authentication flow tests

### E2E Tests
- Critical user journeys
- Deployment workflow
- Authentication flows

## Build & Deployment

### Development
\`\`\`bash
npm run dev  # Start dev server on port 3000
\`\`\`

### Production Build
\`\`\`bash
npm run build  # Create optimized production build
npm run preview  # Preview production build
\`\`\`

### Environment Variables
\`\`\`typescript
// config.ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
\`\`\`

## Accessibility

### WCAG 2.1 Level AA Compliance
- Semantic HTML
- ARIA labels and roles
- Keyboard navigation
- Focus management
- Color contrast ratios
- Screen reader support

### Radix UI Benefits
- Built-in accessibility
- Keyboard navigation
- Focus trapping
- ARIA attributes

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile browsers: iOS Safari, Chrome Android

## Future Enhancements

1. **Progressive Web App (PWA)**
   - Offline support
   - Push notifications
   - Install prompt

2. **Advanced Analytics**
   - Custom dashboards
   - Export reports
   - Real-time metrics

3. **Collaboration Features**
   - Team management
   - Role-based access control
   - Deployment approvals

4. **Enhanced Monitoring**
   - Error tracking integration
   - Performance monitoring
   - User analytics

## Conclusion

AutoStack's frontend represents a modern, scalable, and maintainable React application built with industry-leading technologies. The architecture supports rapid feature development while maintaining code quality, performance, and user experience standards expected in enterprise applications.
