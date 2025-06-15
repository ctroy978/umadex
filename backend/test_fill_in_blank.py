#!/usr/bin/env python3
"""
Test script for Fill-in-the-Blank vocabulary assignment
Tests the complete workflow from sentence generation to student completion
"""
import asyncio
import json
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import AsyncSessionLocal
from app.models.vocabulary import VocabularyList, VocabularyWord, VocabularyStatus
from app.models.vocabulary_practice import VocabularyPracticeProgress
from app.models.classroom import ClassroomAssignment, Classroom
from app.models.user import User, UserRole
from app.services.vocabulary_fill_in_blank_generator import VocabularyFillInBlankGenerator
from app.services.vocabulary_practice import VocabularyPracticeService


async def create_test_data():
    """Create test vocabulary list and user for testing"""
    async with AsyncSessionLocal() as db:
        # Check if test users already exist
        teacher_result = await db.execute(
            select(User).where(User.email == "test_teacher@example.com")
        )
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher:
            # Create a test teacher user
            teacher = User(
                id=uuid4(),
                email="test_teacher@example.com",
                first_name="Test",
                last_name="Teacher",
                username="test_teacher",
                role=UserRole.TEACHER
            )
            db.add(teacher)
        
        # Check if test student already exists
        student_result = await db.execute(
            select(User).where(User.email == "test_student@example.com")
        )
        student = student_result.scalar_one_or_none()
        
        if not student:
            # Create a test student user
            student = User(
                id=uuid4(),
                email="test_student@example.com",
                first_name="Test",
                last_name="Student",
                username="test_student",
                role=UserRole.STUDENT
            )
            db.add(student)
        
        # Check if test vocabulary list already exists
        vocab_list_result = await db.execute(
            select(VocabularyList).where(VocabularyList.title == "Test Vocabulary List")
        )
        vocab_list = vocab_list_result.scalar_one_or_none()
        
        if not vocab_list:
            # Create a test vocabulary list
            vocab_list = VocabularyList(
                id=uuid4(),
                teacher_id=teacher.id,
                title="Test Vocabulary List",
                context_description="A test list for fill-in-the-blank testing",
                grade_level="5th Grade",
                subject_area="Science",
                status=VocabularyStatus.PUBLISHED
            )
            db.add(vocab_list)
        
        # Check if words already exist for this list
        existing_words_result = await db.execute(
            select(VocabularyWord).where(VocabularyWord.list_id == vocab_list.id)
        )
        existing_words = existing_words_result.scalars().all()
        
        if not existing_words:
            # Create test vocabulary words
            test_words = [
                {"word": "photosynthesis", "definition": "The process by which plants make food using sunlight"},
                {"word": "ecosystem", "definition": "A community of living and non-living things that interact"},
                {"word": "habitat", "definition": "The natural home of an animal or plant"},
                {"word": "predator", "definition": "An animal that hunts and eats other animals"},
                {"word": "herbivore", "definition": "An animal that eats only plants"}
            ]
            
            for i, word_data in enumerate(test_words):
                word = VocabularyWord(
                    id=uuid4(),
                    list_id=vocab_list.id,
                    word=word_data["word"],
                    ai_definition=word_data["definition"],
                    position=i + 1
                )
                db.add(word)
        
        # Check if classroom already exists
        classroom_result = await db.execute(
            select(Classroom).where(Classroom.class_code == "TEST123")
        )
        classroom = classroom_result.scalar_one_or_none()
        
        if not classroom:
            # Create a test classroom
            classroom = Classroom(
                id=uuid4(),
                name="Test Classroom",
                teacher_id=teacher.id,
                class_code="TEST123"
            )
            db.add(classroom)
        
        # Check if classroom assignment already exists
        assignment_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom.id,
                    ClassroomAssignment.vocabulary_list_id == vocab_list.id
                )
            )
        )
        classroom_assignment = assignment_result.scalar_one_or_none()
        
        if not classroom_assignment:
            # Create a test classroom assignment  
            classroom_assignment = ClassroomAssignment(
                classroom_id=classroom.id,
                vocabulary_list_id=vocab_list.id,
                assignment_type="vocabulary"
            )
            db.add(classroom_assignment)
        
        await db.commit()
        
        return {
            'teacher_id': teacher.id,
            'student_id': student.id,
            'vocab_list_id': vocab_list.id,
            'classroom_assignment_id': classroom_assignment.id
        }


