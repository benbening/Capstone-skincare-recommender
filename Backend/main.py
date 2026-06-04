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

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# STOPWORDS
stop_words = set(
    stopwords.words('indonesian') +
    stopwords.words('english')
)

custom_stopwords = {
    'aqua', 'water', 'ekstrak', 'extract', 'dan', 'yang', 'untuk', 'dengan'
}
stop_words.update(custom_stopwords)

# REQUEST BODY (Sudah disesuaikan agar menerima budget dan alergi dari Frontend React)
class UserInput(BaseModel):
    skin_text: str
    budget: float = 400000.0
    allergy_ingredients: str = ""

# TEXT CLEANING
def advanced_clean_text(text):
    text = re.sub(r'[^a-zA-Z0-9 ]', '', str(text))
    words = text.lower().split()
    cleaned_words = [w for w in words if w not in stop_words]
    return ' '.join(cleaned_words)

# DYNAMIC REASON
def generate_dynamic_reason(user_text, product_desc):
    user_words = [word.lower() for word in user_text.split() if len(word) > 3]
    claims = [claim.strip() for claim in str(product_desc).split(',')]
    matched_claims = []

    for claim in claims:
        if any(uw in claim.lower() for uw in user_words):
            matched_claims.append(claim.capitalize())

    if matched_claims:
        return f"Produk ini cocok karena {', '.join(matched_claims)}."

    return "Produk ini memiliki kecocokan semantik yang tinggi dengan kebutuhan kulit pengguna."

# HOME
@app.get("/")
def home():
    return {"message": "Advanced Skincare API Running"}

