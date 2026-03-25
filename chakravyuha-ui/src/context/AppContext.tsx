"use client";

import React, {
  createContext,
  useContext,
  useReducer,
  useMemo,
  useCallback,
  useEffect,
  useRef,
} from "react";
import type { LegalSection, GuidedFlowStep } from "@/services/api";
import { checkHealth } from "@/services/api";

// ── Types ────────────────────────────────────────────────────────────────────

type Language = { code: string; label: string };

export interface GuidedFlowLocal {
  step: GuidedFlowStep | null;
  path: string[];
}

export interface AppState {
  currentStep: number;
  isRecording: boolean;
  language: Language;
  chatHistory: { role: "user" | "assistant"; text: string }[];
  caseList: { id: string; issue: string; status: string }[];
  loading: boolean;
  backendOnline: boolean;
  sections: LegalSection[];
  guidedFlow: GuidedFlowLocal;
}

type Action =
  | { type: "SET_STEP"; payload: number }
  | { type: "TOGGLE_RECORDING" }
  | { type: "SET_LANGUAGE"; payload: Language }
  | { type: "ADD_MESSAGE"; payload: { role: "user" | "assistant"; text: string } }
  | { type: "ADD_CASE"; payload: { issue: string } }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_BACKEND_STATUS"; payload: boolean }
  | { type: "SET_SECTIONS"; payload: LegalSection[] }
  | { type: "SET_GUIDED_STEP"; payload: GuidedFlowStep | null }
  | { type: "SET_GUIDED_PATH"; payload: string[] }
  | { type: "CLEAR_CHAT" }
  | { type: "RESET" };

// ── Context + Reducer ─────────────────────────────────────────────────────────

const SUPPORTED_LANGUAGES: Language[] = [
  { code: "en-IN", label: "English" },
  { code: "ta-IN", label: "தமிழ்" },
  { code: "hi-IN", label: "हिन्दी" },
  { code: "te-IN", label: "తెలుగు" },
  { code: "kn-IN", label: "ಕನ್ನಡ" },
  { code: "ml-IN", label: "മലയാളം" },
  { code: "mr-IN", label: "मराठी" },
  { code: "bn-IN", label: "বাংলা" },
];

const initialState: AppState = {
  currentStep: 1,
  isRecording: false,
  language: { code: "en-IN", label: "English" },
  chatHistory: [],
  caseList: [],
  loading: false,
  backendOnline: false,
  sections: [],
  guidedFlow: { step: null, path: [] },
};

function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, currentStep: action.payload };
    case "TOGGLE_RECORDING":
      return { ...state, isRecording: !state.isRecording };
    case "SET_LANGUAGE":
      return { ...state, language: action.payload };
    case "ADD_MESSAGE":
      return {
        ...state,
        chatHistory: [...state.chatHistory, action.payload],
      };
    case "ADD_CASE": {
      const newCase = {
        id: `CASE-${Date.now()}`,
        issue: action.payload.issue,
        status: "Open",
      };
      return { ...state, caseList: [...state.caseList, newCase] };
    }
    case "SET_LOADING":
      return { ...state, loading: action.payload };
    case "SET_BACKEND_STATUS":
      return { ...state, backendOnline: action.payload };
    case "SET_SECTIONS":
      return { ...state, sections: action.payload };
    case "SET_GUIDED_STEP":
      return {
        ...state,
        guidedFlow: { ...state.guidedFlow, step: action.payload },
      };
    case "SET_GUIDED_PATH":
      return {
        ...state,
        guidedFlow: { ...state.guidedFlow, path: action.payload },
      };
    case "CLEAR_CHAT":
      return { ...state, chatHistory: [], sections: [] };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

// ── Context ───────────────────────────────────────────────────────────────────

interface AppContextValue {
  state: AppState;
  supportedLanguages: Language[];
  setStep: (step: number) => void;
  toggleRecording: () => void;
  setLanguage: (lang: Language) => void;
  addMessage: (role: "user" | "assistant", text: string) => void;
  addCase: (issue: string) => void;
  setLoading: (loading: boolean) => void;
  setSections: (sections: LegalSection[]) => void;
  setGuidedStep: (step: GuidedFlowStep | null) => void;
  setGuidedPath: (path: string[]) => void;
  clearChat: () => void;
  reset: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Health check polling — check on mount, then every 30s
  useEffect(() => {
    const poll = async () => {
      const online = await checkHealth();
      dispatch({ type: "SET_BACKEND_STATUS", payload: online });
    };

    poll();
    intervalRef.current = setInterval(poll, 30_000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // Memoized stable callbacks
  const setStep = useCallback(
    (step: number) => dispatch({ type: "SET_STEP", payload: step }),
    []
  );
  const toggleRecording = useCallback(
    () => dispatch({ type: "TOGGLE_RECORDING" }),
    []
  );
  const setLanguage = useCallback(
    (lang: Language) => dispatch({ type: "SET_LANGUAGE", payload: lang }),
    []
  );
  const addMessage = useCallback(
    (role: "user" | "assistant", text: string) =>
      dispatch({ type: "ADD_MESSAGE", payload: { role, text } }),
    []
  );
  const addCase = useCallback(
    (issue: string) => dispatch({ type: "ADD_CASE", payload: { issue } }),
    []
  );
  const setLoading = useCallback(
    (loading: boolean) => dispatch({ type: "SET_LOADING", payload: loading }),
    []
  );
  const setSections = useCallback(
    (sections: LegalSection[]) =>
      dispatch({ type: "SET_SECTIONS", payload: sections }),
    []
  );
  const setGuidedStep = useCallback(
    (step: GuidedFlowStep | null) =>
      dispatch({ type: "SET_GUIDED_STEP", payload: step }),
    []
  );
  const setGuidedPath = useCallback(
    (path: string[]) => dispatch({ type: "SET_GUIDED_PATH", payload: path }),
    []
  );
  const clearChat = useCallback(() => dispatch({ type: "CLEAR_CHAT" }), []);
  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  const value = useMemo(
    () => ({
      state,
      supportedLanguages: SUPPORTED_LANGUAGES,
      setStep,
      toggleRecording,
      setLanguage,
      addMessage,
      addCase,
      setLoading,
      setSections,
      setGuidedStep,
      setGuidedPath,
      clearChat,
      reset,
    }),
    [
      state,
      setStep,
      toggleRecording,
      setLanguage,
      addMessage,
      addCase,
      setLoading,
      setSections,
      setGuidedStep,
      setGuidedPath,
      clearChat,
      reset,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside <AppProvider>");
  return ctx;
}
