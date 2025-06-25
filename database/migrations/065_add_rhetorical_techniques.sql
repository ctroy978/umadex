-- Add rhetorical techniques reference system for UMADebate
-- Phase 1: Add selected_technique field to debate posts

-- Add selected_technique field to debate_posts table
ALTER TABLE debate_posts 
ADD COLUMN selected_technique VARCHAR(100);

-- Create table for rhetorical techniques reference
CREATE TABLE rhetorical_techniques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    technique_type VARCHAR(20) NOT NULL CHECK (technique_type IN ('proper', 'improper')),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    example TEXT NOT NULL,
    tip_or_reason TEXT NOT NULL, -- 'tip' for proper, 'why it's unfair' for improper
    sort_order INTEGER NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index for quick lookups
CREATE INDEX idx_rhetorical_techniques_type ON rhetorical_techniques(technique_type, sort_order);

-- RLS Policy
ALTER TABLE rhetorical_techniques ENABLE ROW LEVEL SECURITY;

-- Read-only access for all users
CREATE POLICY rhetorical_techniques_read ON rhetorical_techniques
    FOR SELECT USING (true);

-- Write access disabled (admin only, will be updated when auth is configured)
CREATE POLICY rhetorical_techniques_write ON rhetorical_techniques
    FOR ALL USING (false);

-- Insert proper rhetorical techniques
INSERT INTO rhetorical_techniques (technique_type, name, display_name, description, example, tip_or_reason, sort_order) VALUES
('proper', 'ethos', 'Ethos (Appeal to Credibility)', 'Build trust by showing you''re knowledgeable and trustworthy.', 'As Dr. Jane Smith, a leading climate scientist, states...', 'Cite credible sources and speak confidently.', 1),
('proper', 'pathos', 'Pathos (Appeal to Emotion)', 'Connect with your audience''s feelings to make your argument hit home.', 'Picture a child missing school due to war...', 'Keep emotions genuine—avoid overdoing it.', 2),
('proper', 'logos', 'Logos (Appeal to Logic)', 'Persuade with clear reasoning, facts, and evidence.', 'A 2021 report shows raising minimum wage could lift 1.3 million workers out of poverty.', 'Ensure your facts are accurate and easy to follow.', 3),
('proper', 'kairos', 'Kairos (Appeal to Timeliness)', 'Show why your argument matters right now.', 'With cyberattacks up 30% this year, we must invest in cybersecurity today.', 'Tie your point to current events or urgent issues.', 4),
('proper', 'repetition', 'Repetition', 'Repeat key words or phrases to emphasize your main point.', 'Education is opportunity. Education is equality. Education is progress.', 'Use sparingly to avoid sounding repetitive.', 5),
('proper', 'rhetorical_question', 'Rhetorical Question', 'Ask a question that doesn''t need an answer to provoke thought.', 'Can we really ignore climate change when our planet''s future is at stake?', 'Use to engage the audience, but don''t overdo it.', 6),
('proper', 'antithesis', 'Antithesis', 'Contrast two opposing ideas in a sentence to create a striking effect.', 'This policy isn''t about restricting freedom; it''s about ensuring safety.', 'Keep it concise for maximum impact.', 7),
('proper', 'refutation', 'Refutation', 'Counter your opponent''s argument to weaken their position.', 'My opponent says social media harms mental health, but studies show it also builds support networks.', 'Attack the argument, not the person.', 8),
('proper', 'metaphor', 'Metaphor', 'Compare two unlike things to make your point vivid and relatable.', 'Education is a ladder, lifting people out of poverty and into opportunity.', 'Choose metaphors that are clear and relevant.', 9),
('proper', 'concession', 'Concession', 'Admit a valid point from your opponent before countering it.', 'My opponent is right that technology creates jobs, but without retraining, it leaves workers behind.', 'Be brief with the concession to keep focus on your counterargument.', 10);

-- Insert improper rhetorical techniques
INSERT INTO rhetorical_techniques (technique_type, name, display_name, description, example, tip_or_reason, sort_order) VALUES
('improper', 'ad_hominem', 'Ad Hominem Attack', 'Attacking your opponent''s character instead of their argument.', 'My opponent can''t be trusted because they drive a gas-guzzling car.', 'Sidesteps the actual argument.', 1),
('improper', 'strawman', 'Strawman Argument', 'Misrepresenting your opponent''s argument to make it easier to attack.', 'My opponent says we should ban all cars! (when they only suggested limiting emissions)', 'Attacks a false version of their argument.', 2),
('improper', 'red_herring', 'Red Herring', 'Introducing an irrelevant topic to divert attention.', 'We''re discussing healthcare, but let''s talk about taxes instead.', 'Derails the debate from the core topic.', 3),
('improper', 'appeal_to_fear', 'Appeal to Fear (Scaremongering)', 'Exaggerating dangers to scare the audience into agreeing.', 'If we allow this policy, crime will skyrocket!', 'Manipulates emotions instead of using reasoned evidence.', 4),
('improper', 'false_dichotomy', 'False Dichotomy', 'Presenting only two options as if they''re the only possibilities.', 'Either we ban all social media, or we let it destroy our youth!', 'Oversimplifies complex issues.', 5),
('improper', 'slippery_slope', 'Slippery Slope', 'Claiming one action will inevitably lead to extreme consequences.', 'If we raise taxes slightly, soon the government will take all our money!', 'Assumes unproven outcomes.', 6),
('improper', 'cherry_picking', 'Cherry-Picking', 'Selectively using evidence that supports your argument while ignoring contradictory data.', 'This study shows our policy works! (ignoring five studies showing it fails)', 'Misleads by hiding the full picture.', 7),
('improper', 'gish_gallop', 'Gish Gallop', 'Overwhelming the opponent with a flood of arguments to prevent proper response.', 'My plan fails because of costs, studies, history, opinion, and ten other reasons!', 'Exploits time limits, making full responses impossible.', 8);