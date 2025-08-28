# Econometrics Data Pipeline

Automated data collection pipeline for economic and financial indicators using Apache Airflow.

## Overview

This DAG collects economic and financial data from official government and market sources:

**Economic Indicators:**
- Consumer Price Index (CPI) - Bureau of Labor Statistics API
- Federal Funds Rate - Federal Reserve (FRED) API
- Treasury Yield Curve (1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y) - FRED API
- S&P 500 Index - FRED API

**Schedule:** Daily at 6 PM ET (11 PM UTC), weekdays only

## Data Sources

- **FRED API** (Federal Reserve Economic Data) - Primary source for most indicators
- **BLS API** (Bureau of Labor Statistics) - CPI data
- All data stored in PostgreSQL database

## Required Environment Variables

Set these in your Airflow secrets:

```bash
# API Keys
FRED_API_KEY=your_fred_api_key_here
BLS_API_KEY=your_bls_api_key_here  # Optional

# Database Connection
DATABASE_URL=postgresql://user:pass@host:port/dbname
# OR individual parameters:
POSTGRES_HOST=your_db_host
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_PORT=5432
```

## Database Schema

All data is stored with proper indexing and constraints:
- Timestamps (created_at, updated_at)
- Unique constraints to prevent duplicates
- Decimal precision for financial data
- Upsert operations for data updates

## Task Dependencies

```
create_database_tables
├── collect_fed_funds_rate
├── collect_cpi_data
├── collect_sp500_data
└── collect_treasury_yields
```

## Features

- **Daily execution** aligned with market data release schedules
- **Automatic table creation** on first run
- **Error handling** with retries and logging
- **Data validation** and conflict resolution
- **ARM64 node scheduling** via nodeSelector
- **Comprehensive logging** for monitoring and debugging

## Monitoring

- Check Airflow UI for task execution status
- Review logs for data collection statistics
- Monitor database for data freshness and accuracy
- Set up alerts for task failures

## Getting API Keys

1. **FRED API Key** (Required):
   - Visit: https://fred.stlouisfed.org/docs/api/api_key.html
   - Free registration required

2. **BLS API Key** (Optional):
   - Visit: https://data.bls.gov/registrationEngine/
   - Increases rate limits for CPI data