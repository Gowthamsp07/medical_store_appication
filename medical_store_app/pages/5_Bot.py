import streamlit as st
import google.generativeai as genai
import sqlite3
import re
from datetime import datetime

# Configure Gemini API (replace with your actual API key)
genai.configure(api_key="AIzaSyCMwunuidzNth0tNu9smdJeo8M5NYfUQw4")

# Use Gemini 2.5 Flash for efficiency (or switch to 'gemini-2.5-pro' for more advanced reasoning)
model = genai.GenerativeModel('gemini-2.5-flash')

# Streamlit page configuration
st.set_page_config(page_title="Medical Store Bot", page_icon="🤖")
st.title("Medical Store Bot")
st.caption("Ask about inventory, stock details, expired medicines, or general queries about tablets/medicines. I'm here to help!")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
user_input = st.chat_input("Type your question here...")

if user_input:
    # Add user message to chat
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Connect to the database (assuming the table is named 'medicines' - adjust if different)
    conn = sqlite3.connect('Medical_Store.db')  # Adjust path if DB is in a different location

    # Database schema (adjust columns if your table differs)
    schema = """
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY,
        name TEXT,
        batch_no TEXT,
        quantity INTEGER,
        price_per_unit REAL,
        percent REAL,
        expiry_date DATE,
        brand_name TEXT
    );
    """

    # Current date for expiry checks
    current_date = datetime.now().date()

    # System prompt for Gemini to handle inventory vs. general queries
    system_prompt = f"""
    You are AI bot, witty, helpful, and accurate, assisting with a medical store inventory system.
    Be concise, engaging, and use humor where appropriate, but prioritize accuracy.
    The current date is {current_date}.

    Database schema:
    {schema}

    User questions can be:
    - About the store's inventory (e.g., "What's the stock of Aspirin?", "List expired medicines", "Expiry date of Insulin").
      For these, generate a SINGLE valid SQLite SQL query to fetch data from the 'medicines' table.
      Use date comparisons like expiry_date < '{current_date}' for expired items.
      Output the SQL in a markdown code block: ```sql\nYOUR_SQL_QUERY_HERE\n```
      Do not explain or add extra text yet - I'll handle the final response.

    - General questions about medicines (e.g., "What is Aspirin used for?", "Side effects of Metformin").
      Answer directly with accurate information. Cite sources if possible, but keep it simple and helpful.

    For mixed questions, generate SQL if inventory data is needed, then I'll provide results for you to incorporate.
    Handle follow-up questions based on context.
    Always ensure responses are safe and advise consulting a doctor for medical advice.
    """

    # Build chat history for context
    chat_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in st.session_state.messages[:-1]])
    full_prompt = system_prompt + "\n" + chat_history + "\nUser: " + user_input

    # Generate initial response from Gemini
    with st.spinner("Thinking..."):
        try:
            response = model.generate_content(full_prompt)
            ai_response = response.text

            # Check for SQL in the response
            sql_match = re.search(r'```sql\n(.*?)\n```', ai_response, re.DOTALL)
            if sql_match:
                sql_query = sql_match.group(1).strip()

                # Execute SQL
                try:
                    cur = conn.cursor()
                    cur.execute(sql_query)
                    results = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    result_str = "SQL Query Results:\nColumns: " + ", ".join(columns) + "\n"
                    if results:
                        result_str += "\n".join([str(row) for row in results])
                    else:
                        result_str += "No rows returned."
                except Exception as e:
                    result_str = f"Error executing SQL: {str(e)}"

                # Follow-up prompt to Gemini with results
                follow_up_prompt = f"""
                User question: {user_input}
                Chat history: {chat_history}
                Your initial thought: {ai_response}
                SQL execution result: {result_str}

                Now, generate a witty, helpful final response to the user.
                Incorporate the data accurately. Use tables or lists for clarity if needed.
                If no data, say so politely.
                End with a note: "Remember, for health advice, consult a professional."
                """
                final_response = model.generate_content(follow_up_prompt).text
            else:
                # No SQL needed - use the direct response
                final_response = ai_response + "\n\nRemember, for health advice, consult a professional."

        except Exception as e:
            final_response = f"Oops, something went wrong: {str(e)}. Try rephrasing your question!"

    # Close DB connection
    conn.close()

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(final_response)
    st.session_state.messages.append({"role": "assistant", "content": final_response})