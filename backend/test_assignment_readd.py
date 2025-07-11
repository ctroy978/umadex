#!/usr/bin/env python3
"""Test script to verify that removed assignments can be re-added to a classroom"""

import asyncio
import sys
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.models.classroom import Classroom, ClassroomAssignment
from app.models.user import User
from app.models.reading import ReadingAssignment
from app.models.vocabulary import VocabularyList
from datetime import datetime

async def test_readd_assignment():
    async with async_session_maker() as db:
        # Find the teacher
        teacher_result = await db.execute(
            select(User).where(User.username == "tcooper-csd8info")
        )
        teacher = teacher_result.scalar_one_or_none()
        if not teacher:
            print("❌ Teacher 'tcooper-csd8info' not found")
            return
        print(f"✅ Found teacher: {teacher.username} (ID: {teacher.id})")
        
        # Find the classroom
        classroom_result = await db.execute(
            select(Classroom).where(
                and_(
                    Classroom.name == "Eng p1",
                    Classroom.teacher_id == teacher.id,
                    Classroom.deleted_at.is_(None)
                )
            )
        )
        classroom = classroom_result.scalar_one_or_none()
        if not classroom:
            print("❌ Classroom 'Eng p1' not found")
            return
        print(f"✅ Found classroom: {classroom.name} (ID: {classroom.id})")
        
        # Find the assignments
        # 1. Alice ch1 (reading assignment)
        alice_result = await db.execute(
            select(ReadingAssignment).where(
                and_(
                    ReadingAssignment.assignment_title == "Alice ch1",
                    ReadingAssignment.teacher_id == teacher.id,
                    ReadingAssignment.deleted_at.is_(None)
                )
            )
        )
        alice_assignment = alice_result.scalar_one_or_none()
        if alice_assignment:
            print(f"✅ Found reading assignment: {alice_assignment.assignment_title} (ID: {alice_assignment.id})")
        else:
            print("❌ Reading assignment 'Alice ch1' not found")
        
        # 2. Bitcoin debate (could be vocabulary or reading)
        bitcoin_vocab_result = await db.execute(
            select(VocabularyList).where(
                and_(
                    VocabularyList.title.ilike("%Bitcoin%world reserve currency%"),
                    VocabularyList.teacher_id == teacher.id,
                    VocabularyList.deleted_at.is_(None)
                )
            )
        )
        bitcoin_vocab = bitcoin_vocab_result.scalar_one_or_none()
        
        bitcoin_reading_result = await db.execute(
            select(ReadingAssignment).where(
                and_(
                    ReadingAssignment.assignment_title.ilike("%Bitcoin%world reserve currency%"),
                    ReadingAssignment.teacher_id == teacher.id,
                    ReadingAssignment.deleted_at.is_(None)
                )
            )
        )
        bitcoin_reading = bitcoin_reading_result.scalar_one_or_none()
        
        if bitcoin_vocab:
            print(f"✅ Found vocabulary assignment: {bitcoin_vocab.title} (ID: {bitcoin_vocab.id})")
        elif bitcoin_reading:
            print(f"✅ Found reading assignment: {bitcoin_reading.assignment_title} (ID: {bitcoin_reading.id})")
        else:
            print("❌ Bitcoin assignment not found")
        
        # Check current assignment status
        print("\n📋 Checking current assignment status in classroom...")
        
        # Check Alice assignment
        if alice_assignment:
            alice_classroom_result = await db.execute(
                select(ClassroomAssignment).where(
                    and_(
                        ClassroomAssignment.classroom_id == classroom.id,
                        ClassroomAssignment.assignment_id == alice_assignment.id
                    )
                )
            )
            alice_classroom_assignments = alice_classroom_result.scalars().all()
            
            print(f"\nAlice ch1 classroom assignments:")
            for ca in alice_classroom_assignments:
                status = "ACTIVE" if ca.removed_from_classroom_at is None else f"REMOVED at {ca.removed_from_classroom_at}"
                print(f"  - ID: {ca.id}, Status: {status}")
        
        # Check Bitcoin assignment
        if bitcoin_vocab:
            bitcoin_classroom_result = await db.execute(
                select(ClassroomAssignment).where(
                    and_(
                        ClassroomAssignment.classroom_id == classroom.id,
                        ClassroomAssignment.vocabulary_list_id == bitcoin_vocab.id
                    )
                )
            )
            bitcoin_classroom_assignments = bitcoin_classroom_result.scalars().all()
            
            print(f"\nBitcoin vocabulary classroom assignments:")
            for ca in bitcoin_classroom_assignments:
                status = "ACTIVE" if ca.removed_from_classroom_at is None else f"REMOVED at {ca.removed_from_classroom_at}"
                print(f"  - ID: {ca.id}, Status: {status}")
        elif bitcoin_reading:
            bitcoin_classroom_result = await db.execute(
                select(ClassroomAssignment).where(
                    and_(
                        ClassroomAssignment.classroom_id == classroom.id,
                        ClassroomAssignment.assignment_id == bitcoin_reading.id
                    )
                )
            )
            bitcoin_classroom_assignments = bitcoin_classroom_result.scalars().all()
            
            print(f"\nBitcoin reading classroom assignments:")
            for ca in bitcoin_classroom_assignments:
                status = "ACTIVE" if ca.removed_from_classroom_at is None else f"REMOVED at {ca.removed_from_classroom_at}"
                print(f"  - ID: {ca.id}, Status: {status}")

if __name__ == "__main__":
    asyncio.run(test_readd_assignment())