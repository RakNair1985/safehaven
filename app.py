from datetime import date

import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

st.set_page_config(
    page_title="SafeHaven",
    page_icon="🌱",
    layout="centered",
)

FREE_MESSAGE_LIMIT = 15
MAX_HISTORY_MESSAGES = 8
MAX_OUTPUT_TOKENS = 300

CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "end my life",
    "want to die",
    "self-harm",
    "hurt myself",
    "no reason to live",
]

SYSTEM_PROMPT = """
You are Aura, a warm, calm, compassionate, and non-judgmental listener.

- Validate the person's feelings before offering perspective.
- Reply in the same language and tone the person uses.
- Keep responses concise: usually 2 to 5 sentences.
- Ask at most one gentle follow-up question.
- Do not diagnose conditions, prescribe medication, or give medical advice.
- Do not provide instructions for self-harm, violence, or illegal activity.
- If someone may be in immediate danger, encourage them to contact local
  emergency services or a trusted person.
- Do not claim to be a therapist, doctor, or crisis service.
"""


@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


supabase = get_supabase_client()
gemini_client = get_gemini_client()


def render_auth_screen():
    st.title("🌱 SafeHaven")
    st.caption(
        "A quiet, judgment-free space for emotional support and active listening."
    )

    login_tab, signup_tab = st.tabs(["Log In", "Create Account"])

    with login_tab:
        email = st.text_input("Email", key="login_email")
        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
        )

        if st.button("Log In", use_container_width=True):
            try:
                response = supabase.auth.sign_in_with_password(
                    {
                        "email": email,
                        "password": password,
                    }
                )

                if response.user:
                    st.session_state.user = response.user
                    st.rerun()

            except Exception:
                st.error(
                    "Login failed. Please check your email and password."
                )

    with signup_tab:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input(
            "Password (minimum 6 characters)",
            type="password",
            key="signup_password",
        )

        if st.button("Create Account", use_container_width=True):
            try:
                response = supabase.auth.sign_up(
                    {
                        "email": email,
                        "password": password,
                    }
                )

                if response.user:
                    st.session_state.user = response.user
                    st.rerun()

            except Exception:
                st.error(
                    "Sign-up failed. Try a different email or a stronger password."
                )


def get_remaining_messages(user_id):
    today = date.today().isoformat()

    try:
        response = (
            supabase.table("user_daily_usage")
            .select("message_count")
            .eq("user_id", user_id)
            .eq("usage_date", today)
            .execute()
        )

        if response.data:
            used = response.data[0]["message_count"]
            return max(0, FREE_MESSAGE_LIMIT - used)

    except Exception:
        pass

    return FREE_MESSAGE_LIMIT


def increment_usage(user_id):
    today = date.today().isoformat()

    try:
        response = (
            supabase.table("user_daily_usage")
            .select("message_count")
            .eq("user_id", user_id)
            .eq("usage_date", today)
            .execute()
        )

        if response.data:
            current_count = response.data[0]["message_count"]

            supabase.table("user_daily_usage").update(
                {"message_count": current_count + 1}
            ).eq("user_id", user_id).eq("usage_date", today).execute()

        else:
            supabase.table("user_daily_usage").insert(
                {
                    "user_id": user_id,
                    "usage_date": today,
                    "message_count": 1,
                }
            ).execute()

    except Exception:
        pass


def save_message(user_id, role, content):
    try:
        supabase.table("chat_messages").insert(
            {
                "user_id": user_id,
                "role": role,
                "content": content,
            }
        ).execute()

    except Exception:
        pass


def load_history(user_id):
    try:
        response = (
            supabase.table("chat_messages")
            .select("role, content")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(50)
            .execute()
        )

        return [
            {
                "role": row["role"],
                "content": row["content"],
            }
            for row in response.data
        ]

    except Exception:
        return []


def detect_crisis(text):
    normalized_text = text.lower()

    return any(
        keyword in normalized_text
        for keyword in CRISIS_KEYWORDS
    )


