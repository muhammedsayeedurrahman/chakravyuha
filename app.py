"""Chakravyuha — AI Legal Assistant for India (Gradio App)."""

import gradio as gr
from backend.config import DISCLAIMER, GRADIO_PORT, GRADIO_TITLE, SUPPORTED_LANGUAGES
from backend.agent.orchestrator import Orchestrator
from backend.agent.form_filler import get_supported_portals
from backend.agent.escalation import get_escalation_info

orchestrator = Orchestrator()

# ── Session state ──────────────────────────────────────────────────────────

def new_session() -> dict:
    return {
        "language": "en-IN",
        "conversation": [],
        "guided_state": None,
        "user_id": "demo_user",
    }


# ── Tab 1: Voice Assistant ─────────────────────────────────────────────────

def voice_chat(audio, history, session_state):
    """Handle voice input from microphone — auto-processes on recording stop."""
    if session_state is None:
        session_state = new_session()

    history = history or []

    if audio is None:
        return history, session_state, None

    # Convert Gradio numpy audio to WAV bytes
    import numpy as np
    import io
    import wave

    sample_rate, audio_data = audio
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        audio_np = np.array(audio_data, dtype=np.int16)
        wf.writeframes(audio_np.tobytes())
    audio_bytes = buf.getvalue()

    result = orchestrator.process_voice_input(audio_bytes, session_state)

    asr_result = result.get("asr_result", {})
    asr_text = asr_result.get("text", "")
    asr_error = asr_result.get("error", "")

    if asr_error:
        history.append({"role": "assistant", "content": f"I couldn't understand the audio: {asr_error}"})
        return history, session_state, None

    if asr_text:
        history.append({"role": "user", "content": asr_text})

    response_text = result.get("text_response", "")
    if response_text:
        history.append({"role": "assistant", "content": response_text})

    return history, result.get("session_state", session_state), result.get("audio_response")


def text_chat(message, history, session_state):
    """Handle text input."""
    if session_state is None:
        session_state = new_session()

    if not message or not message.strip():
        return "", history or [], session_state

    result = orchestrator.process_text_input(message, session_state)
    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": result["text_response"]})

    return "", history, result["session_state"]


def set_language(lang_code, session_state):
    """Update session language."""
    if session_state is None:
        session_state = new_session()
    return {**session_state, "language": lang_code}


# ── Tab 2: Guided Legal Help ───────────────────────────────────────────────

def start_guided_flow():
    """Initialize the guided flow and return first question."""
    result = orchestrator.get_initial_question()
    question = result.get("question", "")
    options = result.get("options", [])
    state = result.get("guided_state", {"current_node": "start", "history": []})

    buttons_text = f"**{question}**\n\n"
    for i, opt in enumerate(options):
        buttons_text += f"{i + 1}. {opt['label']}\n"

    choices = [opt["label"] for opt in options]
    return buttons_text, gr.update(choices=choices, visible=True), state, ""


