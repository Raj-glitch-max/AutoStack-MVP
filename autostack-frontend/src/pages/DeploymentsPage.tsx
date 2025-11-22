import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  GitBranch,
  Search,
  Filter,
  ExternalLink
} from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

type DeploymentItem = {
  id: string;
  name: string;
  projectId?: string | null;
  repo?: string | null;
  branch: string;
  status: string;
  commit?: string | null;
  duration?: string | null;
  time: string;
  url?: string | null;
  failedReason?: string | null;
};

const statusConfig: Record<string, { icon: typeof CheckCircle2; label: string; className: string }> = {
  success: {
    icon: CheckCircle2,
    label: "Success",
    className: "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20",
  },
  failed: {
    icon: XCircle,
    label: "Failed",
    className: "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20",
  },
  building: {
    icon: Clock,
    label: "Building",
    className: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20 animate-pulse",
  },
  queued: {
    icon: Clock,
    label: "Queued",
    className: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20",
  },
  copying: {
    icon: Clock,
    label: "Copying",
    className: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
  },
  cancelled: {
    icon: XCircle,
    label: "Cancelled",
    className: "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20",
  },
};

export default function DeploymentsPage() {
  const { authorizedRequest } = useAuth();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState<string>("");

  const {
    data,
    isLoading,
    error,
  } = useQuery<{ deployments: DeploymentItem[] }>({
    queryKey: ["deployments", { statusFilter, search }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") {
        params.set("status", statusFilter);
      }
      if (search.trim()) {
        params.set("search", search.trim());
      }
      const qs = params.toString();
      const path = qs ? `/api/deployments?${qs}` : "/api/deployments";
      const response = await authorizedRequest(path);
      if (!response.ok) {
        throw new Error("Failed to load deployments");
      }
      const json = await response.json();
      return { deployments: (json.deployments || []) as DeploymentItem[] };
    },
  });

  const deployments = data?.deployments || [];

  if (error) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-2">Deployments</h1>
            <p className="text-muted-foreground">View and manage all your deployments</p>
          </div>
          <Card className="p-6">
            <p className="text-red-500 mb-4">We couldn’t load your deployments right now.</p>
            <Button onClick={() => window.location.reload()}>Reload page</Button>
          </Card>
        </div>
      </Layout>
    );
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="container px-4 py-8 max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-2">Deployments</h1>
            <p className="text-muted-foreground">View and manage all your deployments</p>
          </div>

          <Card className="p-4 mb-6">
            <div className="flex flex-col md:flex-row gap-4">
              <Skeleton className="h-10 flex-1" />
              <Skeleton className="h-10 w-full md:w-[180px]" />
            </div>
          </Card>

          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Project</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Commit</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <Skeleton className="h-4 w-32" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-6 w-24" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-16" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-16" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-4 w-24" />
                    </TableCell>
                    <TableCell>
                      <Skeleton className="h-8 w-20 ml-auto" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container px-4 py-8 max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-2">Deployments</h1>
          <p className="text-muted-foreground">
            View and manage all your deployments
          </p>
        </div>

        {/* Filters */}
        <Card className="p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search deployments..."
                className="pl-10"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select
              value={statusFilter}
              onValueChange={(value) => setStatusFilter(value)}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="building">Building</SelectItem>
                <SelectItem value="queued">Queued</SelectItem>
                <SelectItem value="copying">Copying</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </Card>

        {/* Deployments Table */}
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project</TableHead>
                <TableHead>Branch</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Commit</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Time</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {deployments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No deployments found. Create a new deployment to see it here.
                  </TableCell>
                </TableRow>
              ) : (
                deployments.map((deployment) => {
                  const config = statusConfig[deployment.status] || {
                    icon: Clock,
                    label: deployment.status,
                    className: "bg-muted text-muted-foreground border-border",
                  };
                  const StatusIcon = config.icon;

                  return (
                    <TableRow key={deployment.id} className="hover:bg-accent/50">
                      <TableCell className="font-medium">
                        {deployment.name}
                        {deployment.status === "failed" && deployment.failedReason && (
                          <div
                            className="text-xs text-red-500 mt-1 line-clamp-1"
                            title={deployment.failedReason}
                          >
                            {deployment.failedReason}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <GitBranch className="h-3 w-3 text-muted-foreground" />
                          <span className="font-mono text-sm">{deployment.branch}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={cn("gap-1", config.className)}>
                          <StatusIcon className="h-3 w-3" />
                          {config.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <code className="text-sm">{deployment.commit ?? "-"}</code>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{deployment.duration ?? "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{deployment.time}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {deployment.url && (
                            <Button variant="ghost" size="sm" asChild>
                              <a href={deployment.url} target="_blank" rel="noopener noreferrer">
                                <ExternalLink className="h-4 w-4" />
                              </a>
                            </Button>
                          )}
                          <Button variant="outline" size="sm" asChild>
                            <Link to={`/deployments/${deployment.id}`}>
                              View Logs
                            </Link>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </Layout>
  );
}
