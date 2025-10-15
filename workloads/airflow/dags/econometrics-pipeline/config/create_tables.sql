-- Economic indicators tables
CREATE TABLE IF NOT EXISTS consumer_price_index (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    value DECIMAL(10,4) NOT NULL,
    month_over_month_change DECIMAL(10,4),
    year_over_year_change DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS federal_funds_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    effective_rate DECIMAL(10,4) NOT NULL,
    target_rate_lower DECIMAL(10,4),
    target_rate_upper DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_federal_funds_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    effective_rate DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS unemployment_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    rate DECIMAL(10,4) NOT NULL,
    labor_force INTEGER,
    employed INTEGER,
    unemployed INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gross_domestic_product (
    id SERIAL PRIMARY KEY,
    quarter DATE NOT NULL UNIQUE,
    gdp_billions DECIMAL(15,2) NOT NULL,
    gdp_growth_rate DECIMAL(10,4),
    gdp_per_capita DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS real_gdp_growth_components (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    real_gdp_growth DECIMAL(10,4),
    consumption_contribution DECIMAL(10,4),
    investment_contribution DECIMAL(10,4),
    government_contribution DECIMAL(10,4),
    net_exports_contribution DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GDPNow Forecasts Table (Real-time GDP growth forecasts from Atlanta Fed)
-- Note: Forecasts are revised multiple times per month for the same quarter
-- Records with the same date will be updated with latest forecast revisions
CREATE TABLE IF NOT EXISTS gdpnow_forecasts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    forecast_rate DECIMAL(10,4) NOT NULL,
    data_source VARCHAR(50) DEFAULT 'Atlanta_Fed_GDPNow',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market data tables
CREATE TABLE IF NOT EXISTS sp500_index (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    open_price DECIMAL(12,4) NOT NULL,
    high_price DECIMAL(12,4) NOT NULL,
    low_price DECIMAL(12,4) NOT NULL,
    close_price DECIMAL(12,4) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vix_index (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    open_price DECIMAL(10,4) NOT NULL,
    high_price DECIMAL(10,4) NOT NULL,
    low_price DECIMAL(10,4) NOT NULL,
    close_price DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pe_ratios (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    sp500_pe DECIMAL(10,4),
    sp500_shiller_pe DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fred_treasury_yields (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    series_id VARCHAR(10) NOT NULL,
    maturity VARCHAR(10) NOT NULL,
    yield_rate DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, series_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_cpi_date ON consumer_price_index(date);
CREATE INDEX IF NOT EXISTS idx_fed_funds_date ON federal_funds_rate(date);
CREATE INDEX IF NOT EXISTS idx_daily_fed_funds_date ON daily_federal_funds_rate(date);
CREATE INDEX IF NOT EXISTS idx_unemployment_date ON unemployment_rate(date);
CREATE INDEX IF NOT EXISTS idx_gdp_quarter ON gross_domestic_product(quarter);
CREATE INDEX IF NOT EXISTS idx_real_gdp_growth_components_date ON real_gdp_growth_components(date);
CREATE INDEX IF NOT EXISTS idx_gdpnow_forecasts_date ON gdpnow_forecasts(date);
CREATE INDEX IF NOT EXISTS idx_sp500_date ON sp500_index(date);
CREATE INDEX IF NOT EXISTS idx_vix_date ON vix_index(date);
CREATE INDEX IF NOT EXISTS idx_pe_ratios_date ON pe_ratios(date);
CREATE INDEX IF NOT EXISTS idx_fred_treasury_date_series ON fred_treasury_yields(date, series_id);
CREATE INDEX IF NOT EXISTS idx_fred_treasury_maturity ON fred_treasury_yields(maturity);

-- UK Economic Indicators Tables
CREATE TABLE IF NOT EXISTS uk_consumer_price_index (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    value DECIMAL(10,4) NOT NULL,
    month_over_month_change DECIMAL(10,4),
    year_over_year_change DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- UK Bank Rate tables (monthly and daily to mirror US Fed Funds structure)
CREATE TABLE IF NOT EXISTS uk_monthly_bank_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    rate DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uk_daily_bank_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    rate DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uk_unemployment_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    rate DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uk_gross_domestic_product (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,  -- Changed from 'quarter' to 'date' for monthly GDP data
    sector_classification VARCHAR(10) NOT NULL,  -- ONS sector classification code (A, A--T, B-E, F, G-T)
    gdp_index DECIMAL(15,4) NOT NULL,  -- Changed from 'gdp_billions' to 'gdp_index' to match ONS data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, sector_classification)  -- Allow multiple sectors per date
);

-- UK Market Data Tables
CREATE TABLE IF NOT EXISTS ftse_100_index (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    open_price DECIMAL(12,4) NOT NULL,
    high_price DECIMAL(12,4) NOT NULL,
    low_price DECIMAL(12,4) NOT NULL,
    close_price DECIMAL(12,4) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comprehensive BoE yield curve table (80+ maturities from ZIP files)
CREATE TABLE IF NOT EXISTS boe_yield_curves (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    maturity_years DECIMAL(6,3) NOT NULL,  -- Supports fractional years like 0.5, 1.5, etc.
    yield_rate DECIMAL(10,4) NOT NULL,
    yield_type VARCHAR(20) NOT NULL,  -- 'nominal', 'real', 'inflation', 'ois'
    data_source VARCHAR(50) DEFAULT 'BoE_ZIP_daily',  -- Track data source
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, maturity_years, yield_type)
);

CREATE TABLE IF NOT EXISTS gbp_usd_exchange_rate (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    exchange_rate DECIMAL(10,6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- UK Gilt Yields Table (5Y, 10Y, 20Y from Bank of England IADB)
CREATE TABLE IF NOT EXISTS uk_gilt_yields (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    maturity_years DECIMAL(4,1) NOT NULL,
    yield_rate DECIMAL(8,4) NOT NULL,
    series_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, maturity_years)
);

-- UK indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_uk_cpi_date ON uk_consumer_price_index(date);
CREATE INDEX IF NOT EXISTS idx_uk_monthly_bank_rate_date ON uk_monthly_bank_rate(date);
CREATE INDEX IF NOT EXISTS idx_uk_daily_bank_rate_date ON uk_daily_bank_rate(date);
CREATE INDEX IF NOT EXISTS idx_uk_unemployment_date ON uk_unemployment_rate(date);
CREATE INDEX IF NOT EXISTS idx_uk_gdp_date ON uk_gross_domestic_product(date);  -- Changed from quarter to date
CREATE INDEX IF NOT EXISTS idx_uk_gdp_sector ON uk_gross_domestic_product(sector_classification);
CREATE INDEX IF NOT EXISTS idx_uk_gdp_date_sector ON uk_gross_domestic_product(date, sector_classification);
CREATE INDEX IF NOT EXISTS idx_ftse_100_date ON ftse_100_index(date);
CREATE INDEX IF NOT EXISTS idx_boe_yield_curves_date_maturity_type ON boe_yield_curves(date, maturity_years, yield_type);
CREATE INDEX IF NOT EXISTS idx_boe_yield_curves_yield_type ON boe_yield_curves(yield_type);
CREATE INDEX IF NOT EXISTS idx_boe_yield_curves_maturity ON boe_yield_curves(maturity_years);
CREATE INDEX IF NOT EXISTS idx_gbp_usd_date ON gbp_usd_exchange_rate(date);
CREATE INDEX IF NOT EXISTS idx_uk_gilt_yields_date ON uk_gilt_yields(date);
CREATE INDEX IF NOT EXISTS idx_uk_gilt_yields_maturity ON uk_gilt_yields(maturity_years);
CREATE INDEX IF NOT EXISTS idx_uk_gilt_yields_date_maturity ON uk_gilt_yields(date, maturity_years);

-- Gilt Market Data Table (Real-time broker prices)
CREATE TABLE IF NOT EXISTS gilt_market_prices (
    id SERIAL PRIMARY KEY,
    bond_name VARCHAR(255) NOT NULL,
    clean_price DECIMAL(10,6) NOT NULL,
    accrued_interest DECIMAL(10,6) NOT NULL,
    dirty_price DECIMAL(10,6) NOT NULL,
    coupon_rate DECIMAL(8,6) NOT NULL,
    maturity_date DATE NOT NULL,
    years_to_maturity DECIMAL(8,4) NOT NULL,
    ytm DECIMAL(8,6),
    after_tax_ytm DECIMAL(8,6),
    scraped_date DATE NOT NULL,
    -- Bond identifiers (added for enhanced bond tracking)
    currency_code VARCHAR(3),  -- Currency code (e.g., 'GBP', 'USD', 'EUR')
    isin VARCHAR(12),           -- International Securities Identification Number
    short_code VARCHAR(10),     -- HL internal identifier from URL
    combined_id VARCHAR(30),    -- Full formatted ID: 'Currency | ISIN | Short Code'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bond_name, scraped_date)
);

-- Index for gilt market data
CREATE INDEX IF NOT EXISTS idx_gilt_market_scraped_date ON gilt_market_prices(scraped_date);
CREATE INDEX IF NOT EXISTS idx_gilt_market_maturity ON gilt_market_prices(maturity_date);
CREATE INDEX IF NOT EXISTS idx_gilt_market_bond_name ON gilt_market_prices(bond_name);
CREATE INDEX IF NOT EXISTS idx_gilt_market_isin ON gilt_market_prices(isin);
CREATE INDEX IF NOT EXISTS idx_gilt_market_short_code ON gilt_market_prices(short_code);

-- AJ Bell Gilt Market Data Table (Alternative broker prices for cross-broker comparison)
CREATE TABLE IF NOT EXISTS ajbell_gilt_prices (\n    id SERIAL PRIMARY KEY,
    bond_name VARCHAR(255) NOT NULL,
    clean_price DECIMAL(10,6) NOT NULL,
    accrued_interest DECIMAL(10,6),
    dirty_price DECIMAL(10,6),
    coupon_rate DECIMAL(8,6) NOT NULL,
    maturity_date DATE NOT NULL,
    years_to_maturity DECIMAL(8,4) NOT NULL,
    ytm DECIMAL(8,6),
    after_tax_ytm DECIMAL(8,6),
    scraped_date DATE NOT NULL,
    -- Bond identifiers (consistent with gilt_market_prices structure)
    currency_code VARCHAR(3) DEFAULT 'GBP',  -- Currency code (defaulting to GBP for UK gilts)
    isin VARCHAR(12),                        -- International Securities Identification Number
    short_code VARCHAR(10),                  -- AJ Bell internal identifier
    combined_id VARCHAR(30),                 -- Full formatted ID: 'Currency | ISIN | Short Code'
    data_source VARCHAR(50) DEFAULT 'AJ_Bell',  -- Track data source for cross-broker analysis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bond_name, scraped_date)
);

-- Index for AJ Bell gilt market data
CREATE INDEX IF NOT EXISTS idx_ajbell_gilt_scraped_date ON ajbell_gilt_prices(scraped_date);
CREATE INDEX IF NOT EXISTS idx_ajbell_gilt_maturity ON ajbell_gilt_prices(maturity_date);
CREATE INDEX IF NOT EXISTS idx_ajbell_gilt_bond_name ON ajbell_gilt_prices(bond_name);
CREATE INDEX IF NOT EXISTS idx_ajbell_gilt_isin ON ajbell_gilt_prices(isin);
CREATE INDEX IF NOT EXISTS idx_ajbell_gilt_short_code ON ajbell_gilt_prices(short_code);
CREATE INDEX IF NOT EXISTS idx_ajbell_gilt_data_source ON ajbell_gilt_prices(data_source);

-- UK Swap Rates Table (GBP Interest Rate Swaps)
CREATE TABLE IF NOT EXISTS uk_swap_rates (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    maturity VARCHAR(10) NOT NULL,
    maturity_years DECIMAL(4,1) NOT NULL,
    open_rate DECIMAL(8,4) NOT NULL,
    high_rate DECIMAL(8,4) NOT NULL,
    low_rate DECIMAL(8,4) NOT NULL,
    close_rate DECIMAL(8,4) NOT NULL,
    source VARCHAR(50) DEFAULT 'investiny',
    symbol VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, maturity)
);

-- Index for UK swap rates
CREATE INDEX IF NOT EXISTS idx_uk_swap_rates_date ON uk_swap_rates(date);
CREATE INDEX IF NOT EXISTS idx_uk_swap_rates_maturity ON uk_swap_rates(maturity);
CREATE INDEX IF NOT EXISTS idx_uk_swap_rates_date_maturity ON uk_swap_rates(date, maturity);

-- Index-Linked Gilt Market Prices Table (Real-time broker prices with real yields)
CREATE TABLE IF NOT EXISTS index_linked_gilt_prices (
    id SERIAL PRIMARY KEY,
    bond_name VARCHAR(255) NOT NULL,
    clean_price DECIMAL(10,6) NOT NULL,
    accrued_interest DECIMAL(10,6) NOT NULL,
    dirty_price DECIMAL(10,6) NOT NULL,
    coupon_rate DECIMAL(8,6) NOT NULL,
    maturity_date DATE NOT NULL,
    years_to_maturity DECIMAL(8,4) NOT NULL,
    real_yield DECIMAL(8,6),
    after_tax_real_yield DECIMAL(8,6),
    inflation_assumption DECIMAL(6,2) DEFAULT 3.0,
    scraped_date DATE NOT NULL,
    -- Bond identifiers (added for enhanced bond tracking)
    currency_code VARCHAR(3),  -- Currency code (e.g., 'GBP', 'USD', 'EUR')
    isin VARCHAR(12),           -- International Securities Identification Number
    short_code VARCHAR(10),     -- HL internal identifier from URL
    combined_id VARCHAR(30),    -- Full formatted ID: 'Currency | ISIN | Short Code'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bond_name, scraped_date)
);

-- Index for index-linked gilt market data
CREATE INDEX IF NOT EXISTS idx_index_linked_gilt_scraped_date ON index_linked_gilt_prices(scraped_date);
CREATE INDEX IF NOT EXISTS idx_index_linked_gilt_maturity ON index_linked_gilt_prices(maturity_date);
CREATE INDEX IF NOT EXISTS idx_index_linked_gilt_bond_name ON index_linked_gilt_prices(bond_name);
CREATE INDEX IF NOT EXISTS idx_index_linked_gilt_isin ON index_linked_gilt_prices(isin);
CREATE INDEX IF NOT EXISTS idx_index_linked_gilt_short_code ON index_linked_gilt_prices(short_code);

-- Corporate Bond Market Prices Table (Real-time broker prices with credit analysis)
CREATE TABLE IF NOT EXISTS corporate_bond_prices (
    id SERIAL PRIMARY KEY,
    bond_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(100),
    clean_price DECIMAL(10,6) NOT NULL,
    accrued_interest DECIMAL(10,6) NOT NULL,
    dirty_price DECIMAL(10,6) NOT NULL,
    coupon_rate DECIMAL(8,6) NOT NULL,
    maturity_date DATE NOT NULL,
    years_to_maturity DECIMAL(8,4) NOT NULL,
    ytm DECIMAL(8,6),
    after_tax_ytm DECIMAL(8,6),
    credit_rating VARCHAR(10) DEFAULT 'NR',
    scraped_date DATE NOT NULL,
    -- Bond identifiers (added for enhanced bond tracking)
    currency_code VARCHAR(3),  -- Currency code (e.g., 'GBP', 'USD', 'EUR')
    isin VARCHAR(12),           -- International Securities Identification Number
    short_code VARCHAR(10),     -- HL internal identifier from URL
    combined_id VARCHAR(30),    -- Full formatted ID: 'Currency | ISIN | Short Code'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bond_name, scraped_date)
);

-- Index for corporate bond market data
CREATE INDEX IF NOT EXISTS idx_corporate_bond_scraped_date ON corporate_bond_prices(scraped_date);
CREATE INDEX IF NOT EXISTS idx_corporate_bond_maturity ON corporate_bond_prices(maturity_date);
CREATE INDEX IF NOT EXISTS idx_corporate_bond_company ON corporate_bond_prices(company_name);
CREATE INDEX IF NOT EXISTS idx_corporate_bond_rating ON corporate_bond_prices(credit_rating);
CREATE INDEX IF NOT EXISTS idx_corporate_bond_isin ON corporate_bond_prices(isin);
CREATE INDEX IF NOT EXISTS idx_corporate_bond_short_code ON corporate_bond_prices(short_code);

-- AJ Bell Corporate Bond Market Prices Table (Alternative broker prices for cross-broker comparison)
CREATE TABLE IF NOT EXISTS ajbell_corporate_bond_prices (
    id SERIAL PRIMARY KEY,
    bond_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(100),
    clean_price DECIMAL(10,6) NOT NULL,
    accrued_interest DECIMAL(10,6) NOT NULL,
    dirty_price DECIMAL(10,6) NOT NULL,
    coupon_rate DECIMAL(8,6) NOT NULL,
    maturity_date DATE NOT NULL,
    years_to_maturity DECIMAL(8,4) NOT NULL,
    ytm DECIMAL(8,6),
    after_tax_ytm DECIMAL(8,6),
    credit_rating VARCHAR(10) DEFAULT 'NR',
    scraped_date DATE NOT NULL,
    -- Bond identifiers (consistent with corporate_bond_prices structure)
    currency_code VARCHAR(3) DEFAULT 'GBP',  -- Currency code (defaulting to GBP for UK corporate bonds)
    isin VARCHAR(12),                        -- International Securities Identification Number
    short_code VARCHAR(10),                  -- AJ Bell internal identifier
    combined_id VARCHAR(30),                 -- Full formatted ID: 'Currency | ISIN | Short Code'
    data_source VARCHAR(50) DEFAULT 'AJ_Bell',  -- Track data source for cross-broker analysis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bond_name, scraped_date)
);

-- Index for AJ Bell corporate bond market data
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_scraped_date ON ajbell_corporate_bond_prices(scraped_date);
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_maturity ON ajbell_corporate_bond_prices(maturity_date);
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_company ON ajbell_corporate_bond_prices(company_name);
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_rating ON ajbell_corporate_bond_prices(credit_rating);
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_isin ON ajbell_corporate_bond_prices(isin);
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_short_code ON ajbell_corporate_bond_prices(short_code);
CREATE INDEX IF NOT EXISTS idx_ajbell_corporate_bond_data_source ON ajbell_corporate_bond_prices(data_source);

-- US TIPS (Treasury Inflation-Protected Securities) Table
CREATE TABLE IF NOT EXISTS us_tips_yields (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    maturity VARCHAR(10) NOT NULL,
    maturity_years DECIMAL(4,1) NOT NULL,
    yield_rate DECIMAL(8,4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, maturity)
);

-- US Forward Inflation Expectations Table (T5YIFR, etc.)
CREATE TABLE IF NOT EXISTS us_forward_inflation_expectations (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    maturity_label VARCHAR(10) NOT NULL,
    expectation_rate DECIMAL(8,4) NOT NULL,
    series_id VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, series_id)
);

-- Index for US TIPS data
CREATE INDEX IF NOT EXISTS idx_us_tips_yields_date ON us_tips_yields(date);
CREATE INDEX IF NOT EXISTS idx_us_tips_yields_maturity ON us_tips_yields(maturity);
CREATE INDEX IF NOT EXISTS idx_us_tips_yields_date_maturity ON us_tips_yields(date, maturity);

-- Index for US Forward Inflation Expectations
CREATE INDEX IF NOT EXISTS idx_us_forward_inflation_date ON us_forward_inflation_expectations(date);
CREATE INDEX IF NOT EXISTS idx_us_forward_inflation_maturity ON us_forward_inflation_expectations(maturity_label);
CREATE INDEX IF NOT EXISTS idx_us_forward_inflation_series ON us_forward_inflation_expectations(series_id);
CREATE INDEX IF NOT EXISTS idx_us_forward_inflation_date_series ON us_forward_inflation_expectations(date, series_id);

-- UK GDP Sector Weights Table
CREATE TABLE IF NOT EXISTS uk_gdp_sector_weights (
    id SERIAL PRIMARY KEY,
    section VARCHAR(2) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),
    weight DECIMAL(10,4) NOT NULL,
    data_source VARCHAR(50) DEFAULT 'ONS_GDP_Source_Catalogue',
    file_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(section, data_source, file_version)
);

-- Index for UK GDP Sector Weights
CREATE INDEX IF NOT EXISTS idx_uk_gdp_sector_weights_section ON uk_gdp_sector_weights(section);
CREATE INDEX IF NOT EXISTS idx_uk_gdp_sector_weights_source ON uk_gdp_sector_weights(data_source);
CREATE INDEX IF NOT EXISTS idx_uk_gdp_sector_weights_version ON uk_gdp_sector_weights(file_version);