def guided_select(choice, options_state, guided_state, session_state):
    """Process guided flow selection."""
    if session_state is None:
        session_state = new_session()
    if guided_state is None:
        return "Please click 'Start' first.", gr.update(), guided_state, session_state, ""

    # Find index of selected choice
    choices = options_state if isinstance(options_state, list) else []
    try:
        answer_index = choices.index(choice) if choice in choices else 0
    except (ValueError, IndexError):
        answer_index = 0

    session_state_with_guided = {**session_state, "guided_state": guided_state}
    result = orchestrator.process_guided_answer(answer_index, session_state_with_guided)

    if "error" in result:
        return f"Error: {result['error']}", gr.update(), guided_state, session_state, ""

    new_guided_state = result.get("session_state", {}).get("guided_state", guided_state)

    if result.get("terminal"):
        # Build final result display
        output = f"## {result.get('summary', 'Result')}\n\n"

        sections = result.get("sections", [])
        if sections:
            output += "### Applicable Legal Sections\n\n"
            for s in sections:
                bail = "Bailable" if s.get("bailable") else "Non-bailable"
                cog = "Cognizable" if s.get("cognizable") else "Non-cognizable"
                output += f"**{s['section_id']} — {s['title']}**\n"
                output += f"- {s['description'][:200]}...\n"
                output += f"- Punishment: {s['punishment']}\n"
                output += f"- Status: {cog}, {bail}\n\n"

        ipc_sections = result.get("ipc_sections", [])
        if ipc_sections:
            output += f"**Old IPC Equivalent:** {', '.join(ipc_sections)}\n\n"

        next_steps = result.get("next_steps", [])
        if next_steps:
            output += "### What You Should Do\n\n"
            for step in next_steps:
                output += f"- {step}\n"
            output += "\n"

        if result.get("escalation"):
            esc = get_escalation_info()
            output += "### EMERGENCY CONTACTS\n\n"
            for contact in esc["contacts"]:
                output += f"- **{contact['name']}**: {contact['number']} — {contact['description']}\n"
            output += "\n"

        defence = result.get("defence")
        if defence:
            output += "### Possible Defences\n\n"
            for d in defence.get("defences", []):
                output += f"- **{d['name']}**: {d['description']}\n"
            output += "\n"

        output += f"\n---\n{DISCLAIMER}"

        return output, gr.update(visible=False), new_guided_state, session_state, ""

    if result.get("type") == "free_text":
        return (
            result.get("prompt", "Please describe your issue."),
            gr.update(visible=False),
            new_guided_state,
            session_state,
            "",
        )

    # Next question
    question = result.get("question", "")
    options = result.get("options", [])
    buttons_text = f"**{question}**\n\n"
    for i, opt in enumerate(options):
        buttons_text += f"{i + 1}. {opt['label']}\n"

    choices = [opt["label"] for opt in options]
    return buttons_text, gr.update(choices=choices, visible=True), new_guided_state, session_state, ""


def guided_free_text(text, guided_state, session_state):
    """Handle free text input in guided flow (for 'Other' option)."""
    if session_state is None:
        session_state = new_session()

    result = orchestrator.process_text_input(text, session_state)
    return result["text_response"], result["session_state"]


# ── Tab 3: Form Filing Agent ──────────────────────────────────────────────

def list_portals():
    """Return formatted list of supported portals."""
    portals = get_supported_portals()
    text = "### Supported Government Portals\n\n"
    for p in portals:
        text += f"**{p['name']}** — [{p['url']}]({p['url']})\n"
        text += f"Forms: {', '.join(p['forms'])}\n\n"
    return text


# ── Tab 4: Case Tracker ──────────────────────────────────────────────────

def create_case(issue, sections_text, session_state):
    """Create a new case."""
    if session_state is None:
        session_state = new_session()

    sections = [s.strip() for s in sections_text.split(",") if s.strip()]
    case = orchestrator._tracker.create_case(
        user_id=session_state.get("user_id", "demo"),
        issue=issue,
        sections=sections,
    )
    return f"Case created: **{case['case_id']}**\nIssue: {issue}\nSections: {', '.join(sections)}", session_state


def list_user_cases(session_state):
    """List all cases for current user."""
    if session_state is None:
        session_state = new_session()

    cases = orchestrator._tracker.list_cases(session_state.get("user_id", "demo"))
    if not cases:
        return "No cases found."

    text = "### Your Cases\n\n"
    for c in cases:
        text += f"**{c['case_id']}** — Status: {c['status']}\n"
        text += f"Issue: {c['issue']}\n"
        text += f"Sections: {', '.join(c['sections'])}\n"
        text += f"Created: {c['created_at']}\n\n"
    return text


# ── Build Gradio App ──────────────────────────────────────────────────────

