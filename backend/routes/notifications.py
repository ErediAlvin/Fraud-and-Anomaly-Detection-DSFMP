"""
DSFMP Fraud Detection System — Notifications API Routes
Provides endpoints to fetch and manage user and system notifications.
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from middleware.dependencies import get_current_user

router = APIRouter()


@router.get("", summary="Get recent in-app notifications")
async def get_notifications(
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve latest notifications across the system.
    Orders chronologically descending so new assignments appear immediately.
    """
    query = text("""
        SELECT n.id, n.user_id, n.type, n.title, n.message, n.link, n.is_read, n.created_at,
               CONCAT(u.first_name, ' ', u.last_name) as recipient_name,
               u.email as recipient_email
        FROM notifications n
        LEFT JOIN users u ON n.user_id = u.id
        ORDER BY n.created_at DESC
        LIMIT :limit
    """)
    res = await db.execute(query, {"limit": limit})
    rows = res.fetchall()

    notifications = []
    unread_count = 0
    for r in rows:
        is_read_bool = bool(r[6])
        if not is_read_bool:
            unread_count += 1
        notifications.append({
            "id": r[0],
            "userId": r[1],
            "type": r[2],
            "title": r[3],
            "message": r[4],
            "link": r[5],
            "isRead": is_read_bool,
            "createdAt": r[7].strftime("%Y-%m-%d %H:%M:%S") if r[7] else "",
            "recipientName": r[8] or "System User",
            "recipientEmail": r[9] or "",
        })

    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }


@router.patch("/mark-read", summary="Mark all notifications as read")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read."""
    await db.execute(
        text("UPDATE notifications SET is_read = 1, read_at = CURRENT_TIMESTAMP WHERE is_read = 0")
    )
    await db.commit()
    return {"status": "success", "message": "All notifications marked as read"}


@router.patch("/{notification_id}/read", summary="Mark single notification as read")
async def mark_single_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a specific notification as read."""
    await db.execute(
        text("UPDATE notifications SET is_read = 1, read_at = CURRENT_TIMESTAMP WHERE id = :id"),
        {"id": notification_id},
    )
    await db.commit()
    return {"status": "success", "message": f"Notification {notification_id} marked as read"}

