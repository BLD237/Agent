from pymongo import MongoClient
import os
import hashlib

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]

opportunities = db.opportunities


def generate_hash(title: str, country: str):
    raw = f"{title}-{country}"
    return hashlib.sha256(raw.encode()).hexdigest()


def opportunity_exists(link: str, title: str, country: str) -> bool:
    return opportunities.find_one({
        "$or": [
            {"official_link": link},
            {"hash": generate_hash(title, country)}
        ]
    }) is not None


def save_opportunity(data: dict):
    data["hash"] = generate_hash(data["title"], data["country"])
    opportunities.insert_one(data)
