import streamlit as st
import requests
import json
import pandas as pd 
import time

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

st.text_area(
    label="Describe your peak moment. Feel free to write a couple of paragraphs to explain what was the situation, what actions you took and how the result made you feel",
    height=250,
    key="user_story"
)

if st.button("Analyze My Story", type="primary"):
    if st.session_state.user_story:
        with st.spinner("Contacting agent... This may take a moment."):
            try:
                # Step 1: Trigger Agent 1
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

                # Step 2: Poll for Agent 1 Results
                poll_endpoint = f"https://api-{region}.stack.tryrelevance.com/latest/studios/{studio_id}/async_poll/{job_id}"
                final_result = None

                for i in range(20):
                    status_response = requests.get(poll_endpoint, headers=headers)
                    status_response.raise_for_status()
                    status_data = status_response.json()

                    for update in status_data.get("updates", []):
                        if update.get("type") == "chain-success":
                            try:
                                answer_string = update["output"]["output"]["answer"]
                                start = answer_string.find('{')
                                end = answer_string.rfind('}') + 1
                                json_string = answer_string[start:end]
                                final_result = json.loads(json_string)
                            except (KeyError, json.JSONDecodeError):
                                final_result = {}
                            break
                    
                    if final_result is not None:
                        break
                    time.sleep(1)

                # Step 3: Process Agent 1 Result
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
    
    st.multiselect(
        label="Select your top 3-5 values:",
        options=sorted(list(all_values)),
        key="selected_values"
    )

    if st.button("Generate Mission Statements", type="primary"):
        if 3 <= len(st.session_state.selected_values) <= 5:
            with st.spinner("Crafting your mission statements... This may take a moment."):
                try:
                    # Step 1: Trigger Agent 2
                    region = st.secrets["RELEVANCE_REGION"]
                    auth_token = f"{st.secrets['RELEVANCE_PROJECT_ID']}:{st.secrets['RELEVANCE_API_KEY']}"
                    agent_id = st.secrets["RELEVANCE_AGENT_ID_WRITER"]
                    
                    trigger_endpoint = f"https://api-{region}.stack.tryrelevance.com/latest/agents/trigger"
                    headers = {"Authorization": auth_token, "Content-Type": "application/json"}
                    
                    content_string = ", ".join(st.session_state.selected_values)
                    payload = {"agent_id": agent_id, "message": {"role": "user", "content": content_string}}

                    trigger_response = requests.post(trigger_endpoint, headers=headers, data=json.dumps(payload))
                    trigger_response.raise_for_status()
                    
                    job = trigger_response.json()
                    studio_id = job["job_info"]["studio_id"]
                    job_id = job["job_info"]["job_id"]

                    # Step 2: Poll for Agent 2 Results
                    poll_endpoint = f"https://api-{region}.stack.tryrelevance.com/latest/studios/{studio_id}/async_poll/{job_id}"
                    final_result = None

                    for i in range(20):
                        status_response = requests.get(poll_endpoint, headers=headers)
                        status_response.raise_for_status()
                        status_data = status_response.json()

                        for update in status_data.get("updates", []):
                            if update.get("type") == "chain-success":
                                try:
                                    answer_string = update["output"]["output"]["answer"]
                                    start = answer_string.find('{')
                                    end = answer_string.rfind('}') + 1
                                    json_string = answer_string[start:end]
                                    final_result = json.loads(json_string)
                                except (KeyError, json.JSONDecodeError):
                                    final_result = {}
                                break
                        
                        if final_result is not None:
                            break
                        time.sleep(1)

                    # Step 3: Process Agent 2 Result
                    if final_result and "statements" in final_result:
                        st.session_state.mission_statements = final_result
                        st.success("Drafts complete!")
                    elif final_result is not None:
                        st.error("The agent completed but returned an unexpected format.")
                        st.json(final_result)
                    else:
                        st.error("The agent took too long to respond. Please try again later.")

                except requests.exceptions.RequestException as e:
                    st.error(f"An error occurred with the API request: {e}")
        else:
            st.warning("Please select between 3 and 5 values to continue.")

# --- STAGE 3: DISPLAY MISSION STATEMENTS ---
if st.session_state.mission_statements:
    st.subheader("Step 3: Draft Your Mission Statement")
    st.markdown("Different cultures tend to lean towards different ends for the concept of Internal vs. External locus of control. Here are two distinct drafts based on your values. Use them as a starting point to craft a statement that feels authentic to you.")
    
    for statement in st.session_state.mission_statements["statements"]:
        st.markdown(f"#### {statement['type']}")
        st.info(statement['text'])