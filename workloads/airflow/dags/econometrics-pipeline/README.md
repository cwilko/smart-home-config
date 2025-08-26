# Econometrics Data Pipeline

This Airflow DAG collects economic and financial data from various government and financial sources for dashboard visualization and analysis.

## Data Sources

### Economic Indicators
- **Consumer Price Index (CPI)** - Bureau of Labor Statistics
- **Federal Funds Rate** - Federal Reserve (FRED)
- **Unemployment Rate** - Bureau of Labor Statistics  
- **Gross Domestic Product (GDP)** - Bureau of Economic Analysis

### Market Data
- **S&P 500 Index** - Federal Reserve (FRED)
- **VIX Volatility Index** - Federal Reserve (FRED)
- **Treasury Yield Curve** - U.S. Department of Treasury
- **P/E Ratios** - Various sources (S&P 500 P/E and Shiller P/E)

## Required Environment Variables

Add these to the Airflow sealed secrets:

```yaml
# API Keys
FRED_API_KEY: "your_fred_api_key"
BEA_API_KEY: "your_bea_api_key" 
BLS_API_KEY: "your_bls_api_key"  # Optional but recommended

# Database Connection
POSTGRES_HOST: "your_postgres_host"
POSTGRES_DB: "econometrics"
POSTGRES_USER: "your_postgres_user"
POSTGRES_PASSWORD: "your_postgres_password"
POSTGRES_PORT: "5432"
```

## API Key Registration

1. **FRED API Key** (Required)
   - Register at: https://fred.stlouisfed.org/docs/api/api_key.html
   - Free account, 120 requests/minute

2. **BEA API Key** (Required)
   - Register at: https://apps.bea.gov/API/signup/
   - Free account for GDP data

3. **BLS API Key** (Optional)
   - Register at: https://data.bls.gov/registrationEngine/
   - Increases rate limits from 25 to 500 queries/day

## Schedule

- **Frequency**: Every 6 hours (`0 */6 * * *`)
- **Start Date**: 2024-01-01
- **Catchup**: Disabled
- **Max Active Runs**: 1

## Database Schema

The pipeline creates and populates these PostgreSQL tables:

- `consumer_price_index` - Monthly CPI data
- `federal_funds_rate` - Monthly federal funds rate
- `unemployment_rate` - Monthly unemployment statistics
- `gross_domestic_product` - Quarterly GDP data
- `sp500_index` - Daily S&P 500 index values
- `vix_index` - Daily VIX volatility data
- `treasury_yields` - Daily Treasury yield curve
- `pe_ratios` - S&P 500 and Shiller P/E ratios

## Task Dependencies

```
create_database_tables
    ├── collect_fed_funds_rate
    ├── collect_cpi_data
    ├── collect_sp500_data
    └── collect_treasury_yields
```

## Error Handling

- Each task uses `@task.virtualenv` for isolation
- Automatic retries on failure (configured in Airflow)
- Comprehensive logging for debugging
- Data validation and upsert operations prevent duplicates

## Monitoring

Monitor the DAG through the Airflow UI:
- Task execution times and success rates
- Data collection statistics in task logs  
- Failed tasks and retry attempts
- Overall pipeline health and dependencies