import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  CheckCircle2,
  Github,
  Rocket,
  Settings as SettingsIcon,
  ChevronRight
} from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { API_BASE_URL } from "@/config";

type GithubRepo = {
  id: number;
  name: string;
  fullName: string;
  private: boolean;
  defaultBranch: string;
};

type DockerfileDetectionResult = {
  hasDockerfile: boolean;
  path?: string | null;
};

const steps = [
  { id: 1, name: "Select Repository", icon: Github },
  { id: 2, name: "Configure Build", icon: SettingsIcon },
  { id: 3, name: "Deploy", icon: Rocket }
];

export default function DeployPage() {
  const navigate = useNavigate();
  const { authorizedRequest, token } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [deploying, setDeploying] = useState(false);
  const [formData, setFormData] = useState({
    repository: "",
    branch: "main",
    buildCommand: "npm run build",
    outputDir: "dist",
    envVars: "",
    autoDeployEnabled: false,
    autoDeployBranch: "",
  });

  const { data: githubStatus } = useQuery<{
    connected: boolean;
    username?: string | null;
    avatarUrl?: string | null;
  }>({
    queryKey: ["github-connection"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/github/connection");
      if (!response.ok) {
        if (response.status === 401) {
          return { connected: false, username: null };
        }
        throw new Error("Failed to load GitHub connection status");
      }
      return response.json();
    },
  });

  const {
    data: repos = [],
    isLoading: reposLoading,
    error: reposError,
  } = useQuery<GithubRepo[]>({
    queryKey: ["github-repos"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/github/repos");
      if (!response.ok) {
        throw new Error("Failed to load GitHub repositories");
      }
      const data = await response.json();
      const rawRepos = (data.repos || []) as any[];
      return rawRepos.map((repo) => ({
        id: repo.id,
        name: repo.name,
        // Backend uses camelCase JSON (fullName, defaultBranch) via alias generator,
        // but we support both camelCase and snake_case for safety.
        fullName: repo.fullName ?? repo.full_name ?? repo.name,
        private: repo.private,
        defaultBranch: repo.defaultBranch ?? repo.default_branch ?? "main",
      }));
    },
  });

  const {
    data: dockerfileInfo,
    isLoading: dockerfileLoading,
    error: dockerfileError,
  } = useQuery<DockerfileDetectionResult>({
    queryKey: ["dockerfile-detect", formData.repository, formData.branch],
    enabled: !!formData.repository && !!formData.branch,
    queryFn: async () => {
      const params = new URLSearchParams({
        repository: formData.repository,
        branch: formData.branch || "main",
      });
      const response = await authorizedRequest(`/api/github/dockerfile?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Failed to detect Dockerfile for this repo/branch");
      }
      return response.json();
    },
  });

  const dockerRuntime = dockerfileInfo?.hasDockerfile === true;

  const { data: webhookInfo } = useQuery<{ url: string; secret: string }>({
    queryKey: ["github-webhook-info"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/github/webhook-info");
      if (!response.ok) {
        throw new Error("Failed to load webhook info");
      }
      return response.json();
    },
  });

  const githubConnected = githubStatus?.connected;
  const githubUsername = githubStatus?.username ?? null;
  const githubAvatarUrl = githubStatus?.avatarUrl ?? undefined;

  const handleGithubConnect = () => {
    const url = `${API_BASE_URL}/auth/github` + (token ? `?token=${token}` : "");
    window.location.href = url;
  };

  const handleGithubDisconnect = async () => {
    try {
      const response = await authorizedRequest("/api/github/disconnect", { method: "DELETE" });
      if (!response.ok) {
        throw new Error("Failed to disconnect GitHub account");
      }

      toast({
        title: "GitHub disconnected",
        description: "Your GitHub account has been disconnected.",
      });

      setFormData({
        repository: "",
        branch: "main",
        buildCommand: "npm run build",
        outputDir: "dist",
        envVars: "",
        autoDeployEnabled: false,
        autoDeployBranch: "",
      });
    } catch (error: any) {
      toast({
        title: "Disconnect failed",
        description: error?.message || "Could not disconnect GitHub account.",
        variant: "destructive",
      });
    }
  };

  const handleDeploy = async () => {
    if (!formData.repository) {
      toast({
        title: "Select a repository",
        description: "Please select a GitHub repository before deploying.",
        variant: "destructive",
      });
      return;
    }

    try {
      setDeploying(true);
      toast({
        title: "Deployment started",
        description: "Your app is being deployed...",
      });

      const response = await authorizedRequest("/api/deployments", {
        method: "POST",
        body: JSON.stringify({
          repository: formData.repository,
          branch: formData.branch,
          buildCommand: formData.buildCommand,
          outputDir: formData.outputDir,
          envVars: formData.envVars || null,
          autoDeployEnabled: formData.autoDeployEnabled || undefined,
          autoDeployBranch: formData.autoDeployEnabled
            ? formData.autoDeployBranch || formData.branch
            : undefined,
          runtime: dockerRuntime ? "docker" : "static",
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        const message = error?.error?.message || "Failed to start deployment";
        toast({
          title: "Deployment failed",
          description: message,
          variant: "destructive",
        });
        setDeploying(false);
        return;
      }

      const data = await response.json();

      toast({
        title: "Deployment queued",
        description: `Deployment for ${data.name} has started.`,
      });

      navigate(`/deployments/${data.id}`);
    } catch (error: any) {
      toast({
        title: "Deployment failed",
        description: error?.message || "Something went wrong while starting deployment.",
        variant: "destructive",
      });
      setDeploying(false);
    }
  };

  return (
    <Layout>
      <div className="container px-4 py-8 max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-2">New Deployment</h1>
          <p className="text-muted-foreground">
            Deploy your application in three simple steps
          </p>
        </div>

        {!githubConnected && (
          <Card className="mb-8 p-4 border-primary/40 bg-primary/5 flex items-center justify-between flex-col sm:flex-row gap-3">
            <div>
              <p className="font-medium flex items-center gap-2">
                <Github className="h-4 w-4" />
                Connect your GitHub account
              </p>
              <p className="text-xs text-muted-foreground">
                Link GitHub once, then pick any repo and deploy with a single click.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={handleGithubConnect}>
              <Github className="mr-2 h-4 w-4" />
              Connect GitHub
            </Button>
          </Card>
        )}

        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={cn(
                      "w-12 h-12 rounded-full flex items-center justify-center transition-all mb-2",
                      currentStep >= step.id
                        ? "gradient-primary text-white"
                        : "bg-accent text-muted-foreground"
                    )}
                  >
                    {currentStep > step.id ? (
                      <CheckCircle2 className="h-6 w-6" />
                    ) : (
                      <step.icon className="h-6 w-6" />
                    )}
                  </div>
                  <span className={cn(
                    "text-sm font-medium text-center",
                    currentStep >= step.id ? "text-foreground" : "text-muted-foreground"
                  )}>
                    {step.name}
                  </span>
                </div>
                {index < steps.length - 1 && (
                  <div className={cn(
                    "h-0.5 flex-1 mx-4 transition-all",
                    currentStep > step.id ? "gradient-primary" : "bg-border"
                  )} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <Card className="p-8">
          {currentStep === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold mb-2">Select Repository</h2>
                <p className="text-muted-foreground">
                  Choose a GitHub repository to deploy
                </p>
              </div>

              {githubConnected && (
                <Card className="max-w-md mx-auto p-4 bg-accent/30 border-dashed flex flex-col gap-3">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-10 w-10">
                      {githubAvatarUrl && <AvatarImage src={githubAvatarUrl} alt={githubUsername ?? "GitHub"} />}
                      <AvatarFallback>
                        {(githubUsername ?? "GH").slice(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="text-sm font-medium">GitHub Account</p>
                      <p className="text-xs text-muted-foreground">
                        {githubUsername ? `@${githubUsername}` : "Connected via GitHub OAuth"}
                      </p>
                      {githubUsername && (
                        <p className="text-[11px] text-muted-foreground mt-1">
                          Connected via GitHub OAuth
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {githubUsername && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-1"
                        onClick={() => window.open(`https://github.com/${githubUsername}`, "_blank")}
                      >
                        <Github className="h-3 w-3" />
                        <span className="text-xs">Manage GitHub Account</span>
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="gap-1 text-red-600 border-red-200 hover:text-red-700"
                      onClick={handleGithubDisconnect}
                    >
                      <span className="text-xs">Disconnect</span>
                    </Button>
                  </div>
                </Card>
              )}

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="repository">Repository</Label>
                  <Select
                    value={formData.repository}
                    onValueChange={(value) => {
                      const repo = repos.find((r) => r.fullName === value || r.name === value);
                      const repoLabel = repo?.fullName ?? repo?.name ?? value;
                      setFormData({
                        ...formData,
                        repository: repoLabel,
                        branch: repo?.defaultBranch || formData.branch,
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={reposLoading ? "Loading repositories..." : "Select a repository"} />
                    </SelectTrigger>
                    <SelectContent>
                      {reposLoading && (
                        <SelectItem disabled value="loading">
                          Loading repositories...
                        </SelectItem>
                      )}
                      {reposError && !reposLoading && (
                        <SelectItem disabled value="error">
                          Failed to load GitHub repositories
                        </SelectItem>
                      )}
                      {!reposLoading && !reposError && repos.length === 0 && (
                        <SelectItem disabled value="empty">
                          No repositories found. Connect GitHub and push a repo.
                        </SelectItem>
                      )}
                      {!reposLoading && !reposError &&
                        repos.map((repo) => {
                          const label = repo.fullName ?? repo.name ?? `Repo ${repo.id}`;
                          return (
                            <SelectItem key={repo.id} value={label}>
                              {label}
                            </SelectItem>
                          );
                        })}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="branch">Branch</Label>
                  <Input
                    id="branch"
                    value={formData.branch}
                    onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                    placeholder="main"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button
                  variant="gradient"
                  onClick={() => setCurrentStep(2)}
                  disabled={!formData.repository}
                >
                  Continue
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold mb-2">Configure Build</h2>
                <p className="text-muted-foreground">
                  Set up your build configuration
                </p>
              </div>

              {formData.repository && (
                <div className="space-y-1 text-xs text-muted-foreground">
                  {dockerfileLoading ? (
                    <p>Detecting Dockerfile for {formData.repository} on branch {formData.branch}...</p>
                  ) : dockerfileError ? (
                    <p>
                      Could not detect a Dockerfile automatically; falling back to static build. You can still deploy
                      using the build command and output directory below.
                    </p>
                  ) : dockerRuntime ? (
                    <p>
                      Dockerfile detected at the repo root. This project will use the Docker runtime in addition to
                      the static build pipeline and Kubernetes image.
                    </p>
                  ) : (
                    <p>
                      No Dockerfile detected at the repo root. The deployment will use the static build pipeline and
                      serve the built artifacts directly.
                    </p>
                  )}
                </div>
              )}

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="buildCommand">Build Command</Label>
                  <Input
                    id="buildCommand"
                    value={formData.buildCommand}
                    onChange={(e) => setFormData({ ...formData, buildCommand: e.target.value })}
                    placeholder="npm run build"
                  />
                  <p className="text-xs text-muted-foreground">
                    Command to build your application
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="outputDir">Output Directory</Label>
                  <Input
                    id="outputDir"
                    value={formData.outputDir}
                    onChange={(e) => setFormData({ ...formData, outputDir: e.target.value })}
                    placeholder="dist"
                  />
                  <p className="text-xs text-muted-foreground">
                    Directory where build output is generated
                  </p>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label htmlFor="envVars">Environment Variables (Optional)</Label>
                  <Textarea
                    id="envVars"
                    value={formData.envVars}
                    onChange={(e) => setFormData({ ...formData, envVars: e.target.value })}
                    placeholder="KEY=value&#10;API_KEY=your_api_key"
                    rows={4}
                  />
                  <p className="text-xs text-muted-foreground">
                    One per line, format: KEY=value
                  </p>
                </div>

                <Separator />

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label className="text-sm font-medium">Enable auto-deploy on push</Label>
                      <p className="text-xs text-muted-foreground">
                        Automatically trigger a deployment when a push happens on the configured branch.
                      </p>
                    </div>
                    <Switch
                      checked={formData.autoDeployEnabled}
                      onCheckedChange={(checked) =>
                        setFormData({
                          ...formData,
                          autoDeployEnabled: checked,
                          autoDeployBranch: checked
                            ? formData.autoDeployBranch || formData.branch
                            : "",
                        })
                      }
                    />
                  </div>

                  {formData.autoDeployEnabled && (
                    <div className="space-y-1">
                      <Label htmlFor="autoDeployBranch" className="text-xs">Auto-deploy branch</Label>
                      <Input
                        id="autoDeployBranch"
                        value={formData.autoDeployBranch || formData.branch}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            autoDeployBranch: e.target.value,
                          })
                        }
                        placeholder="main"
                      />
                      <p className="text-[11px] text-muted-foreground">
                        Only pushes to this branch will trigger auto-deploys.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep(1)}>
                  Back
                </Button>
                <Button variant="gradient" onClick={() => setCurrentStep(3)}>
                  Continue
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold mb-2">Review & Deploy</h2>
                <p className="text-muted-foreground">
                  Review your configuration before deploying
                </p>
              </div>

              <div className="space-y-4">
                <Card className="p-4 bg-accent/30">
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Repository</span>
                      <div className="flex items-center gap-2">
                        <Github className="h-4 w-4" />
                        <span className="font-medium">{formData.repository}</span>
                      </div>
                    </div>
                    <Separator />
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Branch</span>
                      <Badge variant="outline">{formData.branch}</Badge>
                    </div>
                    <Separator />
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Build Command</span>
                      <code className="text-sm bg-background px-2 py-1 rounded">
                        {formData.buildCommand}
                      </code>
                    </div>
                    <Separator />
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Output Directory</span>
                      <code className="text-sm bg-background px-2 py-1 rounded">
                        {formData.outputDir}
                      </code>
                    </div>
                    <Separator />
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Runtime</span>
                      <Badge variant="outline">
                        {dockerRuntime ? "Docker container" : "Static artifacts"}
                      </Badge>
                    </div>
                  </div>
                </Card>

                {webhookInfo && (
                  <Card className="p-4 border border-dashed border-muted-foreground/30">
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold">GitHub Webhook Setup</h3>
                      <p className="text-xs text-muted-foreground">
                        To enable auto-deploy on push, add this webhook in your GitHub repository settings:
                      </p>
                      <div className="space-y-1">
                        <p className="text-[11px] font-semibold text-muted-foreground">Payload URL</p>
                        <code className="block text-[11px] break-all bg-background px-2 py-1 rounded">
                          {webhookInfo.url}
                        </code>
                      </div>
                      <div className="space-y-1">
                        <p className="text-[11px] font-semibold text-muted-foreground">Secret</p>
                        <code className="block text-[11px] break-all bg-background px-2 py-1 rounded">
                          {webhookInfo.secret}
                        </code>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        In GitHub: <span className="font-semibold">Settings → Webhooks → Add webhook</span>,
                        set content type to <code>application/json</code>, use the URL and secret above, and
                        enable the <code>push</code> event.
                      </p>
                    </div>
                  </Card>
                )}

                {deploying && (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 mx-auto mb-4 gradient-primary rounded-full flex items-center justify-center animate-pulse">
                      <Rocket className="h-8 w-8 text-white" />
                    </div>
                    <p className="font-medium">Deploying your application...</p>
                    <p className="text-sm text-muted-foreground">This may take a few moments</p>
                  </div>
                )}
              </div>

              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep(2)} disabled={deploying}>
                  Back
                </Button>
                <Button variant="gradient" onClick={handleDeploy} disabled={deploying}>
                  <Rocket className="mr-2 h-4 w-4" />
                  {deploying ? "Deploying..." : "Deploy Now"}
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}
