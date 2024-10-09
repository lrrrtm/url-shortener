import os
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import logging

from database.crud import get_existing_record, add_new_link, get_record_by_short_code, renew_url_record
from utils.link_checker import check_link
from utils.short_code_generator import generate_short_code

logging.basicConfig(
    filename='app.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

user_link_counts = defaultdict(lambda: {'count': 0, 'timestamp': datetime.utcnow()})

MAX_LINKS_PER_USER = 100
LINK_HOST = os.getenv('HOST')

app = FastAPI(
    title="Short link generator app"
)


class LinkCreate(BaseModel):
    original_url: str


class LinkResponse(BaseModel):
    original_url: str
    shortened_url: str
    short_url_code: str


@app.post("/generator/", response_model=LinkResponse,
          description="Создает короткую ссылку на основе полного URL. Если ссылка уже существует, возвращает уже существующую короткую ссылку")
async def create_short_url(link: LinkCreate, request: Request):
    """
    Создание короткой ссылки.

    - **link.original_url**: Полный URL, который нужно сократить.
    - **Returns**: Короткий код URL.
    """
    user_ip = request.client.host
    current_datetime = datetime.utcnow()

    if current_datetime - user_link_counts[user_ip]['timestamp'] > timedelta(hours=1):
        user_link_counts[user_ip] = {'count': 0, 'timestamp': current_datetime}

    existing_link = get_existing_record(link.original_url)
    if existing_link:

        if (current_datetime - existing_link.created_at).total_seconds() > existing_link.ttl:
            renew_url_record(link.original_url)

        return LinkResponse(
            original_url=existing_link.original_url,
            shortened_url=f"{LINK_HOST}/{existing_link.short_url}",
            short_url_code=existing_link.short_url,
        )

    else:
        if user_link_counts[user_ip]['count'] >= MAX_LINKS_PER_USER:
            raise HTTPException(status_code=429,
                                detail="Достигнуто максимальное количество генераций для данного IP-адреса")

        if not check_link(link.original_url):
            raise HTTPException(status_code=400, detail="Неверный формат ссылки")

        short_url_code = generate_short_code(link.original_url)

        new_link = add_new_link(
            original_url=link.original_url,
            short_url_code=short_url_code,
            created_at=current_datetime
        )
        user_link_counts[user_ip]['count'] += 1
        return LinkResponse(
            original_url=new_link.original_url,
            shortened_url=f"{LINK_HOST}/{new_link.short_url}",
            short_url_code=new_link.short_url,
        )


@app.get("/generator/{short_url}",
         description="Получает полный URL по короткой ссылке. Возвращает ошибку, если ссылка не найдена или срок ее действия истёк")
async def get_original_url(short_url: str):
    """
    Получение полного URL по короткому коду.

    - **short_url**: Короткий код URL.
    - **Returns**: Полный URL в формате JSON.
    """
    link = get_record_by_short_code(short_url)

    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    if (datetime.utcnow() - link.created_at).total_seconds() > link.ttl:
        raise HTTPException(status_code=404, detail="Срок действия ссылки истек")

    return {"original_url": link.original_url}


@app.get("/error", description="Тестовая функция для генерации ошибки")
async def test_error():
    """
    Тестирование обработки ошибок.

    - **Returns**: Ошибка деления на ноль.
    """
    result = 1 / 0
    return {"result": result}


@app.get("/{short_url}",
         description="Переадресовывает на полный URL по короткой ссылке. Возвращает ошибку, если ссылка не найдена или срок ее действия истёк")
async def redirect_to_original_url(short_url: str):
    """
    Переадресация по короткому URL.

    - **short_url**: Короткий код URL для переадресации.
    - **Returns**: Переадресация на полный URL.
    """
    data = get_record_by_short_code(short_url)

    if not data:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    if (datetime.utcnow() - data.created_at).total_seconds() > data.ttl:
        raise HTTPException(status_code=404, detail="Срок действия ссылки истек")

    if not data.original_url.startswith("http://") and not data.original_url.startswith("https://"):
        data.original_url = "http://" + data.original_url

    return RedirectResponse(url=data.original_url)


@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    """
    Обработчик исключений для внутренних ошибок сервера.

    - **Returns**: Ошибка 500 с описанием.
    """
    logging.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера", 'exception': str(exc)},
    )
