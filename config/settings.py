import os
from dotenv import load_dotenv

# Load local .env if present (we only use it if user sets environment variables in their shell or if we want to run locally with env variables)
load_dotenv()

INFISICAL_CLIENT_ID = os.environ.get("INFISICAL_CLIENT_ID")
INFISICAL_CLIENT_SECRET = os.environ.get("INFISICAL_CLIENT_SECRET")
INFISICAL_PROJECT_ID = os.environ.get("INFISICAL_PROJECT_ID")

if INFISICAL_CLIENT_ID and INFISICAL_CLIENT_SECRET and INFISICAL_PROJECT_ID:
    try:
        from infisical_sdk import InfisicalSDKClient
        
        # Initialize client and login with Universal Auth
        client = InfisicalSDKClient(host="https://app.infisical.com")
        client.auth.universal_auth.login(
            client_id=INFISICAL_CLIENT_ID,
            client_secret=INFISICAL_CLIENT_SECRET
        )
        
        def get_secret(name: str) -> str:
            secret = client.secrets.get_secret_by_name(
                secret_name=name,
                project_id=INFISICAL_PROJECT_ID,
                environment_slug="dev",
                secret_path="/"
            )
            return secret.secretValue

        SUPABASE_URL = get_secret("SUPABASE_URL")
        SUPABASE_ANON_KEY = get_secret("SUPABASE_ANON_KEY")
        SUPABASE_SERVICE_ROLE_KEY = get_secret("SUPABASE_SERVICE_ROLE_KEY")
        ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY")
    except Exception as e:
        print(f"Error initializing or fetching from Infisical: {e}. Falling back to direct environment variables.")
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
        SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
else:
    # Direct environment fallback (if running in environment where keys are already loaded/set directly)
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
