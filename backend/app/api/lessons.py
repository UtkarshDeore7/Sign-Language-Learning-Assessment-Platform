from fastapi import APIRouter
from content.lesson_service import LessonService

router = APIRouter()
lesson_service = LessonService()

@router.get("/lessons")
def get_all_lessons():
    return lesson_service.get_all_lessons()

@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int):
    return lesson_service.get_lesson_by_id(lesson_id)