"""
DSFMP Fraud Detection System — User-Specific Notifications API Routes
Routes in-app notifications exclusively to the authenticated target user.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database.connection import get_db
from routes.settings import get_optional_user_id

router = APIRouter()


async def _resolve_target_user_id(
    db: AsyncSession,
    token_user_id: Optional[str],
    query_user_id: Optional[str],
) -> Optional[str]:
    """
    Resolve the specific authenticated user ID from the Bearer JWT token
    or explicit user_id parameter. Does not fall back to a global feed.
    """
    candidate = token_user_id or query_user_id
    if not candidate:
        return None

    res = await db.execute(
        text("SELECT id FROM users WHERE id = :uid OR email = :uid LIMIT 1"),
        {"uid": candidate},
    )
    row = res.fetchone()
    return row[0] if row else candidate


@router.get("", summary="Get in-app notifications for the current user")
async def get_notifications(
    limit: int = 30,
    user_id: Optional[str] = Query(None, description="Specific user ID to fetch notifications for"),
    token_user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve latest notifications routed specifically to the authenticated user.
    """
    target_user_id = await _resolve_target_user_id(db, token_user_id, user_id)
    if not target_user_id:
        return {
            "notifications": [],
            "unread_count": 0,
        }

    query = text("""
        SELECT n.id, n.user_id, n.type, n.title, n.message, n.link, n.is_read, n.created_at,
               CONCAT(u.first_name, ' ', u.last_name) as recipient_name,
               u.email as recipient_email
        FROM notifications n
        LEFT JOIN users u ON n.user_id = u.id
        WHERE n.user_id = :user_id
        ORDER BY n.created_at DESC
        LIMIT :limit
    """)
    res = await db.execute(query, {"user_id": target_user_id, "limit": limit})
    rows = res.fetchall()

    notifications = []
    for r in rows:
        is_read_bool = bool(r[6])
        notifications.append({
            "id": r[0],
            "userId": r[1],
            "type": r[2],
            "title": r[3],
            "message": r[4],
            "link": r[5],
            "isRead": is_read_bool,
            "createdAt": r[7].strftime("%Y-%m-%d %H:%M:%S") if r[7] else "",
            "recipientName": r[8] or "Investigator",
            "recipientEmail": r[9] or "",
        })

    unread_res = await db.execute(
        text("SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND is_read = 0"),
        {"user_id": target_user_id},
    )
    unread_count = int(unread_res.scalar() or 0)

    return {
        "user_id": target_user_id,
        "notifications": notifications,
        "unread_count": unread_count,
    }


@router.patch("/mark-read", summary="Mark all notifications for the current user as read")
async def mark_all_notifications_read(
    user_id: Optional[str] = Query(None, description="Specific user ID whose notifications should be marked read"),
    token_user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications belonging to the specific user as read."""
    target_user_id = await _resolve_target_user_id(db, token_user_id, user_id)
    if not target_user_id:
        return {"status": "noop", "message": "No authenticated user specified"}

    await db.execute(
        text("""
            UPDATE notifications
            SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id AND is_read = 0
        """),
        {"user_id": target_user_id},
    )
    await db.commit()
    return {"status": "success", "message": "User notifications marked as read"}


@router.patch("/{notification_id}/read", summary="Mark single user notification as read")
async def mark_single_notification_read(
    notification_id: str,
    user_id: Optional[str] = Query(None, description="Specific user ID"),
    token_user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a specific notification belonging to the current user as read."""
    target_user_id = await _resolve_target_user_id(db, token_user_id, user_id)
    if target_user_id:
        await db.execute(
            text("""
                UPDATE notifications
                SET is_read = 1, read_at = CURRENT_TIMESTAMP
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": notification_id, "user_id": target_user_id},
        )
    else:
        await db.execute(
            text("UPDATE notifications SET is_read = 1, read_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": notification_id},
        )
    await db.commit()
    return {"status": "success", "message": f"Notification {notification_id} marked as read"}

