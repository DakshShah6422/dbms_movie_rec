import mysql.connector
from mysql.connector import errorcode
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime

# --- Configuration ---
# Use 'static' as the folder to serve the frontend
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, static_folder=STATIC_DIR)

# --- !! IMPORTANT !! ---
# EDIT this dictionary to match your MySQL username and password
DB_CONFIG = {
    'host': 'mysql.railway.internal',
    'user': 'root',       # <-- EDIT THIS
    'password': 'XIuLVCbGtrYaHdtdfITHIsNPaRIBEFuL', # <-- EDIT THIS
    'database': 'railway',
    'port': 13138
}

# --- Database Connection Helper ---
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# --- Custom JSON Encoder ---
def default_json_serializer(obj):
    """Handle special types like datetime for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# --- API Endpoints ---

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password') # In a real app, hash this!

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Simple password "hashing" for lab project. DO NOT USE IN PRODUCTION.
        hashed_password = f"hashed_{password}_salt" 
        
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        new_user_id = cursor.lastrowid
        
        # --- NEW: Create a default watchlist for the new user ---
        cursor.execute(
            "INSERT INTO watchlists (user_id, name) VALUES (%s, %s)",
            (new_user_id, "My Watchlist")
        )
        # --- End New ---

        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            return jsonify({"error": "Username or email already exists"}), 409
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# --- NEW: Rating Endpoint ---

@app.route('/api/rate', methods=['POST'])
def add_or_update_rating():
    data = request.get_json()
    user_id = data.get('user_id')
    movie_id = data.get('movie_id')
    rating = data.get('rating')
    if not user_id or not movie_id or not rating:
              return jsonify({"error": "user_id, movie_id, and rating are required"}), 400      
    try:
              rating_int = int(rating)
              if not 1 <= rating_int <= 5:
                        raise ValueError()
    except (ValueError, TypeError):
              return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400

    conn = get_db_connection()
    if not conn: 
              return jsonify({"error": "Database connection failed"}), 500
          
    cursor = conn.cursor()
    
    try:
        # Use INSERT ... ON DUPLICATE KEY UPDATE to handle both new ratings and updates
        query = """
                  INSERT INTO ratings (user_id, movie_id, rating)
                  VALUES (%s, %s, %s)
                  ON DUPLICATE KEY UPDATE rating = VALUES(rating);
        """
        params = (user_id, movie_id, rating_int)
        
        cursor.execute(query, params)
        conn.commit()
        
        # cursor.rowcount == 1 means a new row was inserted
        # cursor.rowcount == 2 means an existing row was updated
        if cursor.rowcount == 1:
                  return jsonify({"status": "created", "new_rating": rating_int}), 201
        else:
                  return jsonify({"status": "updated", "new_rating": rating_int}), 200

    except mysql.connector.Error as err:
              return jsonify({"error": str(err)}), 500
    finally:
              cursor.close()
              conn.close()

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    # Simple password "check"
    hashed_password = f"hashed_{password}_salt"
    
    cursor.execute(
        "SELECT user_id, username, email FROM users WHERE username = %s AND password_hash = %s",
        (username, hashed_password)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        return jsonify({"message": "Login successful", "user": user}), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/genres', methods=['GET'])
def get_genres():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT genre_id, name FROM genres ORDER BY name ASC")
    genres = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(genres), 200

@app.route('/api/movies', methods=['GET'])
def search_movies():
    """
    Search endpoint for movies.
    Can filter by 'search' term (title) and 'genre' (ID).
    Can also fetch by 'list' type (e.g., 'recent')
    """
    search_term = request.args.get('search', '')
    genre_id = request.args.get('genre', '')
    list_type = request.args.get('list', '') # e.g., 'recent'

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    # Base query with average rating
    query = """
        SELECT 
            m.movie_id, m.title, m.release_year,
            COALESCE(AVG(r.rating), 0) AS average_rating
        FROM movies m
        LEFT JOIN ratings r ON m.movie_id = r.movie_id
    """
    params = []

    # Dynamic WHERE clause building
    where_clauses = []
    
    if genre_id:
        query += " JOIN movie_genres mg ON m.movie_id = mg.movie_id"
        where_clauses.append("mg.genre_id = %s")
        params.append(genre_id)
        
    if search_term:
        where_clauses.append("m.title LIKE %s")
        params.append(f"%{search_term}%")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " GROUP BY m.movie_id, m.title, m.release_year"
    
    if list_type == 'recent':
        query += " ORDER BY m.release_year DESC, m.title ASC"
    else:
        query += " ORDER BY m.title ASC"

    query += " LIMIT 50" # Add a limit for performance
    
    try:
        cursor.execute(query, tuple(params))
        movies = cursor.fetchall()
        return jsonify(movies), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/movies/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    user_id = request.args.get('user_id') # Get user_id to check watchlist status

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Get basic movie info and rating stats
        cursor.execute("""
            SELECT 
                m.movie_id, m.title, m.release_year, m.synopsis, m.duration_min,
                COALESCE(AVG(r.rating), 0) AS average_rating,
                COUNT(r.rating) AS total_ratings
            FROM movies m
            LEFT JOIN ratings r ON m.movie_id = r.movie_id
            WHERE m.movie_id = %s
            GROUP BY m.movie_id;
        """, (movie_id,))
        movie = cursor.fetchone()
        
        if not movie:
            return jsonify({"error": "Movie not found"}), 404

        # 2. Get actors
        cursor.execute("""
            SELECT a.first_name, a.last_name, ma.role_name
            FROM actors a
            JOIN movie_actors ma ON a.actor_id = ma.actor_id
            WHERE ma.movie_id = %s;
        """, (movie_id,))
        movie['actors'] = [{"name": f"{row['first_name']} {row['last_name']}", "role": row['role_name']} for row in cursor.fetchall()]

        # 3. Get directors
        cursor.execute("""
            SELECT d.first_name, d.last_name
            FROM directors d
            JOIN movie_directors md ON d.director_id = md.director_id
            WHERE md.movie_id = %s;
        """, (movie_id,))
        movie['directors'] = [{"name": f"{row['first_name']} {row['last_name']}"} for row in cursor.fetchall()]
        
        # 4. Get recent reviews (with usernames)
        cursor.execute("""
            SELECT r.review_id, r.review_text, r.created_at, u.username
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.movie_id = %s
            ORDER BY r.created_at DESC
            LIMIT 10;
        """, (movie_id,))
        reviews_raw = cursor.fetchall()
        movie['reviews'] = json.loads(json.dumps(reviews_raw, default=default_json_serializer))

        # --- NEW: Get user's specific rating ---
        movie['user_rating'] = 0 # Default
        if user_id:
            cursor.execute("""
                SELECT rating FROM ratings
                WHERE movie_id = %s AND user_id = %s
            """, (movie_id, user_id))
            user_rating_row = cursor.fetchone()
            if user_rating_row:
                movie['user_rating'] = user_rating_row['rating']
        # --- End New ---

        # --- NEW: Check watchlist status ---
        movie['on_watchlist'] = False # Default
        if user_id:
            cursor.execute("""
                SELECT wi.item_id 
                FROM watchlist_items wi
                JOIN watchlists w ON wi.watchlist_id = w.watchlist_id
                WHERE wi.movie_id = %s AND w.user_id = %s
                LIMIT 1;
            """, (movie_id, user_id))
            item = cursor.fetchone()
            if item:
                movie['on_watchlist'] = True
        # --- End New ---
        
        return jsonify(movie), 200

    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Recommendation Endpoints ---
@app.route('/api/recommendations/popular', methods=['GET'])
def get_popular_movies():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        MIN_RATINGS = 5 
        cursor.execute("SELECT AVG(rating) as C FROM ratings")
        C_row = cursor.fetchone()
        C = C_row['C'] if C_row and C_row['C'] is not None else 3.0 # Default to 3.0 if no ratings
        
        query = f"""
            SELECT 
                m.movie_id, m.title, m.release_year,
                COUNT(r.rating) AS v, AVG(r.rating) AS R,
                ( (COUNT(r.rating) / (COUNT(r.rating) + %s)) * AVG(r.rating) + ( %s / (COUNT(r.rating) + %s)) * %s ) AS weighted_rating
            FROM movies m
            LEFT JOIN ratings r ON m.movie_id = r.movie_id
            GROUP BY m.movie_id, m.title, m.release_year
            HAVING v >= %s
            ORDER BY weighted_rating DESC
            LIMIT 10;
        """
        params = (MIN_RATINGS, MIN_RATINGS, MIN_RATINGS, C, MIN_RATINGS)
        cursor.execute(query, params)
        movies = cursor.fetchall()
        return jsonify(movies), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recommendations/content/<int:movie_id>', methods=['GET'])
def get_content_recommendations(movie_id):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            WITH TargetGenres AS (SELECT genre_id FROM movie_genres WHERE movie_id = %s),
            TargetDirectors AS (SELECT director_id FROM movie_directors WHERE movie_id = %s),
            MovieRatings AS (SELECT movie_id, COALESCE(AVG(rating), 0) as avg_rating FROM ratings GROUP BY movie_id)
            SELECT 
                m.movie_id, m.title, m.release_year,
                COALESCE(mr.avg_rating, 0) AS average_rating,
                COUNT(DISTINCT mg.genre_id) AS genre_matches,
                COUNT(DISTINCT md.director_id) AS director_matches
            FROM movies m
            LEFT JOIN MovieRatings mr ON m.movie_id = mr.movie_id
            LEFT JOIN movie_genres mg ON m.movie_id = mg.movie_id AND mg.genre_id IN (SELECT genre_id FROM TargetGenres)
            LEFT JOIN movie_directors md ON m.movie_id = md.movie_id AND md.director_id IN (SELECT director_id FROM TargetDirectors)
            WHERE m.movie_id != %s AND (mg.genre_id IS NOT NULL OR md.director_id IS NOT NULL)
            GROUP BY m.movie_id, m.title, m.release_year, mr.avg_rating
            ORDER BY (genre_matches + director_matches) DESC, average_rating DESC
            LIMIT 10;
        """
        params = (movie_id, movie_id, movie_id)
        cursor.execute(query, params)
        movies = cursor.fetchall()
        return jsonify(movies), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recommendations/collaborative/<int:movie_id>', methods=['GET'])