async def test_sentence_generation(vocab_list_id):
    """Test fill-in-the-blank sentence generation"""
    print("🔄 Testing sentence generation...")
    
    async with AsyncSessionLocal() as db:
        generator = VocabularyFillInBlankGenerator(db)
        
        try:
            sentences = await generator.generate_fill_in_blank_sentences(vocab_list_id)
            print(f"✅ Generated {len(sentences)} sentences")
            
            for sentence in sentences[:3]:  # Show first 3 sentences
                print(f"   - {sentence['sentence_with_blank']} (Answer: {sentence['correct_answer']})")
            
            return True
        except Exception as e:
            print(f"❌ Sentence generation failed: {e}")
            return False


async def test_practice_service(student_id, vocab_list_id, classroom_assignment_id):
    """Test the practice service workflow"""
    print("🔄 Testing practice service workflow...")
    
    async with AsyncSessionLocal() as db:
        practice_service = VocabularyPracticeService(db)
        
        try:
            # Test starting fill-in-blank assignment
            session_data = await practice_service.start_fill_in_blank(
                student_id=student_id,
                vocabulary_list_id=vocab_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
            
            print("✅ Successfully started fill-in-blank assignment")
            print(f"   - Total sentences: {session_data['total_sentences']}")
            print(f"   - Current sentence: {session_data['sentence']['sentence_with_blank']}")
            print(f"   - Vocabulary words: {len(session_data['sentence']['vocabulary_words'])}")
            
            attempt_id = session_data['fill_in_blank_attempt_id']
            sentence_id = session_data['sentence']['id']
            correct_answer = None
            
            # Find the correct answer from vocabulary words
            sentence_text = session_data['sentence']['sentence_with_blank']
            for word in session_data['sentence']['vocabulary_words']:
                # Test if this word fits the sentence context
                if len(word) > 3:  # Simple heuristic for testing
                    correct_answer = word
                    break
            
            if not correct_answer:
                correct_answer = session_data['sentence']['vocabulary_words'][0]
            
            print(f"   - Testing with answer: {correct_answer}")
            
            # Test submitting an answer
            result = await practice_service.submit_fill_in_blank_answer(
                fill_in_blank_attempt_id=attempt_id,
                sentence_id=sentence_id,
                student_answer=correct_answer,
                time_spent_seconds=30
            )
            
            print(f"✅ Successfully submitted answer")
            print(f"   - Answer was: {'correct' if result['is_correct'] else 'incorrect'}")
            print(f"   - Progress: {result['progress_percentage']:.1f}%")
            
            return True
            
        except Exception as e:
            print(f"❌ Practice service test failed: {e}")
            import traceback
            print(traceback.format_exc())
            return False


async def test_practice_status(student_id, vocab_list_id, classroom_assignment_id):
    """Test getting practice status including fill-in-blank"""
    print("🔄 Testing practice status...")
    
    async with AsyncSessionLocal() as db:
        practice_service = VocabularyPracticeService(db)
        
        try:
            status = await practice_service.get_practice_status(
                student_id=student_id,
                vocabulary_list_id=vocab_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
            
            print("✅ Successfully retrieved practice status")
            print(f"   - Available assignments: {len(status['assignments'])}")
            
            # Find fill-in-blank assignment
            fill_in_blank = None
            for assignment in status['assignments']:
                if assignment['type'] == 'fill_in_blank':
                    fill_in_blank = assignment
                    break
            
            if fill_in_blank:
                print(f"✅ Fill-in-blank assignment found:")
                print(f"   - Display name: {fill_in_blank['display_name']}")
                print(f"   - Status: {fill_in_blank['status']}")
                print(f"   - Available: {fill_in_blank['available']}")
                print(f"   - Can start: {fill_in_blank['can_start']}")
            else:
                print("❌ Fill-in-blank assignment not found in status")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Practice status test failed: {e}")
            return False


async def main():
    """Run all tests"""
    print("🚀 Starting Fill-in-the-Blank Tests\n")
    
    try:
        # Create test data
        print("📝 Creating test data...")
        test_data = await create_test_data()
        print("✅ Test data created\n")
        
        # Test sentence generation
        success1 = await test_sentence_generation(test_data['vocab_list_id'])
        print()
        
        # Test practice status
        success2 = await test_practice_status(
            test_data['student_id'],
            test_data['vocab_list_id'],
            test_data['classroom_assignment_id']
        )
        print()
        
        # Test practice service workflow
        success3 = await test_practice_service(
            test_data['student_id'],
            test_data['vocab_list_id'],
            test_data['classroom_assignment_id']
        )
        print()
        
        # Summary
        if all([success1, success2, success3]):
            print("🎉 All tests passed! Fill-in-the-blank is working correctly.")
        else:
            print("⚠️  Some tests failed. Please check the output above.")
        
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())