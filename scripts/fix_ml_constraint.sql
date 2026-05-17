ALTER TABLE mart.mart_asteroids_ml
ADD CONSTRAINT mart_asteroids_ml_neo_id_feed_date_key UNIQUE (neo_id, feed_date);
