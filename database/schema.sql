-- Create Database
CREATE DATABASE IF NOT EXISTS news_db;
USE news_db;

-- 1. Users Table
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    category_icon VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. News Sources Table
CREATE TABLE news_sources (
    source_id INT AUTO_INCREMENT PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    source_url VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. News Headlines Table (with category)
CREATE TABLE news_headlines (
    headline_id INT AUTO_INCREMENT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    url VARCHAR(500) NOT NULL,
    image_url VARCHAR(500),
    source_id INT,
    category_id INT DEFAULT 1,
    publish_date DATETIME,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES news_sources(source_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- 5. Favorites Table
CREATE TABLE favorites (
    fav_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    headline_id INT NOT NULL,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (headline_id) REFERENCES news_headlines(headline_id) ON DELETE CASCADE,
    UNIQUE KEY unique_favorite (user_id, headline_id)
);

-- Insert default categories
INSERT INTO categories (category_name, category_icon) VALUES
('General', '📰'),
('Politics', '🏛️'),
('Technology', '💻'),
('Sports', '⚽'),
('Business', '💼'),
('Entertainment', '🎬'),
('Health', '🏥'),
('Science', '🔬'),
('World', '🌍'),
('Education', '📚');

-- Insert default news sources
INSERT INTO news_sources (source_name, source_url) VALUES
('NDTV', 'https://feeds.feedburner.com/ndtvnews-latest'),
('India Today', 'https://www.indiatoday.in/rss/home'),
('Hindustan Times', 'https://www.hindustantimes.com/feeds/rss/latest-news/rssfeed.xml');

-- Create indexes for better performance
CREATE INDEX idx_headline_date ON news_headlines(publish_date DESC);
CREATE INDEX idx_user_favorites ON favorites(user_id);
CREATE INDEX idx_headline_source ON news_headlines(source_id);
CREATE INDEX idx_headline_category ON news_headlines(category_id);