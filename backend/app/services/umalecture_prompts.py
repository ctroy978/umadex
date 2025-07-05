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
        image_descriptions: List[str]
    ) -> str:
        """Get prompt for generating content at a specific difficulty"""
        
        difficulty_guidelines = {
            "basic": "Use simple language, fundamental concepts, concrete examples",
            "intermediate": "Introduce more detail, connections between ideas, some technical terms",
            "advanced": "Include complex relationships, critical thinking, deeper analysis",
            "expert": "Explore nuanced perspectives, cutting-edge information, synthesis of ideas"
        }
        
        return f"""Create educational content for this topic at {difficulty} level:

TOPIC: {topic_title}
GRADE LEVEL: {grade_level}
DIFFICULTY: {difficulty} - {difficulty_guidelines[difficulty]}

AVAILABLE IMAGES:
{chr(10).join(image_descriptions) if image_descriptions else 'No images available'}

Requirements:
1. Base content ONLY on the topic title, learning objectives from the outline, and uploaded images
2. Do NOT incorporate subject area unless explicitly mentioned in the topic/outline
3. Write engaging, age-appropriate content that stays true to the outlined material
4. Include key concepts clearly explained as they appear in the outline
5. Reference images naturally where relevant
6. Build on previous difficulty levels
7. Aim for 200-400 words
8. Use formatting for clarity (paragraphs, lists if needed)

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