def get_collaborative_recommendations(movie_id):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        MIN_RATING = 4
        query = """
            WITH SimilarUsers AS (
                SELECT user_id FROM ratings WHERE movie_id = %s AND rating >= %s
            ),
            SimilarUsersRatings AS (
                SELECT movie_id, COUNT(DISTINCT user_id) as similar_user_likes
                FROM ratings
                WHERE user_id IN (SELECT user_id FROM SimilarUsers)
                  AND rating >= %s AND movie_id != %s
                GROUP BY movie_id
            )
            SELECT 
                m.movie_id, m.title, m.release_year,
                COALESCE(AVG(r.rating), 0) AS average_rating,
                sur.similar_user_likes
            FROM movies m
            JOIN SimilarUsersRatings sur ON m.movie_id = sur.movie_id
            LEFT JOIN ratings r ON m.movie_id = r.movie_id
            GROUP BY m.movie_id, m.title, m.release_year, sur.similar_user_likes
            ORDER BY sur.similar_user_likes DESC, average_rating DESC
            LIMIT 10;
        """
        params = (movie_id, MIN_RATING, MIN_RATING, movie_id)
        cursor.execute(query, params)
        movies = cursor.fetchall()
        return jsonify(movies), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# --- User-Personalized Recommendation Endpoints ---

