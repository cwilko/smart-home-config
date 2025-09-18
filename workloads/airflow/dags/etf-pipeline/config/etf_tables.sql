-- ETF Data Tables for UK Market Analysis
-- Supporting ETF arbitrage strategies

-- ETF NAV and Price Historical Data
CREATE TABLE IF NOT EXISTS etf_nav_history (
    date DATE NOT NULL,
    etf_ticker VARCHAR(10) NOT NULL,
    nav DECIMAL(12, 6) NOT NULL,
    market_price DECIMAL(12, 6), -- Market/trading price for premium/discount analysis
    currency VARCHAR(3) DEFAULT 'GBP',
    data_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date, etf_ticker)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_etf_nav_ticker ON etf_nav_history (etf_ticker);
CREATE INDEX IF NOT EXISTS idx_etf_nav_date ON etf_nav_history (date DESC);
CREATE INDEX IF NOT EXISTS idx_etf_nav_source ON etf_nav_history (data_source);

-- ETF Price Historical Data (from investing.com)
CREATE TABLE IF NOT EXISTS etf_price_history (
    date DATE NOT NULL,
    etf_ticker VARCHAR(10) NOT NULL,
    symbol VARCHAR(100) NOT NULL,
    open_price DECIMAL(12, 6) NOT NULL,
    high_price DECIMAL(12, 6) NOT NULL,
    low_price DECIMAL(12, 6) NOT NULL,
    close_price DECIMAL(12, 6) NOT NULL,
    currency VARCHAR(3) DEFAULT 'GBP',
    provider VARCHAR(50) NOT NULL,
    data_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date, etf_ticker)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_etf_price_ticker ON etf_price_history (etf_ticker);
CREATE INDEX IF NOT EXISTS idx_etf_price_date ON etf_price_history (date DESC);
CREATE INDEX IF NOT EXISTS idx_etf_price_source ON etf_price_history (data_source);

