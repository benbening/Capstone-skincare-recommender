from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
import pickle
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

from nltk.corpus import stopwords


# FASTAPI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LOAD DATA

df = pd.read_pickle("df_final.pkl")

with open("semantic_matrix.pkl", "rb") as f:
    semantic_matrix = pickle.load(f)

model = SentenceTransformer("./skincare_custom_model")

# STOPWORDS

stop_words = set(
    stopwords.words('indonesian') +
    stopwords.words('english')
)

custom_stopwords = {
    'aqua',
    'water',
    'ekstrak',
    'extract',
    'dan',
    'yang',
    'untuk',
    'dengan'
}

stop_words.update(custom_stopwords)

# REQUEST BODY

class UserInput(BaseModel):
    skin_text: str

# TEXT CLEANING

def advanced_clean_text(text):

    text = re.sub(
        r'[^a-zA-Z0-9 ]',
        '',
        str(text)
    )

    words = text.lower().split()

    cleaned_words = [
        w for w in words
        if w not in stop_words
    ]

    return ' '.join(cleaned_words)

# INTENT DETECTION

def extract_product_intent(user_text):

    user_text = user_text.lower()

    allowed_types = [
        'cleanser',
        'toner',
        'serum',
        'moisturizer',
        'sunscreen'
    ]

    for p_type in allowed_types:

        if p_type in user_text:
            return p_type

    return None

# DYNAMIC REASON

def generate_dynamic_reason(user_text, product_desc):

    user_words = [
        word.lower()
        for word in user_text.split()
        if len(word) > 3
    ]

    claims = [
        claim.strip()
        for claim in str(product_desc).split(',')
    ]

    matched_claims = []

    for claim in claims:

        if any(
            uw in claim.lower()
            for uw in user_words
        ):

            matched_claims.append(
                claim.capitalize()
            )

    if matched_claims:

        return (
            f"Produk ini cocok karena "
            f"{', '.join(matched_claims)}."
        )

    return (
        "Produk ini memiliki kecocokan "
        "semantik yang tinggi dengan "
        "kebutuhan kulit pengguna."
    )

# HOME

@app.get("/")
def home():

    return {
        "message": "Advanced Skincare API Running"
    }

# RECOMMENDATION API

@app.post("/recommend")
def recommend(data: UserInput):

    user_input = advanced_clean_text(
        data.skin_text
    )

    df_test = df.copy()

    # INTENT DETECTION

    intent = extract_product_intent(user_input)

    if intent:

        df_test['safe_type'] = (
            df_test['product_type']
            .astype(str)
            .str.lower()
            .str.strip()
        )

        df_test = df_test[
            df_test['safe_type'] == intent
        ]

        if df_test.empty:

            return {
                "status": "error",
                "message": f"Tidak ada produk {intent}"
            }

    # SEMANTIC SIMILARITY

    row_positions = [
        df.index.get_loc(idx)
        for idx in df_test.index
    ]

    user_vector = model.encode([user_input])

    similarity_scores = cosine_similarity(
        user_vector,
        semantic_matrix[row_positions]
    ).flatten()

    df_test['sim_score'] = similarity_scores

    # OOD DETECTION
    
    max_sim = df_test['sim_score'].max()

    if max_sim < 0.25:

        return {
            "status": "rejected",
            "message":
                "Input tidak relevan dengan skincare"
        }

    # HYBRID SCORE
   
    scaler = MinMaxScaler()

    if df_test['popularity_score'].nunique() > 1:

        df_test['norm_popularity'] = (
            scaler.fit_transform(
                df_test[['popularity_score']]
            )
        )

    else:

        df_test['norm_popularity'] = 0.5

    df_test['hybrid_score'] = (

        (0.85 * df_test['sim_score']) +

        (0.15 * df_test['norm_popularity'])

    ) * 100

    # WARNING PENALTY
    
    df_test['final_score'] = (

        df_test['hybrid_score']

        -

        (df_test['warning_count'] * 1.5)

    )

    # FILTER MINIMUM SCORE
    
    df_test = df_test[
        df_test['final_score'] >= 30
    ]

    if df_test.empty:

        return {
            "status": "empty",
            "message":
                "Tidak ada produk dengan skor cukup"
        }

    # TOP PRODUCTS
    
    best_products = (
        df_test
        .sort_values(
            by='final_score',
            ascending=False
        )
        .head(3)
    )

    recommendations = []

    for _, row in best_products.iterrows():

        alasan = generate_dynamic_reason(
            user_input,
            row['description']
        )

        recommendations.append({

            "product_name":
                row.get(
                    "product_name",
                    "Unknown"
                ),

            "brand":
                row.get(
                    "brand",
                    "Unknown"
                ),

            "product_type":
                row.get(
                    "product_type",
                    "Unknown"
                ),

            "description":
                row.get(
                    "description",
                    "No description"
                ),

            "ingredients":
                row.get(
                    "ingredients",
                    "Unknown"
                ),

            "price":
                row.get(
                    "price",
                    0
                ),

            "similarity_score":
                round(
                    float(row['sim_score']) * 100,
                    2
                ),

            "final_score":
                round(
                    float(row['final_score']),
                    2
                ),

            "reason":
                alasan

        })

    return {

        "status": "success",

        "user_input": data.skin_text,

        "recommendations":
            recommendations
    }
