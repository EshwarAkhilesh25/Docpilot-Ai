import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cardVariants } from "@lib/animations";
import { getGreeting } from "@lib/helpers/greeting";
import { Upload, MessageSquare, CloudLightning } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { ROUTES } from "@lib/constants";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import chatbotLottie from "@/chatbot.lottie?url";
import { apiClient } from "@lib/api";
import { useUIStore } from "@store/uiStore";

interface DashboardHeroProps {
  userName: string;
}

export function DashboardHero({ userName }: DashboardHeroProps) {
  const navigate = useNavigate();
  const {
    isBackendWarming,
    hasBackendResponded,
    setIsBackendWarming,
    setHasBackendResponded,
  } = useUIStore();

  useEffect(() => {
    if (hasBackendResponded) return;

    // Trigger a fast health check on mount to test backend responsiveness
    const timer = setTimeout(() => {
      if (!hasBackendResponded) {
        setIsBackendWarming(true);
      }
    }, 1500);

    apiClient
      .get("/health")
      .then(() => {
        clearTimeout(timer);
        setHasBackendResponded(true);
        setIsBackendWarming(false);
      })
      .catch(() => {
        // Even if health fails initially (cold start), keep check timer clean
        clearTimeout(timer);
      });

    return () => clearTimeout(timer);
  }, [hasBackendResponded, setIsBackendWarming, setHasBackendResponded]);

  const showStartupNotice = isBackendWarming && !hasBackendResponded;

  return (
    <motion.div
      variants={cardVariants}
      initial="initial"
      animate="animate"
      className="relative w-full"
    >
      <div className="rounded-2xl bg-card border border-border p-4 sm:p-6 md:p-8 lg:p-10 shadow-sm transition-all hover:shadow-md relative overflow-hidden group">
        {/* Animated Aurora Background */}
        <div className="absolute inset-0 opacity-20 pointer-events-none mix-blend-normal transition-opacity duration-700 group-hover:opacity-30 dark:mix-blend-screen">
          <div className="absolute -top-[50%] -left-[50%] w-[200%] h-[200%] animate-[spin_15s_linear_infinite] bg-[conic-gradient(from_0deg_at_50%_50%,rgba(59,130,246,0.3)_0%,rgba(139,92,246,0.3)_25%,rgba(236,72,153,0.3)_50%,rgba(139,92,246,0.3)_75%,rgba(59,130,246,0.3)_100%)] blur-[80px]" />
        </div>

        {/* Subtle pulsating orbs */}
        <div
          className="absolute top-0 right-0 -mt-20 -mr-20 w-96 h-96 bg-primary/20 rounded-full blur-[80px] animate-pulse pointer-events-none"
          style={{ animationDuration: "4s" }}
        />
        <div
          className="absolute bottom-0 left-10 -mb-20 w-80 h-80 bg-purple-500/15 rounded-full blur-[80px] animate-pulse pointer-events-none"
          style={{ animationDuration: "6s", animationDelay: "2s" }}
        />

        {/* Absolutely positioned giant chatbot animation (Desktop only) */}
        <div className="absolute right-0 bottom-0 h-full w-[400px] md:w-[500px] lg:w-[600px] pointer-events-none hidden sm:flex items-end justify-end z-0 opacity-90 transition-transform hover:scale-105 duration-700 origin-bottom-right">
          <DotLottieReact
            src={chatbotLottie}
            loop
            autoplay
            className="w-full h-full object-cover object-bottom"
          />
        </div>

        <div className="relative z-10 max-w-2xl">
          <div className="flex flex-row items-center sm:items-start gap-2 mb-4">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground tracking-tight">
              {getGreeting()},{" "}
              <span className="text-primary block sm:inline mt-1 sm:mt-0">
                {userName}
              </span>
            </h1>
            {/* Inline small chatbot animation (Mobile only) */}
            <div className="w-[180px] h-[180px] shrink-0 sm:hidden -ml-4 -my-4">
              <DotLottieReact
                src={chatbotLottie}
                loop
                autoplay
                className="w-full h-full object-contain"
              />
            </div>
          </div>

          <p className="text-base sm:text-lg text-muted-foreground mb-6 leading-relaxed max-w-xl">
            Your intelligent document workspace is ready. Upload documents or
            start chatting to discover insights instantly.
          </p>

          <AnimatePresence>
            {showStartupNotice && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-6 overflow-hidden"
              >
                <div className="p-3.5 sm:p-4 rounded-xl bg-primary/10 border border-primary/20 backdrop-blur-sm flex items-start gap-3 text-xs sm:text-sm text-foreground max-w-xl">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5">
                    <CloudLightning className="w-4 h-4 sm:w-5 sm:h-5 animate-pulse" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-primary flex items-center gap-1.5 text-xs sm:text-sm">
                      🚀 AI services are starting...
                    </p>
                    <p className="text-muted-foreground text-xs mt-0.5 leading-relaxed">
                      The backend may take up to a minute to wake up on your
                      first request. Feel free to import documents while it's
                      starting.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <button
              onClick={() => navigate(ROUTES.UPLOAD)}
              className="touch-target px-6 py-3 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl font-medium transition-colors shadow-sm active:scale-95"
            >
              <Upload className="w-5 h-5" />
              Import Documents
            </button>

            <button
              onClick={() => navigate(ROUTES.CHAT)}
              className="touch-target px-6 py-3 bg-secondary hover:bg-secondary/80 text-secondary-foreground border border-border rounded-xl font-medium transition-colors active:scale-95 shadow-sm"
            >
              <MessageSquare className="w-5 h-5" />
              AI Copilot
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