def build_app():
    """Build and return the Gradio app."""
    with gr.Blocks(
        title=GRADIO_TITLE,
    ) as app:
        gr.Markdown(f"# {GRADIO_TITLE}")
        gr.Markdown("Voice-first, multilingual, agentic AI legal assistant for India")

        session_state = gr.State(new_session())

        # Language selector
        with gr.Row():
            lang_dropdown = gr.Dropdown(
                choices=[(v, k) for k, v in SUPPORTED_LANGUAGES.items()],
                value="en-IN",
                label="Language / भाषा",
                scale=1,
            )
            lang_dropdown.change(set_language, [lang_dropdown, session_state], [session_state])

        with gr.Tabs():
            # ── Tab 1: Voice Assistant ──
            with gr.Tab("Voice Assistant"):
                gr.Markdown(
                    "> **How it works:** Click the microphone, speak your legal question, "
                    "then stop recording. Your speech will be converted to text and answered automatically."
                )
                chatbot = gr.Chatbot(label="Conversation", height=400, type="messages")
                with gr.Row():
                    audio_input = gr.Audio(
                        sources=["microphone"],
                        type="numpy",
                        label="🎤 Click to record your question",
                        scale=2,
                    )
                    audio_output = gr.Audio(label="Response Audio", type="numpy", scale=1, visible=False)

                with gr.Row():
                    text_input = gr.Textbox(
                        placeholder="Or type your legal question here...",
                        label="Text Input",
                        scale=4,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                audio_input.stop_recording(
                    voice_chat,
                    [audio_input, chatbot, session_state],
                    [chatbot, session_state, audio_output],
                )
                send_btn.click(
                    text_chat,
                    [text_input, chatbot, session_state],
                    [text_input, chatbot, session_state],
                )
                text_input.submit(
                    text_chat,
                    [text_input, chatbot, session_state],
                    [text_input, chatbot, session_state],
                )

            # ── Tab 2: Guided Legal Help ──
            with gr.Tab("Guided Legal Help"):
                gr.Markdown("### Step-by-Step Legal Guidance")
                gr.Markdown("Answer simple questions to find the right legal sections for your situation.")

                guided_output = gr.Markdown("Click **Start** to begin the guided legal assessment.")
                guided_state = gr.State(None)
                options_state = gr.State([])

                start_btn = gr.Button("Start Guided Flow", variant="primary")
                guided_radio = gr.Radio(choices=[], label="Select your answer", visible=False)
                guided_select_btn = gr.Button("Next", visible=True)

                guided_free_input = gr.Textbox(
                    label="Describe your issue",
                    placeholder="Type your legal issue here...",
                    visible=False,
                )

                def on_start():
                    text, radio_update, state, _ = start_guided_flow()
                    choices = radio_update.get("choices", []) if isinstance(radio_update, dict) else []
                    return text, radio_update, state, choices

                start_btn.click(
                    on_start,
                    [],
                    [guided_output, guided_radio, guided_state, options_state],
                )

                def on_select(choice, options, g_state, s_state):
                    return guided_select(choice, options, g_state, s_state)

                guided_select_btn.click(
                    on_select,
                    [guided_radio, options_state, guided_state, session_state],
                    [guided_output, guided_radio, guided_state, session_state, guided_free_input],
                )

            # ── Tab 3: Form Filing Agent ──
            with gr.Tab("Form Filing Agent"):
                gr.Markdown("### Government Portal Form Automation")
                gr.Markdown(list_portals())

                gr.Markdown("**Demo Mode:** Select a portal and enter your details below.")
                with gr.Row():
                    portal_select = gr.Dropdown(
                        choices=["Parivahan (Transport)", "eCourts", "NALSA Legal Aid"],
                        label="Select Portal",
                    )
                with gr.Row():
                    name_input = gr.Textbox(label="Full Name")
                    state_input = gr.Textbox(label="State")
                with gr.Row():
                    form_btn = gr.Button("Start Form Filling", variant="primary")
                form_output = gr.Markdown("Select a portal and click Start.")

                gr.Markdown(
                    "> **Note:** The form filling agent will open a browser window. "
                    "You will need to complete CAPTCHA/OTP manually."
                )

            # ── Tab 4: Case Tracker ──
            with gr.Tab("Case Tracker"):
                gr.Markdown("### Track Your Legal Cases")

                with gr.Row():
                    case_issue = gr.Textbox(label="Issue Description", scale=3)
                    case_sections = gr.Textbox(label="Sections (comma-separated)", placeholder="BNS-100, BNS-115", scale=2)
                    create_btn = gr.Button("Create Case", variant="primary", scale=1)

                case_output = gr.Markdown("No cases yet.")
                list_btn = gr.Button("Refresh Cases")

                create_btn.click(
                    create_case,
                    [case_issue, case_sections, session_state],
                    [case_output, session_state],
                )
                list_btn.click(
                    list_user_cases,
                    [session_state],
                    [case_output],
                )

        # Footer disclaimer
        gr.Markdown(f"---\n{DISCLAIMER}")

    return app


if __name__ == "__main__":
    app = build_app()
    app.launch(server_port=GRADIO_PORT, share=False)
