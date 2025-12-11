"""Legacy Streamlit entry point.

The ParlayLab project has moved to an API-only architecture. Run the FastAPI
server instead:

    uvicorn parlaylab.api.server:app --host 0.0.0.0 --port 8000

"""

raise RuntimeError("The Streamlit dashboard has been retired. Use the FastAPI backend instead.")
