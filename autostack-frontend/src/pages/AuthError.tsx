import { useMemo } from "react";
import { useLocation, Link } from "react-router-dom";
import { AlertTriangle, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

const AuthError = () => {
  const location = useLocation();

  const { provider, message } = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return {
      provider: params.get("provider") ?? "OAuth",
      message: params.get("message") ?? "Authentication failed. Please try again.",
    };
  }, [location.search]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="text-center max-w-md space-y-4">
        <div className="flex justify-center">
          <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
        </div>
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-1">
            {provider === "github" ? "GitHub connection failed" : `${provider} authentication error`}
          </h1>
          <p className="text-sm md:text-base text-muted-foreground break-words">
            {message}
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button
            variant="gradient"
            size="lg"
            asChild
            className="w-full sm:w-auto"
          >
            <Link to="/dashboard">
              <Home className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Link>
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="w-full sm:w-auto"
            onClick={() => window.history.back()}
          >
            Try Again
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AuthError;
