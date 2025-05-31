"""
Prompt templates for UMARead AI question generation
Content-specific prompts for different text types and difficulty levels
"""
from typing import Dict, List, Tuple
from app.schemas.umaread import AssignmentMetadata, WorkType, LiteraryForm


class PromptTemplateManager:
    """Manages content-specific AI prompts for question generation"""
    
    def get_summary_prompt(self, metadata: AssignmentMetadata) -> str:
        """Get appropriate summary prompt based on content type"""
        if metadata.work_type == WorkType.FICTION:
            return "Summarize what happens in this section of the story."
        elif metadata.genre in ["Science", "Biology", "Chemistry", "Physics"]:
            return "Summarize the information presented in this section."
        elif metadata.genre == "History":
            return "Summarize the historical events described in this section."
        elif metadata.literary_form == LiteraryForm.POETRY:
            return "Describe what the speaker is expressing in these lines."
        else:
            return "Summarize the main points explained in this text."
    
    def get_comprehension_prompt(self, metadata: AssignmentMetadata, difficulty: int, chunk_content: str) -> str:
        """Get comprehension question generation prompt based on content and difficulty"""
        base_prompt = f"""Generate a comprehension question for the following text chunk.
        
Content Type: {metadata.work_type.value}
Genre: {metadata.genre}
Subject: {metadata.subject}
Grade Level: {metadata.grade_level}
Difficulty Level: {difficulty}/8

Text:
{chunk_content}

"""
        
        if metadata.work_type == WorkType.FICTION:
            return base_prompt + self._get_fiction_prompt(metadata.genre, difficulty)
        elif metadata.genre in ["Science", "Biology", "Chemistry", "Physics"]:
            return base_prompt + self._get_science_prompt(metadata.subject, difficulty)
        elif metadata.genre == "History":
            return base_prompt + self._get_history_prompt(metadata.subject, difficulty)
        elif metadata.literary_form == LiteraryForm.POETRY:
            return base_prompt + self._get_poetry_prompt(difficulty)
        else:
            return base_prompt + self._get_informational_prompt(metadata.subject, difficulty)
    
    def _get_fiction_prompt(self, genre: str, difficulty: int) -> str:
        """Fiction-specific prompts focused on character, plot, theme"""
        difficulty_guidelines = self._get_difficulty_guidelines(difficulty)
        
        return f"""Generate a comprehension question for this fiction text following these guidelines:

{difficulty_guidelines}

Focus Areas for Fiction:
- Character development and motivations
- Plot events and their sequence
- Setting and its impact on the story
- Themes and underlying messages
- Literary devices and techniques

Requirements:
1. The question must be answerable from the text provided
2. Use age-appropriate vocabulary
3. Ensure the question tests understanding, not memory
4. Question should be specific to this chunk's content
5. Avoid yes/no questions

Example Good Questions by Difficulty:
Level 1-2: "What did the main character do when they found the key?"
Level 3-4: "Why did Sarah decide to help the stranger?"
Level 5-6: "Based on the character's actions, what can you infer about their feelings?"
Level 7-8: "How does the author use the storm to reflect the character's internal conflict?"

Generate a single, clear question appropriate for difficulty level {difficulty}."""
    
    def _get_science_prompt(self, subject: str, difficulty: int) -> str:
        """Science-specific prompts focused on processes, data, cause/effect"""
        difficulty_guidelines = self._get_difficulty_guidelines(difficulty)
        
        return f"""Generate a comprehension question for this science text following these guidelines:

{difficulty_guidelines}

Focus Areas for Science Content:
- Scientific processes and methods
- Cause and effect relationships
- Data interpretation and evidence
- Key concepts and definitions
- Real-world applications

Subject-Specific Context: {subject}

Requirements:
1. Focus on scientific understanding, not memorization
2. Use appropriate scientific vocabulary for the grade level
3. Connect to real-world examples when possible
4. Ensure accuracy in scientific content
5. Test conceptual understanding

Example Good Questions by Difficulty:
Level 1-2: "What are the three states of water mentioned in the text?"
Level 3-4: "What causes water to change from liquid to gas?"
Level 5-6: "Based on the experiment results, what can you conclude about temperature's effect?"
Level 7-8: "How does this process demonstrate the law of conservation of energy?"

Generate a single, clear question appropriate for difficulty level {difficulty}."""
    
    def _get_history_prompt(self, subject: str, difficulty: int) -> str:
        """History-specific prompts focused on chronology, causation, significance"""
        difficulty_guidelines = self._get_difficulty_guidelines(difficulty)
        
        return f"""Generate a comprehension question for this historical text following these guidelines:

{difficulty_guidelines}

Focus Areas for Historical Content:
- Chronology and sequence of events
- Cause and effect in history
- Historical figures and their actions
- Social, political, and economic factors
- Historical significance and impact

Historical Period/Topic: {subject}

Requirements:
1. Focus on historical thinking skills
2. Connect events to broader historical context
3. Use period-appropriate terminology
4. Encourage analysis over memorization
5. Consider multiple perspectives when appropriate

Example Good Questions by Difficulty:
Level 1-2: "When did the event described in the text take place?"
Level 3-4: "What were the main reasons for the conflict?"
Level 5-6: "How did this event change the lives of ordinary people?"
Level 7-8: "What factors contributed to the different outcomes in similar situations?"

Generate a single, clear question appropriate for difficulty level {difficulty}."""
    
    def _get_poetry_prompt(self, difficulty: int) -> str:
        """Poetry-specific prompts focused on devices, imagery, interpretation"""
        difficulty_guidelines = self._get_difficulty_guidelines(difficulty)
        
        return f"""Generate a comprehension question for this poetry text following these guidelines:

{difficulty_guidelines}

Focus Areas for Poetry:
- Imagery and sensory details
- Literary devices (metaphor, simile, personification)
- Speaker's voice and perspective
- Mood and tone
- Theme and meaning

Requirements:
1. Focus on poetic elements appropriate to grade level
2. Encourage interpretation with textual support
3. Use accessible language to discuss poetry
4. Connect form to meaning when relevant
5. Avoid overly subjective questions

Example Good Questions by Difficulty:
Level 1-2: "What is the poem describing?"
Level 3-4: "What feeling does the poet express about nature?"
Level 5-6: "How does the poet use repetition to emphasize the main idea?"
Level 7-8: "How do the imagery and structure work together to convey the theme?"

Generate a single, clear question appropriate for difficulty level {difficulty}."""
    
    def _get_informational_prompt(self, subject: str, difficulty: int) -> str:
        """General informational text prompts"""
        difficulty_guidelines = self._get_difficulty_guidelines(difficulty)
        
        return f"""Generate a comprehension question for this informational text following these guidelines:

{difficulty_guidelines}

Focus Areas for Informational Text:
- Main ideas and supporting details
- Text structure and organization
- Author's purpose and perspective
- Factual information and evidence
- Practical applications

Topic Area: {subject}

Requirements:
1. Focus on information literacy skills
2. Test understanding of key concepts
3. Connect to real-world applications
4. Use clear, precise language
5. Ensure factual accuracy

Example Good Questions by Difficulty:
Level 1-2: "What are the main steps in the process described?"
Level 3-4: "According to the text, what causes this to happen?"
Level 5-6: "What evidence does the author provide to support the main claim?"
Level 7-8: "How does the information in this section relate to the overall argument?"

Generate a single, clear question appropriate for difficulty level {difficulty}."""
    
    def _get_difficulty_guidelines(self, difficulty: int) -> str:
        """Get cognitive complexity guidelines for each difficulty level"""
        guidelines = {
            1: """Level 1 - Basic Information Retrieval:
- Ask for explicitly stated facts
- Focus on who, what, when, where
- Single-step thinking required
- Direct quotes from text acceptable as answers""",
            
            2: """Level 2 - Details & Specifics:
- Ask for specific details mentioned in text
- Focus on sequences, lists, or descriptions
- Require precise recall of information
- Answers should demonstrate careful reading""",
            
            3: """Level 3 - Stated Relationships:
- Ask about cause-effect relationships that are explicitly stated
- Focus on comparisons or contrasts mentioned in text
- Require understanding of connections between ideas
- Answers found directly in text but require comprehension""",
            
            4: """Level 4 - Main Ideas & Organization:
- Ask about central concepts or main arguments
- Focus on how information is structured
- Require synthesis of multiple details
- Answers demonstrate understanding of overall meaning""",
            
            5: """Level 5 - Simple Inference:
- Ask students to draw conclusions from evidence
- Focus on implied information that's strongly suggested
- Require connecting multiple pieces of information
- Answers go slightly beyond literal text""",
            
            6: """Level 6 - Implied Relationships:
- Ask about unstated connections between ideas
- Focus on author's implied meaning or purpose
- Require reading between the lines
- Answers demonstrate deeper understanding""",
            
            7: """Level 7 - Purpose & Significance:
- Ask about broader meaning or importance
- Focus on why information matters
- Require evaluation of ideas
- Answers show critical thinking""",
            
            8: """Level 8 - Complex Analysis:
- Ask for analysis of how parts contribute to whole
- Focus on patterns, themes, or techniques
- Require sophisticated interpretation
- Answers demonstrate advanced comprehension"""
        }
        
        return guidelines.get(difficulty, guidelines[5])
    
    def get_evaluation_prompt(self, 
                            question: str, 
                            student_answer: str, 
                            chunk_content: str,
                            metadata: AssignmentMetadata,
                            question_type: str,
                            difficulty: int = None) -> str:
        """Get prompt for evaluating student answers"""
        
        context = f"""Evaluate this student answer for accuracy and completeness.

Question Type: {question_type}
Content Type: {metadata.work_type.value}
Genre: {metadata.genre}
Grade Level: {metadata.grade_level}
{"Difficulty Level: " + str(difficulty) + "/8" if difficulty else ""}

Original Text:
{chunk_content}

Question: {question}

Student Answer: {student_answer}

"""
        
        if question_type == "summary":
            return context + self._get_summary_evaluation_criteria(metadata)
        else:
            return context + self._get_comprehension_evaluation_criteria(metadata, difficulty)
    
    def _get_summary_evaluation_criteria(self, metadata: AssignmentMetadata) -> str:
        """Evaluation criteria for summary questions"""
        content_specific = ""
        
        if metadata.work_type == WorkType.FICTION:
            content_specific = """
Fiction-Specific Criteria:
- Identifies main events or actions
- Mentions key characters involved
- Shows understanding of plot progression
- Captures the essence of what happened"""
        elif metadata.genre in ["Science", "Biology", "Chemistry", "Physics"]:
            content_specific = """
Science-Specific Criteria:
- Identifies main concepts or processes
- Shows understanding of scientific principles
- Accurately uses scientific terminology
- Captures key information or findings"""
        elif metadata.genre == "History":
            content_specific = """
History-Specific Criteria:
- Identifies key events or developments
- Shows understanding of chronology
- Mentions important figures or groups
- Captures historical significance"""
        
        return f"""Evaluate the summary based on these criteria:

General Requirements:
1. Completeness: Does it capture the main points?
2. Accuracy: Is the information correct?
3. Conciseness: Is it appropriately brief (2-3 sentences)?
4. Clarity: Is it clearly written?
{content_specific}

Provide evaluation in this format:
1. Is the answer correct? (true/false)
2. Confidence score (0.0-1.0)
3. Brief, encouraging feedback (1-2 sentences)
4. If incorrect, what key elements are missing?

Be encouraging and constructive, especially for younger students."""
    
    def _get_comprehension_evaluation_criteria(self, metadata: AssignmentMetadata, difficulty: int) -> str:
        """Evaluation criteria for comprehension questions"""
        return f"""Evaluate the answer based on these criteria:

Difficulty Level {difficulty} Expectations:
{self._get_evaluation_expectations(difficulty)}

Content-Specific Considerations:
- Accuracy of facts from the text
- Appropriate use of evidence
- Understanding of concepts
- Quality of reasoning (for higher levels)

Provide evaluation in this format:
1. Is the answer correct? (true/false)
2. Confidence score (0.0-1.0)
3. Brief, constructive feedback
4. Specific feedback related to the content type
5. If incorrect, what key elements are missing?
6. Suggested difficulty adjustment (-1, 0, or +1)

Be encouraging and provide specific guidance for improvement."""
    
    def _get_evaluation_expectations(self, difficulty: int) -> str:
        """What to expect in answers at each difficulty level"""
        expectations = {
            1: "Accurate retrieval of basic facts directly stated in text",
            2: "Precise recall of specific details with good attention to text",
            3: "Understanding of stated relationships and connections",
            4: "Grasp of main ideas and how information is organized",
            5: "Reasonable conclusions drawn from textual evidence",
            6: "Understanding of implied meanings and unstated connections",
            7: "Thoughtful analysis of purpose and significance",
            8: "Sophisticated analysis showing deep comprehension"
        }
        return expectations.get(difficulty, expectations[5])