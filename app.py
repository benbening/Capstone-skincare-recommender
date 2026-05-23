import streamlit as st
import pandas as pd
import random
import time

# =====================
# PAGE CONFIG
# =====================

st.set_page_config(
    page_title="Skincare Recommendation",
    layout="wide"
)

# =====================
# DUMMY DATA
# =====================

data = {
    "product_name": [
        "Acne Serum",
        "Hydrating Toner",
        "Brightening Serum",
        "Gentle Cleanser",
        "UV Shield Sunscreen"
    ],

    "brand": [
        "SkinLab",
        "Glow Beauty",
        "Lumi Skin",
        "Pure Face",
        "SunCare"
    ],

    "ingredients": [
        "niacinamide salicylic acid",
        "hyaluronic acid centella",
        "vitamin c ascorbic acid",
        "ceramide glycerin",
        "zinc oxide niacinamide"
    ],

    "price": [
        120000,
        85000,
        140000,
        70000,
        95000
    ],

    "type": [
        "Serum",
        "Toner",
        "Serum",
        "Cleanser",
        "Sunscreen"
    ]
}

df = pd.DataFrame(data)

# =====================
# CUSTOM CSS
# =====================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #fdf6f0;
    }

    h1, h2, h3 {
        color: #8b6f5c;
        font-family: 'Poppins', sans-serif;
    }

    p, label, div {
        color: #5f4b3a;
        font-family: 'Poppins', sans-serif;
    }

    section[data-testid="stSidebar"] {
        background-color: #f7e7dc;
    }

    /* SELECTBOX */
    div[data-baseweb="select"] > div {
        background-color: #fff0f5 !important;
        color: #5f4b3a !important;
        border-radius: 12px !important;
        border: 1px solid #f0cfd8 !important;
    }

    /* INPUT TEXT */
    .stTextInput input {
        background-color: #fff0f5 !important;
        color: #5f4b3a !important;
        border-radius: 12px !important;
        border: 1px solid #f0cfd8 !important;
    }

    /* DROPDOWN MENU */
    div[data-baseweb="popover"] {
        background-color: #fff0f5 !important;
        color: #5f4b3a !important;
    }

        /* DROPDOWN OPTION MENU */
    ul {
        background-color: #fff0f5 !important;
    }

    /* OPTION ITEM */
    li {
        background-color: #fff0f5 !important;
        color: #5f4b3a !important;
    }

    /* HOVER OPTION */
    li:hover {
        background-color: #f7dce5 !important;
        color: #5f4b3a !important;
    }
    
        /* DROPDOWN POPUP */
    div[data-baseweb="popover"] {
        background-color: #fff0f5 !important;
        color: #5f4b3a !important;
    }

    .stButton>button {
        background-color: #d8b4a0;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }

    .stButton>button:hover {
        background-color: #c89b85;
    }

    div[data-testid="metric-container"] {
        background-color: #fff5ee;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #f0d9ce;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# HEADER
# =====================

st.title("SkinMatch Recommendation")
st.write("Content-Based Filtering + Budget & Allergy Optimization")

# =====================
# SIDEBAR
# =====================

st.sidebar.header("Skin Quiz")

skin_concern = st.sidebar.multiselect(
    "Skin Concern",
    [
        "Jerawat",
        "Kulit Kering",
        "Kulit Kusam",
        "Minyak Berlebih",
        "Skin Barrier"
    ]
)

allergy = st.sidebar.text_input(
    "Allergy Ingredients",
    placeholder="contoh: alcohol"
)

budget = st.sidebar.slider(
    "Budget",
    50000,
    500000,
    200000,
    step=50000,
    format="Rp %d"
)

routine = st.sidebar.selectbox(
    "Routine",
    ["AM", "PM"]
)

submit = st.sidebar.button("Generate Recommendation")

# =====================
# RECOMMENDATION
# =====================

if submit:

    with st.spinner("Analyzing your skin profile..."):
        time.sleep(2)

    st.success("Recommendation Generated Successfully!")

    # FILTER BUDGET
    filtered_df = df[df["price"] <= budget]

    # FILTER ALLERGY
    if allergy:
        filtered_df = filtered_df[
            ~filtered_df["ingredients"]
            .str.lower()
            .str.contains(allergy.lower())
        ]

    if filtered_df.empty:

        st.warning(
            "Tidak ada produk yang cocok. Coba naikkan budget atau kurangi filter alergi."
        )

    else:

        st.header(f"✨ {routine} Routine Recommendation")

        for _, row in filtered_df.iterrows():

            score = random.randint(80, 98)

            with st.container(border=True):

                col1, col2 = st.columns([3,1])

                with col1:

                    st.subheader(row["product_name"])

                    st.write(f"Brand: {row['brand']}")
                    st.write(f"Type: {row['type']}")
                    st.write(f"Ingredients: {row['ingredients']}")

                    # FAKE AI REASONING
                    if "Jerawat" in skin_concern:
                        st.info(
                            "Recommended because it contains acne-control ingredients."
                        )

                    elif "Kulit Kering" in skin_concern:
                        st.info(
                            "Recommended because it helps hydrate the skin."
                        )

                    else:
                        st.info(
                            "Recommended based on your skin profile."
                        )

                with col2:

                    st.metric(
                        "Match Score",
                        f"{score}%"
                    )

                    st.success(
                        f"Rp {row['price']:,}"
                    )

                    st.progress(score)
