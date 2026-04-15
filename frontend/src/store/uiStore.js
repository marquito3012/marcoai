/**
 * MarcoAI – UI state Zustand store
 *
 * Tracks layout/interaction state that multiple components need to share:
 *   - Sidebar expand/collapse for mobile
 *   - Currently visible module (for future dashboard multi-panel layout)
 */
import { create } from 'zustand'

const useUiStore = create((set) => ({
  /** Mobile sidebar state */
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  closeSidebar:  () => set({ sidebarOpen: false }),

  /** Active module key – used by future multi-panel dashboard layout */
  activeModule: 'chat',
  setActiveModule: (module) => set({ activeModule: module }),
}))

export default useUiStore
