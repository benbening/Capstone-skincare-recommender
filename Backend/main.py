from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
import pickle

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# FASTAPI

app = FastAPI()

# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LOAD DATASET

df = pd.read_csv("skincare.csv")

# LOAD MODEL

model = SentenceTransformer(
    "./skincare_custom_model"
)

# LOAD SEMANTIC MATRIX

with open(
    "semantic_matrix.pkl",
    "rb"
) as f:

    semantic_matrix = pickle.load(f)

# REQUEST BODY

class UserInput(BaseModel):

    skin_text: str

# HOME

@app.get("/")
def home():

    return {
        "message": "Backend Running"
    }

# RECOMMENDATION API

@app.post("/recommend")
def recommend(data: UserInput):

    # ENCODE USER INPUT
    
    user_embedding = model.encode(
        [data.skin_text]
    )

    # COSINE SIMILARITY
    
    similarity = cosine_similarity(
        user_embedding,
        semantic_matrix
    )

    # TOP 5
    
    top_idx = similarity.argsort()[0][-5:][::-1]


    recommendations = []

    # RESULT
   
    for idx in top_idx:

        row = df.iloc[idx]

        recommendations.append({

            "product_name":
                row.get("product_name", "Unknown"),

            "brand":
                row.get("brand", "Unknown"),

            "description":
                row.get("description", "No description"),

            "ingredients":
                row.get("ingredients", "Unknown"),

            "price":
                row.get("price", 0),

            "score":
                round(
                    float(similarity[0][idx]) * 100,
                    2
                )

        })


    return {
        "recommendations": recommendations
    }