"""Lexaro — Legal Help. Simplified. Localized. (Gradio App)."""

import gradio as gr
from backend.config import DISCLAIMER, GRADIO_PORT, GRADIO_TITLE, SUPPORTED_LANGUAGES
from backend.agent.orchestrator import Orchestrator
from backend.agent.form_filler import get_supported_portals
from backend.agent.escalation import get_escalation_info
from backend.agent.openclaw.orchestrator import get_openclaw

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


# ── Tab 3: OpenClaw Form Filing Agent ─────────────────────────────────────

_openclaw = get_openclaw()

# Portal ID mapping for dropdown
_PORTAL_CHOICES = {
    "CPGRAMS (Public Grievance)": "cpgrams",
    "National Consumer Helpline": "consumer_helpline",
    "eCourts eFiling": "ecourts",
    "mParivahan / Sarathi": "mparivahan",
}

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Chandigarh", "Puducherry",
]


def list_portals():
    """Return formatted list of supported portals."""
    portals = _openclaw.list_portals()
    text = "### Supported Government Portals (OpenClaw Autonomous Filing)\n\n"
    for p in portals:
        text += f"**{p['name']}** — [{p['url']}]({p['url']})\n"
        text += f"Required fields: {', '.join(p['required_fields'])}\n\n"
    return text


async def start_openclaw_filing(
    portal_name, name, mobile, email, state, district, pin_code,
    gender, father_name, dob, description, documents, session_state,
):
    """Start autonomous form filing via OpenClaw."""
    if session_state is None:
        session_state = new_session()

    portal_id = _PORTAL_CHOICES.get(portal_name)
    if not portal_id:
        return "Please select a portal.", gr.update(visible=False), session_state

    user_data = {
        "name": name or "",
        "mobile": mobile or "",
        "email": email or "",
        "state": state or "",
        "district": district or "",
        "pin_code": pin_code or "",
        "gender": gender or "",
        "father_name": father_name or "",
        "dob": dob or "",
        "description": description or "",
        "subject": (description or "")[:100],
        "address": f"{district}, {state} - {pin_code}",
    }

    # Validate
    missing = _openclaw.validate_request(portal_id, user_data)
    if missing:
        return (
            f"Missing required fields: **{', '.join(missing)}**\n\nPlease fill all required fields.",
            gr.update(visible=False),
            session_state,
        )

    # Collect document paths
    doc_paths = []
    if documents:
        for doc in documents:
            if hasattr(doc, "name"):
                doc_paths.append(doc.name)
            elif isinstance(doc, str):
                doc_paths.append(doc)

    progress_log = []

    def on_progress(msg):
        progress_log.append(msg)

    # Run the filing
    result = await _openclaw.file_form(
        portal_id=portal_id,
        user_data=user_data,
        documents=doc_paths,
        on_progress=on_progress,
    )

    # Build result display
    steps_text = "\n".join(f"- {s}" for s in result.steps_completed)
    output = f"## Filing Result: {result.status.value.upper()}\n\n"

    if result.reference_number:
        output += f"### Reference Number: `{result.reference_number}`\n\n"

    output += f"**Portal:** {portal_name}\n"
    output += f"**Message:** {result.message}\n\n"

    if steps_text:
        output += f"### Steps Completed\n{steps_text}\n\n"

    if result.error:
        output += f"### Error\n{result.error}\n\n"

    # Show OTP section if waiting
    show_otp = _openclaw.otp_gate.is_waiting(session_state.get("openclaw_session", ""))

    return output, gr.update(visible=show_otp), session_state


def submit_otp_callback(otp_value, session_state):
    """Handle OTP submission from the UI."""
    if session_state is None:
        session_state = new_session()

    session_id = session_state.get("openclaw_session", "")
    if not session_id or not otp_value:
        return "No pending OTP request.", session_state

    success = _openclaw.otp_gate.submit_otp(session_id, otp_value.strip())
    if success:
        return "OTP submitted. The agent is continuing...", session_state
    return "No pending OTP request for this session.", session_state


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

            # ── Tab 3: OpenClaw Autonomous Form Filing ──
            with gr.Tab("OpenClaw Form Agent"):
                gr.Markdown("### Autonomous Government Portal Filing (OpenClaw)")
                gr.Markdown(
                    "> **How it works:** Select a portal, fill your details, and click Start. "
                    "The AI agent will open a browser, fill the form, solve CAPTCHAs automatically, "
                    "and pause for OTP when needed. You'll get a reference number at the end."
                )
                gr.Markdown(list_portals())

                with gr.Row():
                    portal_select = gr.Dropdown(
                        choices=list(_PORTAL_CHOICES.keys()),
                        label="Select Portal",
                        scale=2,
                    )
                    gender_input = gr.Dropdown(
                        choices=["Male", "Female", "Other"],
                        label="Gender",
                        scale=1,
                    )

                with gr.Row():
                    oc_name = gr.Textbox(label="Full Name", placeholder="Enter your full name")
                    oc_father = gr.Textbox(label="Father's Name", placeholder="(Required for Parivahan)")
                    oc_dob = gr.Textbox(label="Date of Birth", placeholder="DD/MM/YYYY")

                with gr.Row():
                    oc_mobile = gr.Textbox(label="Mobile Number", placeholder="10-digit mobile")
                    oc_email = gr.Textbox(label="Email", placeholder="your@email.com")
                    oc_pin = gr.Textbox(label="PIN Code", placeholder="6-digit PIN")

                with gr.Row():
                    oc_state = gr.Dropdown(choices=INDIAN_STATES, label="State")
                    oc_district = gr.Textbox(label="District", placeholder="Your district")

                oc_description = gr.Textbox(
                    label="Grievance / Complaint / Case Description",
                    placeholder="Describe your issue in detail (max 4000 characters)...",
                    lines=4,
                )

                oc_documents = gr.File(
                    label="Upload Documents (PDF, JPG, PNG)",
                    file_count="multiple",
                    file_types=[".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"],
                )

                with gr.Row():
                    oc_start_btn = gr.Button("Start Autonomous Filing", variant="primary", scale=2)
                    oc_stop_btn = gr.Button("Cancel", variant="stop", scale=1)

                oc_output = gr.Markdown("Select a portal, fill your details, and click **Start Autonomous Filing**.")

                # OTP Section (hidden until needed)
                with gr.Group(visible=False) as otp_group:
                    gr.Markdown("### OTP Required")
                    gr.Markdown("An OTP has been sent to your registered mobile/email. Enter it below:")
                    with gr.Row():
                        oc_otp_input = gr.Textbox(label="Enter OTP", placeholder="6-digit OTP", scale=3)
                        oc_otp_btn = gr.Button("Submit OTP", variant="secondary", scale=1)
                    oc_otp_status = gr.Markdown("")

                # Wire up events
                oc_start_btn.click(
                    start_openclaw_filing,
                    inputs=[
                        portal_select, oc_name, oc_mobile, oc_email, oc_state,
                        oc_district, oc_pin, gender_input, oc_father, oc_dob,
                        oc_description, oc_documents, session_state,
                    ],
                    outputs=[oc_output, otp_group, session_state],
                )

                oc_otp_btn.click(
                    submit_otp_callback,
                    inputs=[oc_otp_input, session_state],
                    outputs=[oc_otp_status, session_state],
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
