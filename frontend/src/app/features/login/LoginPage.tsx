import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Footer } from "./Footer";
import logo from "figma:asset/12b39b0f5302eae32092715fdb2e4a6a0eab7bd3.png";

interface LoginPageProps {
  onLogin: () => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin();
  };

  return (
    <div className="min-h-screen flex flex-col" data-layer="login-page-container">
      <div className="flex-1 bg-[var(--color-brand-teal-primary)] flex items-center justify-center p-4" data-layer="login-background">
        <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md" data-layer="login-card">
          <div className="text-center mb-8" data-layer="login-header">
            <img src={logo} alt="RehearseSR" className="h-20 mx-auto mb-2" data-layer="brand-logo" />
            <p className="text-gray-600" data-layer="tagline-text">Rehearse Today. Inspire Tomorrow.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-layer="login-form">
            <div className="space-y-2" data-layer="email-field-group">
              <Label htmlFor="email">Email</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="teacher@example.com"
                required
              />
            </div>

            <div className="space-y-2" data-layer="password-field-group">
              <Label htmlFor="password">Password</Label>
              <Input 
                id="password" 
                type="password" 
                placeholder="••••••••"
                required
              />
            </div>

            <Button 
              type="submit" 
              className="w-full bg-[var(--color-brand-teal-primary)] hover:bg-[var(--color-brand-teal-primary-hover)]"
              data-layer="primary-submit-button"
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 text-center" data-layer="forgot-password-link-container">
            <a href="#" className="text-sm text-[var(--color-brand-teal-primary)] hover:underline" data-layer="forgot-password-link">
              Forgot your password?
            </a>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}