# RECOMMENDATION API
@app.post("/recommend")
def recommend(data: UserInput):
    user_input = advanced_clean_text(data.skin_text)
    df_test = df.copy()

    df_test['search_pool'] = df_test['product_name'].astype(str).str.lower().str.strip()
    df_test['desc_pool'] = df_test['description'].astype(str).str.lower().str.strip() + " " + df_test['search_pool']

    # 1. FILTER BLACKLIST ALERGI BAHAN KIMIA (Aman & Responsif)
    if data.allergy_ingredients and str(data.allergy_ingredients).strip():
        allergens = [a.strip().lower() for a in str(data.allergy_ingredients).split(',')]
        for allergen in allergens:
            if allergen:
                df_test = df_test[
                    ~df_test['ingredients'].astype(str).str.lower().str.contains(allergen, na=False)
                ]

    if df_test.empty:
        return {"status": "empty", "message": "Tidak ada produk memenuhi kriteria bebas alergen."}

    # 2. SELEKSI KATA KUNCI KELUHAN (Agar Peringkat Berubah Sesuai Pilihan Kuis & Tidak Monoton)
    keywords_keluhan = []
    for word in ["jerawat", "acne", "kusam", "bright", "glow", "pori", "pore", "lembap", "moist", "penuaan", "aging", "minyak", "oil", "barrier", "iritasi", "komedo", "comedo"]:
        if word in user_input.lower():
            keywords_keluhan.append(word)

    def hitung_bonus_keluhan(row_desc):
        desc = str(row_desc).lower()
        if not keywords_keluhan:
            return 0
        return sum(15 for kw in keywords_keluhan if kw in desc)

    # 3. SEMANTIC SIMILARITY
    row_positions = [df.index.get_loc(idx) for idx in df_test.index]
    user_vector = model.encode([user_input])
    similarity_scores = cosine_similarity(user_vector, semantic_matrix[row_positions]).flatten()
    df_test['sim_score'] = similarity_scores

    # OOD DETECTION
    max_sim = df_test['sim_score'].max()
    if max_sim < 0.25:
        return {"status": "rejected", "message": "Input tidak relevan dengan skincare"}

    # 4. HYBRID SCORE (Ditambah Bonus Keluhan Terarah)
    scaler = MinMaxScaler()
    if df_test['popularity_score'].nunique() > 1:
        df_test['norm_popularity'] = scaler.fit_transform(df_test[['popularity_score']])
    else:
        df_test['norm_popularity'] = 0.5

    df_test['bonus_score'] = df_test['desc_pool'].apply(hitung_bonus_keluhan)
    
    # Menghitung skor akhir murni rumus dasar Anda ditambah indikator kesesuaian keluhan
    df_test['hybrid_score'] = ((0.85 * df_test['sim_score']) + (0.15 * df_test['norm_popularity'])) * 100
    df_test['final_score'] = df_test['hybrid_score'] + df_test['bonus_score'] - (df_test['warning_count'] * 1.5)

    # 5. STRATEGI PEMETAAN PAKET 3 LANGKAH (Cleanser, Toner, Serum)
    categories_map = [
        {"key": "cleanser", "keywords": ["wash", "cleanser", "fresh", "whip", "foam", "soap", "sabun"], "exclude": ["toner", "serum", "cream", "sunscreen"]},
        {"key": "toner", "keywords": ["toner", "pad", "liquid", "water", "essence", "ampoule"], "exclude": ["wash", "cleanser", "serum", "moisturizer", "cream", "sunscreen"]},
        {"key": "serum", "keywords": ["serum"], "exclude": ["toner", "wash", "cleanser", "cream", "pad", "sunscreen"]}
    ]

    candidates = {}
    for cat in categories_map:
        key = cat["key"]
        pattern = "|".join(cat["keywords"])
        exclude_pattern = "|".join(cat["exclude"])
        
        category_df = df_test[
            (df_test['product_type'].astype(str).str.lower().str.strip() == key) |
            (df_test['search_pool'].str.contains(pattern, na=False) & ~df_test['search_pool'].str.contains(exclude_pattern, na=False))
        ]
        
        if category_df.empty:
            df_backup = df.copy()
            df_backup['search_pool'] = df_backup['product_name'].astype(str).str.lower().str.strip()
            category_df = df_backup[df_backup['search_pool'].str.contains(pattern, na=False) & ~df_backup['search_pool'].str.contains(exclude_pattern, na=False)].copy()
            category_df['sim_score'] = 0.4
            category_df['final_score'] = 40.0
            
        candidates[key] = category_df.sort_values(by='final_score', ascending=False)

    # 6. FILTER TOTAL BUDGET AKUMULASI (Dihitung dari gabungan 3 produk)
    p_cleanser = candidates["cleanser"].iloc[0] if not candidates["cleanser"].empty else None
    p_toner = candidates["toner"].iloc[0] if not candidates["toner"].empty else None
    p_serum = candidates["serum"].iloc[0] if not candidates["serum"].empty else None

    current_total = sum([p.get('price', 0) for p in [p_cleanser, p_toner, p_serum] if p is not None])
    
    # Jika total harga gabungan melebihi slider budget pilihan user, cari alternatif peringkat di bawahnya yang lebih murah
    if data.budget and current_total > data.budget:
        for key in ["toner", "serum", "cleanser"]: 
            cat_candidates = candidates[key]
            for idx in range(len(cat_candidates)):
                alt_p = cat_candidates.iloc[idx]
                
                # Pastikan alternatif produk harganya memang lebih murah dari produk saat ini
                if alt_p.get('price', 0) < eval(f"p_{key}").get('price', 0):
                    temp_total = current_total - (eval(f"p_{key}").get('price', 0)) + alt_p.get('price', 0)
                    
                    # Langsung eksekusi penggantian produk ke yang lebih murah
                    exec(f"p_{key} = alt_p")
                    current_total = temp_total
                    
                    # Jika total harga sudah aman dan masuk budget, stop pencarian alternatif
                    if current_total <= data.budget:
                        break
            if current_total <= data.budget:
                break

    # 7. PENYUSUNAN RESPONSE JSON AKHIR
    final_products = [p_cleanser, p_toner, p_serum]
    keys_order = ["cleanser", "toner", "serum"]
    recommendations = []

    for i, row in enumerate(final_products):
        if row is not None:
            key = keys_order[i]
            alasan = generate_dynamic_reason(user_input, row.get('description', ''))
            brand_name = row.get("brand", str(row['product_name']).split()[0])
            safe_price = int(row['price']) if 'price' in row and pd.notnull(row['price']) else 0
            sim_val = round(float(row.get('sim_score', 0.45)) * 100, 2)
            score_val = round(float(row.get('final_score', 45.0)), 2)

            recommendations.append({
                "product_name": row.get("product_name", "Unknown Product"),
                "brand": brand_name,
                "product_type": key,
                "category": key,
                "description": row.get("description", "No description"),
                "ingredients": row.get("ingredients", "Unknown"),
                "price": safe_price,
                "similarity_score": sim_val,
                "score": score_val,
                "reason": alasan
            })

    return {
        "status": "success",
        "user_input": data.skin_text,
        "recommendations": recommendations
    }
