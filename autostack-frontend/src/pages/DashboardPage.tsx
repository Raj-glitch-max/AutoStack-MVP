import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Rocket, 
  GitBranch, 
  CheckCircle2, 
  XCircle, 
  Clock,
  Github,
  TrendingUp,
  Activity,
  AlertCircle,
  ChevronDown,
  Settings,
  LogOut,
  User,
  AlertTriangle
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { API_BASE_URL } from "@/config";

const getStatusIcon = (status: string) => {
  switch (status) {
    case "success":
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-600" />;
    case "building":
      return <Clock className="h-4 w-4 text-blue-600 animate-pulse" />;
    default:
      return <Clock className="h-4 w-4 text-yellow-600" />;
  }
};

const formatTimeAgo = (timestamp: string) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
};

export default function DashboardPage() {
  const { authorizedRequest, user, logout } = useAuth();
  const [githubProfile, setGithubProfile] = useState<{
    login: string;
    avatar_url: string;
    html_url: string;
  } | null>(null);
  const [githubLoading, setGithubLoading] = useState(true);
  const [githubError, setGithubError] = useState<string | null>(null);

  // Fetch GitHub profile
  useEffect(() => {
    const fetchGithubProfile = async () => {
      try {
        setGithubLoading(true);
        const response = await authorizedRequest("/api/github/connection");
        if (response.ok) {
          const status = (await response.json()) as {
            connected: boolean;
            username?: string | null;
            avatarUrl?: string | null;
          };

          if (status.connected && status.username) {
            setGithubProfile({
              login: status.username,
              avatar_url: status.avatarUrl ?? "",
              html_url: `https://github.com/${status.username}`,
            });
          } else {
            setGithubProfile(null);
          }
        } else if (response.status !== 401) {
          throw new Error('Failed to fetch GitHub profile');
        }
      } catch (error) {
        console.error('Error fetching GitHub profile:', error);
        setGithubError('Failed to load GitHub profile');
      } finally {
        setGithubLoading(false);
      }
    };

    if (user) {
      fetchGithubProfile();
    }
  }, [authorizedRequest, user]);

  const handleDisconnectGitHub = async () => {
    try {
      await authorizedRequest("/api/github/disconnect", { method: "DELETE" });
      setGithubProfile(null);
    } catch (error) {
      console.error('Error disconnecting GitHub:', error);
      setGithubError('Failed to disconnect GitHub account');
    }
  };

  // Fetch real dashboard stats from backend (authenticated)
  const { data: dashboardData, isLoading, error } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/dashboard/stats");
      if (!response.ok) throw new Error("Failed to fetch dashboard stats");
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: githubStatus } = useQuery<{ connected: boolean; username?: string | null }>({
    queryKey: ["github-connection"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/github/connection");
      if (!response.ok) {
        if (response.status === 401) {
          return { connected: false, username: null };
        }
        throw new Error("Failed to fetch GitHub connection");
      }
      return response.json();
    },
  });

  const githubConnected = githubStatus?.connected;

  if (error) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-2">Dashboard</h1>
            <p className="text-muted-foreground">
              Welcome back! Here's what's happening with your deployments.
            </p>
          </div>

          {githubError && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{githubError}</AlertDescription>
            </Alert>
          )}

          <Alert className="mb-8 border-red-500 bg-red-50">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load dashboard data. Please refresh the page.
            </AlertDescription>
          </Alert>
        </div>
      </Layout>
    );
  }

  // While loading or if no stats yet, render a safe skeleton layout that does not touch stats
  if (isLoading || !dashboardData || !dashboardData.stats) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-2">Dashboard</h1>
            <p className="text-muted-foreground">
              Welcome back! Here's what's happening with your deployments.
            </p>
          </div>

          {githubError && (
            <Alert variant="destructive" className="mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{githubError}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
            {Array.from({ length: 4 }).map((_, index) => (
              <Card key={index} className="p-6">
                <Skeleton className="h-20 w-full" />
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-semibold">Recent Deployments</h2>
                </div>
                <div className="space-y-4">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} className="p-4 rounded-lg border border-border">
                      <Skeleton className="h-6 w-32 mb-2" />
                      <Skeleton className="h-4 w-48 mb-2" />
                      <Skeleton className="h-4 w-24" />
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="space-y-6">
              <Card className="p-6">
                <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
                <div className="space-y-3">
                  <Button variant="gradient" className="w-full justify-start" asChild>
                    <Link to="/deploy">
                      <Rocket className="mr-2 h-4 w-4" />
                      New Deployment
                    </Link>
                  </Button>
                  <Button variant="outline" className="w-full justify-start" asChild>
                    <Link to="/deployments">
                      <GitBranch className="mr-2 h-4 w-4" />
                      View All Deployments
                    </Link>
                  </Button>
                  <Button variant="outline" className="w-full justify-start" asChild>
                    <Link to="/analytics">
                      <TrendingUp className="mr-2 h-4 w-4" />
                      Analytics
                    </Link>
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  // At this point we know dashboardData.stats exists
  const rawTotals = dashboardData.stats || {};
  const totals = {
    total_deployments: rawTotals.total_deployments ?? rawTotals.totalDeployments ?? 0,
    active_projects: rawTotals.active_projects ?? rawTotals.activeProjects ?? 0,
    today_deployments: rawTotals.today_deployments ?? rawTotals.todayDeployments ?? 0,
    success_rate: rawTotals.success_rate ?? rawTotals.successRate ?? 0,
    monthly_success_change:
      rawTotals.monthly_success_change ?? rawTotals.monthlySuccessChange ?? 0,
    avg_deploy_time: rawTotals.avg_deploy_time ?? rawTotals.avgDeployTime ?? "0s",
    time_improvement: rawTotals.time_improvement ?? rawTotals.timeImprovement ?? "0s",
  };

  const stats = [
    {
      label: "Total Deployments",
      value: `${totals.total_deployments ?? 0}`,
      change: `+${totals.today_deployments ?? 0} today`,
      icon: Rocket,
      gradient: "gradient-primary",
    },
    {
      label: "Active Projects",
      value: `${totals.active_projects ?? 0}`,
      change: `${totals.today_deployments ?? 0} deployed today`,
      icon: GitBranch,
      gradient: "gradient-accent",
    },
    {
      label: "Success Rate",
      value: `${totals.success_rate ?? 0}%`,
      change: `${(totals.monthly_success_change ?? 0) > 0 ? "+" : ""}${
        totals.monthly_success_change ?? 0
      }% from last month`,
      icon: CheckCircle2,
      gradient: "gradient-success",
    },
    {
      label: "Avg Deploy Time",
      value: totals.avg_deploy_time ?? "0s",
      change: `${totals.time_improvement ?? "0s"} improvement`,
      icon: Clock,
      gradient: "gradient-warning",
    },
  ];

  const recentDeployments =
    dashboardData.recent_deployments || dashboardData.recentDeployments || [];

  return (
    <Layout>
      <div className="container px-4 py-8 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-2">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's what's happening with your deployments.
          </p>
        </div>
        
        {githubError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{githubError}</AlertDescription>
          </Alert>
        )}

        {/* GitHub Connection Banner */}
        {!isLoading && !githubConnected && recentDeployments.length === 0 && (
          <Alert className="mb-8 border-primary/50 bg-primary/5">
            <Github className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>No deployments yet. Connect your GitHub account to start deploying</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  window.location.href = `${API_BASE_URL}/auth/github`;
                }}
              >
                <Github className="mr-2 h-4 w-4" />
                Connect GitHub
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Stats Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
          {isLoading ? (
            // Show skeletons while loading
            Array.from({ length: 4 }).map((_, index) => (
              <Card key={index} className="p-6">
                <Skeleton className="h-20 w-full" />
              </Card>
            ))
          ) : (
            stats.map((stat, index) => (
              <Card key={index} className="p-6 hover:shadow-lg transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">{stat.label}</p>
                    <h3 className="text-3xl font-bold">{stat.value}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{stat.change}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${stat.gradient}`}>
                    <stat.icon className="h-5 w-5 text-white" />
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Recent Deployments */}
          <div className="lg:col-span-2">
            <Card className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold">Recent Deployments</h2>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/deployments">View all</Link>
                </Button>
              </div>
              <div className="space-y-4">
                {isLoading ? (
                  // Show skeletons while loading
                  Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} className="p-4 rounded-lg border border-border">
                      <Skeleton className="h-6 w-32 mb-2" />
                      <Skeleton className="h-4 w-48 mb-2" />
                      <Skeleton className="h-4 w-24" />
                    </div>
                  ))
                ) : recentDeployments.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Rocket className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No deployments yet. Create your first deployment to see it here.</p>
                  </div>
                ) : (
                  recentDeployments.map((deployment) => (
                    <div
                      key={deployment.id}
                      className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        {getStatusIcon(deployment.status)}
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{deployment.name}</p>
                            <span className="text-xs text-muted-foreground">
                              #{deployment.commit?.slice(0, 7)}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <GitBranch className="h-3 w-3" />
                            <span>{deployment.branch}</span>
                            <span>•</span>
                            <span>{formatTimeAgo(deployment.timestamp)}</span>
                          </div>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" asChild>
                        <Link to={`/deployments/${deployment.id}`}>
                          View
                        </Link>
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>

          {/* Quick Actions */}
          <div className="space-y-6">
            <Card className="p-6">
              <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
              <div className="space-y-3">
                <Button variant="gradient" className="w-full justify-start" asChild>
                  <Link to="/deploy">
                    <Rocket className="mr-2 h-4 w-4" />
                    New Deployment
                  </Link>
                </Button>
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link to="/deployments">
                    <GitBranch className="mr-2 h-4 w-4" />
                    View All Deployments
                  </Link>
                </Button>
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link to="/analytics">
                    <TrendingUp className="mr-2 h-4 w-4" />
                    Analytics
                  </Link>
                </Button>
              </div>
            </Card>

            <Card className="p-6 bg-accent/30">
              <div className="flex items-start gap-3 mb-4">
                <AlertCircle className="h-5 w-5 text-primary mt-0.5" />
                <div>
                  <h3 className="font-semibold mb-1">System Status</h3>
                  <p className="text-sm text-muted-foreground">
                    All systems operational
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" className="w-full" asChild>
                <Link to="/status">
                  View Status Page
                </Link>
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
}
