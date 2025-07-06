"""
Prompt templates and management for UMALecture AI generation
"""
from typing import List, Dict, Any


class UMALecturePromptManager:
    """Manages prompt templates for UMALecture AI operations"""
    
    @staticmethod
    def get_outline_parsing_prompt(outline: str, objectives: List[str]) -> str:
        """Get prompt for parsing teacher's outline into topics"""
        return f"""Parse this educational outline into a structured topic hierarchy:

OUTLINE:
{outline}

LEARNING OBJECTIVES:
{', '.join(objectives)}

Requirements:
1. Identify main topics and subtopics
2. Create clear, descriptive titles
3. Generate unique IDs using snake_case (e.g., "photosynthesis_basics")
4. Maintain the logical flow of the original outline
5. Ensure each topic is substantial enough for 4 difficulty levels

Return a structured list of topics with their relationships."""
    
    @staticmethod
    def get_content_generation_prompt(
        topic_title: str,
        difficulty: str,
        grade_level: str,
        subject: str,
        image_descriptions: List[str],
        learning_objectives: List[str] = None  # Add this parameter
    ) -> str:
        """Get prompt for generating content at a specific difficulty"""
        
        difficulty_guidelines = {
            "basic": "Use simple language, fundamental concepts, concrete examples",
            "intermediate": "Introduce more detail, connections between ideas, some technical terms",
            "advanced": "Include complex relationships, critical thinking, deeper analysis",
            "expert": "Explore nuanced perspectives, cutting-edge information, synthesis of ideas"
        }
        
        explore_guidelines = {
            "basic": "Mark 3-5 fundamental vocabulary words and basic process names",
            "intermediate": "Mark 3-5 mechanism names, system components, and key processes",
            "advanced": "Mark 3-5 complex processes, specialized terminology, and analytical concepts", 
            "expert": "Mark 3-5 research terminology, interdisciplinary connections, and advanced concepts"
        }
        
        return f"""Create educational content for this topic at {difficulty} level:

TOPIC: {topic_title}
GRADE LEVEL: {grade_level}
DIFFICULTY: {difficulty} - {difficulty_guidelines[difficulty]}

LEARNING OBJECTIVES:
{chr(10).join(f"- {obj}" for obj in learning_objectives) if learning_objectives else "No specific learning objectives provided"}

READING LEVEL REQUIREMENTS:
Write at the reading level appropriate for {grade_level} students. This means:
- Use vocabulary that {grade_level} students can understand without assistance
- Keep sentence structure simple and clear for this grade level
- Avoid technical jargon unless it's the specific term being taught
- When introducing new vocabulary, provide context clues within the sentence
- Aim for sentence lengths typical of {grade_level} textbooks
- Use active voice and direct language appropriate for this developmental stage
- If you must use complex terms, immediately follow with simpler explanations

Remember: The content should be intellectually challenging at the {difficulty} level while remaining linguistically accessible to {grade_level} readers.

AVAILABLE IMAGES:
{chr(10).join(image_descriptions) if image_descriptions else 'No images available'}

CRITICAL INSTRUCTION - EXPLORATION POINTS:
You MUST include 3-5 strategic exploration points in your content using <explore>term</explore> tags.
{explore_guidelines[difficulty]}

Examples:
- "The process of <explore>photosynthesis</explore> converts light energy..."
- "Scientists use <explore>spectroscopy</explore> to analyze..."
- "The <explore>mitochondria</explore> are often called..."

IMPORTANT: Create strategic knowledge gaps - don't fully explain terms marked with <explore> tags. 
Instead, mention them in context but leave room for students to explore deeper.

Requirements:
1. Base content ONLY on the topic title, the learning objectives listed above, and uploaded images
2. Ensure content directly supports achievement of the stated learning objectives
3. Do NOT incorporate general subject knowledge unless explicitly mentioned in the topic/objectives
4. Include key concepts clearly explained EXCEPT for <explore> tagged terms
5. Reference images naturally where relevant
6. Build on previous difficulty levels
7. Aim for 200-400 words
8. Use formatting for clarity (paragraphs, lists if needed)
9. MUST include 3-5 <explore> tags for key terms students should investigate

Focus on understanding the specific topic as outlined, not general subject knowledge."""
    
    @staticmethod
    def get_question_generation_prompt(
        topic_title: str,
        content: str,
        difficulty: str,
        with_images: bool = False
    ) -> str:
        """Get prompt for generating questions"""
        
        question_types = {
            "basic": "factual recall, simple comprehension",
            "intermediate": "application, cause-and-effect",
            "advanced": "analysis, synthesis, evaluation",
            "expert": "critical thinking, hypothetical scenarios"
        }
        
        return f"""Generate 2-3 educational questions for this content:

TOPIC: {topic_title}
DIFFICULTY: {difficulty}
QUESTION TYPES: {question_types[difficulty]}

CONTENT:
{content}

CRITICAL QUESTION FORMAT REQUIREMENTS:
- These are SHORT ANSWER questions where students type their own responses
- Do NOT use "which of the following" or "select the best answer"
- Do NOT reference answer choices that don't exist
- Ask direct questions expecting written responses
- Use formats like "What is...", "Explain why...", "Describe how..."

Requirements:
1. Test understanding, not just memorization
2. {"Include at least one visual question using the images" if with_images else "Focus on text comprehension"}
3. All questions must be SHORT ANSWER format
4. Provide clear, unambiguous questions
5. Include correct answers and brief explanations
6. Make questions progressively challenging within the difficulty level

Ensure questions encourage thinking and exploration."""
    
    @staticmethod
    def get_image_enhancement_prompt(
        teacher_description: str,
        topic_context: str,
        grade_level: str
    ) -> str:
        """Get prompt for enhancing image descriptions"""
        return f"""Enhance this educational image description:

TEACHER'S DESCRIPTION: {teacher_description}
TOPIC CONTEXT: {topic_context}
GRADE LEVEL: {grade_level}

Provide:
1. A detailed educational description (2-3 paragraphs)
2. Key visual elements students should notice
3. Connections to the topic content
4. 2-3 potential discussion questions
5. Accessibility considerations

Make the description engaging and educational, helping students understand both what they see and why it matters."""
    
    
    @staticmethod
    def get_lecture_summary_prompt(lecture_structure: Dict[str, Any]) -> str:
        """Get prompt for generating a lecture summary"""
        topics = lecture_structure.get("topics", {})
        topic_list = [f"- {data['title']}" for data in topics.values()]
        
        return f"""Create a concise summary of this interactive lecture:

TOPICS COVERED:
{chr(10).join(topic_list)}

Provide:
1. A 2-3 sentence overview of the lecture
2. Key learning outcomes
3. How topics connect to each other
4. Suggested learning path for students

Keep it brief but informative."""
    
    @staticmethod
    def get_exploration_validation_prompt(exploration_term: str, student_question: str) -> str:
        """Get prompt for validating if a student question is on-topic"""
        return f"""Determine if this student question is relevant to understanding the exploration term.

EXPLORATION TERM: {exploration_term}
STUDENT QUESTION: {student_question}

Is this question directly related to understanding, explaining, or learning about "{exploration_term}"?

Consider ON-TOPIC if the question asks about:
- Definition or explanation of the term
- How the term works or functions
- Examples of the term
- Connection between the term and other concepts
- Details, mechanisms, or components of the term
- Why the term is important

Consider OFF-TOPIC if the question asks about:
- Completely different concepts
- Personal or non-academic topics
- Other homework or assignments
- Topics not related to understanding this specific term

Respond with EXACTLY one of these two responses:
- "ON_TOPIC" if the question is relevant
- "OFF_TOPIC" if the question is not relevant

Do not include any other text in your response."""
    
    @staticmethod
    def get_exploration_response_prompt(
        exploration_term: str,
        student_question: str,
        lecture_context: str,
        conversation_history: List[Dict[str, str]],
        difficulty_level: str,
        grade_level: str
    ) -> str:
        """Get prompt for generating exploration responses"""
        
        history_text = ""
        if conversation_history:
            history_text = "\n\nPREVIOUS CONVERSATION:\n"
            for msg in conversation_history[-4:]:  # Last 4 messages for context
                history_text += f"{msg['role'].upper()}: {msg['content']}\n"
        
        return f"""Provide an educational explanation for this exploration term.

EXPLORATION TERM: {exploration_term}
CURRENT DIFFICULTY LEVEL: {difficulty_level}
GRADE LEVEL: {grade_level}

LECTURE CONTEXT:
{lecture_context[:500]}...

STUDENT QUESTION: {student_question if student_question else "Please explain this term"}
{history_text}

Requirements:
1. Provide a clear, engaging explanation appropriate for {grade_level} students
2. Connect the explanation back to the lecture content when possible
3. Use language appropriate for the {difficulty_level} level
4. Keep response between 150-300 words
5. If this is the first message (no question provided), give a foundational explanation
6. Build on previous conversation if there is history
7. Include a relevant example or analogy when helpful
8. End with an encouraging prompt for further exploration

Focus on helping the student understand this specific concept deeply."""
    
    @staticmethod
    def get_exploration_redirect_prompt(exploration_term: str, student_question: str) -> str:
        """Get prompt for redirecting off-topic questions"""
        return f"""The student asked an off-topic question while exploring a specific term.

EXPLORATION TERM: {exploration_term}
OFF-TOPIC QUESTION: {student_question}

Generate a friendly, encouraging message that:
1. Acknowledges their question
2. Gently redirects them back to the exploration term
3. Suggests how they might reframe their question
4. Provides 1-2 example questions they could ask instead

Keep the tone supportive and educational. Maximum 100 words."""