def render_sidebar(user):
    user_email = getattr(user, "email", "User")

    with st.sidebar:
        st.title("🌱 SafeHaven")
        st.caption(f"Logged in as: **{user_email}**")

        st.divider()

        remaining = get_remaining_messages(user.id)
        st.metric(
            label="Messages remaining today",
            value=remaining,
        )

        st.divider()
        st.markdown("### 🆘 Need immediate help?")

        st.write(
            "If you are in immediate danger or experiencing a mental-health "
            "crisis, contact local emergency services or a trusted person now."
        )

        st.link_button(
            "Find a Helpline",
            "https://findahelpline.com/",
            use_container_width=True,
        )

        st.link_button(
            "India: Tele-MANAS 14416",
            "https://telemanas.mohfw.gov.in/",
            use_container_width=True,
        )

        st.link_button(
            "US & Canada: 988 Lifeline",
            "https://988lifeline.org/",
            use_container_width=True,
        )

        st.divider()

        with st.expander("Terms and disclaimer"):
            st.markdown(
                """
                SafeHaven is an AI-supported wellbeing tool, not a therapist,
                doctor, crisis service, or emergency service.

                It does not provide medical advice, diagnosis, or treatment.
                If you are in immediate danger, contact local emergency
                services or a professional helpline immediately.
                """
            )

        if st.button("Log out", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass

            del st.session_state.user
            st.rerun()


def generate_aura_reply(conversation_history):
    contents = []

    for message in conversation_history:
        role = "model" if message["role"] == "assistant" else "user"

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(
                        text=message["content"]
                    )
                ],
            )
        )

    stream = gemini_client.models.generate_content_stream(
        model="gemini-4-hydrogen",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )

    return stream


if "user" not in st.session_state:
    render_auth_screen()
    st.stop()

user = st.session_state.user
user_id = user.id

render_sidebar(user)

st.title("🌱 SafeHaven")
st.caption(
    "Heard first. Respected always. Supported everywhere."
)

if "messages" not in st.session_state:
    st.session_state.messages = load_history(user_id)

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            feedback = st.feedback(
                "thumbs",
                key=f"feedback_{index}_{user_id}",
            )

            feedback_saved_key = (
                f"feedback_saved_{index}_{user_id}"
            )

            if (
                feedback is not None
                and feedback_saved_key not in st.session_state
            ):
                try:
                    supabase.table("chat_feedback").insert(
                        {
                            "user_id": user_id,
                            "score": feedback,
                        }
                    ).execute()

                    st.session_state[feedback_saved_key] = True

                except Exception:
                    pass

remaining_messages = get_remaining_messages(user_id)

if remaining_messages <= 0:
    st.warning(
        "You have reached today’s free message limit. "
        "Please return tomorrow to continue."
    )
    st.stop()

user_input = st.chat_input("Share what’s on your mind…")

if user_input:
    increment_usage(user_id)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    save_message(user_id, "user", user_input)

    with st.chat_message("user"):
        st.markdown(user_input)

    if detect_crisis(user_input):
        reply = (
            "I’m really sorry you’re carrying this. Your safety matters.\n\n"
            "Please contact local emergency services or a trusted person now. "
            "You can also use the helpline links in the sidebar."
        )

        with st.chat_message("assistant"):
            st.error(reply)

    else:
        with st.chat_message("assistant"):
            reply_placeholder = st.empty()
            reply = ""

            try:
                reply_placeholder.markdown("_Aura is listening…_")

                stream = generate_aura_reply(
                    st.session_state.messages[-MAX_HISTORY_MESSAGES:]
                )

                for chunk in stream:
                    if chunk.text:
                        reply += chunk.text
                        reply_placeholder.markdown(reply + " ▌")

                if not reply.strip():
                    reply = (
                        "I’m here with you. Could you tell me a little more "
                        "about what you’re experiencing?"
                    )

                reply_placeholder.markdown(reply)

            except Exception:
                if reply.strip():
                    reply += (
                        "\n\n*The response was interrupted. "
                        "Please try again shortly.*"
                    )
                else:
                    reply = (
                        "Aura is temporarily unavailable. Please try again "
                        "shortly. Support resources remain available in the "
                        "sidebar."
                    )

                reply_placeholder.markdown(reply)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": reply,
        }
    )

    save_message(user_id, "assistant", reply)
    st.rerun()
