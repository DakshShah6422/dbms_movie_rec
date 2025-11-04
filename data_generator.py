import mysql.connector
from mysql.connector import errorcode
import os
import csv
from faker import Faker
import random
import datetime

# --- IMPORTANT ---
# 1. Install this library: pip install mysql-connector-python
# 2. Update the DB_CONFIG to match your MySQL user/password.
#    (You can copy this from your app.py)
# 3. Run this script ONCE: python data_generator.py
# 4. Your database will be populated. You do not need import_data.sql.
# -----------------

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',       # <-- EDIT THIS
    'password': 'D@ksh1111', # <-- EDIT THIS
    'database': 'movie_rec_db'
}

# --- Configuration ---
NUM_USERS = 200
NUM_MOVIES = 1000
NUM_GENRES = 20
NUM_ACTORS = 500
NUM_DIRECTORS = 100
NUM_RATINGS = 10000  # 10k ratings
NUM_REVIEWS = 500   # 500 of the ratings will also have a review
NUM_WATCHLISTS = 300 # 300 watchlists total
NUM_WATCHLIST_ITEMS = 5000 # 5k movies added to watchlists

# Junction table counts
MOVIE_GENRES_LINKS = 3000
MOVIE_ACTORS_LINKS = 4000
MOVIE_DIRECTORS_LINKS = 1500 # 1-2 directors per movie

# --- Initialize Faker ---
fake = Faker()
Faker.seed(0)
random.seed(0)

# --- Data Generation Functions ---
# (These are the same as before, just generating lists)

def generate_users():
    users = []
    for i in range(1, NUM_USERS + 1):
        users.append({
            "user_id": i,
            "username": fake.user_name() + str(i),
            "email": fake.email(),
            "password_hash": fake.sha256(), # In a real app, hash a real password
            "created_at": fake.date_time_this_decade()
        })
    return users

def generate_movies():
    movies = []
    for i in range(1, NUM_MOVIES + 1):
        movies.append({
            "movie_id": i,
            "title": ' '.join(fake.words(nb=random.randint(2, 5))).title().replace('"', "'"),
            "release_year": random.randint(1980, 2024),
            "synopsis": fake.paragraph(nb_sentences=3).replace('"', "'"),
            "duration_min": random.randint(75, 180)
        })
    return movies

def generate_genres():
    genres_list = [
        'Action', 'Comedy', 'Drama', 'Science Fiction', 'Horror', 'Romance',
        'Thriller', 'Fantasy', 'Documentary', 'Animation', 'Crime', 'Mystery',
        'Adventure', 'Family', 'War', 'History', 'Music', 'Western', 'Biography', 'Musical'
    ]
    return [{"genre_id": i + 1, "name": name} for i, name in enumerate(genres_list)]

def generate_actors():
    actors = []
    for i in range(1, NUM_ACTORS + 1):
        actors.append({
            "actor_id": i,
            "first_name": fake.first_name().replace('"', "'"),
            "last_name": fake.last_name().replace('"', "'"),
            "birthdate": fake.date_of_birth(minimum_age=18, maximum_age=80)
        })
    return actors

def generate_directors():
    directors = []
    for i in range(1, NUM_DIRECTORS + 1):
        directors.append({
            "director_id": i,
            "first_name": fake.first_name().replace('"', "'"),
            "last_name": fake.last_name().replace('"', "'"),
            "birthdate": fake.date_of_birth(minimum_age=30, maximum_age=90)
        })
    return directors

def generate_ratings_and_reviews(user_ids, movie_ids):
    ratings = []
    reviews = []
    used_pairs = set()
    review_id_counter = 1

    while len(ratings) < NUM_RATINGS:
        user_id = random.choice(user_ids)
        movie_id = random.choice(movie_ids)
        if (user_id, movie_id) not in used_pairs:
            used_pairs.add((user_id, movie_id))
            ratings.append({
                "user_id": user_id,
                "movie_id": movie_id,
                "rating": random.randint(1, 5),
                "created_at": fake.date_time_this_year()
            })

    # Create reviews for a subset of ratings
    review_pairs = random.sample(list(used_pairs), NUM_REVIEWS)
    for user_id, movie_id in review_pairs:
        reviews.append({
            "review_id": review_id_counter,
            "user_id": user_id,
            "movie_id": movie_id,
            "review_text": fake.paragraph(nb_sentences=random.randint(1, 4)).replace('"', "'"),
            "created_at": fake.date_time_this_year()
        })
        review_id_counter += 1
    return ratings, reviews

def generate_watchlists(user_ids):
    watchlists = []
    watchlist_id_counter = 1
    list_names = ['Favorites', 'To Watch', 'My Top 10', 'Guilty Pleasures']
    for _ in range(NUM_WATCHLISTS):
        watchlists.append({
            "watchlist_id": watchlist_id_counter,
            "user_id": random.choice(user_ids),
            "name": random.choice(list_names),
            "created_at": fake.date_time_this_year()
        })
        watchlist_id_counter += 1
    return watchlists

def generate_watchlist_items(watchlist_ids, movie_ids):
    items = []
    used_pairs = set()
    while len(items) < NUM_WATCHLIST_ITEMS:
        watchlist_id = random.choice(watchlist_ids)
        movie_id = random.choice(movie_ids)
        if (watchlist_id, movie_id) not in used_pairs:
            used_pairs.add((watchlist_id, movie_id))
            items.append({
                "watchlist_id": watchlist_id,
                "movie_id": movie_id,
                "added_at": fake.date_time_this_year()
            })
    return items

