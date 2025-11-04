/*
-- =============================================================================
-- DBMS Lab Project: Advanced Movie Recommendation System
-- Database Schema (Logical Design)
--
-- This script creates the database and all 12 required tables.
-- It enforces data integrity using Primary Keys, Foreign Keys,
-- UNIQUE constraints, and NOT NULL.
--
-- Tables created:
-- 1.  users           (Stores user login info)
-- 2.  movies          (Stores core movie details)
-- 3.  genres          (Lookup table for genres, e.g., 'Action')
-- 4.  actors          (Lookup table for actors)
-- 5.  directors       (Lookup table for directors)
-- 6.  ratings         (Links users to movies with a 1-5 score)
-- 7.  reviews         (Links users to movies with a text review)
-- 8.  watchlists      (Stores user-created lists, e.g., 'Favorites')
-- 9.  movie_genres    (Junction table: links movies to genres)
-- 10. movie_actors    (Junction table: links movies to actors)
-- 11. movie_directors (Junction table: links movies to directors)
-- 12. watchlist_items (Junction table: links watchlists to movies)
-- =============================================================================
*/

-- Drop the database if it already exists to start fresh
DROP DATABASE IF EXISTS movie_rec_db;

-- Create the new database
CREATE DATABASE movie_rec_db;

-- Select the database to use
USE movie_rec_db;


-- 1. users Table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. movies Table
CREATE TABLE movies (
    movie_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    release_year INT NOT NULL,
    synopsis TEXT,
    duration_min INT,
    -- Index on title for faster searching
    INDEX idx_title (title)
);

-- 3. genres Table
CREATE TABLE genres (
    genre_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- 4. actors Table
CREATE TABLE actors (
    actor_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birthdate DATE,
    -- Index on name for faster searching
    INDEX idx_actor_name (last_name, first_name)
);
select * from actors;
-- 5. directors Table
CREATE TABLE directors (
    director_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    birthdate DATE,
    -- Index on name for faster searching
    INDEX idx_director_name (last_name, first_name)
);

-- 6. ratings Table
CREATE TABLE ratings (
    rating_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    
    -- A user can only rate a specific movie once
    UNIQUE KEY uk_user_movie_rating (user_id, movie_id)
);

-- 7. reviews Table
CREATE TABLE reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    movie_id INT NOT NULL,
    review_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    
    -- A user can only review a specific movie once
    UNIQUE KEY uk_user_movie_review (user_id, movie_id)
);

-- 8. watchlists Table
CREATE TABLE watchlists (
    watchlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- A user's watchlist names must be unique (e.g., only one 'Favorites')
    UNIQUE KEY uk_user_watchlist_name (user_id, name)
);

-- =============================================================================
-- JUNCTION TABLES (Many-to-Many Relationships)
-- =============================================================================

-- 9. movie_genres (Links movies to genres)
CREATE TABLE movie_genres (
    movie_id INT NOT NULL,
    genre_id INT NOT NULL,
    
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE
);

-- 10. movie_actors (Links movies to actors)
CREATE TABLE movie_actors (
    movie_id INT NOT NULL,
    actor_id INT NOT NULL,
    role_name VARCHAR(100) NOT NULL DEFAULT 'Unknown',
    
    PRIMARY KEY (movie_id, actor_id, role_name),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES actors(actor_id) ON DELETE CASCADE
);

-- 11. movie_directors (Links movies to directors)
CREATE TABLE movie_directors (
    movie_id INT NOT NULL,
    director_id INT NOT NULL,
    
    PRIMARY KEY (movie_id, director_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    FOREIGN KEY (director_id) REFERENCES directors(director_id) ON DELETE CASCADE
);

-- 12. watchlist_items (Links watchlists to movies)
-- *** THIS IS THE CORRECTED TABLE ***
CREATE TABLE watchlist_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY, -- Added this ID for the API
    watchlist_id INT NOT NULL,
    movie_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Added this for the data generator
    
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    
    -- A movie can only be on a specific watchlist once
    UNIQUE KEY uk_watchlist_movie (watchlist_id, movie_id) 
);

/*
-- =============================================================================
-- End of Schema
-- =============================================================================
*/
