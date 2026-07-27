import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { useAuthStore } from "@store/authStore";
import { authService } from "@services/authService";
import { loginSchema, LoginInput } from "@lib/validations/auth";
import { ROUTES } from "@lib/constants";
import { pageTransition, cardVariants } from "@lib/animations";
import { AuthLayout } from "@components/layout/AuthLayout";
import { AuthCard } from "@components/auth/AuthCard";
import { AuthHeader } from "@components/auth/AuthHeader";
import { AuthFooter } from "@components/auth/AuthFooter";
import { PasswordInput } from "@components/auth/PasswordInput";
import { FormField } from "@components/auth/FormField";
import { Button } from "@components/common/Button";
import { PremiumBackground } from "@components/common/PremiumBackground";

export default function Login() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginInput) => {
    setIsLoading(true);
    setGlobalError(null);

    try {
      const tokenResponse = await authService.login(data);

      // Store token immediately after successful login
      useAuthStore.getState().login(null, tokenResponse.access_token);

      // Now fetch current user with token in Authorization header
      const user = await authService.getCurrentUser();

      // Update user in store
      useAuthStore.getState().setUser(user);

      // Ensure mobile sidebar is closed after login
      const { useUIStore } = await import("@store/uiStore");
      useUIStore.getState().setSidebarOpen(false);

      toast.success("Welcome back!");
      navigate(ROUTES.HOME);
    } catch (err: unknown) {
      const error = err as Error & {
        response?: { data?: { detail?: string }; status?: number };
        config?: unknown;
      };
      void 0;
      void 0;
      void 0;
      void 0;
      void 0;
      void 0;
      void 0;

      if (error.response?.status === 401) {
        setGlobalError("Invalid email or password");
      } else if (error.response?.status === 403) {
        setGlobalError("Your account is inactive");
      } else if (error.response?.status === 422) {
        setGlobalError("Invalid credentials");
      } else if (error.response?.status === 500) {
        setGlobalError("Server error. Please try again later.");
      } else {
        setGlobalError("An error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout>
      <PremiumBackground variant="gradient" />
      <motion.div
        variants={pageTransition}
        initial="initial"
        animate="animate"
        exit="exit"
        className="w-full"
      >
        <AuthCard className="p-8">
          <motion.div
            variants={cardVariants}
            initial="initial"
            animate="animate"
          >
            <AuthHeader
              title="Welcome Back"
              description="Sign in to your account to continue"
            />

            {globalError && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg"
                role="alert"
              >
                <p className="text-sm text-destructive">{globalError}</p>
              </motion.div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              <FormField label="Email" error={errors.email?.message} required>
                <input
                  type="email"
                  autoComplete="email"
                  autoFocus
                  disabled={isLoading}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  {...register("email")}
                />
              </FormField>

              <FormField
                label="Password"
                error={errors.password?.message}
                required
              >
                <PasswordInput
                  autoComplete="current-password"
                  disabled={isLoading}
                  {...register("password")}
                />
              </FormField>

              <Button
                type="submit"
                className="w-full"
                loading={isLoading}
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>
            </form>

            <AuthFooter>
              <span className="text-muted-foreground">
                Don't have an account?{" "}
              </span>
              <a
                href={ROUTES.REGISTER}
                className="text-primary hover:underline font-medium"
              >
                Sign up
              </a>
            </AuthFooter>
          </motion.div>
        </AuthCard>
      </motion.div>
    </AuthLayout>
  );
}