def generate_movie_genres(movie_ids, genre_ids):
    links = []
    used_pairs = set()
    for movie_id in movie_ids:
        # Ensure every movie has at least one genre
        genre_id = random.choice(genre_ids)
        links.append({"movie_id": movie_id, "genre_id": genre_id})
        used_pairs.add((movie_id, genre_id))
    # Add more random genres
    while len(links) < MOVIE_GENRES_LINKS:
        movie_id = random.choice(movie_ids)
        genre_id = random.choice(genre_ids)
        if (movie_id, genre_id) not in used_pairs:
            used_pairs.add((movie_id, genre_id))
            links.append({"movie_id": movie_id, "genre_id": genre_id})
    return links

def generate_movie_actors(movie_ids, actor_ids):
    links = []
    used_pairs = set()
    while len(links) < MOVIE_ACTORS_LINKS:
        movie_id = random.choice(movie_ids)
        actor_id = random.choice(actor_ids)
        role = fake.first_name().replace('"', "'")
        if (movie_id, actor_id, role) not in used_pairs:
            links.append({"movie_id": movie_id, "actor_id": actor_id, "role_name": role})
            used_pairs.add((movie_id, actor_id, role))
    return links

def generate_movie_directors(movie_ids, director_ids):
    links = []
    used_pairs = set()
    for movie_id in movie_ids:
        # Ensure every movie has at least one director
        director_id = random.choice(director_ids)
        links.append({"movie_id": movie_id, "director_id": director_id})
        used_pairs.add((movie_id, director_id))
    # Add more
    while len(links) < MOVIE_DIRECTORS_LINKS:
        movie_id = random.choice(movie_ids)
        director_id = random.choice(director_ids)
        if (movie_id, director_id) not in used_pairs:
            used_pairs.add((movie_id, director_id))
            links.append({"movie_id": movie_id, "director_id": director_id})
    return links

# --- NEW: Database Insertion ---

def insert_data_to_db(cursor, table_name, data, fields):
    """
    Inserts a list of dictionaries into the specified table.
    """
    if not data:
        print(f"No data to insert for {table_name}")
        return

    # Create the insert statement
    # Example: INSERT INTO users (user_id, username, email, ...) VALUES (%s, %s, %s, ...)
    query = f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({', '.join(['%s'] * len(fields))})"

    # Create a list of tuples from the list of dictionaries
    # This is what executemany() expects
    values = []
    for row in data:
        values.append(tuple(row[field] for field in fields))

    try:
        print(f"Inserting {len(values)} records into {table_name}...")
        cursor.executemany(query, values)
        print(f"Successfully inserted {cursor.rowcount} records.")
    except mysql.connector.Error as err:
        print(f"Error inserting into {table_name}: {err}")
        print("SQL Query was:", query)
        print("First row of data was:", values[0] if values else "No data")


def main():
    print("Generating synthetic data in memory...")

    users = generate_users()
    movies = generate_movies()
    genres = generate_genres()
    actors = generate_actors()
    directors = generate_directors()

    user_ids = [u['user_id'] for u in users]
    movie_ids = [m['movie_id'] for m in movies]
    genre_ids = [g['genre_id'] for g in genres]
    actor_ids = [a['actor_id'] for a in actors]
    director_ids = [d['director_id'] for d in directors]

    ratings, reviews = generate_ratings_and_reviews(user_ids, movie_ids)
    watchlists = generate_watchlists(user_ids)
    
    watchlist_ids = [w['watchlist_id'] for w in watchlists]
    watchlist_items = generate_watchlist_items(watchlist_ids, movie_ids)

    movie_genres = generate_movie_genres(movie_ids, genre_ids)
    movie_actors = generate_movie_actors(movie_ids, actor_ids)
    movie_directors = generate_movie_directors(movie_ids, director_ids)

    print("Data generation complete. Connecting to database...")

    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        print(f"Successfully connected to database '{DB_CONFIG['database']}'.")

        # Disable checks for fast import
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("SET UNIQUE_CHECKS = 0;")

        # Insert data in order of dependency
        insert_data_to_db(cursor, 'users', users, ['user_id', 'username', 'email', 'password_hash', 'created_at'])
        insert_data_to_db(cursor, 'movies', movies, ['movie_id', 'title', 'release_year', 'synopsis', 'duration_min'])
        insert_data_to_db(cursor, 'genres', genres, ['genre_id', 'name'])
        insert_data_to_db(cursor, 'actors', actors, ['actor_id', 'first_name', 'last_name', 'birthdate'])
        insert_data_to_db(cursor, 'directors', directors, ['director_id', 'first_name', 'last_name', 'birthdate'])
        
        # Ratings and Reviews
        insert_data_to_db(cursor, 'ratings', ratings, ['user_id', 'movie_id', 'rating', 'created_at'])
        insert_data_to_db(cursor, 'reviews', reviews, ['review_id', 'user_id', 'movie_id', 'review_text', 'created_at'])
        
        # Watchlists
        insert_data_to_db(cursor, 'watchlists', watchlists, ['watchlist_id', 'user_id', 'name', 'created_at'])
        insert_data_to_db(cursor, 'watchlist_items', watchlist_items, ['watchlist_id', 'movie_id', 'added_at'])

        # Junction Tables
        insert_data_to_db(cursor, 'movie_genres', movie_genres, ['movie_id', 'genre_id'])
        insert_data_to_db(cursor, 'movie_actors', movie_actors, ['movie_id', 'actor_id', 'role_name'])
        insert_data_to_db(cursor, 'movie_directors', movie_directors, ['movie_id', 'director_id'])

        # Re-enable checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        cursor.execute("SET UNIQUE_CHECKS = 1;")

        # Commit all changes
        print("Committing all transactions...")
        cnx.commit()
        print("All data successfully imported into the database!")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()
            print("MySQL connection closed.")

if __name__ == "__main__":
    main()

