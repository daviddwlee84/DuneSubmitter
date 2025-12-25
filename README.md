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

### Custom SQL (Plus)
Write and execute arbitrary SQL queries directly (sync).
- Write custom SQL with `{{parameter}}` syntax
- Dynamic parameter detection and input widgets
- Local parameter substitution
- **Requires Dune Plus subscription**

### Async Custom SQL
Execute arbitrary SQL asynchronously using `execute_sql` endpoint.
- Write custom SQL with parameter support
- Submit and get execution ID
- Poll for completion, cancel if needed
- May work without Plus subscription (uses `/sql/execute`)

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
| Async Custom SQL (`execute_sql`)     | Uses credits   | May work on Free    |
| Create/Update Query                  | N/A            | **Plus required**   |

## Project Structure

```
.
├── main.py                       # Main page / introduction
├── pages/
│   ├── 1_🔍_Sync_Query.py        # Synchronous query execution
│   ├── 2_⏳_Async_Query.py       # Asynchronous query execution
│   ├── 3_📊_Latest_Results.py    # Get cached results
│   ├── 4_✍️_Custom_SQL.py        # Custom SQL execution (Plus)
│   └── 5_🚀_Async_Custom_SQL.py  # Async custom SQL execution
├── shared_components.py          # Shared UI components and utilities
├── pyproject.toml                # Project dependencies
└── README.md
```

## Resources

- [duneanalytics/dune-client: A framework for interacting with Dune Analytics' officially supported API service](https://github.com/duneanalytics/dune-client)
- [Client SDKs - Dune Docs](https://docs.dune.com/api-reference/overview/sdks#python)

- [Secrets management - Streamlit Docs](https://docs.streamlit.io/develop/concepts/connections/secrets-management)
- [st.secrets - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/connections/st.secrets)

- [Export Data Out of Dune - Dune Docs](https://docs.dune.com/learning/how-tos/export-data-out#costs-for-exporting-data)

---

Simplest way => submit with Dune web UI, download using Query ID

```bash
curl -H "x-dune-api-key: $DUNE_API_KEY" "https://api.dune.com/api/v1/query/$QID/results?limit=1000"
curl -H "x-dune-api-key: $DUNE_API_KEY" "https://api.dune.com/api/v1/query/$QID/results/csv?limit=1000"
```

> `{"error":"This api request would exceed your configured datapoint limit per request. Please visit your subscription settings on dune.com and adjust your limits to perform this request."}`
