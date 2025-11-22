import { Suspense, lazy } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { 
  PricingComingSoon, 
  DocsComingSoon, 
  TemplatesComingSoon, 
  PipelinesComingSoon, 
  MonitoringComingSoon, 
  TeamComingSoon, 
  IntegrationsComingSoon 
} from "./pages/ComingSoon";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const DeployPage = lazy(() => import("./pages/DeployPage"));
const DeploymentsPage = lazy(() => import("./pages/DeploymentsPage"));
const DeploymentDetail = lazy(() => import("./pages/DeploymentDetail"));
const SettingsPage = lazy(() => import("./pages/Settings"));
const StatusPage = lazy(() => import("./pages/StatusPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const AuthCallback = lazy(() => import("./pages/AuthCallback"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient();

const LoadingScreen = () => (
  <div className="min-h-screen flex items-center justify-center">
    <Loader2 className="h-8 w-8 animate-spin text-primary" />
  </div>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Suspense fallback={<LoadingScreen />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/deploy"
              element={
                <ProtectedRoute>
                  <DeployPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/deployments"
              element={
                <ProtectedRoute>
                  <DeploymentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/deployments/:id"
              element={
                <ProtectedRoute>
                  <DeploymentDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/status"
              element={
                <ProtectedRoute>
                  <StatusPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <AnalyticsPage />
                </ProtectedRoute>
              }
            />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/pricing" element={<PricingComingSoon />} />
            <Route path="/docs" element={<DocsComingSoon />} />
            <Route path="/templates" element={<TemplatesComingSoon />} />
            <Route path="/pipelines" element={<PipelinesComingSoon />} />
            <Route path="/monitoring" element={<MonitoringComingSoon />} />
            <Route path="/team" element={<TeamComingSoon />} />
            <Route path="/integrations" element={<IntegrationsComingSoon />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