@app.route('/api/recommendations/personal_content', methods=['GET'])
def get_personal_content_recommendations():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    
    try:
        MIN_RATING = 4 
        
        query = """
            WITH UserFavoriteGenres AS (
                SELECT DISTINCT mg.genre_id
                FROM ratings r
                JOIN movie_genres mg ON r.movie_id = mg.movie_id
                WHERE r.user_id = %s AND r.rating >= %s
            ),
            UserRatedMovies AS (
                SELECT DISTINCT movie_id FROM ratings WHERE user_id = %s
            )
            SELECT 
                m.movie_id, 
                m.title, 
                m.release_year,
                COUNT(DISTINCT mg.genre_id) AS genre_matches,
                COALESCE(AVG(r.rating), 0) AS average_rating
            FROM movies m
            JOIN movie_genres mg ON m.movie_id = mg.movie_id
            LEFT JOIN ratings r ON m.movie_id = r.movie_id
            WHERE 
                mg.genre_id IN (SELECT genre_id FROM UserFavoriteGenres)
                AND m.movie_id NOT IN (SELECT movie_id FROM UserRatedMovies)
            GROUP BY m.movie_id, m.title, m.release_year
            ORDER BY 
                genre_matches DESC, 
                average_rating DESC
            LIMIT 10;
        """
        params = (user_id, MIN_RATING, user_id)
        
        cursor.execute(query, params)
        movies = cursor.fetchall()
        return jsonify(movies), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recommendations/personal_collaborative', methods=['GET'])
