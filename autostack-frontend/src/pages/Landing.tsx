import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { 
  Rocket, 
  Github, 
  Zap, 
  Shield, 
  Globe, 
  Terminal,
  CheckCircle2,
  ArrowRight
} from "lucide-react";
import { motion } from "framer-motion";

const features = [
  {
    icon: Github,
    title: "GitHub Integration",
    description: "Connect your repositories and deploy with a single click. Automatic deployments on every push."
  },
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "Optimized build pipeline and edge network deployment. Your sites go live in seconds."
  },
  {
    icon: Shield,
    title: "Secure by Default",
    description: "SSL certificates, DDoS protection, and automatic security updates included."
  },
  {
    icon: Globe,
    title: "Global CDN",
    description: "Deliver your applications from the edge, closest to your users worldwide."
  }
];

const steps = [
  {
    number: "01",
    title: "Connect GitHub",
    description: "Link your GitHub account and select your repository"
  },
  {
    number: "02",
    title: "Configure Build",
    description: "Set environment variables and build commands"
  },
  {
    number: "03",
    title: "Deploy",
    description: "Push to deploy automatically with every commit"
  }
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-3 group">
            <motion.div 
              whileHover={{ scale: 1.05, rotate: 5 }}
              transition={{ type: "spring", stiffness: 400 }}
              className="gradient-hero p-2 rounded-lg"
            >
              <Rocket className="h-6 w-6 text-white" />
            </motion.div>
            <span className="text-xl font-bold text-foreground group-hover:text-primary transition-colors">
              AutoStack
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link to="/login">Log in</Link>
            </Button>
            <Button variant="gradient" asChild>
              <Link to="/signup">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container px-4 py-20 md:py-32">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-4xl text-center"
        >
          <motion.div 
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2 }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-accent/30 px-4 py-1.5"
          >
            <Zap className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">Deploy in seconds, not hours</span>
          </motion.div>
          <h1 className="mb-6 text-5xl md:text-7xl font-bold tracking-tight">
            Ship faster with{" "}
            <span className="autostack-gradient-text md:text-[4.5rem] font-extrabold align-middle">
              AutoStack
            </span>
          </h1>
          <p className="mb-10 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
            The modern deployment platform for indie developers and startups. 
            Connect GitHub, configure once, and deploy automatically.
          </p>
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row gap-4 justify-center"
          >
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button variant="gradient" size="lg" className="text-base" asChild>
                <Link to="/signup">
                  Get Started Free
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button variant="outline" size="lg" className="text-base" asChild>
                <Link to="/login">
                  <Github className="mr-2 h-4 w-4" />
                  Continue with GitHub
                </Link>
              </Button>
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      {/* Features Bento Grid */}
      <section className="container px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            Everything you need to deploy
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Production-ready infrastructure without the DevOps complexity
          </p>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="p-6 h-full hover:shadow-lg transition-all duration-300 hover:scale-105 bg-card/50 backdrop-blur group cursor-pointer">
                <motion.div 
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.6 }}
                  className="gradient-primary p-3 rounded-lg w-fit mb-4"
                >
                  <feature.icon className="h-6 w-6 text-white" />
                </motion.div>
                <h3 className="text-xl font-semibold mb-2 group-hover:text-primary transition-colors">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section className="container px-4 py-20 bg-accent/20">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4">
            How it works
          </h2>
          <p className="text-lg text-muted-foreground">
            Get your app deployed in three simple steps
          </p>
        </div>
        <div className="max-w-4xl mx-auto">
          <div className="space-y-8">
            {steps.map((step, index) => (
              <motion.div 
                key={index}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.2 }}
                className="flex gap-6 items-start"
              >
                <motion.div 
                  whileHover={{ scale: 1.1 }}
                  className="gradient-hero text-white rounded-full h-12 w-12 flex items-center justify-center font-bold text-lg shrink-0"
                >
                  {step.number}
                </motion.div>
                <div className="flex-1">
                  <h3 className="text-2xl font-bold mb-2">{step.title}</h3>
                  <p className="text-muted-foreground">{step.description}</p>
                </div>
                {index < steps.length - 1 && (
                  <div className="hidden md:block h-24 w-px bg-border ml-6" />
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container px-4 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <Card className="gradient-hero p-12 text-center text-white overflow-hidden relative">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl"
            />
            <Terminal className="h-16 w-16 mx-auto mb-6 opacity-80" />
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Ready to deploy your first app?
            </h2>
            <p className="text-lg text-white/80 mb-8 max-w-2xl mx-auto">
              Join thousands of developers shipping faster with Autostack
            </p>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button variant="secondary" size="lg" asChild className="font-semibold">
                <Link to="/signup">
                  Get Started Free
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </motion.div>
          </Card>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="container px-4 py-12">
          <div className="grid gap-8 md:grid-cols-4">
            <div>
              <Link to="/" className="flex items-center gap-3 mb-4 group w-fit">
                <motion.div 
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  className="gradient-hero p-2 rounded-lg"
                >
                  <Rocket className="h-5 w-5 text-white" />
                </motion.div>
                <span className="font-bold group-hover:text-primary transition-colors">Autostack</span>
              </Link>
              <p className="text-sm text-muted-foreground">
                Deploy faster, ship better.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <div className="space-y-2 text-sm">
                <Button variant="link" className="h-auto p-0 text-muted-foreground" disabled>
                  Docs <span className="ml-2 text-xs">(Coming Soon)</span>
                </Button>
                <Button variant="link" className="h-auto p-0 text-muted-foreground" disabled>
                  Pricing <span className="ml-2 text-xs">(Coming Soon)</span>
                </Button>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <div className="space-y-2 text-sm">
                <Button variant="link" className="h-auto p-0 text-muted-foreground" disabled>
                  About <span className="ml-2 text-xs">(Coming Soon)</span>
                </Button>
                <Button variant="link" className="h-auto p-0 text-muted-foreground" disabled>
                  Blog <span className="ml-2 text-xs">(Coming Soon)</span>
                </Button>
              </div>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Connect</h4>
              <div className="space-y-2 text-sm">
                <Button variant="link" className="h-auto p-0 text-muted-foreground" disabled>
                  GitHub <span className="ml-2 text-xs">(Coming Soon)</span>
                </Button>
                <Button variant="link" className="h-auto p-0 text-muted-foreground" disabled>
                  Twitter <span className="ml-2 text-xs">(Coming Soon)</span>
                </Button>
              </div>
            </div>
          </div>
          <div className="border-t border-border mt-8 pt-8 text-center text-sm text-muted-foreground">
            <p>© 2025 Autostack. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
