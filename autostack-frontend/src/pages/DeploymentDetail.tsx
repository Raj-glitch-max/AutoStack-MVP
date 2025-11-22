import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  CheckCircle2,
  XCircle,
  Clock,
  GitBranch,
  ExternalLink,
  Copy,
  ArrowLeft,
  Play,
  Pause,
  Trash2,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { API_BASE_URL } from "@/config";
import { loadTokens } from "@/lib/auth-storage";

type DeploymentStage = {
  name: string;
  status: string;
  timestamp?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
};

type CommitInfo = {
  sha?: string | null;
  message?: string | null;
  author?: string | null;
  timestamp?: string | null;
};

type DeploymentDetailResponse = {
  id: string;
  name: string;
  repo?: string | null;
  branch: string;
  status: string;
  time: string;
  url?: string | null;
  commit?: CommitInfo | null;
  duration?: string | null;
  creatorType: string;
  isProduction: boolean;
  envVars?: string | null;
  stages: DeploymentStage[];
  logs: string[];
};

type RuntimeMetrics = {
  uptime_seconds?: number | null;
  container_status?: string | null;
  last_health?: {
    url?: string | null;
    http_status?: number | null;
    latency_ms?: number | null;
    is_live?: boolean;
    checked_at?: string | null;
  } | null;
};

type PipelineStageMetric = {
  name: string;
  display_name: string;
  status: string;
  duration_seconds: number;
  start_time?: string | null;
  end_time?: string | null;
};

type PipelineMetricsResponse = {
  deployment_id: string;
  pipeline: {
    style: string;
    stages: PipelineStageMetric[];
    total_duration: number;
    estimated_duration: number;
    efficiency: number | null;
    start_time?: string | null;
    end_time?: string | null;
  };
  timestamp: string;
};

const getStatusConfig = (status: string) => {
  switch (status) {
    case "success":
      return {
        label: "Success",
        className: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
        icon: CheckCircle2,
      };
    case "failed":
      return {
        label: "Failed",
        className: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20",
        icon: XCircle,
      };
    case "building":
      return {
        label: "Building",
        className: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20 animate-pulse",
        icon: Clock,
      };
    case "queued":
      return {
        label: "Queued",
        className: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20",
        icon: Clock,
      };
    case "copying":
      return {
        label: "Copying",
        className: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
        icon: Clock,
      };
    case "cancelled":
      return {
        label: "Cancelled",
        className: "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20",
        icon: XCircle,
      };
    default:
      return {
        label: status,
        className: "bg-muted text-muted-foreground border-border",
        icon: Clock,
      };
  }
};

const buildLogsWebSocketUrl = (deploymentId: string, token: string): string => {
  try {
    const apiUrl = new URL(API_BASE_URL);
    const wsProtocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${apiUrl.host}/api/deployments/${deploymentId}/logs/stream?token=${encodeURIComponent(
      token,
    )}`;
  } catch {
    const loc = window.location;
    const wsProtocol = loc.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${loc.host}/api/deployments/${deploymentId}/logs/stream?token=${encodeURIComponent(
      token,
    )}`;
  }
};

