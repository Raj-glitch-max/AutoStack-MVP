import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  User,
  Bell,
  Shield,
  Key,
  Github,
  Moon,
  Sun
} from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { GithubConnectionCard, GithubConnectionStatus } from "@/components/GithubConnectionCard";
import { API_BASE_URL } from "@/config";
import { toast } from "@/hooks/use-toast";

export default function SettingsPage() {
  const { user, authorizedRequest, token } = useAuth();
  const [isDark, setIsDark] = useState(false);

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle("dark");
  };

  const { data: githubStatus, isLoading: githubLoading, error: githubError, refetch: refetchGithub } = useQuery<GithubConnectionStatus>({
    queryKey: ["github-connection"],
    queryFn: async () => {
      const response = await authorizedRequest("/api/github/connection");
      if (!response.ok) {
        throw new Error("Failed to load GitHub connection status");
      }
      return response.json();
    },
  });

  const disconnectGithub = useMutation({
    mutationFn: async () => {
      const response = await authorizedRequest("/api/github/disconnect", { method: "DELETE" });
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.error?.message || "Failed to disconnect GitHub");
      }
    },
    onSuccess: () => {
      toast({ title: "GitHub disconnected" });
      refetchGithub();
    },
    onError: (error: any) => {
      toast({ title: "GitHub disconnect failed", description: error?.message || "Unexpected error", variant: "destructive" });
    },
  });

  const handleGithubConnect = () => {
    const url = `${API_BASE_URL}/auth/github` + (token ? `?token=${token}` : "");
    window.location.href = url;
  };

  return (
    <Layout>
      <div className="container px-4 py-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-2">Settings</h1>
          <p className="text-base md:text-lg text-muted-foreground">
            Manage your account and preferences
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-1">
            <Card className="p-4">
              <div className="flex items-center gap-3 p-4 mb-4">
                <Avatar className="h-16 w-16">
                  <AvatarImage src={user?.avatarUrl ?? undefined} />
                  <AvatarFallback>{user?.name?.[0]?.toUpperCase() ?? "U"}</AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-semibold">{user?.name ?? "Account"}</p>
                  <p className="text-sm text-muted-foreground">{user?.email ?? ""}</p>
                </div>
              </div>
              <Separator className="mb-2" />
              <nav className="space-y-1">
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-accent text-foreground font-medium">
                  <User className="h-4 w-4" />
                  Profile
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                  <Bell className="h-4 w-4" />
                  Notifications
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                  <Shield className="h-4 w-4" />
                  Security
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                  <Key className="h-4 w-4" />
                  API Keys
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                  <Github className="h-4 w-4" />
                  GitHub
                </button>
              </nav>
            </Card>
          </div>

          {/* Settings Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Profile Settings */}
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-6">Profile Information</h3>
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input id="firstName" placeholder="Your name" defaultValue={user?.name ?? ""} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input id="lastName" placeholder="Doe" defaultValue="Doe" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" placeholder="you@example.com" defaultValue={user?.email ?? ""} disabled />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company">Company</Label>
                  <Input id="company" placeholder="Acme Inc." />
                </div>
                <Button variant="gradient">Save Changes</Button>
              </div>
            </Card>

            {/* GitHub Integration */}
            <GithubConnectionCard
              status={githubStatus}
              loading={githubLoading || disconnectGithub.isPending}
              error={githubError instanceof Error ? githubError.message : null}
              onConnect={handleGithubConnect}
              onDisconnect={() => disconnectGithub.mutate()}
              onRetry={() => refetchGithub()}
            />

            {/* Notification Settings */}
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-6">Notification Preferences</h3>
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Deployment Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Get notified when deployments complete
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Failure Alerts</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive alerts for failed deployments
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Weekly Reports</Label>
                    <p className="text-sm text-muted-foreground">
                      Get weekly summary of your deployments
                    </p>
                  </div>
                  <Switch />
                </div>
                <Separator />
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>System Updates</Label>
                    <p className="text-sm text-muted-foreground">
                      Stay informed about platform updates
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </div>
            </Card>

            {/* Appearance Settings */}
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-6">Appearance</h3>
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Theme</Label>
                    <p className="text-sm text-muted-foreground">
                      Choose your preferred color theme
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={toggleTheme}
                    className="gap-2"
                  >
                    {isDark ? (
                      <>
                        <Sun className="h-4 w-4" />
                        Light
                      </>
                    ) : (
                      <>
                        <Moon className="h-4 w-4" />
                        Dark
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </Card>

            {/* Security Settings */}
            <Card className="p-6">
              <h3 className="text-xl font-semibold mb-6">Security</h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <Input id="currentPassword" type="password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input id="newPassword" type="password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input id="confirmPassword" type="password" />
                </div>
                <Button variant="outline">Update Password</Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </Layout>
  );
}
