-- Add technique bonus field for Phase 2 of rhetorical techniques enhancement

-- Add technique_bonus_awarded field to debate_posts table
ALTER TABLE debate_posts 
ADD COLUMN technique_bonus_awarded DECIMAL(3,1);

-- Add comment for clarity
COMMENT ON COLUMN debate_posts.technique_bonus_awarded IS 'Bonus points (0-5) awarded for correct use of selected rhetorical technique';