
import io
import re
import json
import requests
import pandas as pd
import streamlit as st
import speech_recognition as sr

st.set_page_config(
    page_title="PerXL Voice Assistant",
    page_icon="🎙️",
    layout="wide"
)

DEFAULT_API_URL = "https://perxl-data-review.onrender.com"

st.markdown("""
<style>
.stApp {
    background: #f3f6fb;
}
header[data-testid="stHeader"] {
    background: #111c36;
}
.brand {
    background: #111c36;
    color: white;
    padding: 18px 26px;
    border-radius: 12px;
    margin-bottom: 22px;
}
.brand h2 {
    margin: 0;
    color: white;
    font-size: 25px;
}
.brand p {
    margin: 6px 0 0 0;
    color: #d7e1ff;
    font-size: 13px;
}
.panel {
    background: white;
    border: 1px solid #d9e3f3;
    border-radius: 14px;
    padding: 22px;
    margin-bottom: 18px;
}
.eyebrow {
    color: #315cff;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.4px;
}
.recognized {
    background: #f4f7ff;
    border: 1px solid #d9e3ff;
    border-radius: 10px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="brand">
    <h2>🎙️ PerXL Voice Assistant</h2>
    <p>Speak naturally. Review the transcript. Run your command.</p>
</div>
""", unsafe_allow_html=True)

if "transcript" not in st.session_state:
    st.session_state.transcript = ""

if "command_history" not in st.session_state:
    st.session_state.command_history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_error" not in st.session_state:
    st.session_state.last_error = None

with st.sidebar:
    st.header("Connection Settings")
    api_url = st.text_input(
        "Backend API URL",
        value=st.session_state.get("api_url", DEFAULT_API_URL),
        key="backend_url"
    ).strip().rstrip("/")

    st.caption("Enter the base URL of your deployed FastAPI backend.")

    if st.button("Check API", use_container_width=True):
        try:
            response = requests.get(
                f"{api_url}/health",
                timeout=30
            )
            st.write("HTTP status:", response.status_code)
            try:
                st.json(response.json())
            except ValueError:
                st.code(response.text[:2000])
        except requests.RequestException as exc:
            st.error(str(exc))

    st.divider()
    st.caption("Voice recognition uses Google's speech recognition service.")
    st.caption("Recorded audio is sent for transcription when you click Transcribe.")

def request_api(endpoint, params=None):
    response = requests.get(
        f"{api_url}{endpoint}",
        params=params,
        timeout=60
    )

    try:
        data = response.json()
    except ValueError:
        data = {"response": response.text[:5000]}

    if not response.ok:
        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{json.dumps(data, ensure_ascii=False)}"
        )

    return data

def transcribe_audio(audio_file):
    recognizer = sr.Recognizer()

    with sr.AudioFile(io.BytesIO(audio_file.getvalue())) as source:
        audio = recognizer.record(source)

    return recognizer.recognize_google(audio)

def classify_command(command):
    text = command.lower().strip()
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    if any(phrase in text for phrase in [
        "check api", "check connection", "check backend",
        "api status", "is the api working"
    ]):
        return {
            "label": "API Health",
            "endpoint": "/health",
            "params": None
        }

    if any(phrase in text for phrase in [
        "task summary", "summary of tasks", "total tasks",
        "how many tasks", "show all task summary"
    ]):
        return {
            "label": "Task Summary",
            "endpoint": "/tasks/summary",
            "params": None
        }

    if any(phrase in text for phrase in [
        "completed tasks", "show completed", "finished tasks",
        "tasks completed"
    ]):
        return {
            "label": "Completed Tasks",
            "endpoint": "/tasks/by-status",
            "params": {"status": "Completed"}
        }

    if any(phrase in text for phrase in [
        "in progress", "ongoing tasks", "currently working",
        "tasks in progress"
    ]):
        return {
            "label": "In-Progress Tasks",
            "endpoint": "/tasks/by-status",
            "params": {"status": "In Progress"}
        }

    if any(phrase in text for phrase in [
        "to do tasks", "todo tasks", "pending tasks",
        "tasks to do"
    ]):
        return {
            "label": "To-Do Tasks",
            "endpoint": "/tasks/by-status",
            "params": {"status": "ToDo"}
        }

    if any(phrase in text for phrase in [
        "task priority", "tasks by priority", "priority summary"
    ]):
        return {
            "label": "Task Priority",
            "endpoint": "/tasks/by-priority",
            "params": None
        }

    if any(phrase in text for phrase in [
        "show collections", "list collections", "available collections"
    ]):
        return {
            "label": "Collections",
            "endpoint": "/collections",
            "params": None
        }

    if "show sections" in text or "list sections" in text:
        return {
            "label": "Sections",
            "endpoint": "/sections",
            "params": None
        }

    if "show spaces" in text or "list spaces" in text:
        return {
            "label": "Spaces",
            "endpoint": "/spaces",
            "params": None
        }

    return None

