-- Janakpur Bolts Analytics Database Schema v1.0
-- Created: 2026-05-15
-- Purpose: Cricket analytics for NPL T20 franchise

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text matching

-- =====================================================
-- REFERENCE TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS competitions (
    competition_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20),
    country VARCHAR(50),
    format VARCHAR(20) CHECK (format IN ('T20', 'ODI', 'Test', 'T10', 'The Hundred')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, country)
);

CREATE TABLE IF NOT EXISTS seasons (
    season_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    competition_id BIGINT NOT NULL REFERENCES competitions(competition_id),
    name VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(competition_id, year)
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    city VARCHAR(100),
    country VARCHAR(50),
    capacity INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, city)
);

CREATE TABLE IF NOT EXISTS teams (
    team_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20),
    home_venue_id BIGINT REFERENCES venues(venue_id),
    primary_color VARCHAR(7), -- hex color
    secondary_color VARCHAR(7),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name)
);

-- =====================================================
-- PLAYER TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS players (
    player_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    canonical_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    batting_hand VARCHAR(20) CHECK (batting_hand IN ('Right', 'Left', 'Unknown')),
    bowling_arm VARCHAR(20) CHECK (bowling_arm IN ('Right', 'Left', 'Unknown')),
    bowling_type VARCHAR(50),
    primary_role VARCHAR(50) CHECK (primary_role IN ('Batter', 'Bowler', 'All-rounder', 'Wicket-keeper')),
    country VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(canonical_name, date_of_birth)
);

CREATE TABLE IF NOT EXISTS player_aliases (
    alias_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(player_id),
    alias_name VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(alias_name, source)
);

-- =====================================================
-- MATCH TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS matches (
    match_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(season_id),
    match_number INT,
    match_date DATE NOT NULL,
    venue_id BIGINT REFERENCES venues(venue_id),
    team1_id BIGINT NOT NULL REFERENCES teams(team_id),
    team2_id BIGINT NOT NULL REFERENCES teams(team_id),
    toss_winner_id BIGINT REFERENCES teams(team_id),
    toss_decision VARCHAR(10) CHECK (toss_decision IN ('bat', 'field')),
    match_winner_id BIGINT REFERENCES teams(team_id),
    win_type VARCHAR(20) CHECK (win_type IN ('runs', 'wickets', 'no result', 'tie', 'DLS')),
    win_margin INT,
    player_of_match_id BIGINT REFERENCES players(player_id),
    source VARCHAR(50) NOT NULL,
    source_match_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (team1_id != team2_id),
    UNIQUE(source, source_match_id)
);

CREATE TABLE IF NOT EXISTS innings (
    innings_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id),
    innings_number INT NOT NULL CHECK (innings_number BETWEEN 1 AND 4),
    batting_team_id BIGINT NOT NULL REFERENCES teams(team_id),
    bowling_team_id BIGINT NOT NULL REFERENCES teams(team_id),
    total_runs INT NOT NULL DEFAULT 0,
    total_wickets INT NOT NULL DEFAULT 0,
    total_overs DECIMAL(3,1) NOT NULL DEFAULT 0,
    total_extras INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(match_id, innings_number),
    CHECK (batting_team_id != bowling_team_id)
);

-- =====================================================
-- CORE BALL-BY-BALL TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    innings_id BIGINT NOT NULL REFERENCES innings(innings_id),
    over_number INT NOT NULL CHECK (over_number >= 0),
    ball_number INT NOT NULL CHECK (ball_number >= 1),
    striker_id BIGINT NOT NULL REFERENCES players(player_id),
    non_striker_id BIGINT NOT NULL REFERENCES players(player_id),
    bowler_id BIGINT NOT NULL REFERENCES players(player_id),
    
    -- Runs
    runs_batter INT NOT NULL DEFAULT 0,
    runs_extras INT NOT NULL DEFAULT 0,
    runs_total INT NOT NULL DEFAULT 0,
    
    -- Extras detail
    is_wide BOOLEAN DEFAULT FALSE,
    is_noball BOOLEAN DEFAULT FALSE,
    is_bye BOOLEAN DEFAULT FALSE,
    is_legbye BOOLEAN DEFAULT FALSE,
    penalty_runs INT DEFAULT 0,
    
    -- Boundaries
    is_boundary_four BOOLEAN DEFAULT FALSE,
    is_boundary_six BOOLEAN DEFAULT FALSE,
    
    -- Wicket
    is_wicket BOOLEAN DEFAULT FALSE,
    dismissal_type VARCHAR(30),
    dismissed_player_id BIGINT REFERENCES players(player_id),
    fielder1_id BIGINT REFERENCES players(player_id),
    fielder2_id BIGINT REFERENCES players(player_id),
    
    -- Phase (computed)
    phase VARCHAR(10) CHECK (phase IN ('powerplay', 'middle', 'death')),
    
    -- Metadata
    commentary TEXT,
    source VARCHAR(50) NOT NULL,
    raw_file_path VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(innings_id, over_number, ball_number),
    CHECK (striker_id != non_striker_id)
);

