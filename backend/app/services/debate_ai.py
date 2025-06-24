import random
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.debate import AIPersonality, FallacyTemplate
from app.schemas.student_debate import PostScore, ChallengeResult
from app.utils.ai_helper import get_ai_response

logger = logging.getLogger(__name__)


class DebateAIService:
    def __init__(self):
        self._personalities_cache = {}
        self._fallacy_templates_cache = {}
    
    async def load_personalities(self, db: AsyncSession):
        """Load AI personalities from database."""
        if not self._personalities_cache:
            result = await db.execute(
                select(AIPersonality).where(AIPersonality.active == True)
            )
            personalities = result.scalars().all()
            self._personalities_cache = {p.name: p for p in personalities}
    
    async def load_fallacy_templates(self, db: AsyncSession):
        """Load fallacy templates from database."""
        if not self._fallacy_templates_cache:
            result = await db.execute(
                select(FallacyTemplate).where(FallacyTemplate.active == True)
            )
            templates = result.scalars().all()
            self._fallacy_templates_cache = {t.fallacy_type: t for t in templates}
    
    def _select_personality(self, difficulty: str):
        """Select a random AI personality appropriate for difficulty level."""
        if not self._personalities_cache:
            # Return a default personality if none are loaded
            return type('DefaultPersonality', (), {
                'name': 'Logical Debater',
                'display_name': 'Logical Debater',
                'prompt_template': 'You are a logical and analytical debater. Present clear, evidence-based arguments while maintaining respect for opposing viewpoints.',
                'difficulty_levels': ['beginner', 'intermediate', 'advanced']
            })()
        
        appropriate_personalities = [
            p for p in self._personalities_cache.values()
            if p.difficulty_levels and difficulty in p.difficulty_levels
        ]
        return random.choice(appropriate_personalities) if appropriate_personalities else list(self._personalities_cache.values())[0]
    
    def _select_fallacy(self, topic: str, difficulty: str):
        """Select an appropriate fallacy for the topic and difficulty."""
        if not self._fallacy_templates_cache:
            # Return a default fallacy if none are loaded
            return type('DefaultFallacy', (), {
                'fallacy_type': 'strawman',
                'display_name': 'Strawman Fallacy',
                'description': 'Misrepresenting someone\'s argument to make it easier to attack',
                'template': 'While my opponent seems to suggest [exaggerated version], the reality is...',
                'difficulty_levels': ['beginner', 'intermediate', 'advanced'],
                'topic_keywords': []
            })()
            
        # Filter by difficulty
        appropriate_fallacies = [
            f for f in self._fallacy_templates_cache.values()
            if f.difficulty_levels and difficulty in f.difficulty_levels
        ]
        
        # Try to find topic-relevant fallacies
        topic_words = topic.lower().split()
        topic_relevant = [
            f for f in appropriate_fallacies
            if f.topic_keywords and any(keyword in topic_words for keyword in f.topic_keywords)
        ]
        
        if topic_relevant:
            return random.choice(topic_relevant)
        elif appropriate_fallacies:
            return random.choice(appropriate_fallacies)
        else:
            return random.choice(list(self._fallacy_templates_cache.values()))
    
    async def generate_ai_response(
        self,
        student_post: str,
        debate_context: Dict,
        should_include_fallacy: bool = False
    ) -> Dict:
        """Generate AI debate response with optional fallacy."""
        logger.info(f"Starting AI response generation. Fallacy: {should_include_fallacy}")
        
        # Select personality
        personality = self._select_personality(debate_context['difficulty'])
        logger.info(f"Selected personality: {personality.name}")
        
        # Determine AI position (opposite of student)
        student_position = debate_context.get('position')
        if not student_position:
            logger.error(f"No student position provided in debate context")
            raise ValueError("Student position is required but not provided")
        
        ai_position = 'con' if student_position == 'pro' else 'pro'
        logger.info(f"Positions - Student: {student_position}, AI: {ai_position}")
        
        # Get the debate point for this round
        debate_point = debate_context.get('debate_point', '')
        statement_number = debate_context.get('statement_number', 2)
        
        if should_include_fallacy:
            fallacy = self._select_fallacy(debate_context['topic'], debate_context['difficulty'])
            
            prompt = f"""You are {personality.display_name} engaging in a structured debate about: {debate_context['topic']}

This round focuses on a SINGLE DEBATE POINT: {debate_point}

You are arguing the {ai_position.upper()} position.
The student just posted (Statement #{statement_number - 1}): {student_post}

Debate Context:
- This is statement #{statement_number} of 5 in Round {debate_context['round_number']}
- You must focus ONLY on the single debate point for this round
- Difficulty level: {debate_context['difficulty']}
- Grade level: {debate_context['grade_level']}

{personality.prompt_template}

IMPORTANT: Include a {fallacy.display_name} fallacy in your response.
The fallacy is: {fallacy.description}
Use this template as inspiration: {fallacy.template}

The fallacy should be:
- Detectable but not obvious
- Believable within the argument flow
- Naturally integrated into your argument

Generate a {ai_position.upper()} response that:
1. Directly counters the student's argument about the single debate point
2. Introduces new evidence or perspectives ONLY related to this point
3. Contains the specified fallacy
4. Stays within 100-150 words (this is statement {statement_number} of 5)
5. Remains appropriate for {debate_context['grade_level']} students
6. Does NOT introduce new debate points or change the topic

Previous statements in this round:
{self._summarize_round_posts(debate_context.get('previous_posts', []), debate_context['round_number'])}"""
            
            logger.info(f"Calling get_ai_response with prompt length: {len(prompt)}")
            response = await get_ai_response(prompt, max_tokens=400)
            logger.info(f"Received AI response: {len(response)} chars")
            
            return {
                'content': response,
                'word_count': len(response.split()),
                'personality': personality.name,
                'is_fallacy': True,
                'fallacy_type': fallacy.fallacy_type
            }
        
        else:
            prompt = f"""You are {personality.display_name} engaging in a structured debate about: {debate_context['topic']}

This round focuses on a SINGLE DEBATE POINT: {debate_point}

You are arguing the {ai_position.upper()} position.
The student just posted (Statement #{statement_number - 1}): {student_post}

Debate Context:
- This is statement #{statement_number} of 5 in Round {debate_context['round_number']}
- You must focus ONLY on the single debate point for this round
- Difficulty level: {debate_context['difficulty']}
- Grade level: {debate_context['grade_level']}

{personality.prompt_template}

Generate a {ai_position.upper()} response that:
1. Directly counters the student's argument about the single debate point
2. Introduces new evidence or perspectives ONLY related to this point
3. Stays within 100-150 words (this is statement {statement_number} of 5)
4. Remains appropriate for {debate_context['grade_level']} students
5. Uses strong, valid arguments without logical fallacies
6. Does NOT introduce new debate points or change the topic

Previous statements in this round:
{self._summarize_round_posts(debate_context.get('previous_posts', []), debate_context['round_number'])}"""
            
            logger.info(f"Calling get_ai_response with prompt length: {len(prompt)}")
            response = await get_ai_response(prompt, max_tokens=400)
            logger.info(f"Received AI response: {len(response)} chars")
            
            return {
                'content': response,
                'word_count': len(response.split()),
                'personality': personality.name,
                'is_fallacy': False,
                'fallacy_type': None
            }
    
    def _summarize_previous_posts(self, posts: List) -> str:
        """Summarize previous AI arguments to avoid repetition."""
        ai_posts = [p for p in posts if p.post_type == 'ai']
        if not ai_posts:
            return "None"
        
        summaries = []
        for post in ai_posts[-3:]:  # Last 3 AI posts
            # Extract first sentence or key point
            first_sentence = post.content.split('.')[0] + '.'
            summaries.append(f"- Round {post.round_number}: {first_sentence}")
        
        return '\n'.join(summaries)
    
    def _summarize_round_posts(self, posts: List, current_round: int) -> str:
        """Summarize posts from the current round only."""
        round_posts = [p for p in posts if p.debate_number == current_round]
        if not round_posts:
            return "This is the first statement"
        
        summaries = []
        for post in round_posts:
            # Show who said what in sequence
            speaker = "Student" if post.post_type == 'student' else "AI"
            first_point = post.content.split('.')[0]
            summaries.append(f"- Statement {post.statement_number} ({speaker}): {first_point}")
        
        return '\n'.join(summaries)
    
    async def evaluate_student_post(
        self,
        post_content: str,
        round_number: int,
        topic: str,
        difficulty: str,
        grade_level: str,
        student_position: str
    ) -> PostScore:
        """Evaluate student post using rubric."""
        
        prompt = f"""Evaluate this student debate post on a 1-5 scale for each category:

Student Post: {post_content}
Debate Topic: {topic}
Student Position: {student_position.upper()}
Round: {round_number}
Grade Level: {grade_level}
Difficulty: {difficulty}

Scoring Criteria:
- Clarity (1-5): Clear, organized argument structure. Well-defined thesis and supporting points.
- Evidence (1-5): Relevant facts, examples, or reasoning. Quality and relevance of support.
- Logic (1-5): Sound reasoning, avoids contradictions. Arguments follow logically.
- Persuasiveness (1-5): Compelling use of ethos/pathos/logos. Engaging and convincing.
- Rebuttal (1-5): Addresses opponent's previous points. Shows understanding and counters effectively.

Provide your evaluation in this exact format:
CLARITY: [score]
EVIDENCE: [score]
LOGIC: [score]
PERSUASIVENESS: [score]
REBUTTAL: [score]
FEEDBACK: [2-3 sentences focusing on strengths and one area for improvement. Be encouraging and educational.]"""
        
        response = await get_ai_response(prompt, max_tokens=300)
        
        # Parse response
        scores = self._parse_evaluation_response(response)
        
        # Calculate percentages with lenient baseline
        # New formula: 70 baseline + (score/25 * 30)
        # This gives 70% for minimal effort, up to 100% for perfect scores
        numeric_scores = {k: v for k, v in scores.items() if k != 'feedback'}
        total_score = sum(numeric_scores.values())
        
        # Lenient grading: 70% baseline + up to 30% based on performance
        baseline = 70  # Can be made configurable per assignment
        score_ratio = total_score / 25.0
        remaining_points = 100 - baseline
        base_percentage = Decimal(str(baseline + (score_ratio * remaining_points)))
        
        return PostScore(
            clarity=Decimal(str(scores['clarity'])),
            evidence=Decimal(str(scores['evidence'])),
            logic=Decimal(str(scores['logic'])),
            persuasiveness=Decimal(str(scores['persuasiveness'])),
            rebuttal=Decimal(str(scores['rebuttal'])),
            base_percentage=base_percentage,
            bonus_points=Decimal('0'),
            final_percentage=base_percentage,
            feedback=scores['feedback']
        )
    
    def _parse_evaluation_response(self, response: str) -> Dict:
        """Parse the AI evaluation response."""
        lines = response.strip().split('\n')
        scores = {}
        
        for line in lines:
            if line.startswith('CLARITY:'):
                scores['clarity'] = int(line.split(':')[1].strip())
            elif line.startswith('EVIDENCE:'):
                scores['evidence'] = int(line.split(':')[1].strip())
            elif line.startswith('LOGIC:'):
                scores['logic'] = int(line.split(':')[1].strip())
            elif line.startswith('PERSUASIVENESS:'):
                scores['persuasiveness'] = int(line.split(':')[1].strip())
            elif line.startswith('REBUTTAL:'):
                scores['rebuttal'] = int(line.split(':')[1].strip())
            elif line.startswith('FEEDBACK:'):
                scores['feedback'] = ':'.join(line.split(':')[1:]).strip()
        
        # Ensure all scores are present and valid
        for category in ['clarity', 'evidence', 'logic', 'persuasiveness', 'rebuttal']:
            if category not in scores:
                scores[category] = 3  # Default middle score
            else:
                scores[category] = max(1, min(5, scores[category]))  # Clamp to 1-5
        
        if 'feedback' not in scores:
            scores['feedback'] = "Good effort! Keep working on developing your arguments."
        
        return scores
    
    async def evaluate_challenge(
        self,
        ai_post,
        challenge_type: str,
        challenge_value: str,
        explanation: Optional[str]
    ) -> ChallengeResult:
        """Evaluate if student correctly identified fallacy or appeal."""
        
        if challenge_type == 'fallacy':
            if ai_post.is_fallacy and ai_post.fallacy_type == challenge_value:
                # Correct identification
                if explanation and len(explanation) > 20:
                    # Good explanation
                    prompt = f"""The student correctly identified a {challenge_value} fallacy in this AI post:
                    
AI Post: {ai_post.content}
Student's Explanation: {explanation}

Is this a good explanation of why it's a {challenge_value} fallacy? Answer YES or NO and provide brief feedback."""
                    
                    eval_response = await get_ai_response(prompt, max_tokens=100)
                    
                    if 'YES' in eval_response.upper():
                        return ChallengeResult(
                            is_correct=True,
                            points_awarded=Decimal('5.0'),
                            ai_feedback="Excellent! You correctly identified the fallacy and explained it well."
                        )
                    else:
                        return ChallengeResult(
                            is_correct=True,
                            points_awarded=Decimal('3.0'),
                            ai_feedback="Correct identification! Your explanation could be clearer. " + eval_response.split('\n')[0]
                        )
                else:
                    return ChallengeResult(
                        is_correct=True,
                        points_awarded=Decimal('3.0'),
                        ai_feedback="Correct identification! Next time, provide a more detailed explanation."
                    )
            
            elif not ai_post.is_fallacy:
                return ChallengeResult(
                    is_correct=False,
                    points_awarded=Decimal('-1.0'),
                    ai_feedback="This was a valid argument, not a fallacy. Be more careful in your analysis."
                )
            
            else:
                correct_fallacy = self._fallacy_templates_cache.get(ai_post.fallacy_type)
                return ChallengeResult(
                    is_correct=False,
                    points_awarded=Decimal('-1.0'),
                    ai_feedback=f"This was actually a {correct_fallacy.display_name if correct_fallacy else ai_post.fallacy_type}, not {challenge_value}."
                )
        
        elif challenge_type == 'appeal':
            # Evaluate appeal recognition
            prompt = f"""Analyze if this AI debate post contains an appeal to {challenge_value}:

AI Post: {ai_post.content}
Student's Explanation: {explanation if explanation else 'No explanation provided'}

Does this post contain a clear appeal to {challenge_value}? Answer YES or NO with brief reasoning."""
            
            eval_response = await get_ai_response(prompt, max_tokens=150)
            
            if 'YES' in eval_response.upper()[:10]:
                return ChallengeResult(
                    is_correct=True,
                    points_awarded=Decimal('3.0'),
                    ai_feedback=f"Good recognition of the appeal to {challenge_value}! " + eval_response.split('\n')[0]
                )
            else:
                return ChallengeResult(
                    is_correct=False,
                    points_awarded=Decimal('-1.0'),
                    ai_feedback=f"This doesn't appear to be an appeal to {challenge_value}. " + eval_response.split('\n')[0]
                )
        
        return ChallengeResult(
            is_correct=False,
            points_awarded=Decimal('0'),
            ai_feedback="Invalid challenge type."
        )