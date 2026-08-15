"""
Notifications API
=================
GET  /api/notifications/{student_id}           — all notifications
GET  /api/notifications/{student_id}/unread    — unread only + count
PUT  /api/notifications/{student_id}/{id}/read — mark one read
PUT  /api/notifications/{student_id}/read-all  — mark all read
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.notification_service import NotificationService

router  = APIRouter()
notif_svc = NotificationService()


@router.get("/notifications/{student_id}")
def get_notifications(student_id: str, db: Session = Depends(get_db)):
    return notif_svc.get_notifications(db, student_id)


@router.get("/notifications/{student_id}/unread")
def get_unread(student_id: str, db: Session = Depends(get_db)):
    return notif_svc.get_notifications(db, student_id, unread_only=True)


@router.put("/notifications/{student_id}/{notification_id}/read")
def mark_read(student_id: str, notification_id: int, db: Session = Depends(get_db)):
    return notif_svc.mark_read(db, student_id, notification_id)


@router.put("/notifications/{student_id}/read-all")
def mark_all_read(student_id: str, db: Session = Depends(get_db)):
    return notif_svc.mark_all_read(db, student_id)