import { Navigate } from "react-router-dom";
import { useAuthStore } from "@store/authStore";
import Dashboard from "./dashboard";

export default function Home() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (isAuthenticated) {
    return <Dashboard />;
  }

  return <Navigate to="/login" replace />;
}
