import html
import io
import urllib.request
import pandas as pd
import streamlit as st
import folium
from folium import IFrame
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Ocean Data Sharing CoP Community Map",
    layout="wide"
)

st.title("Ocean Data Sharing CoP Global Community Map")

st.write(
    "Explore participating organisations and their ocean data sharing interests. "
    "Each marker represents an organisation that has consented to appear on the map."
)

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRMqzSM1yhQ2XRIBKhBfdLEBy_RvsPwAJU37HygysIbWti5qGI-EiloEAr2CkFrmcv2n6CuR00EPxkb/pub?gid=1112095258&single=true&output=csv"


def read_google_sheet_csv(url: str) -> pd.DataFrame:
    """
    Reads a published Google Sheet CSV without relying on fsspec.
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        csv_text = response.read().decode("utf-8")

    return pd.read_csv(io.StringIO(csv_text))


@st.cache_data(ttl=300)
def load_data(url: str) -> pd.DataFrame:
    df = read_google_sheet_csv(url)

    df.columns = [c.strip().lower() for c in df.columns]
    df = df.fillna("")

    required_columns = [
        "organisation",
        "city",
        "country",
        "latitude",
        "longitude",
        "organisation_type",
        "data_focus",
        "tools_used",
        "ai_interests",
        "public_profile",
        "website",
        "public_contact",
        "logo_url",
        "consent_map",
        "show_on_map",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        st.error("Your Google Sheet is missing some required columns.")
        st.write("Missing columns:")
        st.write(missing)
        st.write("Current columns found in your sheet:")
        st.write(list(df.columns))
        st.stop()

    df = df[
        (df["consent_map"].astype(str).str.lower().str.strip() == "yes")
        & (df["show_on_map"].astype(str).str.lower().str.strip() == "yes")
    ]

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df.dropna(subset=["latitude", "longitude"])

    return df


st.sidebar.header("Data source")

data_source = st.sidebar.radio(
    "Choose data source",
    ["Google Sheet", "Upload CSV manually"]
)

data = None

if data_source == "Google Sheet":
    try:
        data = load_data(SHEET_CSV_URL)
        st.sidebar.success("Connected to Google Sheet")
    except Exception as e:
        st.error("The app could not connect to the Google Sheet.")
        st.write("This usually means one of three things:")
        st.write("1. The Google Sheet is not properly published as a CSV.")
        st.write("2. Your internet/work network is blocking the connection.")
        st.write("3. The link is temporarily unavailable.")
        st.write("Technical error:")
        st.code(str(e))

        st.info("Use the manual CSV upload option in the sidebar as a backup.")
        st.stop()

else:
    uploaded_file = st.sidebar.file_uploader("Upload your Map_Data CSV", type=["csv"])

    if uploaded_file is None:
        st.warning("Please upload a CSV file to display the map.")
        st.stop()

    data = pd.read_csv(uploaded_file)
    data.columns = [c.strip().lower() for c in data.columns]
    data = data.fillna("")

    data = data[
        (data["consent_map"].astype(str).str.lower().str.strip() == "yes")
        & (data["show_on_map"].astype(str).str.lower().str.strip() == "yes")
    ]

    data["latitude"] = pd.to_numeric(data["latitude"], errors="coerce")
    data["longitude"] = pd.to_numeric(data["longitude"], errors="coerce")
    data = data.dropna(subset=["latitude", "longitude"])


if data.empty:
    st.warning("No approved organisations are currently available to display.")
    st.write(
        "Check that your sheet has rows where `consent_map` is `Yes`, "
        "`show_on_map` is `Yes`, and latitude/longitude values are filled in."
    )
    st.stop()


st.sidebar.header("Filter map")

organisation_types = sorted(data["organisation_type"].dropna().unique())

selected_types = st.sidebar.multiselect(
    "Organisation type",
    organisation_types,
    default=organisation_types
)

filtered = data[data["organisation_type"].isin(selected_types)]

st.subheader("Interactive global community map")

m = folium.Map(
    location=[20, 0],
    zoom_start=2,
    tiles="OpenStreetMap"
)

for _, row in filtered.iterrows():
    organisation = html.escape(str(row["organisation"]))
    city = html.escape(str(row["city"]))
    country = html.escape(str(row["country"]))
    organisation_type = html.escape(str(row["organisation_type"]))
    data_focus = html.escape(str(row["data_focus"]))
    tools_used = html.escape(str(row["tools_used"]))
    ai_interests = html.escape(str(row["ai_interests"]))
    public_profile = html.escape(str(row["public_profile"]))
    website = html.escape(str(row["website"]))
    public_contact = html.escape(str(row["public_contact"]))
    logo_url = str(row["logo_url"]).strip()

    logo_html = ""

    if logo_url.startswith("http"):
        logo_html = f"""
        <div style="margin-bottom:10px;">
            <img src="{html.escape(logo_url)}" style="max-width:120px; max-height:80px;">
        </div>
        """

    website_html = ""

    if website.startswith("http"):
        website_html = f"""
        <p>
            <b>Website:</b>
            <a href="{website}" target="_blank">Open link</a>
        </p>
        """

    contact_html = ""

    if public_contact:
        contact_html = f"""
        <p>
            <b>Public contact:</b> {public_contact}
        </p>
        """

    popup_html = f"""
    <div style="font-family: Arial; font-size: 13px; width: 300px;">
        {logo_html}
        <h4>{organisation}</h4>
        <p><b>Location:</b> {city}, {country}</p>
        <p><b>Organisation type:</b> {organisation_type}</p>
        <p><b>Data focus:</b> {data_focus}</p>
        <p><b>Tools/platforms used:</b> {tools_used}</p>
        <p><b>AI/data-sharing interests:</b> {ai_interests}</p>
        <p><b>Profile:</b> {public_profile}</p>
        {website_html}
        {contact_html}
    </div>
    """

    iframe = IFrame(popup_html, width=340, height=430)
    popup = folium.Popup(iframe, max_width=360)

    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        popup=popup,
        tooltip=organisation,
        icon=folium.Icon(icon="info-sign")
    ).add_to(m)


st_folium(m, width=1200, height=650)

st.caption(
    "Prototype map. Only organisations that consented to appear on the map are displayed."
)

st.subheader("Community directory")

display_columns = [
    "organisation",
    "city",
    "country",
    "organisation_type",
    "data_focus",
    "tools_used",
    "ai_interests",
    "website",
]

st.dataframe(
    filtered[display_columns],
    use_container_width=True
)