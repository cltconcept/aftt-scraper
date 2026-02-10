"""
Requêtes et opérations sur la base de données AFTT
"""
import sqlite3
from typing import List, Optional, Dict, Any
from .connection import get_db
from .models import Club, Player, Match, PlayerStats, InterclubsDivision, InterclubsRanking


# =============================================================================
# CLUBS
# =============================================================================

def insert_club(club: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour un club."""
    sql = """
    INSERT INTO clubs (code, name, province, full_name, email, phone, status, 
                       website, has_shower, venue_name, venue_address, venue_phone,
                       venue_pmr, venue_remarks, teams_men, teams_women, teams_youth,
                       teams_veterans, label, palette)
    VALUES (:code, :name, :province, :full_name, :email, :phone, :status,
            :website, :has_shower, :venue_name, :venue_address, :venue_phone,
            :venue_pmr, :venue_remarks, :teams_men, :teams_women, :teams_youth,
            :teams_veterans, :label, :palette)
    ON CONFLICT(code) DO UPDATE SET
        name = COALESCE(excluded.name, clubs.name),
        province = COALESCE(excluded.province, clubs.province),
        full_name = COALESCE(excluded.full_name, clubs.full_name),
        email = COALESCE(excluded.email, clubs.email),
        phone = COALESCE(excluded.phone, clubs.phone),
        status = COALESCE(excluded.status, clubs.status),
        website = COALESCE(excluded.website, clubs.website),
        has_shower = COALESCE(excluded.has_shower, clubs.has_shower),
        venue_name = COALESCE(excluded.venue_name, clubs.venue_name),
        venue_address = COALESCE(excluded.venue_address, clubs.venue_address),
        venue_phone = COALESCE(excluded.venue_phone, clubs.venue_phone),
        venue_pmr = COALESCE(excluded.venue_pmr, clubs.venue_pmr),
        venue_remarks = COALESCE(excluded.venue_remarks, clubs.venue_remarks),
        teams_men = COALESCE(excluded.teams_men, clubs.teams_men),
        teams_women = COALESCE(excluded.teams_women, clubs.teams_women),
        teams_youth = COALESCE(excluded.teams_youth, clubs.teams_youth),
        teams_veterans = COALESCE(excluded.teams_veterans, clubs.teams_veterans),
        label = COALESCE(excluded.label, clubs.label),
        palette = COALESCE(excluded.palette, clubs.palette),
        updated_at = CURRENT_TIMESTAMP
    """
    
    # Valeurs par défaut - convertir les chaînes vides en None pour que COALESCE fonctionne
    def normalize(val):
        """Convertit les chaînes vides en None."""
        if val is None or (isinstance(val, str) and val.strip() == ''):
            return None
        return val
    
    data = {
        'code': club.get('code'),
        'name': normalize(club.get('name')),
        'province': normalize(club.get('province')),
        'full_name': normalize(club.get('full_name')),
        'email': normalize(club.get('email')),
        'phone': normalize(club.get('phone')),
        'status': normalize(club.get('status')),
        'website': normalize(club.get('website')),
        'has_shower': club.get('has_shower'),
        'venue_name': normalize(club.get('venue_name')),
        'venue_address': normalize(club.get('venue_address')),
        'venue_phone': normalize(club.get('venue_phone')),
        'venue_pmr': club.get('venue_pmr'),
        'venue_remarks': normalize(club.get('venue_remarks')),
        'teams_men': club.get('teams_men', 0),
        'teams_women': club.get('teams_women', 0),
        'teams_youth': club.get('teams_youth', 0),
        'teams_veterans': club.get('teams_veterans', 0),
        'label': normalize(club.get('label')),
        'palette': normalize(club.get('palette')),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_all_clubs(province: str = None, limit: int = None, offset: int = 0) -> List[Dict]:
    """Récupère tous les clubs avec filtres optionnels."""
    sql = "SELECT * FROM clubs"
    params = []
    
    if province:
        sql += " WHERE province = ?"
        params.append(province)
    
    sql += " ORDER BY code"
    
    if limit:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_club(code: str) -> Optional[Dict]:
    """Récupère un club par son code."""
    with get_db() as db:
        cursor = db.execute("SELECT * FROM clubs WHERE code = ?", (code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_provinces() -> List[str]:
    """Récupère la liste des provinces distinctes."""
    with get_db() as db:
        cursor = db.execute("SELECT DISTINCT province FROM clubs WHERE province IS NOT NULL ORDER BY province")
        return [row[0] for row in cursor.fetchall()]


# =============================================================================
# PLAYERS
# =============================================================================

def insert_player(player: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour un joueur."""
    sql = """
    INSERT INTO players (licence, name, club_code, ranking, category, points_start,
                         points_current, ranking_position, total_wins, total_losses,
                         women_points_start, women_points_current, women_total_wins,
                         women_total_losses, last_update)
    VALUES (:licence, :name, :club_code, :ranking, :category, :points_start,
            :points_current, :ranking_position, :total_wins, :total_losses,
            :women_points_start, :women_points_current, :women_total_wins,
            :women_total_losses, :last_update)
    ON CONFLICT(licence) DO UPDATE SET
        name = COALESCE(NULLIF(excluded.name, ''), players.name),
        club_code = COALESCE(excluded.club_code, players.club_code),
        ranking = COALESCE(NULLIF(excluded.ranking, ''), players.ranking),
        category = COALESCE(excluded.category, players.category),
        points_start = COALESCE(excluded.points_start, players.points_start),
        points_current = COALESCE(excluded.points_current, players.points_current),
        ranking_position = COALESCE(excluded.ranking_position, players.ranking_position),
        total_wins = COALESCE(excluded.total_wins, players.total_wins),
        total_losses = COALESCE(excluded.total_losses, players.total_losses),
        women_points_start = COALESCE(excluded.women_points_start, players.women_points_start),
        women_points_current = COALESCE(excluded.women_points_current, players.women_points_current),
        women_total_wins = COALESCE(excluded.women_total_wins, players.women_total_wins),
        women_total_losses = COALESCE(excluded.women_total_losses, players.women_total_losses),
        last_update = COALESCE(excluded.last_update, players.last_update),
        updated_at = CURRENT_TIMESTAMP
    """
    
    data = {
        'licence': player.get('licence'),
        'name': player.get('name'),
        'club_code': player.get('club_code'),
        'ranking': player.get('ranking'),
        'category': player.get('category'),
        'points_start': player.get('points_start'),
        'points_current': player.get('points_current'),
        'ranking_position': player.get('ranking_position'),
        'total_wins': player.get('total_wins', 0),
        'total_losses': player.get('total_losses', 0),
        'women_points_start': player.get('women_points_start'),
        'women_points_current': player.get('women_points_current'),
        'women_total_wins': player.get('women_total_wins', 0),
        'women_total_losses': player.get('women_total_losses', 0),
        'last_update': player.get('last_update'),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_all_players(
    club_code: str = None,
    ranking: str = None,
    min_points: float = None,
    max_points: float = None,
    search: str = None,
    limit: int = None,
    offset: int = 0,
    order_by: str = "points_current DESC"
) -> List[Dict]:
    """Récupère les joueurs avec filtres."""
    sql = "SELECT * FROM players WHERE 1=1"
    params = []
    
    if club_code:
        sql += " AND club_code = ?"
        params.append(club_code)
    
    if ranking:
        sql += " AND ranking = ?"
        params.append(ranking)
    
    if min_points is not None:
        sql += " AND points_current >= ?"
        params.append(min_points)
    
    if max_points is not None:
        sql += " AND points_current <= ?"
        params.append(max_points)
    
    if search:
        sql += " AND (name LIKE ? OR licence LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    # Validation de order_by pour éviter injection SQL
    allowed_orders = ["points_current DESC", "points_current ASC", "name ASC", "name DESC", 
                      "ranking ASC", "ranking DESC", "ranking_position ASC"]
    if order_by not in allowed_orders:
        order_by = "points_current DESC"
    
    sql += f" ORDER BY {order_by}"
    
    if limit:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_player(licence: str) -> Optional[Dict]:
    """Récupère un joueur par sa licence."""
    with get_db() as db:
        cursor = db.execute("SELECT * FROM players WHERE licence = ?", (licence,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_club_players(club_code: str) -> List[Dict]:
    """Récupère tous les joueurs d'un club."""
    return get_all_players(club_code=club_code, order_by="points_current DESC")


# =============================================================================
# MATCHES
# =============================================================================

def insert_match(match: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère un match (ignore si doublon)."""
    sql = """
    INSERT OR IGNORE INTO matches (player_licence, fiche_type, date, division, 
                                   opponent_club, opponent_name, opponent_licence,
                                   opponent_ranking, opponent_points, score, won, points_change)
    VALUES (:player_licence, :fiche_type, :date, :division, :opponent_club,
            :opponent_name, :opponent_licence, :opponent_ranking, :opponent_points,
            :score, :won, :points_change)
    """
    
    data = {
        'player_licence': match.get('player_licence'),
        'fiche_type': match.get('fiche_type', 'masculine'),
        'date': match.get('date'),
        'division': match.get('division'),
        'opponent_club': match.get('opponent_club'),
        'opponent_name': match.get('opponent_name'),
        'opponent_licence': match.get('opponent_licence'),
        'opponent_ranking': match.get('opponent_ranking'),
        'opponent_points': match.get('opponent_points'),
        'score': match.get('score'),
        'won': match.get('won', False),
        'points_change': match.get('points_change'),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_player_matches(
    licence: str,
    fiche_type: str = None,
    opponent_licence: str = None,
    limit: int = None
) -> List[Dict]:
    """Récupère les matchs d'un joueur."""
    sql = "SELECT * FROM matches WHERE player_licence = ?"
    params = [licence]
    
    if fiche_type:
        sql += " AND fiche_type = ?"
        params.append(fiche_type)
    
    if opponent_licence:
        sql += " AND opponent_licence = ?"
        params.append(opponent_licence)
    
    sql += " ORDER BY date DESC"
    
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_head_to_head(licence1: str, licence2: str) -> Dict:
    """Récupère l'historique des confrontations entre deux joueurs."""
    with get_db() as db:
        # Matchs de licence1 contre licence2
        cursor = db.execute("""
            SELECT * FROM matches 
            WHERE player_licence = ? AND opponent_licence = ?
            ORDER BY date DESC
        """, (licence1, licence2))
        matches_1v2 = [dict(row) for row in cursor.fetchall()]
        
        # Matchs de licence2 contre licence1
        cursor = db.execute("""
            SELECT * FROM matches 
            WHERE player_licence = ? AND opponent_licence = ?
            ORDER BY date DESC
        """, (licence2, licence1))
        matches_2v1 = [dict(row) for row in cursor.fetchall()]
        
        wins_1 = sum(1 for m in matches_1v2 if m['won'])
        wins_2 = sum(1 for m in matches_2v1 if m['won'])
        
        return {
            'player1_licence': licence1,
            'player2_licence': licence2,
            'player1_wins': wins_1,
            'player2_wins': wins_2,
            'total_matches': len(matches_1v2) + len(matches_2v1),
            'matches': matches_1v2 + matches_2v1
        }


# =============================================================================
# PLAYER STATS
# =============================================================================

def insert_player_stat(stat: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour une statistique par classement."""
    sql = """
    INSERT INTO player_stats (player_licence, fiche_type, opponent_ranking, wins, losses, ratio)
    VALUES (:player_licence, :fiche_type, :opponent_ranking, :wins, :losses, :ratio)
    ON CONFLICT(player_licence, fiche_type, opponent_ranking) DO UPDATE SET
        wins = excluded.wins,
        losses = excluded.losses,
        ratio = excluded.ratio
    """
    
    data = {
        'player_licence': stat.get('player_licence'),
        'fiche_type': stat.get('fiche_type', 'masculine'),
        'opponent_ranking': stat.get('opponent_ranking') or stat.get('ranking'),
        'wins': stat.get('wins', 0),
        'losses': stat.get('losses', 0),
        'ratio': stat.get('ratio', 0.0),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_player_stats(licence: str, fiche_type: str = None) -> List[Dict]:
    """Récupère les statistiques d'un joueur par classement adverse."""
    sql = "SELECT * FROM player_stats WHERE player_licence = ?"
    params = [licence]
    
    if fiche_type:
        sql += " AND fiche_type = ?"
        params.append(fiche_type)
    
    sql += " ORDER BY opponent_ranking"
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# RANKINGS & STATISTICS
# =============================================================================

def get_top_players(
    limit: int = 100,
    province: str = None,
    club_code: str = None,
    ranking: str = None
) -> List[Dict]:
    """Récupère le classement des meilleurs joueurs."""
    sql = """
        SELECT p.*, c.name as club_name, c.province
        FROM players p
        LEFT JOIN clubs c ON p.club_code = c.code
        WHERE p.points_current IS NOT NULL
    """
    params = []
    
    if province:
        sql += " AND c.province = ?"
        params.append(province)
    
    if club_code:
        sql += " AND p.club_code = ?"
        params.append(club_code)
    
    if ranking:
        sql += " AND p.ranking = ?"
        params.append(ranking)
    
    sql += " ORDER BY p.points_current DESC LIMIT ?"
    params.append(limit)
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_top_progressions(limit: int = 100) -> List[Dict]:
    """Récupère les meilleures progressions de la saison."""
    sql = """
        SELECT p.*, c.name as club_name,
               (p.points_current - p.points_start) as progression
        FROM players p
        LEFT JOIN clubs c ON p.club_code = c.code
        WHERE p.points_start IS NOT NULL AND p.points_current IS NOT NULL
        ORDER BY progression DESC
        LIMIT ?
    """
    
    with get_db() as db:
        cursor = db.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def search_players(query: str, limit: int = 50) -> List[Dict]:
    """Recherche de joueurs par nom ou licence."""
    sql = """
        SELECT p.*, c.name as club_name
        FROM players p
        LEFT JOIN clubs c ON p.club_code = c.code
        WHERE p.name LIKE ? OR p.licence LIKE ?
        ORDER BY p.points_current DESC NULLS LAST
        LIMIT ?
    """
    
    with get_db() as db:
        cursor = db.execute(sql, (f"%{query}%", f"%{query}%", limit))
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# GESTION DES TÂCHES DE SCRAPING
# =============================================================================

def create_scrape_task(trigger_type: str = "manual", total_clubs: int = 0) -> int:
    """Crée une nouvelle tâche de scraping et retourne son ID."""
    sql = """
        INSERT INTO scrape_tasks (trigger_type, total_clubs, status)
        VALUES (?, ?, 'running')
    """
    with get_db() as db:
        cursor = db.execute(sql, (trigger_type, total_clubs))
        return cursor.lastrowid


def update_scrape_task(
    task_id: int,
    completed_clubs: int = None,
    total_clubs: int = None,
    total_players: int = None,
    current_club: str = None,
    current_province: str = None,
    status: str = None,
    errors_count: int = None,
    errors_detail: str = None
):
    """Met à jour une tâche de scraping."""
    updates = []
    values = []
    
    if completed_clubs is not None:
        updates.append("completed_clubs = ?")
        values.append(completed_clubs)
    if total_clubs is not None:
        updates.append("total_clubs = ?")
        values.append(total_clubs)
    if total_players is not None:
        updates.append("total_players = ?")
        values.append(total_players)
    if current_club is not None:
        updates.append("current_club = ?")
        values.append(current_club)
    if current_province is not None:
        updates.append("current_province = ?")
        values.append(current_province)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
        if status in ('success', 'failed', 'cancelled'):
            updates.append("finished_at = CURRENT_TIMESTAMP")
    if errors_count is not None:
        updates.append("errors_count = ?")
        values.append(errors_count)
    if errors_detail is not None:
        updates.append("errors_detail = ?")
        values.append(errors_detail)
    
    if not updates:
        return
    
    sql = f"UPDATE scrape_tasks SET {', '.join(updates)} WHERE id = ?"
    values.append(task_id)
    
    with get_db() as db:
        db.execute(sql, values)


def get_current_scrape_task() -> Optional[Dict]:
    """Récupère la tâche de scraping en cours (si existe)."""
    sql = """
        SELECT * FROM scrape_tasks 
        WHERE status = 'running'
        ORDER BY started_at DESC
        LIMIT 1
    """
    with get_db() as db:
        cursor = db.execute(sql)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_scrape_task_history(limit: int = 20) -> List[Dict]:
    """Récupère l'historique des tâches de scraping."""
    sql = """
        SELECT * FROM scrape_tasks
        ORDER BY started_at DESC
        LIMIT ?
    """
    with get_db() as db:
        cursor = db.execute(sql, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_scrape_task_by_id(task_id: int) -> Optional[Dict]:
    """Récupère une tâche par son ID."""
    sql = "SELECT * FROM scrape_tasks WHERE id = ?"
    with get_db() as db:
        cursor = db.execute(sql, (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def cancel_running_tasks():
    """Annule toutes les tâches en cours (au démarrage de l'app)."""
    sql = """
        UPDATE scrape_tasks 
        SET status = 'cancelled', finished_at = CURRENT_TIMESTAMP 
        WHERE status = 'running'
    """
    with get_db() as db:
        db.execute(sql)


# =============================================================================
# STATISTIQUES
# =============================================================================

def get_last_scrape_date() -> Optional[str]:
    """Récupère la date du dernier scrap réussi."""
    sql = """
        SELECT finished_at, started_at
        FROM scrape_tasks
        WHERE status = 'success' AND (finished_at IS NOT NULL OR started_at IS NOT NULL)
        ORDER BY COALESCE(finished_at, started_at) DESC
        LIMIT 1
    """
    with get_db() as db:
        cursor = db.execute(sql)
        row = cursor.fetchone()
        if row:
            # Préférer finished_at, sinon started_at
            return row['finished_at'] or row['started_at']
        return None


def get_clubs_count() -> int:
    """Récupère le nombre total de clubs."""
    sql = "SELECT COUNT(*) as count FROM clubs"
    with get_db() as db:
        cursor = db.execute(sql)
        row = cursor.fetchone()
        return row['count'] if row else 0


def get_active_players_count() -> int:
    """Récupère le nombre total de joueurs actifs (avec points ou classement)."""
    sql = """
        SELECT COUNT(*) as count 
        FROM players 
        WHERE points_current IS NOT NULL OR ranking IS NOT NULL
    """
    with get_db() as db:
        cursor = db.execute(sql)
        row = cursor.fetchone()
        return row['count'] if row else 0


# =============================================================================
# TOURNAMENTS
# =============================================================================

def insert_tournament(tournament: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour un tournoi."""
    sql = """
    INSERT INTO tournaments (t_id, name, level, date_start, date_end, reference, series_count)
    VALUES (:t_id, :name, :level, :date_start, :date_end, :reference, :series_count)
    ON CONFLICT(t_id) DO UPDATE SET
        name = COALESCE(excluded.name, tournaments.name),
        level = COALESCE(excluded.level, tournaments.level),
        date_start = COALESCE(excluded.date_start, tournaments.date_start),
        date_end = COALESCE(excluded.date_end, tournaments.date_end),
        reference = COALESCE(excluded.reference, tournaments.reference),
        series_count = COALESCE(excluded.series_count, tournaments.series_count),
        updated_at = CURRENT_TIMESTAMP
    """
    
    data = {
        't_id': tournament.get('t_id'),
        'name': tournament.get('name'),
        'level': tournament.get('level'),
        'date_start': tournament.get('date_start'),
        'date_end': tournament.get('date_end'),
        'reference': tournament.get('reference'),
        'series_count': tournament.get('series_count', 0),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_tournament(t_id: int) -> Optional[Dict]:
    """Récupère un tournoi par son ID."""
    with get_db() as db:
        cursor = db.execute("SELECT * FROM tournaments WHERE t_id = ?", (t_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_tournaments(
    level: str = None,
    date_from: str = None,
    date_to: str = None,
    search: str = None,
    limit: int = None,
    offset: int = 0
) -> List[Dict]:
    """Récupère les tournois avec filtres optionnels."""
    sql = "SELECT * FROM tournaments WHERE 1=1"
    params = []
    
    if level:
        sql += " AND level = ?"
        params.append(level)
    
    if date_from:
        sql += " AND date_start >= ?"
        params.append(date_from)
    
    if date_to:
        sql += " AND date_start <= ?"
        params.append(date_to)
    
    if search:
        sql += " AND (name LIKE ? OR reference LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    sql += " ORDER BY date_start DESC"
    
    if limit:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_tournament_levels() -> List[str]:
    """Récupère la liste des niveaux de tournois distincts."""
    with get_db() as db:
        cursor = db.execute("SELECT DISTINCT level FROM tournaments WHERE level IS NOT NULL ORDER BY level")
        return [row[0] for row in cursor.fetchall()]


def get_tournaments_count() -> int:
    """Récupère le nombre total de tournois."""
    sql = "SELECT COUNT(*) as count FROM tournaments"
    with get_db() as db:
        cursor = db.execute(sql)
        row = cursor.fetchone()
        return row['count'] if row else 0


# =============================================================================
# TOURNAMENT SERIES
# =============================================================================

def insert_tournament_series(series: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour une série de tournoi."""
    sql = """
    INSERT INTO tournament_series (tournament_id, series_name, date, time, inscriptions_count, inscriptions_max)
    VALUES (:tournament_id, :series_name, :date, :time, :inscriptions_count, :inscriptions_max)
    ON CONFLICT(tournament_id, series_name) DO UPDATE SET
        date = COALESCE(excluded.date, tournament_series.date),
        time = COALESCE(excluded.time, tournament_series.time),
        inscriptions_count = COALESCE(excluded.inscriptions_count, tournament_series.inscriptions_count),
        inscriptions_max = COALESCE(excluded.inscriptions_max, tournament_series.inscriptions_max)
    """
    
    data = {
        'tournament_id': series.get('tournament_id'),
        'series_name': series.get('series_name'),
        'date': series.get('date'),
        'time': series.get('time'),
        'inscriptions_count': series.get('inscriptions_count', 0),
        'inscriptions_max': series.get('inscriptions_max', 0),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_tournament_series(tournament_id: int) -> List[Dict]:
    """Récupère les séries d'un tournoi."""
    sql = """
        SELECT * FROM tournament_series 
        WHERE tournament_id = ?
        ORDER BY date, time, series_name
    """
    with get_db() as db:
        cursor = db.execute(sql, (tournament_id,))
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# TOURNAMENT INSCRIPTIONS
# =============================================================================

def insert_tournament_inscription(inscription: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour une inscription à un tournoi."""
    sql = """
    INSERT INTO tournament_inscriptions (tournament_id, series_name, player_licence, player_name, player_club, player_ranking)
    VALUES (:tournament_id, :series_name, :player_licence, :player_name, :player_club, :player_ranking)
    ON CONFLICT(tournament_id, series_name, player_licence) DO UPDATE SET
        player_name = COALESCE(excluded.player_name, tournament_inscriptions.player_name),
        player_club = COALESCE(excluded.player_club, tournament_inscriptions.player_club),
        player_ranking = COALESCE(excluded.player_ranking, tournament_inscriptions.player_ranking)
    """
    
    data = {
        'tournament_id': inscription.get('tournament_id'),
        'series_name': inscription.get('series_name'),
        'player_licence': inscription.get('player_licence'),
        'player_name': inscription.get('player_name'),
        'player_club': inscription.get('player_club'),
        'player_ranking': inscription.get('player_ranking'),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_tournament_inscriptions(tournament_id: int, series_name: str = None) -> List[Dict]:
    """Récupère les inscriptions d'un tournoi."""
    sql = "SELECT * FROM tournament_inscriptions WHERE tournament_id = ?"
    params = [tournament_id]
    
    if series_name:
        sql += " AND series_name = ?"
        params.append(series_name)
    
    sql += " ORDER BY series_name, player_ranking, player_name"
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_player_tournament_inscriptions(player_licence: str) -> List[Dict]:
    """Récupère les inscriptions d'un joueur à des tournois."""
    sql = """
        SELECT ti.*, t.name as tournament_name, t.date_start, t.level
        FROM tournament_inscriptions ti
        JOIN tournaments t ON ti.tournament_id = t.t_id
        WHERE ti.player_licence = ?
        ORDER BY t.date_start DESC
    """
    with get_db() as db:
        cursor = db.execute(sql, (player_licence,))
        return [dict(row) for row in cursor.fetchall()]


# =============================================================================
# TOURNAMENT RESULTS
# =============================================================================

def insert_tournament_result(result: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère un résultat de tournoi."""
    sql = """
    INSERT INTO tournament_results (tournament_id, series_name, player1_licence, player1_name, 
                                    player2_licence, player2_name, score, winner_licence, round)
    VALUES (:tournament_id, :series_name, :player1_licence, :player1_name,
            :player2_licence, :player2_name, :score, :winner_licence, :round)
    """
    
    data = {
        'tournament_id': result.get('tournament_id'),
        'series_name': result.get('series_name'),
        'player1_licence': result.get('player1_licence'),
        'player1_name': result.get('player1_name'),
        'player2_licence': result.get('player2_licence'),
        'player2_name': result.get('player2_name'),
        'score': result.get('score'),
        'winner_licence': result.get('winner_licence'),
        'round': result.get('round'),
    }
    
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def get_tournament_results(tournament_id: int, series_name: str = None) -> List[Dict]:
    """Récupère les résultats d'un tournoi."""
    sql = "SELECT * FROM tournament_results WHERE tournament_id = ?"
    params = [tournament_id]
    
    if series_name:
        sql += " AND series_name = ?"
        params.append(series_name)
    
    sql += " ORDER BY series_name, round, id"
    
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_player_tournament_results(player_licence: str) -> List[Dict]:
    """Récupère les résultats de tournois d'un joueur."""
    sql = """
        SELECT tr.*, t.name as tournament_name, t.date_start, t.level
        FROM tournament_results tr
        JOIN tournaments t ON tr.tournament_id = t.t_id
        WHERE tr.player1_licence = ? OR tr.player2_licence = ?
        ORDER BY t.date_start DESC
    """
    with get_db() as db:
        cursor = db.execute(sql, (player_licence, player_licence))
        return [dict(row) for row in cursor.fetchall()]


def delete_tournament_data(tournament_id: int) -> None:
    """Supprime toutes les données d'un tournoi (séries, inscriptions, résultats)."""
    with get_db() as db:
        db.execute("DELETE FROM tournament_results WHERE tournament_id = ?", (tournament_id,))
        db.execute("DELETE FROM tournament_inscriptions WHERE tournament_id = ?", (tournament_id,))
        db.execute("DELETE FROM tournament_series WHERE tournament_id = ?", (tournament_id,))


# =============================================================================
# INTERCLUBS DIVISIONS & RANKINGS
# =============================================================================

def insert_interclubs_division(division: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour une division interclubs."""
    sql = """
    INSERT INTO interclubs_divisions (division_index, division_name, division_category, division_gender)
    VALUES (:division_index, :division_name, :division_category, :division_gender)
    ON CONFLICT(division_index) DO UPDATE SET
        division_name = COALESCE(excluded.division_name, interclubs_divisions.division_name),
        division_category = COALESCE(excluded.division_category, interclubs_divisions.division_category),
        division_gender = COALESCE(excluded.division_gender, interclubs_divisions.division_gender)
    """
    data = {
        'division_index': division.get('division_index'),
        'division_name': division.get('division_name'),
        'division_category': division.get('division_category'),
        'division_gender': division.get('division_gender'),
    }
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def insert_interclubs_ranking(ranking: Dict[str, Any], db: sqlite3.Connection = None) -> None:
    """Insère ou met à jour un classement interclubs."""
    sql = """
    INSERT INTO interclubs_rankings (division_index, division_name, week, rank, team_name,
                                     played, wins, losses, draws, forfeits, points)
    VALUES (:division_index, :division_name, :week, :rank, :team_name,
            :played, :wins, :losses, :draws, :forfeits, :points)
    ON CONFLICT(division_index, week, team_name) DO UPDATE SET
        division_name = excluded.division_name,
        rank = excluded.rank,
        played = excluded.played,
        wins = excluded.wins,
        losses = excluded.losses,
        draws = excluded.draws,
        forfeits = excluded.forfeits,
        points = excluded.points
    """
    data = {
        'division_index': ranking.get('division_index'),
        'division_name': ranking.get('division_name'),
        'week': ranking.get('week'),
        'rank': ranking.get('rank'),
        'team_name': ranking.get('team_name'),
        'played': ranking.get('played', 0),
        'wins': ranking.get('wins', 0),
        'losses': ranking.get('losses', 0),
        'draws': ranking.get('draws', 0),
        'forfeits': ranking.get('forfeits', 0),
        'points': ranking.get('points', 0),
    }
    if db:
        db.execute(sql, data)
    else:
        with get_db() as conn:
            conn.execute(sql, data)


def insert_interclubs_rankings_batch(rankings: List[Dict[str, Any]]) -> None:
    """Insère un batch de classements interclubs dans une transaction."""
    if not rankings:
        return
    sql = """
    INSERT INTO interclubs_rankings (division_index, division_name, week, rank, team_name,
                                     played, wins, losses, draws, forfeits, points)
    VALUES (:division_index, :division_name, :week, :rank, :team_name,
            :played, :wins, :losses, :draws, :forfeits, :points)
    ON CONFLICT(division_index, week, team_name) DO UPDATE SET
        division_name = excluded.division_name,
        rank = excluded.rank,
        played = excluded.played,
        wins = excluded.wins,
        losses = excluded.losses,
        draws = excluded.draws,
        forfeits = excluded.forfeits,
        points = excluded.points
    """
    with get_db() as conn:
        for ranking in rankings:
            data = {
                'division_index': ranking.get('division_index'),
                'division_name': ranking.get('division_name'),
                'week': ranking.get('week'),
                'rank': ranking.get('rank'),
                'team_name': ranking.get('team_name'),
                'played': ranking.get('played', 0),
                'wins': ranking.get('wins', 0),
                'losses': ranking.get('losses', 0),
                'draws': ranking.get('draws', 0),
                'forfeits': ranking.get('forfeits', 0),
                'points': ranking.get('points', 0),
            }
            conn.execute(sql, data)


def get_interclubs_divisions(category: str = None, gender: str = None) -> List[Dict]:
    """Récupère les divisions interclubs avec filtres optionnels."""
    sql = "SELECT * FROM interclubs_divisions WHERE 1=1"
    params = []
    if category:
        sql += " AND division_category LIKE ?"
        params.append(f"%{category}%")
    if gender:
        sql += " AND division_gender = ?"
        params.append(gender)
    sql += " ORDER BY division_index"
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def get_interclubs_ranking(division_index: int, week: int) -> List[Dict]:
    """Récupère le classement d'une division pour une semaine donnée."""
    sql = """
        SELECT * FROM interclubs_rankings
        WHERE division_index = ? AND week = ?
        ORDER BY rank ASC, points DESC
    """
    with get_db() as db:
        cursor = db.execute(sql, (division_index, week))
        return [dict(row) for row in cursor.fetchall()]


def get_interclubs_team_history(team_name: str, division_index: int = None) -> List[Dict]:
    """Récupère la progression d'une équipe semaine par semaine."""
    sql = "SELECT * FROM interclubs_rankings WHERE team_name = ?"
    params = [team_name]
    if division_index is not None:
        sql += " AND division_index = ?"
        params.append(division_index)
    sql += " ORDER BY division_index, week"
    with get_db() as db:
        cursor = db.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]


def search_interclubs_teams(query: str, limit: int = 50) -> List[Dict]:
    """Recherche des équipes interclubs par nom."""
    sql = """
        SELECT DISTINCT team_name, division_index, division_name
        FROM interclubs_rankings
        WHERE team_name LIKE ?
        ORDER BY team_name
        LIMIT ?
    """
    with get_db() as db:
        cursor = db.execute(sql, (f"%{query}%", limit))
        return [dict(row) for row in cursor.fetchall()]


def delete_interclubs_rankings(division_index: int = None, week: int = None) -> int:
    """Supprime des classements interclubs (filtrage optionnel)."""
    sql = "DELETE FROM interclubs_rankings WHERE 1=1"
    params = []
    if division_index is not None:
        sql += " AND division_index = ?"
        params.append(division_index)
    if week is not None:
        sql += " AND week = ?"
        params.append(week)
    with get_db() as db:
        cursor = db.execute(sql, params)
        return cursor.rowcount


def get_interclubs_stats() -> Dict:
    """Récupère des statistiques sur les données interclubs."""
    with get_db() as db:
        cursor = db.execute("SELECT COUNT(*) FROM interclubs_divisions")
        divisions_count = cursor.fetchone()[0]
        cursor = db.execute("SELECT COUNT(*) FROM interclubs_rankings")
        rankings_count = cursor.fetchone()[0]
        cursor = db.execute("SELECT COUNT(DISTINCT team_name) FROM interclubs_rankings")
        teams_count = cursor.fetchone()[0]
        cursor = db.execute("SELECT MIN(week), MAX(week) FROM interclubs_rankings")
        row = cursor.fetchone()
        min_week = row[0]
        max_week = row[1]
    return {
        'divisions_count': divisions_count,
        'rankings_count': rankings_count,
        'teams_count': teams_count,
        'min_week': min_week,
        'max_week': max_week,
    }