export default function DeploymentDetail() {
  const { id } = useParams<{ id: string }>();
  const { authorizedRequest } = useAuth();

  const [logs, setLogs] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [streaming, setStreaming] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const {
    data,
    isLoading,
    error,
  } = useQuery<DeploymentDetailResponse>({
    queryKey: ["deployment-detail", id],
    enabled: !!id,
    queryFn: async () => {
      const response = await authorizedRequest(`/api/deployments/${id}`);
      if (!response.ok) {
        throw new Error("Failed to load deployment");
      }
      const json = await response.json();
      return json as DeploymentDetailResponse;
    },
  });

  const { data: pipelineData, isLoading: pipelineLoading } = useQuery<PipelineMetricsResponse>({
    queryKey: ["pipeline-metrics", id],
    enabled: !!id,
    queryFn: async () => {
      const response = await authorizedRequest(`/api/monitoring/pipeline/${id}`);
      if (!response.ok) {
        throw new Error("Failed to load pipeline metrics");
      }
      const json = await response.json();
      return json as PipelineMetricsResponse;
    },
    refetchInterval: 5000,
  });

  const { data: runtimeMetrics } = useQuery<RuntimeMetrics>({
    queryKey: ["deployment-runtime-metrics", id],
    enabled: !!id,
    queryFn: async () => {
      const response = await authorizedRequest(`/api/deployments/${id}/metrics`);
      if (!response.ok) {
        throw new Error("Failed to load runtime metrics");
      }
      return response.json();
    },
    refetchInterval: 10000,
  });

  // Seed logs from initial API response
  useEffect(() => {
    if (data && data.logs && data.logs.length > 0 && logs.length === 0) {
      setLogs(data.logs);
    }
  }, [data, logs.length]);

  // WebSocket log streaming
  useEffect(() => {
    if (!id) return;

    const tokens = loadTokens();
    const accessToken = tokens?.accessToken;
    if (!accessToken) return;

    const wsUrl = buildLogsWebSocketUrl(id, accessToken);
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;
    setStreaming(true);

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "history" && Array.isArray(payload.logs)) {
          setLogs(payload.logs);
        } else if (payload.type === "log" && typeof payload.line === "string") {
          setLogs((prev) => [...prev, payload.line]);
        } else if (payload.type === "pipeline_stage" && typeof payload.message === "string") {
          setLogs((prev) => [...prev, payload.message]);
        }
      } catch {
        // ignore non-JSON messages
      }
    };

    socket.onclose = () => {
      setStreaming(false);
    };

    socket.onerror = () => {
      setStreaming(false);
    };

    return () => {
      setStreaming(false);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [id]);

  // Auto-scroll logs
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const copyUrl = () => {
    if (!data?.url) return;
    navigator.clipboard.writeText(data.url);
    toast({
      title: "URL copied",
      description: "Deployment URL copied to clipboard",
    });
  };

  const deleteDeployment = async () => {
    if (!id) return;

    if (!confirm("Are you sure you want to delete this deployment? This will stop and remove the container.")) {
      return;
    }

    try {
      const response = await authorizedRequest(`/api/deployments/${id}/delete`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to delete deployment");
      }

      toast({
        title: "Deployment deleted",
        description: "The deployment and its container have been removed",
      });

      // Redirect to deployments page
      window.location.href = "/deployments";
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete deployment. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-6xl mx-auto">
          <p className="text-muted-foreground">Loading deployment...</p>
        </div>
      </Layout>
    );
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-6xl mx-auto">
          <p className="text-red-500 mb-4">Failed to load deployment. Please go back and try again.</p>
          <Button variant="ghost" asChild>
            <Link to="/deployments">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Deployments
            </Link>
          </Button>
        </div>
      </Layout>
    );
  }

  const deployment = data;
  const statusConfig = getStatusConfig(deployment.status);
  const StatusIcon = statusConfig.icon;
  const commitShaShort = deployment.commit?.sha?.slice(0, 7) ?? "-";
  const duration = deployment.duration ?? "-";
  const deployedAt = new Date(deployment.time);
  const pipeline = pipelineData?.pipeline;

  return (
    <Layout>
      <div className="container px-4 py-8 max-w-6xl mx-auto">
        <Button variant="ghost" className="mb-6" asChild>
          <Link to="/deployments">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Deployments
          </Link>
        </Button>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Deployment Info */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold mb-1">{deployment.name}</h2>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <GitBranch className="h-3 w-3" />
                    <span className="font-mono">{deployment.branch}</span>
                  </div>
                </div>
                <Badge className={cn("gap-1", statusConfig.className)}>
                  <StatusIcon className="h-3 w-3" />
                  <span className="capitalize">{statusConfig.label}</span>
                </Badge>
              </div>

              <Separator className="my-4" />

              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Commit</span>
                  <code className="font-mono">{commitShaShort}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration</span>
                  <span>{duration}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Deployed</span>
                  <span>{deployedAt.toLocaleString()}</span>
                </div>
              </div>

              <Separator className="my-4" />

              <div className="space-y-2">
                {deployment.url && (
                  <Button variant="gradient" className="w-full gap-2" asChild>
                    <a href={deployment.url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4" />
                      Visit Site
                    </a>
                  </Button>
                )}
                {deployment.url && (
                  <Button variant="outline" className="w-full gap-2" onClick={copyUrl}>
                    <Copy className="h-4 w-4" />
                    Copy URL
                  </Button>
                )}
                <Button
                  variant="destructive"
                  className="w-full gap-2"
                  onClick={deleteDeployment}
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Deployment
                </Button>
              </div>
            </Card>

            {/* Deployment Stages */}
            <Card className="p-6">
              <h3 className="font-semibold mb-4">Deployment Stages</h3>
              <div className="space-y-3">
                {deployment.stages.map((stage, index) => {
                  const isCompleted = stage.status === "completed";
                  const isActive = stage.status === "in_progress";
                  const isFailed = stage.status === "failed" || stage.status === "cancelled";
                  let icon = Clock;
                  let iconClass = "text-muted-foreground";

                  if (isCompleted) {
                    icon = CheckCircle2;
                    iconClass = "text-green-600";
                  } else if (isFailed) {
                    icon = XCircle;
                    iconClass = "text-red-600";
                  } else if (isActive) {
                    icon = Clock;
                    iconClass = "text-blue-600 animate-pulse";
                  }

                  const StageIcon = icon;

                  return (
                    <div key={`${stage.name}-${index}`} className="flex items-center gap-3">
                      <StageIcon className={cn("h-5 w-5 shrink-0", iconClass)} />
                      <span
                        className={cn(
                          "text-sm",
                          isCompleted
                            ? "text-foreground"
                            : isFailed
                              ? "text-red-600"
                              : "text-muted-foreground",
                        )}
                      >
                        {stage.name}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="font-semibold mb-4">Jenkins Pipeline</h3>
              {pipelineLoading && !pipeline ? (
                <p className="text-sm text-muted-foreground">Loading pipeline metrics...</p>
              ) : !pipeline ? (
                <p className="text-sm text-muted-foreground">Pipeline metrics not available for this deployment.</p>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <div>
                      <span className="text-muted-foreground">Total duration</span>
                      <div className="font-mono">
                        {Math.round(pipeline.total_duration)}s
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Estimated</span>
                      <div className="font-mono">
                        {Math.round(pipeline.estimated_duration)}s
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Efficiency</span>
                      <div className="font-mono">
                        {pipeline.efficiency != null ? `${pipeline.efficiency.toFixed(1)}%` : "-"}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {pipeline.stages.map((stage) => {
                      const statusLower = stage.status.toLowerCase();
                      const isSuccess = statusLower === "completed" || statusLower === "success";
                      const isFailed = statusLower === "failed" || statusLower === "cancelled";
                      const isRunning = statusLower === "in_progress" || statusLower === "started";

                      let Icon = Clock;
                      let colorClass = "text-muted-foreground";
                      if (isSuccess) {
                        Icon = CheckCircle2;
                        colorClass = "text-green-600";
                      } else if (isFailed) {
                        Icon = XCircle;
                        colorClass = "text-red-600";
                      } else if (isRunning) {
                        Icon = Clock;
                        colorClass = "text-blue-600 animate-pulse";
                      }

                      return (
                        <div key={stage.name} className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <Icon className={cn("h-4 w-4", colorClass)} />
                            <div>
                              <div className="text-sm font-medium">{stage.display_name}</div>
                              <div className="text-xs text-muted-foreground">{stage.status.toLowerCase()}</div>
                            </div>
                          </div>
                          <div className="text-xs font-mono text-muted-foreground">
                            {Math.round(stage.duration_seconds)}s
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </Card>

            <Card className="p-6">
              <h3 className="font-semibold mb-4">Runtime Status</h3>
              {!runtimeMetrics ? (
                <p className="text-sm text-muted-foreground">
                  Runtime metrics are not available yet for this deployment.
                </p>
              ) : (
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Container status</span>
                    <span className="font-mono capitalize">
                      {runtimeMetrics.container_status ?? "unknown"}
                    </span>
                  </div>
                  {runtimeMetrics.uptime_seconds != null && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Uptime</span>
                      <span className="font-mono">
                        {Math.max(0, Math.round(runtimeMetrics.uptime_seconds))}s
                      </span>
                    </div>
                  )}
                  {runtimeMetrics.last_health && (
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        Last health check at{" "}
                        {runtimeMetrics.last_health.checked_at
                          ? new Date(runtimeMetrics.last_health.checked_at).toLocaleString()
                          : "–"}
                      </p>
                      <div className="flex items-center justify-between text-xs">
                        <span>
                          HTTP {runtimeMetrics.last_health.http_status ?? "–"} •{" "}
                          {runtimeMetrics.last_health.latency_ms ?? "–"} ms
                        </span>
                        <Badge
                          variant="outline"
                          className={
                            runtimeMetrics.last_health.is_live
                              ? "border-green-500/40 text-green-500"
                              : "border-red-500/40 text-red-500"
                          }
                        >
                          {runtimeMetrics.last_health.is_live ? "Healthy" : "Unhealthy"}
                        </Badge>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>
          </div>

          {/* Logs Viewer */}
          <div className="lg:col-span-2">
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Deployment Logs</h3>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAutoScroll(!autoScroll)}
                    className="gap-2"
                  >
                    {autoScroll ? (
                      <>
                        <Pause className="h-3 w-3" />
                        Pause Auto-scroll
                      </>
                    ) : (
                      <>
                        <Play className="h-3 w-3" />
                        Resume Auto-scroll
                      </>
                    )}
                  </Button>
                  {streaming && (
                    <Badge variant="outline" className="gap-1 animate-pulse">
                      <div className="h-2 w-2 rounded-full bg-green-600" />
                      Live
                    </Badge>
                  )}
                </div>
              </div>

              <div className="relative">
                <div className="bg-black/90 text-green-400 font-mono text-sm p-4 rounded-lg h-[600px] overflow-auto">
                  {logs.map((log, index) => {
                    const lower = log.toLowerCase();
                    const isError = lower.includes("error") || lower.includes("failed");
                    const isSuccess = lower.includes("success") || lower.includes("completed");
                    const isInfo = lower.includes("starting") || lower.includes("running");

                    return (
                      <div
                        key={index}
                        className={cn(
                          "py-0.5",
                          isError && "text-red-400",
                          isSuccess && "text-green-400",
                          isInfo && "text-blue-400",
                        )}
                      >
                        {log}
                      </div>
                    );
                  })}
                  <div ref={logsEndRef} />
                  {streaming && (
                    <div className="flex items-center gap-2 py-0.5">
                      <div className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
                      <span className="text-muted-foreground">Streaming logs...</span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
}
