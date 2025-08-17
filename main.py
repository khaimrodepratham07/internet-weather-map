from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import requests
import json
from datetime import datetime
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Internet Weather – Local Backend")

# CORS (handy if you open index.html directly in a browser)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Location(BaseModel):
    latitude: float
    longitude: float

@app.get("/")
def get_home():
    """
    Serves the main HTML page.
    """
    return FileResponse("index.html")

@app.post("/generate-measurement")
def generate_measurement(location: Location):
    """
    API endpoint to generate plausible internet measurement data for a given location using an LLM.
    """
    try:
        # A simple reverse geocoding simulation based on coordinates
        if 10.0 < location.latitude < 30.0 and 70.0 < location.longitude < 90.0:
            location_name = "Major City in India"
        elif 30.0 < location.latitude < 45.0 and -120.0 < location.longitude < -70.0:
            location_name = "Major City in USA"
        elif 45.0 < location.latitude < 60.0 and -10.0 < location.longitude < 10.0:
            location_name = "Major City in Western Europe"
        else:
            location_name = "Rural or Remote Area"

        prompt = (
            f"Generate a plausible, single JSON object for internet measurement data for a location. "
            f"The location is approximately in a {location_name} at latitude {location.latitude:.2f} and longitude {location.longitude:.2f}. "
            "The JSON object must have the following keys: 'location_name', 'latency_ms', 'jitter_ms', and 'packet_loss_pct'. "
            "The 'location_name' should be a descriptive name like 'City, Country' or 'Rural, Region'. "
            "The 'latency_ms' and 'jitter_ms' should be floats and 'packet_loss_pct' should be a float between 0.0 and 1.0. "
            "Make the values plausible for the given location type. "
            "For example, a major city should have low latency/jitter and near zero packet loss. A rural area might have higher values."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "location_name": {"type": "STRING"},
                        "latency_ms": {"type": "NUMBER"},
                        "jitter_ms": {"type": "NUMBER"},
                        "packet_loss_pct": {"type": "NUMBER"}
                    },
                    "required": ["location_name", "latency_ms", "jitter_ms", "packet_loss_pct"]
                }
            }
        }
        
        # Exponential backoff for API calls
        retries = 3
        delay = 1
        for i in range(retries):
            try:
                # IMPORTANT: Replace "YOUR_API_KEY_HERE" with your actual Google API key.
                # In this hosted environment, the key is set automatically.
                api_key = "AIzaSyCYhH_mVBNshRJ0BZgQQXbAFcmTZykjWVc" 
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
                
                response = requests.post(api_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
                response.raise_for_status()

                result = response.json()
                data_string = result["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(data_string)
            except requests.exceptions.HTTPError as e:
                # This will print the HTTP status code and response text for debugging
                print(f"HTTP error on attempt {i+1}: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
                if e.response.status_code == 429 and i < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise
            except Exception as e:
                print(f"An error occurred on attempt {i+1}: {e}")
                if i < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

        raise HTTPException(status_code=500, detail="Failed to generate data after multiple retries.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate data: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)