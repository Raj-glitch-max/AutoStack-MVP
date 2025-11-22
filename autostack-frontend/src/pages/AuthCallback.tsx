import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/useAuth";

export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { completeOAuth } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const provider = params.get("provider");
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const expiresInParam = params.get("expires_in");
    const expiresIn = expiresInParam ? Number(expiresInParam) : null;

    async function finalize() {
      if (accessToken && refreshToken) {
        try {
          await completeOAuth({ provider, accessToken, refreshToken, expiresIn });
          toast({
            title: `${provider ?? "OAuth"} login successful`,
            description: "Redirecting you to the dashboard.",
          });
          navigate("/dashboard", { replace: true });
          return;
        } catch (error) {
          toast({
            title: "Authentication failed",
            description: error instanceof Error ? error.message : "Could not finish OAuth login.",
            variant: "destructive",
          });
        }
      } else {
        toast({
          title: "Authentication failed",
          description: "Missing tokens in callback response.",
          variant: "destructive",
        });
      }
      navigate("/login", { replace: true });
    }

    finalize();
  }, [completeOAuth, location.search, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="p-8 flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center space-y-1">
          <p className="font-semibold">Completing sign in…</p>
          <p className="text-sm text-muted-foreground">You’ll be redirected in just a moment.</p>
        </div>
        <Button variant="ghost" onClick={() => navigate("/login")}>
          Back to login
        </Button>
      </Card>
    </div>
  );
}

