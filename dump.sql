-- Script de migration vers Turso
CREATE TABLE IF NOT EXISTS historique_artistes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_enregistrement DATE NOT NULL,
    artiste_name TEXT NOT NULL,
    spotify_id TEXT NOT NULL,
    followers_count INTEGER NOT NULL,
    popularity_score INTEGER NOT NULL,
    streams_real INTEGER DEFAULT 0,
    UNIQUE (spotify_id, date_enregistrement)
);

INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-06-23', 'KITO', '0T4d2alRNWD29IME6Yb142', 22321, 32, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-06-30', 'KITO', '0T4d2alRNWD29IME6Yb142', 22755, 33, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-07-07', 'KITO', '0T4d2alRNWD29IME6Yb142', 23445, 37, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-07-14', 'KITO', '0T4d2alRNWD29IME6Yb142', 22530, 33, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-07-21', 'KITO', '0T4d2alRNWD29IME6Yb142', 23607, 35, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-07-28', 'KITO', '0T4d2alRNWD29IME6Yb142', 23845, 38, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-08-04', 'KITO', '0T4d2alRNWD29IME6Yb142', 24187, 37, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-08-11', 'KITO', '0T4d2alRNWD29IME6Yb142', 23546, 33, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-08-18', 'KITO', '0T4d2alRNWD29IME6Yb142', 23661, 37, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-08-25', 'KITO', '0T4d2alRNWD29IME6Yb142', 23573, 36, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-09-01', 'KITO', '0T4d2alRNWD29IME6Yb142', 23803, 35, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-09-08', 'KITO', '0T4d2alRNWD29IME6Yb142', 24830, 38, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-09-15', 'KITO', '0T4d2alRNWD29IME6Yb142', 23998, 35, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-09-22', 'KITO', '0T4d2alRNWD29IME6Yb142', 24473, 36, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-09-29', 'KITO', '0T4d2alRNWD29IME6Yb142', 24363, 38, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-10-06', 'KITO', '0T4d2alRNWD29IME6Yb142', 24757, 35, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-10-13', 'KITO', '0T4d2alRNWD29IME6Yb142', 25541, 35, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-10-20', 'KITO', '0T4d2alRNWD29IME6Yb142', 25701, 38, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-10-27', 'KITO', '0T4d2alRNWD29IME6Yb142', 25475, 36, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-11-03', 'KITO', '0T4d2alRNWD29IME6Yb142', 25319, 39, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-11-10', 'KITO', '0T4d2alRNWD29IME6Yb142', 26654, 37, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-11-17', 'KITO', '0T4d2alRNWD29IME6Yb142', 26369, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-11-24', 'KITO', '0T4d2alRNWD29IME6Yb142', 25774, 39, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-12-01', 'KITO', '0T4d2alRNWD29IME6Yb142', 26136, 38, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-12-08', 'KITO', '0T4d2alRNWD29IME6Yb142', 26203, 36, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-12-15', 'KITO', '0T4d2alRNWD29IME6Yb142', 26630, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-12-22', 'KITO', '0T4d2alRNWD29IME6Yb142', 27365, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2025-12-29', 'KITO', '0T4d2alRNWD29IME6Yb142', 26839, 41, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-01-05', 'KITO', '0T4d2alRNWD29IME6Yb142', 27739, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-01-12', 'KITO', '0T4d2alRNWD29IME6Yb142', 27518, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-01-19', 'KITO', '0T4d2alRNWD29IME6Yb142', 27674, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-01-26', 'KITO', '0T4d2alRNWD29IME6Yb142', 27750, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-02-02', 'KITO', '0T4d2alRNWD29IME6Yb142', 29031, 43, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-02-09', 'KITO', '0T4d2alRNWD29IME6Yb142', 28389, 37, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-02-16', 'KITO', '0T4d2alRNWD29IME6Yb142', 29118, 41, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-02-23', 'KITO', '0T4d2alRNWD29IME6Yb142', 29346, 38, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-03-02', 'KITO', '0T4d2alRNWD29IME6Yb142', 29637, 41, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-03-09', 'KITO', '0T4d2alRNWD29IME6Yb142', 29420, 42, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-03-16', 'KITO', '0T4d2alRNWD29IME6Yb142', 29004, 42, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-03-23', 'KITO', '0T4d2alRNWD29IME6Yb142', 29720, 39, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-03-30', 'KITO', '0T4d2alRNWD29IME6Yb142', 29824, 41, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-04-06', 'KITO', '0T4d2alRNWD29IME6Yb142', 29844, 44, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-04-13', 'KITO', '0T4d2alRNWD29IME6Yb142', 29758, 42, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-04-20', 'KITO', '0T4d2alRNWD29IME6Yb142', 30779, 39, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-04-27', 'KITO', '0T4d2alRNWD29IME6Yb142', 30040, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-05-04', 'KITO', '0T4d2alRNWD29IME6Yb142', 31352, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-05-11', 'KITO', '0T4d2alRNWD29IME6Yb142', 31174, 40, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-05-18', 'KITO', '0T4d2alRNWD29IME6Yb142', 31093, 44, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-05-25', 'KITO', '0T4d2alRNWD29IME6Yb142', 31409, 42, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-06-01', 'KITO', '0T4d2alRNWD29IME6Yb142', 31899, 45, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-06-08', 'KITO', '0T4d2alRNWD29IME6Yb142', 31293, 43, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-06-15', 'KITO', '0T4d2alRNWD29IME6Yb142', 31992, 46, 0);
INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ('2026-06-22', 'KITO', '0T4d2alRNWD29IME6Yb142', 0, 0, 0);
