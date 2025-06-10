-- Add audio pronunciation fields to vocabulary_words table
-- These fields will store pronunciation data from Free Dictionary API

ALTER TABLE vocabulary_words 
ADD COLUMN audio_url VARCHAR(500),
ADD COLUMN phonetic_text VARCHAR(200);

-- Add comments to document the purpose
COMMENT ON COLUMN vocabulary_words.audio_url IS 'URL to pronunciation audio file from Free Dictionary API';
COMMENT ON COLUMN vocabulary_words.phonetic_text IS 'Phonetic spelling of the word (e.g., həˈləʊ)';