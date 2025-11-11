"""
HTTP route handlers for the AI Blog Generator application.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models.blog_model import Blog
from ..services.ai_service import AIService
from ..utils import (
    ParsedTitles,
    chunk_text,
    download_filename,
    parse_titles,
    summarize,
)


router = APIRouter(tags=["Blogs"])
templates = Jinja2Templates(directory="app/templates")

TONES = ["Neutral", "Formal", "Conversational", "Technical"]


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the landing page where users provide titles."""

    recent_blogs = await _fetch_recent_blogs(request, limit=3)
    context = {
        "request": request,
        "tones": TONES,
        "recent_blogs": recent_blogs,
        "warnings": [],
        "message": None,
    }
    return templates.TemplateResponse("index.html", context)


@router.post("/generate", response_class=HTMLResponse)
async def generate_blogs(
    request: Request,
    titles: str = Form(...),
    tone: Optional[str] = Form(default="Neutral"),
) -> HTMLResponse:
    """
    Generate blogs for the submitted titles and persist them to the database.
    """

    parsed: ParsedTitles = parse_titles(titles)

    if not parsed.titles:
        recent_blogs = await _fetch_recent_blogs(request, limit=3)
        context = {
            "request": request,
            "tones": TONES,
            "recent_blogs": recent_blogs,
            "warnings": parsed.warnings or ["Provide at least one title to generate."],
            "message": None,
        }
        return templates.TemplateResponse("index.html", context, status_code=status.HTTP_400_BAD_REQUEST)

    async_session: async_sessionmaker[AsyncSession] = request.app.state.async_session
    ai_service: Optional[AIService] = getattr(request.app.state, "ai_service", None)
    ai_error: Optional[str] = getattr(request.app.state, "ai_error", None)

    if not ai_service:
        recent_blogs = await _fetch_recent_blogs(request, limit=3)
        context = {
            "request": request,
            "tones": TONES,
            "recent_blogs": recent_blogs,
            "warnings": parsed.warnings + [ai_error or "OpenAI API is not configured."],
            "message": None,
        }
        return templates.TemplateResponse("index.html", context, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    async with async_session() as session:
        for title in parsed.titles:
            try:
                response = await ai_service.generate_blog(title, tone if tone != "Neutral" else None)
            except Exception as exc:  # noqa: BLE001
                recent_blogs = await _fetch_recent_blogs(request, limit=3)
                context = {
                    "request": request,
                    "tones": TONES,
                    "recent_blogs": recent_blogs,
                    "warnings": parsed.warnings + [f"Failed to generate '{title}': {exc}"],
                    "message": None,
                }
                return templates.TemplateResponse("index.html", context, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            blog = Blog(title=title, content=response.content, tone=tone if tone else None)
            session.add(blog)
        await session.commit()

    redirect_url = request.url_for("list_blogs")
    message = f"Generated {len(parsed.titles)} blog(s) successfully."
    response = RedirectResponse(url=f"{redirect_url}?message={message}", status_code=status.HTTP_303_SEE_OTHER)
    return response


@router.get("/blogs", response_class=HTMLResponse)
async def list_blogs(
    request: Request,
    message: Optional[str] = None,
) -> HTMLResponse:
    """Display all generated blogs."""

    session_factory: async_sessionmaker[AsyncSession] = request.app.state.async_session
    async with session_factory() as session:
        stmt = select(Blog).order_by(Blog.updated_at.desc())
        result = await session.execute(stmt)
        blogs: List[Blog] = list(result.scalars().all())

    cards = [
        {
            "id": blog.id,
            "title": blog.title,
            "preview": summarize(blog.content),
            "content": blog.content,
            "tone": blog.tone or "Neutral",
            "updated_at": blog.updated_at,
        }
        for blog in blogs
    ]

    context = {
        "request": request,
        "blogs": cards,
        "message": message,
    }
    return templates.TemplateResponse("blogs.html", context)


@router.post("/blogs/{blog_id}/regenerate", response_class=HTMLResponse)
async def regenerate_blog(
    request: Request,
    blog_id: int,
) -> RedirectResponse:
    """Regenerate a blog's content by re-querying the AI model."""

    session_factory: async_sessionmaker[AsyncSession] = request.app.state.async_session
    ai_service: Optional[AIService] = getattr(request.app.state, "ai_service", None)
    ai_error: Optional[str] = getattr(request.app.state, "ai_error", None)

    if not ai_service:
        redirect_url = request.url_for("list_blogs")
        fallback_message = ai_error or "OpenAI API is not configured."
        return RedirectResponse(
            url=f"{redirect_url}?message={fallback_message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    async with session_factory() as session:
        blog = await session.get(Blog, blog_id)
        if not blog:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found.")

        try:
            response = await ai_service.generate_blog(blog.title, blog.tone)
        except Exception as exc:  # noqa: BLE001
            redirect_url = request.url_for("list_blogs")
            return RedirectResponse(
                url=f"{redirect_url}?message=Failed to regenerate blog: {exc}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

        blog.update_content(response.content)
        session.add(blog)
        await session.commit()

    redirect_url = request.url_for("list_blogs")
    return RedirectResponse(
        url=f"{redirect_url}?message=Regenerated '{blog.title}' successfully.",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/blogs/{blog_id}/download")
async def download_blog(
    request: Request,
    blog_id: int,
) -> StreamingResponse:
    """Download the blog content as a text file."""

    session_factory: async_sessionmaker[AsyncSession] = request.app.state.async_session
    async with session_factory() as session:
        blog = await session.get(Blog, blog_id)
        if not blog:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found.")

    filename = download_filename(blog.title)

    def _iter_text() -> Iterable[str]:
        yield f"{blog.title}\n"
        yield f"Tone: {blog.tone or 'Neutral'}\n"
        yield "\n"
        for line in chunk_text(blog.content):
            yield f"{line}\n"

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(_iter_text(), media_type="text/plain", headers=headers)


async def _fetch_recent_blogs(request: Request, *, limit: int) -> List[Blog]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.async_session
    async with session_factory() as session:
        stmt = select(Blog).order_by(Blog.updated_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


