import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { useUIStore } from "@store/uiStore";
import { LAYOUT, ROUTES } from "@lib/constants";
import {
  Home,
  FileText,
  UploadCloud,
  MessageSquare,
  Settings,
  Menu,
  X,
} from "lucide-react";
import { PageContainer } from "./PageContainer";
import { ThemeToggle } from "../common/ThemeToggle";
import { cn } from "@lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface DashboardLayoutProps {
  children: ReactNode;
  fullHeight?: boolean;
}

const navItems = [
  { path: ROUTES.HOME, label: "AI Workspace", icon: Home },
  { path: ROUTES.DOCUMENTS, label: "Knowledge Base", icon: FileText },
  { path: ROUTES.UPLOAD, label: "Import Documents", icon: UploadCloud },
  { path: ROUTES.CHAT, label: "AI Copilot", icon: MessageSquare },
  { path: ROUTES.SETTINGS, label: "Workspace Settings", icon: Settings },
];

export const DashboardLayout = ({
  children,
  fullHeight = false,
}: DashboardLayoutProps) => {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const location = useLocation();

  return (
    <div className="h-[100dvh] bg-background flex flex-col w-full overflow-hidden">
      {/* Mobile Header (Top App Bar) */}
      <div className="md:hidden flex items-center justify-between px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))] border-b border-border bg-card sticky top-0 z-[40]">
        <h1 className="text-xl font-bold gradient-text">DocPilot AI</h1>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            onClick={() => setSidebarOpen(true)}
            className="touch-target rounded-md hover:bg-muted text-foreground focus:outline-none"
            aria-label="Open sidebar"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>
      </div>

      <div
        className={cn("flex flex-1 w-full relative min-h-0 overflow-hidden")}
      >
        {/* Backdrop for Mobile Sidebar */}
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[45] md:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}
        </AnimatePresence>

        {/* Sidebar */}
        <motion.aside
          drag="x"
          dragConstraints={{ left: -300, right: 0 }}
          dragElastic={0.1}
          onDragEnd={(_, info) => {
            if (info.offset.x < -100 || info.velocity.x < -500) {
              setSidebarOpen(false);
            }
          }}
          className={cn(
            "fixed inset-y-0 left-0 bg-card border-r border-border transition-transform duration-300 ease-in-out flex flex-col",
            "z-[50] md:z-[30]",
            // Mobile: Slide in/out based on state. Desktop: Always visible and static width.
            sidebarOpen
              ? "translate-x-0"
              : "-translate-x-full md:translate-x-0",
            // Disable drag on desktop by stripping the drag events using CSS touch-action
            "md:touch-auto touch-pan-y",
            "w-[85vw] max-w-[320px] md:w-[280px]", // Strict mobile drawer widths
          )}
          style={{
            width:
              typeof window !== "undefined" && window.innerWidth >= 768
                ? `${LAYOUT.SIDEBAR_WIDTH}px`
                : undefined,
          }}
        >
          <div className="p-6 border-b border-border flex items-center justify-between">
            <h1 className="text-xl font-bold gradient-text">DocPilot AI</h1>
            <div className="flex items-center gap-2">
              <div className="hidden md:block">
                <ThemeToggle />
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="md:hidden touch-target rounded hover:bg-muted text-muted-foreground"
                aria-label="Close sidebar"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          <nav
            className="flex-1 p-4 space-y-2 overflow-y-auto custom-scrollbar"
            aria-label="Main navigation"
          >
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                location.pathname === item.path ||
                (item.path === ROUTES.HOME &&
                  location.pathname === ROUTES.DASHBOARD);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setSidebarOpen(false)} // Close sidebar on mobile when navigating
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                    "hover:bg-muted/50",
                    "focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground",
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  <span className="font-medium truncate">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </motion.aside>

        {/* Main content */}
        <main
          className={cn(
            "flex-1 w-full transition-all duration-300 ease-in-out relative flex flex-col min-w-0 min-h-0 overflow-hidden",
          )}
          style={{
            // On desktop, add left margin. On mobile, 0 margin (since sidebar overlays).
            marginLeft:
              typeof window !== "undefined" && window.innerWidth >= 768
                ? `${LAYOUT.SIDEBAR_WIDTH}px`
                : "0px",
          }}
        >
          {/* We use CSS media queries to handle the margin correctly to avoid hydration issues or window resizing bugs */}
          <style
            dangerouslySetInnerHTML={{
              __html: `
            @media (min-width: 768px) {
              main { margin-left: ${LAYOUT.SIDEBAR_WIDTH}px !important; }
            }
            @media (max-width: 767px) {
              main { margin-left: 0px !important; }
            }
          `,
            }}
          />

          <PageContainer
            maxWidth="full"
            className={cn(
              fullHeight ? "h-full py-4 flex flex-col overflow-hidden" : "py-0",
            )}
            fullHeight={fullHeight}
            withPadding={true}
          >
            {children}
          </PageContainer>
        </main>
      </div>
    </div>
  );
};
