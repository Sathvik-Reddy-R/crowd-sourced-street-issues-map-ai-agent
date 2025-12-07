from dotenv import load_dotenv 
import os
from app import create_app

# Load .env (used locally)
load_dotenv()

# Read Mongo URI from environment
MONGO_URI_VALUE = os.environ.get("MONGO_URI")
if not MONGO_URI_VALUE:
    print("❌ MONGO_URI missing, using local fallback...")
    MONGO_URI_VALUE = "mongodb://localhost:27017/urban_issues_db"

config_dict = {
    "SECRET_KEY": os.environ.get("SECRET_KEY", "default_secret"),
    "MONGO_URI": MONGO_URI_VALUE,
    # In production (Render) FLASK_ENV=production so DEBUG=False
    "DEBUG": os.environ.get("FLASK_ENV") == "development"
}

app = create_app(config_dict=config_dict)

if __name__ == "__main__":
    # Render gives us PORT env automatically (e.g. 10000, 12345...)
    port = int(os.environ.get("PORT", 5000))

    print("Attempting to connect with URI:", MONGO_URI_VALUE)
    print(f"Starting server on 0.0.0.0:{port}")

    # IMPORTANT: Bind to 0.0.0.0 and use PORT from env
    app.run(host="0.0.0.0", port=port, debug=config_dict["DEBUG"])
