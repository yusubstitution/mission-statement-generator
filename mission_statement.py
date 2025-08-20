import requests
import json
import streamlit as st
import pandas as pd 
import time

# --- MOCK API DATA (PLACEHOLDERS) ---
# This simulates the JSON response from your "Values Identifier" agent
mock_analysis_response = {
    "analysis": [
        { "behavior": "Brought misaligned teams together for a workshop.", "values": ["Proactive", "Leadership", "Initiative"] },
        { "behavior": "Facilitated to ensure everyone felt heard.", "values": ["Empathetic", "Fair", "Objective"] },
        { "behavior": "Mapped out dependencies on a whiteboard.", "values": ["Thoughtful", "Analytical", "Clarity"] },
        { "behavior": "Created a new, integrated plan everyone liked.", "values": ["Collaborative", "Unifying", "Constructive"] },
        { "behavior": "Stepped into a high-tension situation.", "values": ["Brave", "Responsible", "Committed"] }
    ]
}

# This simulates the JSON response from your "Mission Statement Writer" agent
mock_statements_response = {
    "statements": [
        { "type": "Internal-Focused", "text": "My mission is to apply relentless rigor to every question, driven by a deep curiosity. I hold myself accountable for the quality of my work and aim to master my craft." },
        { "type": "Contextual", "text": "I strive to create environments where collaboration thrives, fueled by a genuine curiosity about the perspectives of others. My goal is to be a catalyst for our shared success." }
    ]
}

# --- SESSION STATE INITIALIZATION ---
if "user_story" not in st.session_state:
    st.session_state.user_story = ""
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "selected_values" not in st.session_state:
    st.session_state.selected_values = []
if "mission_statements" not in st.session_state:
    st.session_state.mission_statements = None

# --- UI LAYOUT ---
st.title("Personal Mission Statement Generator")

# --- STAGE 1: CAPTURE USER STORY ---
st.subheader("Step 1: Reflect on a Peak Moment")
st.markdown(
    'Your personal mission statement is about who you want to be and how you want to act. '
    'To start, recall a specific project, day, or interaction that made you feel, "This is why I do what I do."'
)

personal_story = st.text_area(
    label="Describe your peak moment. What was the situation? What actions did you take? What was your impact?",
    height=250,
    key="user_story"
)

# --- Call Relevance AI Agent using API
if st.button("Analyze My Story", type="primary"):
    if st.session_state.user_story:
        with st.spinner("Contacting agent... This may take a moment."):
            try:
                # --- Step 1: Trigger the Agent ---
                region = st.secrets["RELEVANCE_REGION"]
                auth_token = f"{st.secrets['RELEVANCE_PROJECT_ID']}:{st.secrets['RELEVANCE_API_KEY']}"
                agent_id = st.secrets["RELEVANCE_AGENT_ID_VALUES"]
                
                trigger_endpoint = f"https://api-{region}.stack.tryrelevance.com/latest/agents/trigger"
                headers = {"Authorization": auth_token, "Content-Type": "application/json"}
                payload = {"agent_id": agent_id, "message": {"role": "user", "content": st.session_state.user_story}}

                trigger_response = requests.post(trigger_endpoint, headers=headers, data=json.dumps(payload))
                trigger_response.raise_for_status()
                
                job = trigger_response.json()
                studio_id = job["job_info"]["studio_id"]
                job_id = job["job_info"]["job_id"]

                # --- Step 2: Poll for the Results ---
                poll_endpoint = f"https://api-{region}.stack.tryrelevance.com/latest/studios/{studio_id}/async_poll/{job_id}"
                final_result = None

                for i in range(20):
                    status_response = requests.get(poll_endpoint, headers=headers)
                    status_response.raise_for_status()
                    status_data = status_response.json()

                    for update in status_data.get("updates", []):
                        if update.get("type") == "chain-success":
                            try:
                                # 1. Navigate the nested structure to find the answer string
                                answer_string = update["output"]["output"]["answer"]
                                
                                # 2. Clean the string to remove markdown fences and get pure JSON
                                start = answer_string.find('{')
                                end = answer_string.rfind('}') + 1
                                json_string = answer_string[start:end]
                                
                                # 3. Parse the cleaned string into a dictionary
                                final_result = json.loads(json_string)

                            except (KeyError, json.JSONDecodeError):
                                st.error("Found the success message, but failed to parse the final JSON.")
                                final_result = {} # Ensure loop breaks
                            break
                    
                    if final_result is not None:
                        break
                    
                    time.sleep(1)

                # --- Step 3: Process the final result ---
                if final_result and "analysis" in final_result:
                    st.session_state.analysis_results = final_result
                    st.success("Analysis complete!")
                elif final_result is not None:
                    st.error("The agent completed but returned an unexpected format.")
                    st.json(final_result)
                else:
                    st.error("The agent took too long to respond. Please try again later.")

            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred with the API request: {e}")
    else:
        st.warning("Please describe your moment before continuing.")

# --- STAGE 2: DISPLAY VALUES & GET SELECTION ---
if st.session_state.analysis_results:
    st.subheader("Step 2: Identify Your Core Values")
    st.markdown("Here are the behaviors and potential values extracted from your story. This helps reveal the qualities you demonstrate when you're at your best.")

    df = pd.DataFrame(st.session_state.analysis_results["analysis"])
    df['values'] = df['values'].apply(lambda x: ', '.join(x))
    st.table(df)

    all_values = set()
    for item in st.session_state.analysis_results["analysis"]:
        all_values.update(item["values"])

    st.markdown("From the list of potential values, select the **3 to 5** that resonate most with you.")
    
    st.session_state.selected_values = st.multiselect(
        label="Select your top 3-5 values:",
        options=sorted(list(all_values)),
        key="value_selection"
    )

    # This button is now correctly nested, so it will only appear with the multiselect.
    if st.button("Generate Mission Statements", type="primary"):
        if 3 <= len(st.session_state.selected_values) <= 5:
            # (Your API call logic for Agent 2 goes here)
            with st.spinner("Crafting your mission statements... This may take a moment."):
                # ... existing Agent 2 API call code ...
        else:
            st.warning("Please select between 3 and 5 values to continue.")

# --- STAGE 3: DISPLAY MISSION STATEMENTS ---
# This block remains at the top level.
if st.session_state.mission_statements:
    st.subheader("Step 3: Draft Your Mission Statement")
    st.markdown("Here are two distinct drafts based on your values. Use them as a starting point to craft a statement that feels authentic to you.")
    
    for statement in st.session_state.mission_statements["statements"]:
        st.markdown(f"#### {statement['type']}")
        st.info(statement['text'])