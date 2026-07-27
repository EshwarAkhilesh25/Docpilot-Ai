import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { ROUTES } from "@lib/constants";
import { PublicRoute } from "@components/common/PublicRoute";
import { ProtectedRoute } from "@components/common/ProtectedRoute";
import { lazy, Suspense } from "react";
import { PageLoading } from "@components/common/PageLoading";

// Lazy-loaded page components
const Login = lazy(() => import("./login"));
const Register = lazy(() => import("./register"));
const Dashboard = lazy(() => import("./dashboard"));
const Documents = lazy(() => import("./documents"));
const Upload = lazy(() => import("./upload"));
const Chat = lazy(() => import("./chat"));
const Conversations = lazy(() => import("./conversations"));
const Settings = lazy(() => import("./settings"));
const Home = lazy(() => import("./home"));

// Wrapper components for route protection
const LoginRoute = () => (
  <PublicRoute>
    <Suspense fallback={<PageLoading />}>
      <Login />
    </Suspense>
  </PublicRoute>
);

const RegisterRoute = () => (
  <PublicRoute>
    <Suspense fallback={<PageLoading />}>
      <Register />
    </Suspense>
  </PublicRoute>
);

const DashboardRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Dashboard />
    </Suspense>
  </ProtectedRoute>
);

const DocumentsRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Documents />
    </Suspense>
  </ProtectedRoute>
);

const UploadRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Upload />
    </Suspense>
  </ProtectedRoute>
);

const ChatRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Chat />
    </Suspense>
  </ProtectedRoute>
);

const ConversationsRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Conversations />
    </Suspense>
  </ProtectedRoute>
);

const SettingsRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Settings />
    </Suspense>
  </ProtectedRoute>
);

const HomeRoute = () => (
  <ProtectedRoute>
    <Suspense fallback={<PageLoading />}>
      <Home />
    </Suspense>
  </ProtectedRoute>
);

// Placeholder routes - pages will be implemented later
// All routes use lazy loading for optimal performance
const router = createBrowserRouter([
  {
    path: ROUTES.HOME,
    element: <HomeRoute />,
  },
  {
    path: ROUTES.LOGIN,
    element: <LoginRoute />,
  },
  {
    path: ROUTES.REGISTER,
    element: <RegisterRoute />,
  },
  {
    path: ROUTES.DASHBOARD,
    element: <DashboardRoute />,
  },
  {
    path: ROUTES.DOCUMENTS,
    element: <DocumentsRoute />,
  },
  {
    path: ROUTES.UPLOAD,
    element: <UploadRoute />,
  },
  {
    path: ROUTES.CHAT,
    element: <ChatRoute />,
  },
  {
    path: ROUTES.CONVERSATIONS,
    element: <ConversationsRoute />,
  },
  {
    path: ROUTES.SETTINGS,
    element: <SettingsRoute />,
  },
]);

export const AppRouter = () => {
  return <RouterProvider router={router} />;
};
