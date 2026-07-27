import { Navigate } from "react-router-dom";
import { ReactNode } from "react";
import { useAuthStore } from "@store/authStore";
import { ROUTES } from "@lib/constants";

interface PublicRouteProps {
  children: ReactNode;
  redirectTo?: string;
}

export const PublicRoute = ({
  children,
  redirectTo = ROUTES.HOME,
}: PublicRouteProps) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
};
