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
        learning_objectives: List[str] = None,  # Add this parameter
        subtopics: List[str] = None  # Add subtopics parameter
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
        
        # Determine which subtopics to focus on based on difficulty
        subtopic_focus = ""
        if subtopics and len(subtopics) >= 4:
            if difficulty in ["basic", "intermediate"]:
                relevant_subtopics = subtopics[:2]  # First two subtopics
                subtopic_focus = f"""
FOCUS SUBTOPICS FOR {difficulty.upper()} LEVEL:
You should focus your content PRIMARILY on these two subtopics:
{chr(10).join(f"- {subtopic}" for subtopic in relevant_subtopics)}

These subtopics are designed for foundational understanding. Do NOT include advanced concepts from subtopics 3 and 4."""
            else:  # advanced or expert
                relevant_subtopics = subtopics[2:4]  # Last two subtopics
                subtopic_focus = f"""
FOCUS SUBTOPICS FOR {difficulty.upper()} LEVEL:
You should focus your content PRIMARILY on these two subtopics:
{chr(10).join(f"- {subtopic}" for subtopic in relevant_subtopics)}

These subtopics contain more complex material. You may reference basic concepts from subtopics 1 and 2 as foundation, but focus on the advanced aspects."""
        
        return f"""Create educational content for this topic at {difficulty} level:

TOPIC: {topic_title}
GRADE LEVEL: {grade_level}
DIFFICULTY: {difficulty} - {difficulty_guidelines[difficulty]}
{subtopic_focus}

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

TEACHER-PROVIDED IMAGES:
{chr(10).join(f"- {desc}" for desc in image_descriptions) if image_descriptions else 'No images provided'}
Note: These images will be displayed to students alongside your content.

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
1. Base content ONLY on the topic title, the learning objectives listed above, and teacher-provided context
2. Ensure content directly supports achievement of the stated learning objectives
3. Do NOT incorporate general subject knowledge unless explicitly mentioned in the topic/objectives
4. Include key concepts clearly explained EXCEPT for <explore> tagged terms
5. You may reference the teacher's images conceptually (e.g., "as shown in the circuit diagram") but do not embed them
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
            "basic": "factual recall, simple comprehension, identifying key concepts",
            "intermediate": "application of concepts, cause-and-effect relationships, making connections",
            "advanced": "analysis of complex ideas, synthesis of information, evaluation of concepts",
            "expert": "critical thinking, hypothetical scenarios, innovative applications"
        }
        
        difficulty_examples = {
            "basic": [
                "What is the main function of [concept]?",
                "Name two key features of [process].",
                "In your own words, describe what [term] means."
            ],
            "intermediate": [
                "Explain how [process A] leads to [outcome B].",
                "Why is [concept] important for [broader topic]?",
                "Compare and contrast [item A] with [item B]."
            ],
            "advanced": [
                "Analyze the role of [concept] in [complex system].",
                "How would [process] be affected if [variable] changed?",
                "Evaluate the effectiveness of [method] for achieving [goal]."
            ],
            "expert": [
                "Design an experiment to test [hypothesis about concept].",
                "Propose a novel application of [concept] in [new context].",
                "Critique the current understanding of [topic] and suggest improvements."
            ]
        }
        
        return f"""Generate exactly 3 educational questions based on this content. Each question must be carefully crafted to test genuine understanding.

TOPIC: {topic_title}
DIFFICULTY LEVEL: {difficulty}
FOCUS AREAS: {question_types[difficulty]}

CONTENT TO BASE QUESTIONS ON:
{content}

STRICT FORMATTING REQUIREMENTS:
You must format your response EXACTLY as follows:

Question 1: [Your first question here]
Answer: [A complete but concise answer - 1-3 sentences]
Explanation: [Brief explanation of why this answer is correct and what concept it tests]

Question 2: [Your second question here]
Answer: [A complete but concise answer - 1-3 sentences]
Explanation: [Brief explanation of why this answer is correct and what concept it tests]

Question 3: [Your third question here]
Answer: [A complete but concise answer - 1-3 sentences]
Explanation: [Brief explanation of why this answer is correct and what concept it tests]

CRITICAL REQUIREMENTS:
1. ALL questions must be SHORT ANSWER format - students will type their responses
2. NEVER use multiple choice format or reference non-existent options
3. Questions must be directly answerable from the provided content
4. Avoid yes/no questions - require explanation or description
5. Each question should test a different aspect or concept from the content
6. Questions should progress in complexity within the {difficulty} level
7. Use clear, specific language appropriate for the difficulty level
8. {"At least one question should reference the visual elements described in the content" if with_images else "Focus entirely on the text content provided"}

EXAMPLE QUESTIONS FOR {difficulty.upper()} LEVEL:
{chr(10).join(f"- {ex}" for ex in difficulty_examples[difficulty])}

AVOID THESE COMMON ISSUES:
- Questions that are too vague or open-ended
- Questions that can be answered without reading the content
- Questions that test trivial details instead of key concepts
- Questions that are not directly related to the provided content
- Questions that assume knowledge not present in the content
- Leading questions that give away the answer

Remember: Questions should guide students to demonstrate their understanding of the core concepts presented in the content."""
    
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