def get_personal_collaborative_recommendations():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
        
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    
    try:
        MIN_RATING = 4 
        SIMILARITY_THRESHOLD = 3 

        query = """
            WITH TargetUserRatings AS (
                SELECT movie_id FROM ratings WHERE user_id = %s AND rating >= %s
            ),
            SimilarUsers AS (
                SELECT 
                    r.user_id, 
                    COUNT(r.movie_id) AS shared_likes
                FROM ratings r
                WHERE 
                    r.movie_id IN (SELECT movie_id FROM TargetUserRatings)
                    AND r.user_id != %s 
                    AND r.rating >= %s
                GROUP BY r.user_id
                HAVING shared_likes >= %s
            ),
            RecommendedMovies AS (
                SELECT 
                    r.movie_id, 
                    COUNT(DISTINCT r.user_id) AS similar_user_likes
                FROM ratings r
                WHERE 
                    r.user_id IN (SELECT user_id FROM SimilarUsers)
                    AND r.rating >= %s
                    AND r.movie_id NOT IN (SELECT movie_id FROM TargetUserRatings)
                GROUP BY r.movie_id
            )
            SELECT 
                m.movie_id, 
                m.title, 
                m.release_year,
                rm.similar_user_likes,
                COALESCE(AVG(r_all.rating), 0) AS average_rating
            FROM RecommendedMovies rm
            JOIN movies m ON rm.movie_id = m.movie_id
            LEFT JOIN ratings r_all ON m.movie_id = r_all.movie_id
            GROUP BY m.movie_id, m.title, m.release_year, rm.similar_user_likes
            ORDER BY 
                rm.similar_user_likes DESC,
                average_rating DESC
            LIMIT 10;
        """
        params = (user_id, MIN_RATING, user_id, MIN_RATING, SIMILARITY_THRESHOLD, MIN_RATING)
        
        cursor.execute(query, params)
        movies = cursor.fetchall()
        return jsonify(movies), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# --- NEW: Watchlist Endpoints ---

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Find the user's primary (first) watchlist
        cursor.execute("SELECT watchlist_id FROM watchlists WHERE user_id = %s LIMIT 1", (user_id,))
        watchlist = cursor.fetchone()
        
        if not watchlist:
            return jsonify([]), 200 # User has no watchlist, return empty
            
        watchlist_id = watchlist['watchlist_id']
        
        # 2. Get all movies on that watchlist
        cursor.execute("""
            SELECT 
                m.movie_id, m.title, m.release_year,
                COALESCE(AVG(r.rating), 0) AS average_rating
            FROM movies m
            JOIN watchlist_items wi ON m.movie_id = wi.movie_id
            LEFT JOIN ratings r ON m.movie_id = r.movie_id
            WHERE wi.watchlist_id = %s
            GROUP BY m.movie_id, m.title, m.release_year
            ORDER BY m.title ASC;
        """, (watchlist_id,))
        
        movies = cursor.fetchall()
        return jsonify(movies), 200
        
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/watchlist/toggle', methods=['POST'])
def toggle_watchlist_item():
    data = request.get_json()
    user_id = data.get('user_id')
    movie_id = data.get('movie_id')

    if not user_id or not movie_id:
        return jsonify({"error": "user_id and movie_id are required"}), 400
        
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Find the user's primary (first) watchlist
        cursor.execute("SELECT watchlist_id FROM watchlists WHERE user_id = %s LIMIT 1", (user_id,))
        watchlist = cursor.fetchone()
        
        if not watchlist:
            return jsonify({"error": "User has no watchlist"}), 404
            
        watchlist_id = watchlist['watchlist_id']
        
        # 2. Check if the item already exists
        cursor.execute("""
            SELECT item_id FROM watchlist_items
            WHERE watchlist_id = %s AND movie_id = %s
        """, (watchlist_id, movie_id))
        item = cursor.fetchone()
        
        # 3. If it exists, remove it. If not, add it.
        if item:
            cursor.execute("DELETE FROM watchlist_items WHERE item_id = %s", (item['item_id'],))
            message = "removed"
        else:
            cursor.execute(
                "INSERT INTO watchlist_items (watchlist_id, movie_id) VALUES (%s, %s)",
                (watchlist_id, movie_id)
            )
            message = "added"
        
        conn.commit()
        return jsonify({"status": message}), 200
        
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Admin API Endpoints ---

