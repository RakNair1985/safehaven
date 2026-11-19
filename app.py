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
TODAY = date.today().isoformat()

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
You are Aura, a compassionate, patient, non-judgmental listener.

- Validate the person's feelings before offering perspective.
- Do not rush to solve problems or use toxic positivity.
- Be calm, respectful, inclusive, and culturally neutral.
- Reply in the same language and tone the person uses.
- Do not diagnose conditions, prescribe medication, or give medical advice.
- Do not provide instructions for self-harm, violence, or illegal activity.
- If someone may be in immediate danger, encourage them to contact local
  emergency services or a trusted person, and avoid acting as a crisis service.
"""


def init_supabase():
    try:
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"],
        )
    except Exception:
        return None


supabase = init_supabase()


def render_auth_screen():
    st.title("🌱 SafeHaven")
    st.caption("A quiet, judgment-free space for emotional support and active listening.")

    login_tab, signup_tab = st.tabs(["Log In", "Create Account"])

    with login_tab:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log In", use_container_width=True):
            if not supabase:
                st.error("Database connection error. Check your Supabase secrets.")
            else:
                try:
                    response = supabase.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    if response.user:
                        st.session_state.user = response.user
                        st.rerun()
                except Exception:
                    st.error("Login failed. Check your email and password.")

    with signup_tab:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input(
            "Password (minimum 6 characters)",
            type="password",
            key="signup_password",
        )

        if st.button("Create Account", use_container_width=True):
            if not supabase:
                st.error("Database connection error. Check your Supabase secrets.")
            else:
                try:
                    response = supabase.auth.sign_up(
                        {"email": email, "password": password}
                    )
                    if response.user:
                        st.session_state.user = response.user
                        st.rerun()
                except Exception:
                    st.error(
                        "Sign-up failed. Try a different email or stronger password."
                    )


def get_remaining_messages(user_id):
    if not supabase:
        return FREE_MESSAGE_LIMIT

    try:
        response = (
            supabase.table("user_daily_usage")
            .select("message_count")
            .eq("user_id", user_id)
            .eq("usage_date", TODAY)
            .execute()
        )

        if response.data:
            used = response.data[0]["message_count"]
            return max(0, FREE_MESSAGE_LIMIT - used)
    except Exception:
        pass

    return FREE_MESSAGE_LIMIT


def increment_usage(user_id):
    if not supabase:
        return

    try:
        response = (
            supabase.table("user_daily_usage")
            .select("message_count")
            .eq("user_id", user_id)
            .eq("usage_date", TODAY)
            .execute()
        )

        if response.data:
            current_count = response.data[0]["message_count"]
            supabase.table("user_daily_usage").update(
                {"message_count": current_count + 1}
            ).eq("user_id", user_id).eq("usage_date", TODAY).execute()
        else:
            supabase.table("user_daily_usage").insert(
                {
                    "user_id": user_id,
                    "usage_date": TODAY,
                    "message_count": 1,
                }
            ).execute()
    except Exception:
        pass


def save_message(user_id, role, content):
    if not supabase:
        return

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
    if not supabase:
        return []

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
            {"role": row["role"], "content": row["content"]}
            for row in response.data
        ]
    except Exception:
        return []


def detect_crisis(text):
    normalized = text.lower()
    return any(keyword in normalized for keyword in CRISIS_KEYWORDS)


if "user" not in st.session_state:
    render_auth_screen()
    st.stop()

user = st.session_state.user
user_id = user.id

with st.sidebar:
    st.title("🌱 SafeHaven")

    user_email = getattr(user, "email", "User")
    st.caption(f"Logged in as: **{user_email}**")

    st.divider()
    remaining = get_remaining_messages(user_id)
    st.metric("Messages remaining today", remaining)

    st.divider()
    st.markdown("### 🆘 Need immediate help?")
    st.write(
        "If you are in immediate danger or experiencing a mental-health crisis, "
        "contact local emergency services or a trusted person now."
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
            If you are in immediate danger, contact local emergency services
            or a professional helpline immediately.
            """
        )

    if st.button("Log out", use_container_width=True):
        if supabase:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
        del st.session_state.user
        st.rerun()

st.title("🌱 SafeHaven")
st.caption("Heard first. Respected always. Supported everywhere.")

try:
    gemini_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("Gemini API key is missing or invalid. Check Streamlit Secrets.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = load_history(user_id)

for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            feedback_state_key = f"feedback_saved_{index}_{user_id}"

            feedback = st.feedback(
                "thumbs",
                key=f"feedback_{index}_{user_id}",
            )

            if (
                feedback is not None
                and supabase
                and feedback_state_key not in st.session_state
            ):
                try:
                    supabase.table("chat_feedback").insert(
                        {
                            "user_id": user_id,
                            "score": feedback,
                        }
                    ).execute()
                    st.session_state[feedback_state_key] = True
                except Exception:
                    pass

current_remaining = get_remaining_messages(user_id)

if current_remaining <= 0:
    st.warning(
        "You have reached today’s free message limit. Please return tomorrow."
    )
    st.stop()

user_input = st.chat_input("Share what’s on your mind…")

if user_input:
    increment_usage(user_id)
    st.session_state.messages.append(
        {"role": "user", "content": user_input}
    )
    save_message(user_id, "user", user_input)

    with st.chat_message("user"):
        st.markdown(user_input)

    if detect_crisis(user_input):
        reply = (
            "I’m really sorry you’re carrying this. Your safety matters. "
            "Please contact local emergency services or a trusted person now. "
            "You can also use the helpline links in the sidebar."
        )

        with st.chat_message("assistant"):
            st.error(reply)
    else:
        with st.chat_message("assistant"):
            with st.spinner("Listening…"):
                try:
                    contents = []

                    for message in st.session_state.messages:
                        role = "model" if message["role"] == "assistant" else "user"
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[
                                    types.Part.from_text(text=message["content"])
                                ],
                            )
                        )

reply_placeholder = st.empty()
reply = ""

stream = gemini_client.models.generate_content_stream(
    model="gemini-4-hydrogen",
    contents=contents,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.7,
        max_output_tokens=300,
    ),
)

for chunk in stream:
    if chunk.text:
        reply += chunk.text
        reply_placeholder.markdown(reply + "▌")

reply_placeholder.markdown(reply)

                except Exception:
                    reply = (
                        "I’m here with you, but I’m having trouble responding "
                        "right now. Please try again shortly."
                    )
                    st.error(reply)

    st.session_state.messages.append(
        {"role": "assistant", "content": reply}
    )
    save_message(user_id, "assistant", reply)
    st.rerun()
