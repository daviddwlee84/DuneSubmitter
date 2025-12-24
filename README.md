# Dune Query Tool

> A Streamlit-based interface for interacting with Dune Analytics through their official Python SDK

## Features

This tool provides multiple ways to work with Dune queries:

### Sync Query
Execute existing Dune queries by their Query ID synchronously.
- Run queries and wait for results
- Pass custom parameters
- Uses execution credits

### Async Query
Start query execution asynchronously and poll for results.
- Non-blocking execution
- Monitor execution status
- Cancel running queries
- Efficient for long-running queries

### Latest Results
Get the most recent cached results without re-executing.
- **No execution credits used!**
- Fast retrieval
- Configurable staleness threshold
- Great for frequently updated queries

## Getting Started

1. Get a Dune API key from [Dune API Keys](https://dune.com/apis?tab=keys)

2. Set up environment (optional - you can also enter the key in the UI):
   ```bash
   cp .env.sample .env
   # Edit .env and add your DUNE_API_KEY
   ```

3. Run the app:
   ```bash
   uv run streamlit run main.py
   ```

## API Usage Notes

| Feature                              | Credits        | Subscription        |
| ------------------------------------ | -------------- | ------------------- |
| Sync Query (`run_query`)             | Uses credits   | Free tier available |
| Async Query (`execute_query`)        | Uses credits   | Free tier available |
| Latest Results (`get_latest_result`) | **No credits** | Free tier available |
| Custom SQL (`run_sql`)               | Uses credits   | **Plus required**   |
| Create/Update Query                  | N/A            | **Plus required**   |

## Project Structure

```
.
├── main.py                 # Main page / introduction
├── pages/
│   ├── 1_🔍_Sync_Query.py  # Synchronous query execution
│   ├── 2_⏳_Async_Query.py # Asynchronous query execution
│   └── 3_📊_Latest_Results.py  # Get cached results
├── shared_components.py    # Shared UI components and utilities
├── pyproject.toml          # Project dependencies
└── README.md
```

## Resources

- [duneanalytics/dune-client](https://github.com/duneanalytics/dune-client) - Official Python SDK
- [Dune API Documentation](https://docs.dune.com/api-reference/overview/sdks#python)
- [Streamlit Documentation](https://docs.streamlit.io/)
