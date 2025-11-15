import base64
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from streamlit_arborist import tree_view
from urllib.parse import quote

USERNAME = st.secrets.github.USERNAME
REPO = st.secrets.data.REPO
BRANCH = st.secrets.github.BRANCH
ROOT_FOLDER = st.secrets.github.ROOT_FOLDER
TOKEN = st.secrets.github.TOKEN
HEADERS = {"Authorization": f"token {TOKEN}"}

@st.cache_data

def fetch_dataframe(file_path):
    api_url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/{quote(file_path)}?ref={BRANCH}"
    response = requests.get(api_url, headers=HEADERS)

    if response.status_code != 200:
        st.error(f"Failed to fetch {file_path}: {response.status_code}")
        return pd.DataFrame()

    try:
        data = response.json()
    except Exception as e:
        st.error(f"Failed to parse JSON from {file_path}: {e}")
        return pd.DataFrame()

    if "content" not in data:
        st.error(f"No content field found in {file_path}")
        return pd.DataFrame()

    try:
        decoded = base64.b64decode(data["content"]).decode("utf-8")
        if file_path.endswith(".csv"):
            return pd.read_csv(pd.io.common.StringIO(decoded))
        elif file_path.endswith(".json"):
            return pd.read_json(pd.io.common.StringIO(decoded))
        else:
            st.error(f"Unsupported file type: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error decoding {file_path}: {e}")
        return pd.DataFrame()


df_anime = fetch_dataframe("data/anime.csv")
df_procrastination = fetch_dataframe("data/procrastination.csv")
df_youtube = fetch_dataframe("data/youtube.csv")
df_deadlines = fetch_dataframe("data/deadlines.csv")

st.set_page_config(page_title="My Autobiography")

with st.container():
    st.title("Hi, I'm Jive!")
    st.markdown(
        """
        A developer, knowledge hoarder, and lifelong procrastinator trying to turn chaos into craft. 
        I enjoy learning how things work from algorithms and automation, to anime arcs and the odd rabbit holes of YouTube at 2 AM.
        """
    )
    st.write(
        """
        #### This autobiography is a small digital museum of the things that shape me:
        - the notes I archived  
        - the shows and streams I disappear into  
        - the stories I read obsessively
        - and deadlines I ignore  
        
        Welcome to my corner of the internet.
        """
    )

with st.container(border=True):
    st.subheader("Procrastination Graph")
    df_procrastination["Date"] = pd.to_datetime(df_procrastination["Date"])

    timeframe = st.segmented_control("Interval", options=["Week", "Month", "Year"])

    if timeframe == "Week":
        df_grouped = df_procrastination.sort_values("Date").copy()  # daily data
        tick_format = "%Y-%m-%d"
        title = "Daily Procrastination (Past 2 Weeks)"

    elif timeframe == "Month":
        df_grouped = df_procrastination.resample("ME", on="Date")['Hours Procrastinated'].sum().reset_index()
        tick_format = "%b %Y"
        title = "Monthly Procrastination"

    else:  # Year
        df_grouped = df_procrastination.resample("YE", on="Date")['Hours Procrastinated'].sum().reset_index()
        tick_format = "%Y"
        title = "Yearly Procrastination"

    fig = px.line(
        df_grouped,
        x="Date",
        y="Hours Procrastinated",
        markers=True,
        title=title
    )
    fig.update_layout(xaxis_tickformat=tick_format)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_grouped)


with st.container(border=True):
    st.subheader("Recently Watched Anime 🍥")
    st.dataframe(df_anime)

with st.container(border=True):
    st.subheader("Recently Watched YouTube Videos")
    st.dataframe(df_youtube)

with st.container(border=True):
    st.subheader("Deadlines")
    df_deadlines["deadline"] = pd.to_datetime(df_deadlines["deadline"])
    today = datetime.today().date()
    st.dataframe(df_deadlines)
    for _, row in df_deadlines.iterrows():
        with st.expander(row["task"]):
            st.write(f"Deadline: {row['deadline'].strftime('%Y-%m-%d')}")
            days_left = (row["deadline"].date() - today).days
            if days_left <= 0:
                progress_value = 1.0
            elif days_left > 30:
                progress_value = 0.0
            else:
                progress_value = (30 - days_left) / 30
            st.progress(progress_value)
            st.write(f"{max(0, days_left)} days left")

@st.cache_data
def list_folder(path=""):
    api_url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/{quote(path)}?ref={BRANCH}"
    response = requests.get(api_url, headers=HEADERS)
    if response.status_code != 200:
        st.error(f"Failed to fetch {path}: {response.status_code}")
        return []
    return response.json()

@st.cache_data
def build_tree(path=ROOT_FOLDER):
    tree = []
    contents = list_folder(path)
    for item in contents:
        if item["name"] == ".obsidian":
            continue
        item_path = item["path"]
        if item["type"] == "dir":
            tree.append({"id": item_path, "name": item["name"], "children": build_tree(item_path)})
        elif item["type"] == "file" and item["name"].endswith(".md"):
            tree.append({"id": item_path, "name": item["name"], "path": item_path})
    return tree

@st.cache_data
def fetch_note_content(file_path):
    api_url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/{quote(file_path)}?ref={BRANCH}"
    response = requests.get(api_url, headers=HEADERS).json()
    if "content" not in response:
        return "Could not fetch note content."
    try:
        decoded = base64.b64decode(response["content"]).decode("utf-8")
        return decoded
    except Exception as e:
        return f"Error decoding file: {e}"

REPO = st.secrets.github.REPO

st.subheader("Jive's Notes")
st.write("Notes are synced to my Github notes repository")
tree_data = build_tree(ROOT_FOLDER)

with st.expander(label="Obsidian Notes Explorer"):
    tree_selection = tree_view(
        tree_data,
        icons={'open': ':material/keyboard_arrow_down:', 'closed': ':material/keyboard_arrow_right:', 'leaf': ''},
        open_by_default=False,
        padding=10
    )

selected_path = None
if tree_selection and tree_selection.get("selected"):
    selected_id = tree_selection["selected"][0]
    if selected_id.endswith(".md"):
        selected_path = selected_id

with st.container(border=True):
    if tree_selection:
        note_content = fetch_note_content(tree_selection["path"])
        st.subheader(note_content)
        st.markdown(note_content, unsafe_allow_html=True)
    else:
        st.info("Select a note from the tree to view its content.")
