import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

print("Listing models...")
try:
    for m in genai.list_models():
        if 'embedContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")

print("\nTesting embedding with 'models/text-embedding-004'...")
try:
    res = genai.embed_content(model="models/text-embedding-004", content="Hello world")
    print(f"Success! Dimensions: {len(res['embedding'])}")
except Exception as e:
    print(f"Failed models/text-embedding-004: {e}")

print("\nTesting embedding with 'gemini-embedding-2-preview'...")
try:
    res = genai.embed_content(model="gemini-embedding-2-preview", content="Hello world")
    print(f"Success! Dimensions: {len(res['embedding'])}")
except Exception as e:
    print(f"Failed models/embedding-001: {e}")
