import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
from dotenv import load_dotenv
import streamlit as st
from evaluation.qwen_path import _get_client, live_qwen
from neo4j import GraphDatabase

load_dotenv() 
st.set_page_config(page_title="Mirror in the Library", page_icon="📚", layout="centered")

@st.cache_resource
def get_neo4j_driver():
    neo4j_pass = os.getenv("NEO4J_PASSWORD", "bishowhero") 
    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", neo4j_pass))

if "character" not in st.session_state:
    st.session_state.character = None
if "messages" not in st.session_state:
    st.session_state.messages = []

CHARACTERS = {
    "Warm Friend": {"img": "🫂", "desc": "Gentle, validating.", "color": "#FFB6C1", "prompt": "You are a warm, empathetic friend. Validate their feelings gently. First, quote the matched passage exactly. Then, speak to them like a close friend."},
    "Wise Stoic": {"img": "🏛️", "desc": "Grounded, philosophical.", "color": "#A9C2D9", "prompt": "You are a wise Stoic philosopher. First, quote the matched passage exactly. Then, speak to them like Marcus Aurelius—calm, rational, and focused on virtue."},
    "Witty Librarian": {"img": "🦉", "desc": "Clever, eccentric.", "color": "#D4B8A8", "prompt": "You are a witty, slightly eccentric librarian. First, quote the matched passage exactly. Then, speak to them like you've been waiting in a dusty library just to hand them this exact book."}
}

active_color = CHARACTERS[st.session_state.character]["color"] if st.session_state.character else "#808080"

st.markdown(f"""
    <style>
    /* Change the chat input to be bigger and highly visible */
    .stChatInput textarea {{
        min-height: 100px !important;
        font-size: 1.1rem !important;
        background-color: #f0f2f6 !important; /* Light gray background */
        color: #000000 !important;            /* Black text */
        border: 2px solid {active_color} !important; /* Border matches character */
    }}
    
    /* Change accent colors (buttons) */
    .stButton>button {{
        background-color: {active_color} !important;
        color: black !important;
        font-weight: bold;
        border: none;
    }}
    
    /* Loading dots animation */
    .typing-indicator {{
        display: inline-block;
        width: 20px;
        text-align: left;
    }}
    .typing-indicator::after {{
        content: '...';
        animation: blink 1.4s infinite both;
        font-size: 24px;
        color: {active_color};
    }}
    @keyframes blink {{
        0% {{ opacity: 0.2; }}
        20% {{ opacity: 1; }}
        100% {{ opacity: 0.2; }}
    }}
    </style>
""", unsafe_allow_html=True)

if st.session_state.character is None:
    st.title("📚 Mirror in the Library")
    st.write("Welcome. Before we begin, who would you like to talk to today?")
    
    cols = st.columns(3)
    for i, (name, data) in enumerate(CHARACTERS.items()):
        with cols[i]:
            st.markdown(f"<h1 style='text-align: center; font-size: 60px;'>{data['img']}</h1>", unsafe_allow_html=True)
            st.markdown(f"**{name}**")
            st.caption(data['desc'])
            if st.button(f"Choose {name}", key=name):
                st.session_state.character = name
                st.rerun()

else:
    char_info = CHARACTERS[st.session_state.character]
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### {char_info['img']} Talking to: {st.session_state.character}")
    with col2:
        if st.button("Change"):
            st.session_state.character = None
            st.session_state.messages = []
            st.rerun()

    st.write("---")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input(f"Talk to your {st.session_state.character}..."):
        
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            loading_placeholder = st.empty()
            loading_placeholder.markdown("<div class='typing-indicator'></div>", unsafe_allow_html=True)
            
            pred = live_qwen(user_input)
                        # --- SAVE TO PERSONAL KNOWLEDGE GRAPH ---
            driver = get_neo4j_driver()
            with driver.session() as session:
                # 1. Create a CheckIn node and link it to the User
                session.run("""
                    MERGE (u:User {name: "Bishow"})
                    CREATE (c:CheckIn {text: $text, date: datetime()})
                    CREATE (u)-[:MADE_CHECKIN]->(c)
                """, text=user_input)
                
                # 2. Link the detected emotions to this CheckIn
                for emo in pred.emotions:
                    session.run("""
                        MATCH (c:CheckIn {text: $text})
                        MERGE (e:Emotion {name: $emo_name})
                        MERGE (c)-[:FELT]->(e)
                    """, text=user_input, emo_name=emo.label)
            # --- NEO4J GRAPH MATCHING ---
            driver = get_neo4j_driver()
            top_emotion = pred.emotions[0].label if pred.emotions else "unknown"
            
            with driver.session() as session:
                result = session.run("""
                    MATCH (p:Passage)-[:EXPRESSES]->(e:Emotion {name: $emo})
                    MATCH (b:Book)-[:CONTAINS]->(p)
                    RETURN p.text AS text, b.title AS book
                    LIMIT 1
                """, emo=top_emotion).single()
                
                if result:
                    passage_text = result["text"]
                    passage_book = result["book"]
                else:
                    passage_text = "No exact match found in the library."
                    passage_book = "The Library"

            # --- GENERATE PERSONA RESPONSE ---
            system_prompt = f"""
            {char_info['prompt']}
            
            The user said: "{user_input}"
            The AI detected their emotions as: {[e.label for e in pred.emotions]}.
            The matched literary passage from the Knowledge Graph is: "{passage_text}" from {passage_book}.
            
            Format your response exactly like this:
            > "{passage_text}"
            — *{passage_book}*
            
            [Your persona's reply to the user here, humanized and speaking directly to their emotion.]
            """

            client = _get_client()
            response = client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.8
            )
            
            ai_text = response.choices[0].message.content
            
            loading_placeholder.empty()
            st.markdown(ai_text)
            st.session_state.messages.append({"role": "assistant", "content": ai_text})