-- =====================================================
-- VALIDATION TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS scorecards_batting (
    batting_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    innings_id BIGINT NOT NULL REFERENCES innings(innings_id),
    player_id BIGINT NOT NULL REFERENCES players(player_id),
    batting_position INT NOT NULL CHECK (batting_position BETWEEN 1 AND 11),
    runs_scored INT NOT NULL DEFAULT 0,
    balls_faced INT NOT NULL DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,
    strike_rate DECIMAL(5,2),
    dismissal_type VARCHAR(30),
    fielder_id BIGINT REFERENCES players(player_id),
    bowler_id BIGINT REFERENCES players(player_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(innings_id, player_id)
);

CREATE TABLE IF NOT EXISTS scorecards_bowling (
    bowling_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    innings_id BIGINT NOT NULL REFERENCES innings(innings_id),
    player_id BIGINT NOT NULL REFERENCES players(player_id),
    overs_bowled DECIMAL(3,1) NOT NULL,
    maidens INT DEFAULT 0,
    runs_conceded INT NOT NULL,
    wickets_taken INT NOT NULL DEFAULT 0,
    economy_rate DECIMAL(4,2),
    wides INT DEFAULT 0,
    noballs INT DEFAULT 0,
    fours_conceded INT DEFAULT 0,
    sixes_conceded INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(innings_id, player_id)
);

CREATE TABLE IF NOT EXISTS player_match_roles (
    role_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id),
    team_id BIGINT NOT NULL REFERENCES teams(team_id),
    player_id BIGINT NOT NULL REFERENCES players(player_id),
    is_playing_xi BOOLEAN DEFAULT FALSE,
    is_captain BOOLEAN DEFAULT FALSE,
    is_wicket_keeper BOOLEAN DEFAULT FALSE,
    is_substitute BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(match_id, team_id, player_id)
);

-- =====================================================
-- STAGING TABLES (for raw data before validation)
-- =====================================================

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.stg_deliveries (
    stg_delivery_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_match_id VARCHAR(100),
    innings_number INT,
    over_number INT,
    ball_number INT,
    striker_name VARCHAR(200),
    non_striker_name VARCHAR(200),
    bowler_name VARCHAR(200),
    runs_batter INT,
    runs_extras INT,
    runs_total INT,
    extras_type VARCHAR(20),
    is_wicket BOOLEAN,
    dismissal_type VARCHAR(50),
    dismissed_player_name VARCHAR(200),
    fielder_name VARCHAR(200),
    commentary TEXT,
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    validated BOOLEAN DEFAULT FALSE,
    validation_errors TEXT[]
);

CREATE TABLE IF NOT EXISTS staging.stg_matches (
    stg_match_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_match_id VARCHAR(100),
    competition VARCHAR(100),
    season VARCHAR(50),
    match_date DATE,
    venue VARCHAR(200),
    team1_name VARCHAR(100),
    team2_name VARCHAR(100),
    toss_winner VARCHAR(100),
    toss_decision VARCHAR(10),
    match_winner VARCHAR(100),
    win_type VARCHAR(20),
    win_margin VARCHAR(50),
    player_of_match VARCHAR(100),
    raw_json JSONB,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    validated BOOLEAN DEFAULT FALSE,
    validation_errors TEXT[]
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX idx_deliveries_innings ON deliveries(innings_id);
CREATE INDEX idx_deliveries_striker ON deliveries(striker_id);
CREATE INDEX idx_deliveries_bowler ON deliveries(bowler_id);
CREATE INDEX idx_deliveries_phase ON deliveries(phase);
CREATE INDEX idx_deliveries_wicket ON deliveries(is_wicket) WHERE is_wicket = TRUE;

CREATE INDEX idx_matches_season ON matches(season_id);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_teams ON matches(team1_id, team2_id);

CREATE INDEX idx_player_aliases_name ON player_aliases USING gin(alias_name gin_trgm_ops);
CREATE INDEX idx_players_name ON players USING gin(canonical_name gin_trgm_ops);

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE deliveries IS 'Core ball-by-ball data - the atomic unit of cricket analytics';
COMMENT ON TABLE players IS 'Canonical player registry with deduplicated names';
COMMENT ON TABLE player_aliases IS 'Maps various name spellings to canonical players';
COMMENT ON COLUMN deliveries.phase IS 'T20 phase: powerplay (1-6), middle (7-15), death (16-20)';
COMMENT ON COLUMN deliveries.runs_total IS 'runs_batter + runs_extras for this delivery';
COMMENT ON SCHEMA staging IS 'Temporary tables for unvalidated scraped data';

-- =====================================================
-- INITIAL DATA (Competition and Teams)
-- =====================================================

INSERT INTO competitions (name, short_name, country, format) VALUES 
('Nepal Premier League', 'NPL', 'Nepal', 'T20'),
('Prime Minister Cup', 'PM Cup', 'Nepal', 'T20')
ON CONFLICT DO NOTHING;

INSERT INTO venues (name, city, country) VALUES
('Tribhuvan University International Cricket Ground', 'Kirtipur', 'Nepal')
ON CONFLICT DO NOTHING;

INSERT INTO teams (name, short_name) VALUES
('Janakpur Bolts', 'JKB'),
('Kathmandu Kings XI', 'KTM'),
('Sudurpashchim Royals', 'SPR'),
('Pokhara Avengers', 'PKR'),
('Chitwan Tigers', 'CTG'),
('Lumbini Lions', 'LMB'),
('Karnali Yaks', 'KYK'),
('Biratnagar Warriors', 'BTW')
ON CONFLICT DO NOTHING;

-- Create update trigger for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_competitions_updated_at BEFORE UPDATE ON competitions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_seasons_updated_at BEFORE UPDATE ON seasons
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_innings_updated_at BEFORE UPDATE ON innings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
