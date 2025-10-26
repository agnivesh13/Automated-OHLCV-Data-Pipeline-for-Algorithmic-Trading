/*
  PostgreSQL Schema for AWS RDS - Stock Price Data Pipeline
  
  This schema supports metadata tracking and reference data for the AWS pipeline:
  - security_master: Master data for securities/instruments
  - marketcap_snapshot: Daily market capitalization snapshots  
  - ohlcv_metadata: Metadata for OHLCV data ingestion and ETL processing
  
  NOTE: This is for AWS RDS PostgreSQL, not Supabase
*/

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS stock_data;

-- Set search path
SET search_path TO stock_data, public;

-- Security Master Table
CREATE TABLE IF NOT EXISTS security_master (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol varchar(50) NOT NULL,
    exchange varchar(20) NOT NULL,
    isin_code varchar(12) UNIQUE,
    company_name varchar(200) NOT NULL,
    sector varchar(100),
    industry varchar(100),
    market_lot int DEFAULT 1,
    face_value decimal(10,2),
    listing_date date,
    instrument_type varchar(50) DEFAULT 'EQUITY',
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    CONSTRAINT uk_symbol_exchange UNIQUE (symbol, exchange),
    CONSTRAINT chk_symbol_format CHECK (length(symbol) >= 2),
    CONSTRAINT chk_exchange_valid CHECK (exchange IN ('NSE', 'BSE', 'MCX', 'NCDEX'))
);

-- OHLCV Metadata Table (Main table for Parquet tracking)
CREATE TABLE IF NOT EXISTS ohlcv_metadata (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    s3_path varchar(500) NOT NULL,
    processing_date date NOT NULL,
    resolution varchar(10) NOT NULL,
    row_count bigint NOT NULL,
    file_size_bytes bigint NOT NULL,
    symbols_count int NOT NULL,
    ingested_at timestamptz NOT NULL,
    processing_status varchar(50) DEFAULT 'completed',
    error_message text,
    glue_job_run_id varchar(100),
    data_quality_score decimal(5,2),
    parquet_files_created int DEFAULT 0,
    partition_count int DEFAULT 0,
    compression_ratio decimal(5,2),
    created_at timestamptz DEFAULT now(),
    
    CONSTRAINT chk_row_count_positive CHECK (row_count >= 0),
    CONSTRAINT chk_file_size_positive CHECK (file_size_bytes >= 0),
    CONSTRAINT chk_symbols_count_positive CHECK (symbols_count >= 0),
    CONSTRAINT chk_status_valid CHECK (
        processing_status IN ('processing', 'completed', 'failed', 'partial')
    )
);

-- Market Cap Snapshot Table
CREATE TABLE IF NOT EXISTS marketcap_snapshot (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol varchar(50) NOT NULL,
    exchange varchar(20) NOT NULL,
    snapshot_date date NOT NULL,
    market_cap_cr decimal(15,2) NOT NULL,
    shares_outstanding bigint,
    close_price decimal(10,2) NOT NULL,
    free_float_market_cap_cr decimal(15,2),
    rank_by_market_cap int,
    rank_by_free_float int,
    created_at timestamptz DEFAULT now(),
    
    CONSTRAINT uk_marketcap_symbol_date UNIQUE (symbol, exchange, snapshot_date),
    CONSTRAINT chk_market_cap_positive CHECK (market_cap_cr > 0),
    CONSTRAINT chk_close_price_positive CHECK (close_price > 0)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_security_master_symbol ON security_master(symbol);
CREATE INDEX IF NOT EXISTS idx_security_master_exchange ON security_master(exchange);
CREATE INDEX IF NOT EXISTS idx_ohlcv_metadata_date ON ohlcv_metadata(processing_date DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_metadata_status ON ohlcv_metadata(processing_status);
CREATE INDEX IF NOT EXISTS idx_ohlcv_metadata_s3_path ON ohlcv_metadata(s3_path);
CREATE INDEX IF NOT EXISTS idx_marketcap_snapshot_date ON marketcap_snapshot(snapshot_date DESC);

-- Sample data for major NSE stocks
INSERT INTO security_master (symbol, exchange, company_name, sector, is_active) VALUES
('RELIANCE', 'NSE', 'Reliance Industries Limited', 'Oil & Gas', true),
('TCS', 'NSE', 'Tata Consultancy Services Limited', 'Information Technology', true),  
('HDFCBANK', 'NSE', 'HDFC Bank Limited', 'Banking', true),
('INFY', 'NSE', 'Infosys Limited', 'Information Technology', true),
('HINDUNILVR', 'NSE', 'Hindustan Unilever Limited', 'Consumer Goods', true),
('ICICIBANK', 'NSE', 'ICICI Bank Limited', 'Banking', true),
('KOTAKBANK', 'NSE', 'Kotak Mahindra Bank Limited', 'Banking', true),
('SBIN', 'NSE', 'State Bank of India', 'Banking', true),
('BHARTIARTL', 'NSE', 'Bharti Airtel Limited', 'Telecommunications', true),
('ITC', 'NSE', 'ITC Limited', 'Consumer Goods', true)
ON CONFLICT (symbol, exchange) DO NOTHING;

-- Views for monitoring
CREATE OR REPLACE VIEW v_parquet_processing_summary AS
SELECT 
    processing_date,
    resolution,
    COUNT(*) as total_files,
    SUM(row_count) as total_records,
    SUM(file_size_bytes) as total_size_bytes,
    SUM(parquet_files_created) as total_parquet_files,
    AVG(compression_ratio) as avg_compression_ratio,
    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as successful_files,
    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_files
FROM ohlcv_metadata
GROUP BY processing_date, resolution
ORDER BY processing_date DESC;

-- Grant permissions
GRANT USAGE ON SCHEMA stock_data TO public;
GRANT SELECT ON ALL TABLES IN SCHEMA stock_data TO public;
GRANT INSERT, UPDATE ON ohlcv_metadata TO public;
