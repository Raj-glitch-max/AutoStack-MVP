import { Layout } from "@/components/Layout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Construction } from "lucide-react";
import { Link } from "react-router-dom";

interface ComingSoonProps {
  title: string;
  description: string;
  emoji?: string;
}

export default function ComingSoon({ title, description, emoji = "🚧" }: ComingSoonProps) {
  return (
    <Layout>
      <div className="container px-4 py-8 max-w-2xl mx-auto">
        <div className="min-h-[60vh] flex items-center justify-center">
          <Card className="p-12 text-center">
            <div className="mb-6">
              <div className="text-6xl mb-4">{emoji}</div>
              <div className="w-16 h-16 mx-auto gradient-primary rounded-full flex items-center justify-center mb-4">
                <Construction className="h-8 w-8 text-white" />
              </div>
            </div>
            <h1 className="text-4xl font-bold mb-4">{title}</h1>
            <p className="text-lg text-muted-foreground mb-8 max-w-md mx-auto">
              {description}
            </p>
            <Badge variant="outline" className="mb-8">
              Coming Soon
            </Badge>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button variant="gradient" asChild>
                <Link to="/dashboard">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Dashboard
                </Link>
              </Button>
              <Button variant="outline" disabled>
                Notify Me
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

// Individual Coming Soon pages
export function PricingComingSoon() {
  return (
    <ComingSoon
      title="Pricing Plans"
      description="We're working on transparent, developer-friendly pricing tiers. From free hobby projects to enterprise solutions."
      emoji="💰"
    />
  );
}

export function DocsComingSoon() {
  return (
    <ComingSoon
      title="Documentation"
      description="Comprehensive guides, API references, and tutorials are on their way. Learn how to make the most of Autostack."
      emoji="📚"
    />
  );
}

export function AnalyticsComingSoon() {
  return (
    <ComingSoon
      title="Analytics Dashboard"
      description="Track deployment metrics, performance insights, and usage analytics. Make data-driven decisions."
      emoji="📊"
    />
  );
}

export function TemplatesComingSoon() {
  return (
    <ComingSoon
      title="Deployment Templates"
      description="Pre-configured templates for popular frameworks and stacks. Deploy React, Vue, Next.js, and more with zero config."
      emoji="📦"
    />
  );
}

export function PipelinesComingSoon() {
  return (
    <ComingSoon
      title="CI/CD Pipelines"
      description="Advanced pipeline configurations with multi-stage deployments, testing, and approval workflows."
      emoji="🔄"
    />
  );
}

export function MonitoringComingSoon() {
  return (
    <ComingSoon
      title="Advanced Monitoring"
      description="Real-time application monitoring, error tracking, and performance metrics. Keep your apps healthy."
      emoji="🔍"
    />
  );
}

export function TeamComingSoon() {
  return (
    <ComingSoon
      title="Team Collaboration"
      description="Invite team members, manage permissions, and collaborate on deployments. Better together."
      emoji="👥"
    />
  );
}

export function IntegrationsComingSoon() {
  return (
    <ComingSoon
      title="Integrations"
      description="Connect with Slack, Discord, GitHub Actions, and more. Integrate Autostack into your workflow."
      emoji="🔌"
    />
  );
}
