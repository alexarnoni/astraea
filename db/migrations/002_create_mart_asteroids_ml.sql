CREATE TABLE IF NOT EXISTS mart.mart_asteroids_ml (
    neo_id             VARCHAR(20)  NOT NULL,
    feed_date          DATE         NOT NULL,
    risk_proba_baixo   FLOAT,
    risk_proba_medio   FLOAT,
    risk_proba_alto    FLOAT,
    risk_label_ml      VARCHAR(20),
    PRIMARY KEY (neo_id, feed_date)
);