@app.route('/api/schema', methods=['GET'])
def get_schema():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SHOW TABLES")
        tables = [row[f'Tables_in_{DB_CONFIG["database"]}'] for row in cursor.fetchall()]
        
        schema = {}
        for table in tables:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            schema[table] = columns
        
        return jsonify(schema), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/insert', methods=['POST'])
def insert_data():
    data = request.get_json()
    table_name = data.get('table')
    row_data = data.get('data') 

    if not table_name or not row_data:
        return jsonify({"error": "Table name and data are required"}), 400

    if not table_name.replace('_', '').isalnum():
         return jsonify({"error": "Invalid table name"}), 400

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor()

    try:
        columns = ", ".join(row_data.keys())
        placeholders = ", ".join(["%s"] * len(row_data))
        values = list(row_data.values())
        
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        cursor.execute(query, values)
        conn.commit()
        
        return jsonify({"message": "Data inserted successfully", "id": cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": f"MySQL Error: {err.msg}", "errno": err.errno}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/query', methods=['POST'])
def execute_query():
    data = request.get_json()
    query = data.get('query')

    if not query:
        return jsonify({"error": "Query is required"}), 400

    if not query.strip().lower().startswith('select'):
        return jsonify({"error": "Only SELECT statements are allowed."}), 403

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        results = json.loads(json.dumps(results, default=default_json_serializer))
        
        return jsonify({"message": "Query executed successfully", "results": results, "columns": cursor.column_names}), 200
    except mysql.connector.Error as err:
        return jsonify({"error": f"MySQL Error: {err.msg}", "errno": err.errno}), 400
    finally:
        cursor.close()
        conn.close()

# --- Frontend Serving Routes ---

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/app')
def serve_app():
    return send_from_directory(app.static_folder, 'app.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if filename not in ['index.html', 'app.html']:
        return send_from_directory(app.static_folder, filename)
    else:
        return "Not Found", 404

# --- Main Entry Point ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

