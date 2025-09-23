-- German Economic Data Tables

-- German Bund Yield Curve Table (Bundesbank data)
CREATE TABLE IF NOT EXISTS german_bund_yields (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    maturity_years DECIMAL(6,3) NOT NULL,  -- Supports 1.0, 2.0, ..., 30.0 years
    yield_rate DECIMAL(10,4) NOT NULL,
    data_source VARCHAR(50) DEFAULT 'Bundesbank_StatisticDownload',  -- Track data source
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, maturity_years)
);

-- Indexes for German Bund yields for better query performance
CREATE INDEX IF NOT EXISTS idx_german_bund_yields_date ON german_bund_yields(date);
CREATE INDEX IF NOT EXISTS idx_german_bund_yields_maturity ON german_bund_yields(maturity_years);
CREATE INDEX IF NOT EXISTS idx_german_bund_yields_date_maturity ON german_bund_yields(date, maturity_years);
CREATE INDEX IF NOT EXISTS idx_german_bund_yields_data_source ON german_bund_yields(data_source);