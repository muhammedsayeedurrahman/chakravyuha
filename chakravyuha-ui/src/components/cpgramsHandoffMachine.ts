import type { CPGRAMSHandoffState } from "@/services/api";

export interface CPGRAMSHandoffMachineState {
  phase: CPGRAMSHandoffState;
  serverBlockers: string[];
  localBlockers: string[];
  hasPreparedDraft: boolean;
  confirmationAccepted: boolean;
}

export type CPGRAMSHandoffEvent =
  | {
      type: "PREPARATION_RECEIVED";
      backendState: CPGRAMSHandoffState;
      serverBlockers: string[];
      hasDraft: boolean;
      subject: string;
      draftText: string;
    }
  | { type: "DRAFT_EDITED"; subject: string; draftText: string }
  | { type: "REVIEW_REQUESTED" }
  | { type: "CONFIRMATION_REQUESTED" }
  | { type: "CONFIRMATION_CHANGED"; accepted: boolean }
  | { type: "RETURN_TO_DRAFT" }
  | { type: "HANDOFF_REQUESTED" }
  | { type: "RESET" };

export const INITIAL_CPGRAMS_HANDOFF_STATE: CPGRAMSHandoffMachineState = {
  phase: "DRAFT",
  serverBlockers: [],
  localBlockers: [],
  hasPreparedDraft: false,
  confirmationAccepted: false,
};

function uniqueBlockers(items: string[]): string[] {
  return Array.from(new Set(items.map((item) => item.trim()).filter(Boolean)));
}

function draftBlockers(hasDraft: boolean, subject: string, draftText: string): string[] {
  return uniqueBlockers([
    ...(!hasDraft ? ["A prepared grievance draft is required."] : []),
    ...(!subject.trim() ? ["A grievance subject is required."] : []),
    ...(!draftText.trim() ? ["Grievance text is required."] : []),
  ]);
}

function preparationBlockers(state: CPGRAMSHandoffMachineState): string[] {
  return uniqueBlockers([...state.serverBlockers, ...state.localBlockers]);
}

export function cpgramsReviewBlockers(state: CPGRAMSHandoffMachineState): string[] {
  const blockers = preparationBlockers(state);
  if (state.phase !== "PREPARED" && blockers.length === 0) {
    blockers.push(`The grievance must be in PREPARED state before review (currently ${state.phase}).`);
  }
  return uniqueBlockers(blockers);
}

export function cpgramsConfirmationBlockers(state: CPGRAMSHandoffMachineState): string[] {
  const blockers = preparationBlockers(state);
  if (state.phase !== "REVIEWED") {
    blockers.push('Complete "Review safe hand-off" before requesting confirmation.');
  }
  return uniqueBlockers(blockers);
}

export function cpgramsHandoffBlockers(
  state: CPGRAMSHandoffMachineState,
  hasHandoffHandler: boolean,
): string[] {
  if (state.phase === "HANDOFF") return [];

  const blockers = preparationBlockers(state);
  if (state.phase !== "CONFIRMATION_REQUIRED") {
    blockers.push("Continue the reviewed draft to the mandatory confirmation stage.");
  }
  if (!state.confirmationAccepted) {
    blockers.push("Select the mandatory confirmation checkbox.");
  }
  if (!hasHandoffHandler) {
    blockers.push("The assisted CPGRAMS filing screen is unavailable.");
  }
  return uniqueBlockers(blockers);
}

export function cpgramsHandoffReducer(
  state: CPGRAMSHandoffMachineState,
  event: CPGRAMSHandoffEvent,
): CPGRAMSHandoffMachineState {
  switch (event.type) {
    case "PREPARATION_RECEIVED": {
      const serverBlockers = uniqueBlockers(event.serverBlockers);
      const localBlockers = draftBlockers(event.hasDraft, event.subject, event.draftText);
      const phase = event.backendState === "PREPARED" && serverBlockers.length === 0 && localBlockers.length === 0
        ? "PREPARED"
        : "DRAFT";
      return {
        phase,
        serverBlockers,
        localBlockers,
        hasPreparedDraft: event.hasDraft,
        confirmationAccepted: false,
      };
    }
    case "DRAFT_EDITED": {
      const localBlockers = draftBlockers(state.hasPreparedDraft, event.subject, event.draftText);
      return {
        ...state,
        phase: state.serverBlockers.length === 0 && localBlockers.length === 0 ? "PREPARED" : "DRAFT",
        localBlockers,
        confirmationAccepted: false,
      };
    }
    case "REVIEW_REQUESTED":
      if (state.phase !== "PREPARED" || cpgramsReviewBlockers(state).length > 0) return state;
      return { ...state, phase: "REVIEWED", confirmationAccepted: false };
    case "CONFIRMATION_REQUESTED":
      if (state.phase !== "REVIEWED" || cpgramsConfirmationBlockers(state).length > 0) return state;
      return { ...state, phase: "CONFIRMATION_REQUIRED", confirmationAccepted: false };
    case "CONFIRMATION_CHANGED":
      if (state.phase !== "CONFIRMATION_REQUIRED") return state;
      return { ...state, confirmationAccepted: event.accepted };
    case "RETURN_TO_DRAFT": {
      const phase = preparationBlockers(state).length === 0 ? "PREPARED" : "DRAFT";
      return { ...state, phase, confirmationAccepted: false };
    }
    case "HANDOFF_REQUESTED":
      if (
        state.phase !== "CONFIRMATION_REQUIRED" ||
        !state.confirmationAccepted ||
        preparationBlockers(state).length > 0
      ) {
        return state;
      }
      return { ...state, phase: "HANDOFF" };
    case "RESET":
      return INITIAL_CPGRAMS_HANDOFF_STATE;
    default:
      return state;
  }
}
