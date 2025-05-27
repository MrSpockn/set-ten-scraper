INSERT INTO articles_category (id, name, parent_id, slug, created_at, updated_at)
SELECT 1, 'キャリア・働き方', NULL, 'career-work', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM articles_category WHERE id = 1);

INSERT INTO articles_category (id, name, parent_id, slug, created_at, updated_at)
SELECT 2, '技術・AI活用', NULL, 'tech-ai', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM articles_category WHERE id = 2);

INSERT INTO articles_category (id, name, parent_id, slug, created_at, updated_at)
SELECT 3, 'レビュー・仕事術', NULL, 'review-work', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM articles_category WHERE id = 3);

INSERT INTO articles_category (id, name, parent_id, slug, created_at, updated_at)
SELECT 4, '投資・マネー', NULL, 'investment-money', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM articles_category WHERE id = 4);

UPDATE articles_article SET category_id = 
  CASE 
    WHEN category = 'キャリア・働き方' THEN 1
    WHEN category = '技術・AI活用' THEN 2
    WHEN category = 'レビュー・仕事術' THEN 3
    WHEN category = '投資・マネー' THEN 4
  END;
