import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell,
  AreaChart,
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from "recharts";
import { 
  TrendingUp, 
  TrendingDown,
  Activity, 
  CheckCircle2, 
  XCircle,
  Clock,
  Zap,
  Server,
  ArrowUp,
  ArrowDown,
  AlertTriangle,
  Cpu,
  HardDrive,
  Network,
  DollarSign
} from "lucide-react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";

// Generate deployment frequency based on actual recent deployments (by hour of day)
const generateDeploymentFrequency = (deployments: RecentDeploymentItem[]) => {
  const buckets = new Array(24).fill(0);

  for (const dep of deployments || []) {
    const rawTs: string | null | undefined = (dep as any).timestamp ?? dep.time;
    if (!rawTs) continue;
    const d = new Date(rawTs);
    if (Number.isNaN(d.getTime())) continue;
    const hour = d.getHours();
    if (hour >= 0 && hour < 24) {
      buckets[hour] += 1;
    }
  }

  return buckets.map((count, hour) => ({
    hour: `${hour.toString().padStart(2, "0")}:00`,
    deployments: count,
  }));
};

// Generate success vs failed data from real aggregate metrics
const generateSuccessRates = (applicationMetrics: any) => {
  const total = applicationMetrics?.deployments?.total ?? 0;
  const successful = applicationMetrics?.deployments?.successful ?? 0;
  const failed = applicationMetrics?.deployments?.failed ?? 0;

  if (total === 0) {
    return [];
  }

  return [
    {
      date: "All Time",
      success: successful,
      failed,
    },
  ];
};

type RecentDeploymentItem = {
  id: string;
  name: string;
  status: string;
  duration?: string | null;
  time: string;
  projectId?: string | null;
};

type RecentDeploymentsResponse = {
  recent_deployments?: RecentDeploymentItem[];
  recentDeployments?: RecentDeploymentItem[];
};

type PipelineMetricsResponse = {
  deployment_id: string;
  pipeline: {
    style: string;
    total_duration: number;
  };
  timestamp: string;
};

type ProjectAnalyticsResponse = {
  analytics: {
    deployments_count: number;
    success_count: number;
    failure_count: number;
    last_5_durations: number[];
    avg_build_time: number | null;
    uptime_last_24h: number | null;
  };
};

interface MetricCardProps {
  title: string;
  value: string;
  change: number;
  icon: any;
  trend: "up" | "down";
}

const MetricCard = ({ title, value, change, icon: Icon, trend }: MetricCardProps) => (
  <Card className="p-6 hover:shadow-lg transition-all duration-300">
    <div className="flex items-start justify-between mb-4">
      <div className="gradient-primary p-2 rounded-lg">
        <Icon className="h-5 w-5 text-white" />
      </div>
      <Badge variant="outline" className={trend === "up" ? "text-green-500 border-green-500/20" : "text-red-500 border-red-500/20"}>
        {trend === "up" ? <ArrowUp className="h-3 w-3 mr-1" /> : <ArrowDown className="h-3 w-3 mr-1" />}
        {Math.abs(change)}%
      </Badge>
    </div>
    <p className="text-sm text-muted-foreground mb-1">{title}</p>
    <p className="text-3xl font-bold">{value}</p>
  </Card>
);

const formatNumber = (value: unknown, fractionDigits = 1): string => {
  const num = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(num)) return "0";
  try {
    return num.toFixed(fractionDigits);
  } catch {
    return "0";
  }
};