def execute_command(command):
    if not command.strip():
        st.warning("Please speak or type a command first.")
        return

    route = classify_command(command)

    if route is None:
        st.warning(
            "Command not recognized. Try 'show task summary', "
            "'show completed tasks', 'show in progress tasks', "
            "'show to-do tasks', or 'check API'."
        )
        return

    with st.spinner(f"Executing: {route['label']}..."):
        try:
            result = request_api(
                route["endpoint"],
                route["params"]
            )

            st.session_state.last_result = {
                "command": command,
                "label": route["label"],
                "endpoint": route["endpoint"],
                "data": result
            }
            st.session_state.last_error = None
            st.session_state.command_history.insert(0, {
                "command": command,
                "action": route["label"],
                "status": "Success"
            })
            st.success(f"Command executed: {route['label']}")

        except Exception as exc:
            st.session_state.last_error = {
                "command": command,
                "endpoint": route["endpoint"],
                "error": str(exc)
            }
            st.session_state.last_result = None
            st.session_state.command_history.insert(0, {
                "command": command,
                "action": route["label"],
                "status": "Failed"
            })
            st.error(f"Backend request failed: {exc}")

left, right = st.columns([1.5, 1])

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">VOICE COMMAND CENTRE</div>', unsafe_allow_html=True)
    st.subheader("What would you like to know?")
    st.write(
        "Record your command, transcribe your speech, "
        "review the text, and run the command."
    )

    audio = st.audio_input("🎤 Click to record your command")

    if audio is not None:
        st.audio(audio, format="audio/wav")

        if st.button("Transcribe Recording", use_container_width=True):
            with st.spinner("Recognizing your speech..."):
                try:
                    recognized = transcribe_audio(audio)
                    st.session_state.transcript = recognized
                    st.success("Speech recognized successfully.")
                except sr.UnknownValueError:
                    st.error("Speech could not be understood. Please try again.")
                except sr.RequestError as exc:
                    st.error(f"Speech recognition service error: {exc}")
                except Exception as exc:
                    st.error(f"Transcription failed: {exc}")

    st.markdown("**Recognized speech / command**")

    command = st.text_area(
        "Recognized command",
        key="command_input",
        value=st.session_state.transcript,
        placeholder="Your spoken words will appear here. You can also type: Show completed tasks.",
        height=100,
        label_visibility="collapsed"
    )

    col_run, col_clear, col_check = st.columns([1.4, 0.7, 0.9])

    with col_run:
        run_command = st.button(
            "▶ Run Command",
            type="primary",
            use_container_width=True
        )

    with col_clear:
        clear_command = st.button(
            "Clear",
            use_container_width=True
        )

    with col_check:
        check_api = st.button(
            "Check API",
            use_container_width=True
        )

    if clear_command:
        st.session_state.transcript = ""
        st.session_state.command_input = ""
        st.rerun()

    if check_api:
        try:
            result = request_api("/health")
            st.session_state.last_result = {
                "command": "Check API",
                "label": "API Health",
                "endpoint": "/health",
                "data": result
            }
            st.session_state.last_error = None
            st.success("API health endpoint responded successfully.")
        except Exception as exc:
            st.session_state.last_error = {
                "command": "Check API",
                "endpoint": "/health",
                "error": str(exc)
            }
            st.error(str(exc))

    if run_command:
        execute_command(command)

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">QUICK COMMANDS</div>', unsafe_allow_html=True)
    st.subheader("Try a command")

    quick_commands = [
        ("Task summary", "Show task summary"),
        ("Completed tasks", "Show completed tasks"),
        ("In-progress tasks", "Show in progress tasks"),
        ("To-do tasks", "Show to-do tasks"),
        ("Task priority", "Show tasks by priority"),
        ("Collections", "Show collections"),
        ("Sections", "Show sections"),
        ("Spaces", "Show spaces")
    ]

    quick_columns = st.columns(2)

    for index, (label, value) in enumerate(quick_commands):
        with quick_columns[index % 2]:
            if st.button(label, key=f"quick_{index}", use_container_width=True):
                st.session_state.transcript = value
                st.session_state.command_input = value
                execute_command(value)

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">COMMAND OUTPUT</div>', unsafe_allow_html=True)
    st.subheader("Results")

    if st.session_state.last_error:
        st.error(
            f"{st.session_state.last_error['endpoint']}: "
            f"{st.session_state.last_error['error']}"
        )

    elif st.session_state.last_result:
        result = st.session_state.last_result
        st.success(result["label"])
        st.caption(f"Endpoint: {result['endpoint']}")

        data = result["data"]

        if isinstance(data, dict):
            if isinstance(data.get("records"), list):
                records = data["records"]
                if records and all(isinstance(item, dict) for item in records):
                    st.dataframe(pd.DataFrame(records), use_container_width=True)
                else:
                    st.json(data)
            elif isinstance(data.get("tasks"), list):
                tasks = data["tasks"]
                if tasks and all(isinstance(item, dict) for item in tasks):
                    st.dataframe(pd.DataFrame(tasks), use_container_width=True)
                else:
                    st.json(data)
            else:
                st.json(data)
        elif isinstance(data, list) and data and all(
            isinstance(item, dict) for item in data
        ):
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.json(data)

    else:
        st.info("Your API response will appear here after you run a command.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">RECENT ACTIVITY</div>', unsafe_allow_html=True)
    st.subheader("Command history")

    if st.session_state.command_history:
        st.dataframe(
            pd.DataFrame(st.session_state.command_history),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("Your recent commands will appear here.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">CONNECTION SETTINGS</div>', unsafe_allow_html=True)
    st.subheader("Backend API")
    st.code(api_url, language=None)
    st.caption(
        "Use the base URL of the API that contains your task endpoints. "
        "The API must be healthy and its database collections must be available."
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    "<center><small>PerXL Voice Assistant · Streamlit + FastAPI</small></center>",
    unsafe_allow_html=True
)
