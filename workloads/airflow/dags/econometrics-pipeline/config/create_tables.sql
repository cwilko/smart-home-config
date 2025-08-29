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
CREATE INDEX IF NOT EXISTS idx_unemployment_date ON unemployment_rate(date);
CREATE INDEX IF NOT EXISTS idx_gdp_quarter ON gross_domestic_product(quarter);
CREATE INDEX IF NOT EXISTS idx_sp500_date ON sp500_index(date);
CREATE INDEX IF NOT EXISTS idx_vix_date ON vix_index(date);
CREATE INDEX IF NOT EXISTS idx_pe_ratios_date ON pe_ratios(date);
CREATE INDEX IF NOT EXISTS idx_fred_treasury_date_series ON fred_treasury_yields(date, series_id);
CREATE INDEX IF NOT EXISTS idx_fred_treasury_maturity ON fred_treasury_yields(maturity);