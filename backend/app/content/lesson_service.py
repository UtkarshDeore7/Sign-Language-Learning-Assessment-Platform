from datetime import datetime

LESSONS = [
    {
        "id": 1,
        "sign": "A",
        "description": "Closed fist with thumb resting on the side.",
        "meaning": "Letter A in American Sign Language",
        "image": "assets/asl/A.jpg",
        "difficulty": "Beginner"
    },
    {
        "id": 2,
        "sign": "B",
        "description": "Four fingers held straight up, thumb tucked in.",
        "meaning": "Letter B in American Sign Language",
        "image": "assets/asl/B.jpg",
        "difficulty": "Beginner"
    },
    {
        "id": 3,
        "sign": "C",
        "description": "Hand curved into a C shape.",
        "meaning": "Letter C in American Sign Language",
        "image": "assets/asl/C.jpg",
        "difficulty": "Beginner"
    },
    {
        "id": 4,
        "sign": "D",
        "description": "Index finger pointing up, other fingers and thumb form a circle.",
        "meaning": "Letter D in American Sign Language",
        "image": "assets/asl/D.jpg",
        "difficulty": "Beginner"
    },
    {
        "id": 5,
        "sign": "E",
        "description": "Fingers bent down, thumb tucked under fingers.",
        "meaning": "Letter E in American Sign Language",
        "image": "assets/asl/E.jpg",
        "difficulty": "Beginner"
    }
]

class LessonService:
    def get_all_lessons(self):
        return {
            "success": True,
            "message": "Lessons fetched successfully.",
            "data": [{"id": l["id"], "sign": l["sign"]} for l in LESSONS],
            "timestamp": datetime.now().isoformat()
        }

    def get_lesson_by_id(self, lesson_id: int):
        lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
        if not lesson:
            return {
                "success": False,
                "message": f"Lesson {lesson_id} not found.",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }
        return {
            "success": True,
            "message": "Lesson fetched successfully.",
            "data": lesson,
            "timestamp": datetime.now().isoformat()
        }