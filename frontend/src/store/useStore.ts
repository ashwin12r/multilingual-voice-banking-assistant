import { create } from 'zustand'

interface StoreState {
  token: string | null;
  activeLanguage: string;
  isListening: boolean;
  isSpeaking: boolean;
  dashboardData: any;
  setToken: (token: string) => void;
  setLanguage: (lang: string) => void;
  setListening: (status: boolean) => void;
  setSpeaking: (status: boolean) => void;
  setDashboardData: (data: any) => void;
}

export const useStore = create<StoreState>((set) => ({
  token: null, // Require explicit login now that backend uses JWT
  activeLanguage: 'en',
  isListening: false,
  isSpeaking: false,
  dashboardData: null,
  setToken: (token) => set({ token }),
  setLanguage: (lang) => set({ activeLanguage: lang }),
  setListening: (status) => set({ isListening: status }),
  setSpeaking: (status) => set({ isSpeaking: status }),
  setDashboardData: (data) => set({ dashboardData: data })
}))