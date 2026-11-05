import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, SessionLocal
from backend.app.models.user import User
from backend.app.models.chatbot import KnowledgeBaseItem, ChatSession, ChatMessage
from backend.app.schemas.chatbot import (
    ChatQueryRequest,
    ChatQueryResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
)
from backend.app.auth.dependencies import get_current_user, require_admin
from backend.app.auth.security import decode_access_token
from backend.app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/api/chatbot", tags=["NIEresolve Institutional AI Chatbot"])

@router.post("/query", response_model=ChatQueryResponse)
def query_chatbot(
    payload: ChatQueryRequest,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    HTTP endpoint for chatbot inference.
    Supports authenticated personalized live queries & anonymous institutional assistance.
    """
    current_user = None
    if token:
        token_data = decode_access_token(token)
        if token_data and "sub" in token_data:
            current_user = db.query(User).filter(User.id == int(token_data["sub"])).first()

    session_uuid = payload.session_uuid or f"session_{uuid.uuid4().hex[:12]}"

    # Fetch or create session
    chat_session = db.query(ChatSession).filter(ChatSession.session_uuid == session_uuid).first()
    if not chat_session:
        chat_session = ChatSession(
            session_uuid=session_uuid,
            user_id=current_user.id if current_user else None,
        )
        db.add(chat_session)
        db.flush()

    # Log user message
    db.add(ChatMessage(
        session_id=chat_session.id,
        sender="user",
        message=payload.query,
    ))

    # Process query
    result = ChatbotService.process_query(
        db=db,
        query=payload.query,
        current_user=current_user,
        session_uuid=session_uuid,
    )

    # Log bot reply
    db.add(ChatMessage(
        session_id=chat_session.id,
        sender="bot",
        message=result["response"],
        context_sources=", ".join(result["sources"]),
    ))

    db.commit()

    return ChatQueryResponse(
        session_uuid=session_uuid,
        response=result["response"],
        sources=result["sources"],
        is_live_data=result["is_live_data"],
        context_type=result.get("context_type"),
        created_at=datetime.utcnow(),
    )

@router.websocket("/ws")
async def websocket_chatbot(websocket: WebSocket):
    """
    Bidirectional WebSocket endpoint for real-time institutional grievance assistance.
    Receives JSON payload: {"query": "...", "token": "...", "session_uuid": "..."}
    """
    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            data = await websocket.receive_json()
            query_text = data.get("query", "").strip()
            token = data.get("token")
            session_uuid = data.get("session_uuid") or f"ws_{uuid.uuid4().hex[:12]}"

            if not query_text:
                continue

            current_user = None
            if token:
                token_data = decode_access_token(token)
                if token_data and "sub" in token_data:
                    current_user = db.query(User).filter(User.id == int(token_data["sub"])).first()

            result = ChatbotService.process_query(
                db=db,
                query=query_text,
                current_user=current_user,
                session_uuid=session_uuid,
            )

            await websocket.send_json({
                "session_uuid": session_uuid,
                "response": result["response"],
                "sources": result["sources"],
                "is_live_data": result["is_live_data"],
                "context_type": result.get("context_type"),
                "timestamp": datetime.utcnow().isoformat(),
            })
    except WebSocketDisconnect:
        pass
    finally:
        db.close()

@router.get("/knowledge-base", response_model=List[KnowledgeBaseResponse])
def get_knowledge_base(db: Session = Depends(get_db)):
    """Returns active institutional notices, policies, and FAQs."""
    return db.query(KnowledgeBaseItem).filter(KnowledgeBaseItem.is_active == True).all()

@router.post("/knowledge-base", response_model=KnowledgeBaseResponse)
def add_knowledge_item(
    payload: KnowledgeBaseCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin endpoint to publish or update institutional notices, FAQs, and policies."""
    item = KnowledgeBaseItem(
        category=payload.category,
        title=payload.title,
        content=payload.content,
        keywords=payload.keywords,
        source_reference=payload.source_reference,
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

