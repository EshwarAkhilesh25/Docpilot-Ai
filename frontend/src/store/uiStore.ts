import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  loading: boolean;
  setLoading: (loading: boolean) => void;
  isBackendWarming: boolean;
  setIsBackendWarming: (warming: boolean) => void;
  hasBackendResponded: boolean;
  setHasBackendResponded: (responded: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  loading: false,
  setLoading: (loading) => set({ loading }),
  isBackendWarming: false,
  setIsBackendWarming: (warming) => set({ isBackendWarming: warming }),
  hasBackendResponded: false,
  setHasBackendResponded: (responded) =>
    set({ hasBackendResponded: responded }),
}));
