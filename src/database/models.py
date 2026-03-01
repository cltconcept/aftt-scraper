"""
Modèles de données pour la base SQLite AFTT
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date


@dataclass
class Club:
    """Représente un club de tennis de table."""
    code: str
    name: str
    province: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    website: Optional[str] = None
    has_shower: Optional[bool] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_phone: Optional[str] = None
    venue_pmr: Optional[bool] = None
    venue_remarks: Optional[str] = None
    teams_men: int = 0
    teams_women: int = 0
    teams_youth: int = 0
    teams_veterans: int = 0
    label: Optional[str] = None
    palette: Optional[str] = None


@dataclass
class Player:
    """Représente un joueur."""
    licence: str
    name: str
    club_code: Optional[str] = None
    ranking: Optional[str] = None
    category: Optional[str] = None  # S, J, V, etc.
    points_start: Optional[float] = None
    points_current: Optional[float] = None
    ranking_position: Optional[int] = None
    total_wins: int = 0
    total_losses: int = 0
    # Stats féminines (si applicable)
    women_points_start: Optional[float] = None
    women_points_current: Optional[float] = None
    women_total_wins: int = 0
    women_total_losses: int = 0
    last_update: Optional[str] = None


@dataclass
class Match:
    """Représente un match individuel."""
    id: Optional[int] = None
    player_licence: str = ""
    fiche_type: str = "masculine"  # "masculine" ou "feminine"
    date: Optional[str] = None
    division: Optional[str] = None
    opponent_club: Optional[str] = None
    opponent_name: str = ""
    opponent_licence: Optional[str] = None
    opponent_ranking: Optional[str] = None
    opponent_points: Optional[float] = None
    score: str = ""
    won: bool = False
    points_change: Optional[float] = None


@dataclass
class PlayerStats:
    """Statistiques par classement adverse."""
    id: Optional[int] = None
    player_licence: str = ""
    fiche_type: str = "masculine"
    opponent_ranking: str = ""
    wins: int = 0
    losses: int = 0
    ratio: float = 0.0


@dataclass
class ScrapeTask:
    """Représente une tâche de scraping."""
    id: Optional[int] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    status: str = "running"  # running, success, failed, cancelled
    total_clubs: int = 0
    completed_clubs: int = 0
    total_players: int = 0
    errors_count: int = 0
    errors_detail: Optional[str] = None  # JSON des erreurs
    trigger_type: str = "manual"  # manual, cron
    current_club: Optional[str] = None
    current_province: Optional[str] = None


@dataclass
class Tournament:
    """Représente un tournoi de tennis de table."""
    t_id: int
    name: str
    level: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    reference: Optional[str] = None
    series_count: int = 0


@dataclass
class TournamentSeries:
    """Représente une série d'un tournoi."""
    id: Optional[int] = None
    tournament_id: int = 0
    series_name: str = ""
    date: Optional[str] = None
    time: Optional[str] = None
    inscriptions_count: int = 0
    inscriptions_max: int = 0


@dataclass
class TournamentInscription:
    """Représente une inscription à un tournoi."""
    id: Optional[int] = None
    tournament_id: int = 0
    series_name: str = ""
    player_licence: str = ""
    player_name: str = ""
    player_club: Optional[str] = None
    player_ranking: Optional[str] = None


@dataclass
class TournamentResult:
    """Représente un résultat de match dans un tournoi."""
    id: Optional[int] = None
    tournament_id: int = 0
    series_name: str = ""
    player1_licence: Optional[str] = None
    player1_name: str = ""
    player2_licence: Optional[str] = None
    player2_name: str = ""
    score: str = ""
    winner_licence: Optional[str] = None
    round: Optional[str] = None


@dataclass
class InterclubsDivision:
    """Représente une division interclubs."""
    id: Optional[int] = None
    division_index: int = 0
    division_id: Optional[str] = None  # valeur option du <select> (ex: "8662")
    division_name: str = ""
    division_category: Optional[str] = None
    division_gender: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'division_index': self.division_index,
            'division_id': self.division_id,
            'division_name': self.division_name,
            'division_category': self.division_category,
            'division_gender': self.division_gender,
        }


@dataclass
class InterclubsRanking:
    """Représente un classement d'équipe dans une division/semaine."""
    id: Optional[int] = None
    division_index: int = 0
    division_name: str = ""
    week: int = 0
    rank: Optional[int] = None
    team_name: str = ""
    played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    forfeits: int = 0
    points: int = 0

    def to_dict(self) -> dict:
        return {
            'division_index': self.division_index,
            'division_name': self.division_name,
            'week': self.week,
            'rank': self.rank,
            'team_name': self.team_name,
            'played': self.played,
            'wins': self.wins,
            'losses': self.losses,
            'draws': self.draws,
            'forfeits': self.forfeits,
            'points': self.points,
        }


