import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Github } from "lucide-react";

export type GithubConnectionStatus = {
  connected: boolean;
  username?: string | null;
  avatarUrl?: string | null;
  scope?: string | null;
  connectedAt?: string | null;
};

interface Props {
  status: GithubConnectionStatus | undefined;
  loading: boolean;
  error?: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
  onRetry?: () => void;
}

export function GithubConnectionCard({ status, loading, error, onConnect, onDisconnect, onRetry }: Props) {
  if (loading) {
    return (
      <Card className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
        </div>
        <Skeleton className="h-8 w-28" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6 flex items-center justify-between border-destructive/40 bg-destructive/5">
        <div className="flex flex-col gap-1">
          <p className="font-semibold">Unable to load GitHub connection</p>
          <p className="text-xs text-muted-foreground max-w-md break-words">{error}</p>
        </div>
        <div className="flex items-center gap-2">
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              Retry
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onConnect}>
            <Github className="mr-2 h-4 w-4" />
            Connect GitHub
          </Button>
        </div>
      </Card>
    );
  }

  if (!status || !status.connected) {
    return (
      <Card className="p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-accent">
            <Github className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold">GitHub not connected</p>
            <p className="text-sm text-muted-foreground">
              Connect your GitHub account to select repositories and enable auto-deploy on push.
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={onConnect}>
          <Github className="mr-2 h-4 w-4" />
          Connect GitHub
        </Button>
      </Card>
    );
  }

  const initials = status.username?.[0]?.toUpperCase() ?? "GH";
  const connectedAt = status.connectedAt ? new Date(status.connectedAt) : null;

  return (
    <Card className="p-6 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Avatar className="h-10 w-10">
          <AvatarImage src={status.avatarUrl ?? undefined} />
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        <div>
          <p className="font-semibold flex items-center gap-2">
            <Github className="h-4 w-4" />
            {status.username}
            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 border-green-500/30 text-green-600 bg-green-500/5"
            >
              Connected
            </Badge>
          </p>
          <p className="text-xs text-muted-foreground">
            Connected
            {connectedAt && ` • since ${connectedAt.toLocaleDateString()} ${connectedAt.toLocaleTimeString()}`}
          </p>
          {status.scope && (
            <p className="text-[11px] text-muted-foreground mt-1">
              Scopes: {status.scope}
            </p>
          )}
        </div>
      </div>
      <Button variant="outline" onClick={onDisconnect}>
        Disconnect
      </Button>
    </Card>
  );
}
