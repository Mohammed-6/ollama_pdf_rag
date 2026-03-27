"""RAG query endpoints."""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
import uuid

from ..dependencies import get_db, get_rag_service
from ..models import QueryRequest, QueryResponse, SourceInfo
from ..services.rag_service import RAGService

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_pdfs(
    file: Optional[UploadFile] = File(None),
    share_name: str = Form(""),
    question: str = Form(""),
    model: str = Form("llama3.2:latest"),
    session_id: str = Form(""),
    pdf_ids: Optional[List[str]] = Form(None),
    db: Session = Depends(get_db),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Query across PDFs with source attribution."""
    # Your RAG/LLM logic here
    # answer = f"Processed question: '{question}'"  # Replace with real LLM
    # sources = [{"pdf_id": pid, "score": 0.95} for pid in (pdf_ids or [])]
    # metadata = {
    #     "model": model,
    #     "share_name": share_name,
    #     "file": file.filename if file else None
    # }
    
    # return QueryResponse(
    #     answer=answer,
    #     sources=sources,
    #     metadata=metadata,
    #     session_id=session_id or "default",
    #     message_id=123
    # )
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"📥 Received query request: question='{question[:50]}...', model={model}")

    # Generate session ID if not provided
    session_id = session_id or str(uuid.uuid4())
    logger.info(f"🔑 Session ID: {session_id}")

    # Save user message
    rag_service.save_message(
        session_id=session_id,
        role="user",
        content=question,
        sources=None,
        db=db
    )
    logger.info("💾 User message saved")

    # Query RAG
    logger.info("🚀 Starting RAG query...")
    try:
        answer, sources, reasoning_steps = rag_service.query_multi_pdf(
            question=question,
            model=model,
            pdf_ids=pdf_ids,
            file=file,
            share_name=share_name,
            db=db
        )
        logger.info(f"✅ RAG query complete: answer_length={len(answer)}, sources_count={len(sources)}, reasoning_steps={len(reasoning_steps)}")
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() and "404" in error_msg:
            logger.error(f"❌ Model not found: {model}")
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model}' not found. Please select a different model from the dropdown or install it with: ollama pull {model}"
            )
        logger.error(f"❌ Query failed: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Query failed: {error_msg}")

    # Save assistant message
    message = rag_service.save_message(
        session_id=session_id,
        role="assistant",
        content=answer,
        sources=sources,
        db=db
    )
    logger.info(f"💾 Assistant message saved with ID: {message.message_id}")

    response = QueryResponse(
        answer=answer,
        sources=[SourceInfo(**s) for s in sources],
        metadata={
            "model_used": model,
            "chunks_retrieved": len(sources),
            "pdfs_queried": len(set(s["pdf_id"] for s in sources)),
            "reasoning_steps": reasoning_steps
        },
        session_id=session_id,
        message_id=message.message_id
    )

    logger.info(f"📤 Returning response: answer_length={len(response.answer)}, sources={len(response.sources)}")
    logger.info(f"📊 First 200 chars of answer: {response.answer[:200]}")

    return response


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Get chat history for a session."""
    messages = rag_service.get_session_messages(session_id, db)
    return [
        {
            "message_id": msg.message_id,
            "role": msg.role,
            "content": msg.content,
            "sources": msg.sources,
            "timestamp": msg.timestamp
        }
        for msg in messages
    ]