# SQL pour créer les tables
CREATE_TABLES_SQL = """
-- Table des clubs
CREATE TABLE IF NOT EXISTS clubs (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    province TEXT,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    status TEXT,
    website TEXT,
    has_shower BOOLEAN,
    venue_name TEXT,
    venue_address TEXT,
    venue_phone TEXT,
    venue_pmr BOOLEAN,
    venue_remarks TEXT,
    teams_men INTEGER DEFAULT 0,
    teams_women INTEGER DEFAULT 0,
    teams_youth INTEGER DEFAULT 0,
    teams_veterans INTEGER DEFAULT 0,
    label TEXT,
    palette TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des joueurs
CREATE TABLE IF NOT EXISTS players (
    licence TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    club_code TEXT REFERENCES clubs(code),
    ranking TEXT,
    category TEXT,
    points_start REAL,
    points_current REAL,
    ranking_position INTEGER,
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    women_ranking TEXT,
    women_points_start REAL,
    women_points_current REAL,
    women_total_wins INTEGER DEFAULT 0,
    women_total_losses INTEGER DEFAULT 0,
    last_update TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des matchs
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_licence TEXT NOT NULL REFERENCES players(licence),
    fiche_type TEXT DEFAULT 'masculine',
    date TEXT,
    division TEXT,
    opponent_club TEXT,
    opponent_name TEXT NOT NULL,
    opponent_licence TEXT,
    opponent_ranking TEXT,
    opponent_points REAL,
    score TEXT,
    won BOOLEAN,
    points_change REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_licence, fiche_type, date, opponent_licence, score)
);

-- Table des statistiques par classement
CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_licence TEXT NOT NULL REFERENCES players(licence),
    fiche_type TEXT DEFAULT 'masculine',
    opponent_ranking TEXT,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ratio REAL DEFAULT 0.0,
    UNIQUE(player_licence, fiche_type, opponent_ranking)
);

-- Table des tâches de scraping
CREATE TABLE IF NOT EXISTS scrape_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    status TEXT DEFAULT 'running',
    total_clubs INTEGER DEFAULT 0,
    completed_clubs INTEGER DEFAULT 0,
    total_players INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    errors_detail TEXT,
    trigger_type TEXT DEFAULT 'manual',
    current_club TEXT,
    current_province TEXT
);

-- Table des tournois
CREATE TABLE IF NOT EXISTS tournaments (
    t_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    level TEXT,
    date_start TEXT,
    date_end TEXT,
    reference TEXT,
    series_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des séries de tournoi
CREATE TABLE IF NOT EXISTS tournament_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(t_id),
    series_name TEXT NOT NULL,
    date TEXT,
    time TEXT,
    inscriptions_count INTEGER DEFAULT 0,
    inscriptions_max INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, series_name)
);

-- Table des inscriptions aux tournois
CREATE TABLE IF NOT EXISTS tournament_inscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(t_id),
    series_name TEXT,
    player_licence TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_club TEXT,
    player_ranking TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tournament_id, series_name, player_licence)
);

-- Table des résultats de tournoi
CREATE TABLE IF NOT EXISTS tournament_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(t_id),
    series_name TEXT,
    player1_licence TEXT,
    player1_name TEXT,
    player2_licence TEXT,
    player2_name TEXT,
    score TEXT,
    winner_licence TEXT,
    round TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des divisions interclubs
CREATE TABLE IF NOT EXISTS interclubs_divisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    division_index INTEGER NOT NULL,
    division_id TEXT,
    division_name TEXT NOT NULL,
    division_category TEXT,
    division_gender TEXT,
    UNIQUE(division_index)
);

-- Table des classements par division et semaine
CREATE TABLE IF NOT EXISTS interclubs_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    division_index INTEGER NOT NULL,
    division_name TEXT NOT NULL,
    week INTEGER NOT NULL,
    rank INTEGER,
    team_name TEXT NOT NULL,
    played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    forfeits INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    UNIQUE(division_index, week, team_name)
);

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_players_club ON players(club_code);
CREATE INDEX IF NOT EXISTS idx_players_ranking ON players(ranking);
CREATE INDEX IF NOT EXISTS idx_players_points ON players(points_current);
CREATE INDEX IF NOT EXISTS idx_matches_player ON matches(player_licence);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_opponent ON matches(opponent_licence);
CREATE INDEX IF NOT EXISTS idx_matches_player_fiche ON matches(player_licence, fiche_type);
CREATE INDEX IF NOT EXISTS idx_player_stats_licence_fiche ON player_stats(player_licence, fiche_type);
CREATE INDEX IF NOT EXISTS idx_clubs_province ON clubs(province);
CREATE INDEX IF NOT EXISTS idx_scrape_tasks_status ON scrape_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tournaments_level ON tournaments(level);
CREATE INDEX IF NOT EXISTS idx_tournaments_date ON tournaments(date_start);
CREATE INDEX IF NOT EXISTS idx_tournament_series_tournament ON tournament_series(tournament_id);
CREATE INDEX IF NOT EXISTS idx_tournament_inscriptions_tournament ON tournament_inscriptions(tournament_id);
CREATE INDEX IF NOT EXISTS idx_tournament_inscriptions_player ON tournament_inscriptions(player_licence);
CREATE INDEX IF NOT EXISTS idx_tournament_results_tournament ON tournament_results(tournament_id);
CREATE INDEX IF NOT EXISTS idx_interclubs_rankings_division ON interclubs_rankings(division_index);
CREATE INDEX IF NOT EXISTS idx_interclubs_rankings_week ON interclubs_rankings(week);
CREATE INDEX IF NOT EXISTS idx_interclubs_rankings_team ON interclubs_rankings(team_name);
CREATE INDEX IF NOT EXISTS idx_interclubs_rankings_div_week ON interclubs_rankings(division_index, week);
"""