export default function AnalyticsPage() {
  const { authorizedRequest } = useAuth();

  // Fetch real monitoring data (authenticated)
  const {
    data: monitoringData,
    isLoading: monitoringLoading,
    error: monitoringError,
  } = useQuery({
    queryKey: ["monitoring-metrics"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/monitoring/metrics");
      if (!response.ok) throw new Error("Failed to fetch monitoring metrics");
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const {
    data: pipelineStats,
    isLoading: pipelineStatsLoading,
    error: pipelineStatsError,
  } = useQuery<{
    points: { label: string; duration: number }[];
    fastestLabel?: string;
    fastestDuration?: number;
    slowestLabel?: string;
    slowestDuration?: number;
    averageDuration?: number;
    projectIdForAnalytics?: string;
    recentDeployments?: RecentDeploymentItem[];
  }>({
    queryKey: ["pipeline-stats"],
    queryFn: async () => {
      const recentRes = await authorizedRequest("/api/deployments/recent?limit=7");
      if (!recentRes.ok) {
        throw new Error("Failed to fetch recent deployments");
      }
      const recentJson = (await recentRes.json()) as RecentDeploymentsResponse;
      const deployments =
        recentJson.recent_deployments || recentJson.recentDeployments || [];
      if (deployments.length === 0) {
        return { points: [], recentDeployments: [] };
      }

      const pipelineResponses = await Promise.all(
        deployments.map(async (dep) => {
          const res = await authorizedRequest(`/api/monitoring/pipeline/${dep.id}`);
          if (!res.ok) {
            return null;
          }
          const json = (await res.json()) as PipelineMetricsResponse;
          const total = json.pipeline?.total_duration ?? 0;
          return {
            label: dep.name || dep.id,
            duration: Math.round(total),
          };
        }),
      );

      const points = pipelineResponses.filter(
        (p): p is { label: string; duration: number } => !!p,
      );
      if (points.length === 0) {
        return { points: [], recentDeployments: deployments };
      }

      const durations = points.map((p) => p.duration);
      const min = Math.min(...durations);
      const max = Math.max(...durations);
      const avg = durations.reduce((acc, val) => acc + val, 0) / durations.length;

      const fastest = points.find((p) => p.duration === min);
      const slowest = points.find((p) => p.duration === max);

      const firstWithProject = deployments.find((d) => d.projectId);

      return {
        points,
        fastestLabel: fastest?.label,
        fastestDuration: fastest?.duration,
        slowestLabel: slowest?.label,
        slowestDuration: slowest?.duration,
        averageDuration: avg,
        projectIdForAnalytics: firstWithProject?.projectId || undefined,
        recentDeployments: deployments,
      };
    },
    refetchInterval: 60000,
  });

  const { data: projectAnalyticsData } = useQuery<ProjectAnalyticsResponse | null>({
    queryKey: ["project-analytics", pipelineStats?.projectIdForAnalytics],
    enabled: !!pipelineStats?.projectIdForAnalytics,
    queryFn: async () => {
      const projectId = pipelineStats?.projectIdForAnalytics;
      if (!projectId) return null;
      const response = await authorizedRequest(`/api/projects/${projectId}/analytics`);
      if (!response.ok) throw new Error("Failed to fetch project analytics");
      return response.json();
    },
  });

  const {
    data: clusterData,
    isLoading: clusterLoading,
    error: clusterError,
  } = useQuery({
    queryKey: ["cluster-status"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/monitoring/cluster");
      if (!response.ok) throw new Error("Failed to fetch cluster status");
      return response.json();
    },
    refetchInterval: 30000,
  });

  const {
    data: applicationData,
    isLoading: applicationLoading,
    error: applicationError,
  } = useQuery({
    queryKey: ["application-metrics"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/monitoring/application");
      if (!response.ok) throw new Error("Failed to fetch application metrics");
      return response.json();
    },
    refetchInterval: 60000, // Refresh every minute
  });

  const {
    data: billingData,
    isLoading: billingLoading,
    error: billingError,
  } = useQuery<{
    billing: {
      currency: string;
      total_month_to_date: number;
      projected_monthly: number;
      last_updated: string;
      projects: {
        project_id: string;
        name: string;
        total_deployments: number;
        successful_deployments: number;
        pipeline_minutes: number;
        estimated_cost: number;
      }[];
    };
  }>({
    queryKey: ["billing-summary"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/billing/summary");
      if (!response.ok) throw new Error("Failed to fetch billing summary");
      return response.json();
    },
    refetchInterval: 300000,
  });

  // Process real data for charts
  const systemMetrics = monitoringData?.system || {};
  const dockerMetrics = monitoringData?.docker || {};
  const clusterMetrics = clusterData?.cluster || {};
  const applicationMetrics =
    applicationData?.application || monitoringData?.application || {};
  const billing = billingData?.billing;

  const deploymentFrequencyData = generateDeploymentFrequency(
    pipelineStats?.recentDeployments || [],
  );
  const successRateData = generateSuccessRates(applicationMetrics);

  // Create real resource usage data
  const resourceUsage = [
    { 
      name: "CPU", 
      value: systemMetrics?.cpu?.percent || 0, 
      color: "#3b82f6",
      icon: Cpu
    },
    { 
      name: "Memory", 
      value: systemMetrics?.memory?.percent || 0, 
      color: "#8b5cf6",
      icon: Server
    },
    { 
      name: "Storage", 
      value: systemMetrics?.disk?.percent || 0, 
      color: "#ec4899",
      icon: HardDrive
    },
    { 
      name: "Network", 
      value: Math.min(100, (systemMetrics?.network?.bytes_sent || 0) / 10485760), // Convert to percentage
      color: "#f59e0b",
      icon: Network
    },
  ];

  // Create deployment status data
  const deploymentStatus = [
    { 
      name: "Success", 
      value: applicationMetrics?.deployments?.successful || 0, 
      color: "#10b981" 
    },
    { 
      name: "Failed", 
      value: applicationMetrics?.deployments?.failed || 0, 
      color: "#ef4444" 
    },
  ];

  // Create container metrics data
  const containerMetrics = dockerMetrics?.containers || [];
  const runningContainers = containerMetrics.filter(c => c.status === "running").length;
  const totalContainers = containerMetrics.length;
  const buildDurationPoints = pipelineStats?.points || [];
  const projectAnalytics = projectAnalyticsData?.analytics;

  const initialLoading =
    monitoringLoading ||
    pipelineStatsLoading ||
    clusterLoading ||
    applicationLoading ||
    billingLoading;

  const dataLoadFailed =
    monitoringError ||
    pipelineStatsError ||
    clusterError ||
    applicationError ||
    billingError;

  if (dataLoadFailed) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-7xl mx-auto">
          <div className="text-center py-12">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-2xl font-semibold mb-2">Analytics temporarily unavailable</h2>
            <p className="text-muted-foreground">
              We couldn’t load your monitoring data right now. Please refresh the page.
            </p>
            <Button className="mt-4" onClick={() => window.location.reload()}>
              Retry
            </Button>
          </div>
        </div>
      </Layout>
    );
  }

  if (initialLoading) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-7xl mx-auto">
          <div className="mb-8">
            <Skeleton className="h-10 w-64 mb-2" />
            <Skeleton className="h-4 w-96" />
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-6">
                <Skeleton className="h-20 w-full" />
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="p-6 lg:col-span-2">
              <Skeleton className="h-64 w-full" />
            </Card>
            <Card className="p-6">
              <Skeleton className="h-64 w-full" />
            </Card>
          </div>
        </div>
      </Layout>
    );
  }
  return (
    <Layout>
      <div className="container px-4 py-8 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="gradient-hero p-2 rounded-lg">
              <Activity className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-3xl md:text-4xl font-bold">Analytics Dashboard</h1>
          </div>
          <p className="text-muted-foreground">
            Comprehensive insights into your deployment performance and resource usage
          </p>
        </motion.div>

        {/* Key Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid gap-4 md:grid-cols-4 mb-8"
        >
          {monitoringLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Card key={i} className="p-6">
                <Skeleton className="h-20 w-full" />
              </Card>
            ))
          ) : (
            <>
              <MetricCard
                title="Total Deployments"
                value={`${applicationMetrics?.deployments?.total ?? 0}`}
                change={applicationMetrics?.deployments?.success_rate || 0}
                icon={Zap}
                trend="up"
              />
              <MetricCard
                title="Success Rate"
                value={`${formatNumber(applicationMetrics?.deployments?.success_rate, 1)}%`}
                change={2.3}
                icon={CheckCircle2}
                trend="up"
              />
              <MetricCard
                title="Running Containers"
                value={`${runningContainers}/${totalContainers}`}
                change={totalContainers > 0 ? (runningContainers / totalContainers * 100) : 0}
                icon={Server}
                trend="up"
              />
              <MetricCard
                title="System Load"
                value={`${formatNumber(systemMetrics?.cpu?.percent, 1)}%`}
                change={systemMetrics?.memory?.percent || 0}
                icon={Cpu}
                trend={systemMetrics?.cpu?.percent > 80 ? "up" : "down"}
              />
            </>
          )}
        </motion.div>

        {/* Charts Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Tabs defaultValue="frequency" className="space-y-4">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="frequency">Frequency</TabsTrigger>
              <TabsTrigger value="success">Success Rate</TabsTrigger>
              <TabsTrigger value="duration">Build Times</TabsTrigger>
              <TabsTrigger value="resources">Resources</TabsTrigger>
              <TabsTrigger value="billing">Billing</TabsTrigger>
            </TabsList>

            {/* Deployment Frequency */}
            <TabsContent value="frequency" className="space-y-4">
              <Card className="p-6">
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-2">Deployment Frequency</h3>
                  <p className="text-sm text-muted-foreground">
                    Number of deployments over the last 6 weeks
                  </p>
                </div>
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={deploymentFrequencyData}>
                    <defs>
                      <linearGradient id="colorDeployments" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis dataKey="hour" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--card))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }} 
                    />
                    <Area 
                      type="monotone" 
                      dataKey="deployments" 
                      stroke="#3b82f6" 
                      strokeWidth={2}
                      fillOpacity={1} 
                      fill="url(#colorDeployments)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              <Card className="p-6">
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-2">Hourly Distribution</h3>
                  <p className="text-sm text-muted-foreground">
                    When your team deploys most frequently
                  </p>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={deploymentFrequencyData}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                    <XAxis dataKey="hour" stroke="hsl(var(--muted-foreground))" />
                    <YAxis stroke="hsl(var(--muted-foreground))" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: "hsl(var(--card))", 
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "8px"
                      }} 
                    />
                    <Bar dataKey="deployments" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </TabsContent>

            {/* Success Rates */}
            <TabsContent value="success" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="p-6">
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold mb-2">Success vs Failed</h3>
                    <p className="text-sm text-muted-foreground">
                      Weekly success and failure rates
                    </p>
                  </div>
                  {successRateData.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No deployment success data available yet.
                    </p>
                  ) : (
                    <ResponsiveContainer width="100%" height={350}>
                      <LineChart data={successRateData}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                        <XAxis
                          dataKey="date"
                          stroke="hsl(var(--muted-foreground))"
                        />
                        <YAxis stroke="hsl(var(--muted-foreground))" />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "8px",
                          }}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="success"
                          stroke="#10b981"
                          strokeWidth={3}
                          dot={{ fill: "#10b981", r: 5 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="failed"
                          stroke="#ef4444"
                          strokeWidth={3}
                          dot={{ fill: "#ef4444", r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card className="p-6">
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold mb-2">Status Distribution</h3>
                    <p className="text-sm text-muted-foreground">
                      Overall deployment outcomes
                    </p>
                  </div>
                  <ResponsiveContainer width="100%" height={350}>
                    <PieChart>
                      <Pie
                        data={deploymentStatus}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${formatNumber((percent ?? 0) * 100, 0)}%`}
                        outerRadius={120}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {deploymentStatus.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: "hsl(var(--card))", 
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px"
                        }} 
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="mt-4 space-y-2">
                    {deploymentStatus.map((status) => (
                      <div key={status.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: status.color }} />
                          <span className="text-sm">{status.name}</span>
                        </div>
                        <span className="text-sm font-semibold">{status.value}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </TabsContent>

            {/* Build Duration */}
            <TabsContent value="duration" className="space-y-4">
              <Card className="p-6">
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-2">Build Duration Trends</h3>
                  <p className="text-sm text-muted-foreground">
                    Real Jenkins-style pipeline durations for your most recent deployments
                  </p>
                </div>
                {pipelineStatsLoading && buildDurationPoints.length === 0 ? (
                  <Skeleton className="h-64 w-full" />
                ) : buildDurationPoints.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No recent deployments with pipeline data yet.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={buildDurationPoints}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                      <XAxis dataKey="label" stroke="hsl(var(--muted-foreground))" />
                      <YAxis
                        stroke="hsl(var(--muted-foreground))"
                        label={{ value: "Seconds", angle: -90, position: "insideLeft" }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="duration"
                        stroke="#3b82f6"
                        strokeWidth={3}
                        name="Pipeline Duration"
                        dot={{ fill: "#3b82f6", r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </Card>

              <div className="grid gap-4 md:grid-cols-3">
                <Card className="p-6 text-center">
                  <div className="gradient-primary p-3 rounded-lg w-fit mx-auto mb-3">
                    <TrendingDown className="h-6 w-6 text-white" />
                  </div>
                  <p className="text-sm text-muted-foreground mb-1">Fastest Build</p>
                  <p className="text-3xl font-bold text-green-500">
                    {pipelineStats?.fastestDuration != null
                      ? `${Math.round(pipelineStats.fastestDuration)}s`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {pipelineStats?.fastestLabel || "Most recent deployments"}
                  </p>
                </Card>
                <Card className="p-6 text-center">
                  <div className="gradient-primary p-3 rounded-lg w-fit mx-auto mb-3">
                    <Clock className="h-6 w-6 text-white" />
                  </div>
                  <p className="text-sm text-muted-foreground mb-1">Average Build</p>
                  <p className="text-3xl font-bold">
                    {pipelineStats?.averageDuration != null
                      ? `${Math.round(pipelineStats.averageDuration)}s`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">Based on recent pipelines</p>
                </Card>
                <Card className="p-6 text-center">
                  <div className="gradient-primary p-3 rounded-lg w-fit mx-auto mb-3">
                    <TrendingUp className="h-6 w-6 text-white" />
                  </div>
                  <p className="text-sm text-muted-foreground mb-1">Slowest Build</p>
                  <p className="text-3xl font-bold text-red-500">
                    {pipelineStats?.slowestDuration != null
                      ? `${Math.round(pipelineStats.slowestDuration)}s`
                      : "-"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {pipelineStats?.slowestLabel || "Most recent deployments"}
                  </p>
                </Card>
              </div>

              {projectAnalytics && (
                <Card className="p-4 mt-2">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-semibold">Latest project analytics</h4>
                      <p className="text-xs text-muted-foreground">
                        Based on deployments for the most recently analysed project.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs sm:text-sm">
                      <div>
                        <span className="text-muted-foreground mr-1">Deployments:</span>
                        <span className="font-mono">{projectAnalytics.deployments_count}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground mr-1">Success:</span>
                        <span className="font-mono text-green-500">{projectAnalytics.success_count}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground mr-1">Failures:</span>
                        <span className="font-mono text-red-500">{projectAnalytics.failure_count}</span>
                      </div>
                      {projectAnalytics.avg_build_time != null && (
                        <div>
                          <span className="text-muted-foreground mr-1">Avg build:</span>
                          <span className="font-mono">{formatNumber(projectAnalytics.avg_build_time, 1)}s</span>
                        </div>
                      )}
                      {projectAnalytics.uptime_last_24h != null && (
                        <div>
                          <span className="text-muted-foreground mr-1">Uptime (24h):</span>
                          <span className="font-mono">{formatNumber(projectAnalytics.uptime_last_24h, 1)}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              )}
            </TabsContent>

            {/* Resource Usage */}
            <TabsContent value="resources" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="p-6">
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold mb-2">Current Resource Usage</h3>
                    <p className="text-sm text-muted-foreground">
                      Real-time infrastructure utilization
                    </p>
                  </div>
                  {monitoringLoading ? (
                    <Skeleton className="h-64 w-full" />
                  ) : (
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={resourceUsage} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                        <XAxis type="number" stroke="hsl(var(--muted-foreground))" />
                        <YAxis dataKey="name" type="category" stroke="hsl(var(--muted-foreground))" />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: "hsl(var(--card))", 
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "8px"
                          }} 
                        />
                        <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                          {resourceUsage.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </Card>

                <Card className="p-6">
                  <div className="mb-6">
                    <h3 className="text-xl font-semibold mb-2">System Metrics</h3>
                    <p className="text-sm text-muted-foreground">
                      Detailed performance statistics
                    </p>
                  </div>
                  {monitoringLoading ? (
                    <Skeleton className="h-64 w-full" />
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-3 bg-accent/50 rounded-lg">
                        <div className="flex items-center gap-2">
                          <Cpu className="h-4 w-4 text-blue-500" />
                          <span className="text-sm font-medium">CPU Usage</span>
                        </div>
                        <span className="text-sm font-bold">{`${formatNumber(systemMetrics?.cpu?.percent, 1)}%`}</span>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-accent/50 rounded-lg">
                        <div className="flex items-center gap-2">
                          <Server className="h-4 w-4 text-purple-500" />
                          <span className="text-sm font-medium">Memory Usage</span>
                        </div>
                        <span className="text-sm font-bold">{`${formatNumber(systemMetrics?.memory?.percent, 1)}%`}</span>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-accent/50 rounded-lg">
                        <div className="flex items-center gap-2">
                          <HardDrive className="h-4 w-4 text-pink-500" />
                          <span className="text-sm font-medium">Disk Usage</span>
                        </div>
                        <span className="text-sm font-bold">{`${formatNumber(systemMetrics?.disk?.percent, 1)}%`}</span>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-accent/50 rounded-lg">
                        <div className="flex items-center gap-2">
                          <Network className="h-4 w-4 text-amber-500" />
                          <span className="text-sm font-medium">Network I/O</span>
                        </div>
                        <span className="text-sm font-bold">
                          {`${formatNumber((systemMetrics?.network?.bytes_sent ?? 0) / 1048576, 1)} MB`}
                        </span>
                      </div>
                      
                      <div className="mt-4 pt-4 border-t">
                        <h4 className="text-sm font-medium mb-2">Container Status</h4>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">Running Containers</span>
                          <Badge variant={runningContainers > 0 ? "default" : "secondary"}>
                            {runningContainers}/{totalContainers}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  )}
                </Card>
              </div>
            </TabsContent>

            {/* Billing */}
            <TabsContent value="billing" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <Card className="p-6 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="h-5 w-5 text-green-500" />
                      <h3 className="text-lg font-semibold">Month-to-date</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      Estimated pipeline cost accumulated so far this month.
                    </p>
                  </div>
                  {billingLoading && !billing ? (
                    <Skeleton className="h-10 w-32" />
                  ) : (
                    <p className="text-3xl font-bold">
                      {billing
                        ? `${billing.currency} ${formatNumber(billing.total_month_to_date, 2)}`
                        : "-"}
                    </p>
                  )}
                </Card>

                <Card className="p-6 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-5 w-5 text-blue-500" />
                      <h3 className="text-lg font-semibold">Projected Monthly</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      Projection based on current usage for a 30-day month.
                    </p>
                  </div>
                  {billingLoading && !billing ? (
                    <Skeleton className="h-10 w-32" />
                  ) : (
                    <p className="text-3xl font-bold">
                      {billing
                        ? `${billing.currency} ${formatNumber(billing.projected_monthly, 2)}`
                        : "-"}
                    </p>
                  )}
                </Card>

                <Card className="p-6 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="h-5 w-5 text-amber-500" />
                      <h3 className="text-lg font-semibold">Total Pipeline Minutes</h3>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      Sum of pipeline runtime across all projects this month.
                    </p>
                  </div>
                  {billingLoading && !billing ? (
                    <Skeleton className="h-10 w-32" />
                  ) : (
                    <p className="text-3xl font-bold">
                      {billing
                        ? (billing.projects ?? [])
                            .reduce((acc, p) => acc + (p.pipeline_minutes ?? 0), 0)
                            .toFixed(1)
                        : "0.0"}
                    </p>
                  )}
                </Card>
              </div>

              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Per-project breakdown</h3>
                    <p className="text-sm text-muted-foreground">
                      Detailed cost estimates for each project this month.
                    </p>
                  </div>
                  {billing?.last_updated && (
                    <span className="text-xs text-muted-foreground">
                      Last updated {new Date(billing.last_updated).toLocaleString()}
                    </span>
                  )}
                </div>
                {billingLoading && !billing ? (
                  <Skeleton className="h-40 w-full" />
                ) : !billing || billing.projects.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No billable deployments yet this month.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="text-xs text-muted-foreground border-b">
                        <tr>
                          <th className="py-2 text-left">Project</th>
                          <th className="py-2 text-right">Deployments</th>
                          <th className="py-2 text-right">Success</th>
                          <th className="py-2 text-right">Pipeline minutes</th>
                          <th className="py-2 text-right">Estimated cost</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(billing.projects ?? []).map((p) => (
                          <tr key={p.project_id} className="border-b last:border-0">
                            <td className="py-2 pr-4 font-medium">{p.name}</td>
                            <td className="py-2 text-right">{p.total_deployments}</td>
                            <td className="py-2 text-right">{p.successful_deployments}</td>
                            <td className="py-2 text-right">{formatNumber(p.pipeline_minutes, 1)}</td>
                            <td className="py-2 text-right">
                              {billing.currency} {formatNumber(p.estimated_cost, 3)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </Layout>
  );
}
