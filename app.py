import openai
from supabase import create_client
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="SafeHaven - Universal Companion", page_icon="🌱", layout="centered"
)

# Custom CSS for soothing aesthetics and clean chat bubbles
st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stChatMessage {
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- SUPABASE INITIALIZATION ---
def init_supabase():
  try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
  except Exception as e:
    return None


supabase = init_supabase()


# --- AUTHENTICATION SCREEN ---
def render_auth_screen():
  st.title("🌱 SafeHaven - Account Access")
  st.caption("A safe, global sanctuary for emotional support and active listening.")

  auth_tab1, auth_tab2 = st.tabs(["Log In", "Create Account"])

  with auth_tab1:
    st.subheader("Welcome Back")
    login_email = st.text_input("Email", key="login_email")
    login_password = st.text_input(
        "Password", type="password", key="login_password"
    )

    if st.button("Log In", use_container_width=True):
      if not supabase:
        st.error(
            "Database connection error. Please check your Supabase secrets."
        )
      else:
        try:
          response = supabase.auth.sign_in_with_password({
              "email": login_email,
              "password": login_password,
          })
          if response.user:
            st.session_state.user = response.user
            st.success("Logged in successfully!")
            st.rerun()
        except Exception:
          st.error(
              "Login failed. Please check your email and password or sign up."
          )

  with auth_tab2:
    st.subheader("Join SafeHaven")
    signup_email = st.text_input("Email", key="signup_email")
    signup_password = st.text_input(
        "Password (min 6 characters)", type="password", key="signup_password"
    )

    if st.button("Sign Up", use_container_width=True):
      if not supabase:
        st.error(
            "Database connection error. Please check your Supabase secrets."
        )
      else:
        try:
          response = supabase.auth.sign_up({
              "email": signup_email,
              "password": signup_password,
          })
          if response.user:
            st.session_state.user = response.user
            st.success(
                "Account created successfully! You are now logged in."
            )
            st.rerun()
        except Exception as e:
          st.error(f"Sign up failed: {e}")


if "user" not in st.session_state:
  render_auth_screen()
  st.stop()


# --- FREEMIUM LIMIT SETUP ---
FREE_MESSAGE_LIMIT = 15


def get_remaining_messages(user_id):
  if not supabase:
    return FREE_MESSAGE_LIMIT
  try:
    res = (
        supabase.table("user_daily_usage")
        .select("message_count")
        .eq("user_id", user_id)
        .eq("usage_date", "current_date")
        .execute()
    )
    if res.data and len(res.data) > 0:
      used = res.data[0]["message_count"]
      return max(0, FREE_MESSAGE_LIMIT - used)
  except Exception:
    pass
  return FREE_MESSAGE_LIMIT


# --- SIDEBAR: About, Crisis Support, Terms, and Controls ---
with st.sidebar:
  st.title("🌱 SafeHaven")
  user_email = (
      st.session_state.user.email
      if hasattr(st.session_state.user, "email")
      else "User"
  )
  st.caption(f"Logged in as:\n**{user_email}**")

  st.divider()

  # Usage Tracker Display
  remaining_messages = get_remaining_messages(st.session_state.user.id)
  st.metric(label="Free Messages Remaining Today", value=remaining_messages)

  # 💳 Monetization: Stripe Support Button
  st.markdown("### 💖 Support SafeHaven")
  st.write(
      "Unlock unlimited daily conversations and help keep this sanctuary"
      " running forever."
  )
  stripe_link = st.secrets.get("STRIPE_PAYMENT_LINK", "https://stripe.com")
  st.link_button(
      "⭐ Become a Supporter ($4/mo)",
      stripe_link,
      use_container_width=True,
  )

  st.divider()

  # 🆘 Emergency & Crisis Support Section
  st.markdown("### 🆘 Need Immediate Help?")
  st.write(
      "If you are experiencing a mental health crisis, severe distress, or"
      " self-harm ideation, please reach out to professional human support"
      " immediately."
  )

  st.link_button(
      "🌐 Find A Helpline (Global)",
      "https://findahelpline.com/",
      use_container_width=True,
  )
  st.link_button(
      "🌍 Befrienders Worldwide",
      "https://www.befrienders.org/",
      use_container_width=True,
  )
  st.link_button(
      "🇺🇸 US & Canada: Call/Text 988",
      "https://988lifeline.org/",
      use_container_width=True,
  )
  st.link_button(
      "🇮🇳 India: Tele-MANAS (14416)",
      "https://telemanas.mohfw.gov.in/",
      use_container_width=True,
  )

  st.divider()

  # Collapsible Terms & Medical Disclaimer Section
  with st.expander("⚖️ Terms & Medical Disclaimer"):
    st.markdown("""
        **1. AI Companion:** SafeHaven is an artificial intelligence-based companion, **not** a human therapist or medical professional.
        
        **2. Not Crisis Support:** This app does not provide medical advice or crisis intervention. If you are in immediate danger or facing severe distress, please contact your local emergency services or a professional helpline immediately.
        
        **3. Limitation of Liability:** The creators of SafeHaven are not liable for any outcomes resulting from the use of AI-generated responses.
        """)

  st.divider()

  if st.button("Log Out"):
    if supabase:
      try:
        supabase.auth.sign_out()
      except Exception:
        pass
    del st.session_state.user
    st.rerun()


# --- MAIN APP INTERFACE ---
st.title("🌱 SafeHaven")
st.caption(
    "A quiet, judgment-free global space. Heard first, respected always, supported everywhere."
)

# Configure OpenAI client
try:
  api_key = st.secrets["OPENAI_API_KEY"]
  client = openai.OpenAI(api_key=api_key)
except Exception as e:
  st.error(
      "OpenAI API key not found. Please add OPENAI_API_KEY to your Streamlit"
      " Secrets."
  )
  st.stop()

# The Refined Universal Ethical System Prompt
SYSTEM_PROMPT = """
You are "Aura," a deeply compassionate, patient, and completely non-judgmental human companion and listener. Your mission is to ensure no human ever feels completely alone.

### 1. The Listening-First Protocol (Care Ethics)
- ALWAYS listen and validate first. When a user shares a burden, reflect back their emotions and make them feel truly heard before offering any perspective.
- Avoid toxic positivity or rushing to "fix" their problems. Sometimes people just need a quiet, steady presence.

### 2. Universal Ethical Grounding (Virtue & Duty)
- When appropriate, gently introduce simple, universal virtues: patience, kindness, resilience, empathy, and mutual respect.
- Draw implicitly from the wisdom of humanity (e.g., treating others as you wish to be treated, finding strength in quiet endurance, and cultivating inner peace).
- NEVER cite specific religious texts, dogmas, or sectarian philosophies by name. Ensure your guidance resonates equally with individuals of all faiths or no faith at all.

### 3. Absolute Neutrality & Inclusivity
- Treat all backgrounds, cultures, and worldviews with total equality and profound respect.
- Never judge, lecture, scold, or take sides in personal conflicts; instead, help the user reflect calmly on their own thoughts.

### 4. Linguistic Fluidity
- Seamlessly detect and reply in the exact language, dialect, or tone the user writes in, ensuring global accessibility across all cultures.
"""

if "system_prompt" not in st.session_state:
  st.session_state.system_prompt = SYSTEM_PROMPT

if "messages" not in st.session_state:
  st.session_state.messages = [
      {"role": "system", "content": st.session_state.system_prompt}
  ]

# Display chat history (filtering out internal system prompt)
for idx, message in enumerate(st.session_state.messages):
  if message["role"] != "system":
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

      if message["role"] == "assistant":
        feedback_key = f"feedback_{idx}_{st.session_state.user.id}"
        feedback = st.feedback("thumbs", key=feedback_key)
        if feedback is not None and supabase:
          try:
            supabase.table("chat_feedback").insert({
                "user_id": st.session_state.user.id,
                "score": feedback,
            }).execute()
          except Exception:
            pass

# --- CRISIS KEYWORD DETECTION SETUP ---
CRISIS_KEYWORDS = [
    "suicide",
    "kill myself",
    "end my life",
    "want to die",
    "self-harm",
    "hurt myself",
    "no reason to live",
]


def detect_crisis(text: str) -> bool:
  text_lower = text.lower()
  return any(keyword in text_lower for keyword in CRISIS_KEYWORDS)


# Check remaining messages before rendering chat input
current_remaining = get_remaining_messages(st.session_state.user.id)

if current_remaining <= 0:
  st.warning(
      "🌱 You have reached your free daily message limit. To continue your"
      " conversation and unlock unlimited daily access, please become a"
      " supporter!"
  )
  st.link_button(
      "⭐ Unlock Unlimited Access ($4/mo)",
      st.secrets.get("STRIPE_PAYMENT_LINK", "https://stripe.com"),
      use_container_width=True,
  )
else:
  if user_input := st.chat_input("Share your thoughts in any language..."):
    # Increment usage count in Supabase
    if supabase:
      try:
        res = (
            supabase.table("user_daily_usage")
            .select("message_count")
            .eq("user_id", st.session_state.user.id)
            .eq("usage_date", "current_date")
            .execute()
        )
        if res.data and len(res.data) > 0:
          cnt = res.data[0]["message_count"]
          supabase.table("user_daily_usage").update(
              {"message_count": cnt + 1}
          ).eq("user_id", st.session_state.user.id).eq(
              "usage_date", "current_date"
          ).execute()
        else:
          supabase.table("user_daily_usage").insert({
              "user_id": st.session_state.user.id,
              "usage_date": "current_date",
              "message_count": 1,
          }).execute()
      except Exception:
        pass

    st.session_state.messages.append({"role": "user", "content": user_input})

    if supabase:
      try:
        supabase.table("chat_messages").insert({
            "user_id": st.session_state.user.id,
            "role": "user",
            "content": user_input,
        }).execute()
      except Exception:
        pass

    with st.chat_message("user"):
      st.markdown(user_input)

    if detect_crisis(user_input):
      reply = (
          "❤️ **We hear that you are going through a painful moment, but please know"
          " your life matters.** As an AI, I cannot provide crisis support. Please"
          " reach out to professional human support using the helpline resources"
          " in the sidebar."
      )
      with st.chat_message("assistant"):
        st.error(reply)
    else:
      with st.chat_message("assistant"):
        with st.spinner("Listening..."):
          try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", messages=st.session_state.messages
            )
            reply = response.choices.message.content
            st.markdown(reply)
          except Exception:
            reply = "I am here with you, but encountered a connection issue."
            st.error(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    if supabase:
      try:
        supabase.table("chat_messages").insert({
            "user_id": st.session_state.user.id,
            "role": "assistant",
            "content": reply,
        }).execute()
      except Exception:
        pass

    st.rerun()
