from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import logging

from database.crud import get_existing_link, add_new_link, get_full_link_by_short_code, renew_link
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

app = FastAPI()


class LinkCreate(BaseModel):
    full_url: str


class LinkResponse(BaseModel):
    short_url: str


@app.post("/short/", response_model=LinkResponse,
          description="Создает короткую ссылку на основе полного URL. Если ссылка уже существует, возвращает уже существующую короткую ссылку")
async def create_short_url(link: LinkCreate, request: Request):
    """
    Создание короткой ссылки.

    - **link.full_url**: Полный URL, который нужно сократить.
    - **Returns**: Короткий код URL.
    """
    user_ip = request.client.host
    current_datetime = datetime.utcnow()

    if current_datetime - user_link_counts[user_ip]['timestamp'] > timedelta(hours=1):
        user_link_counts[user_ip] = {'count': 0, 'timestamp': current_datetime}

    existing_link = get_existing_link(link.full_url)
    if existing_link:

        if (current_datetime - existing_link.created_at).total_seconds() > existing_link.ttl:

            link = renew_link(link.full_url)
            return LinkResponse(short_url=link.short_url)
        else:
            return LinkResponse(short_url=existing_link.short_url)

    else:
        if user_link_counts[user_ip]['count'] >= MAX_LINKS_PER_USER:
            raise HTTPException(status_code=429,
                                detail="Достигнуто максимальное количество генераций для данного IP-адреса")

        if not check_link(link.full_url):
            raise HTTPException(status_code=400, detail="Неверный формат ссылки")

        short_url = generate_short_code(link.full_url)

        new_link = add_new_link(
            full_url=link.full_url,
            short_url=short_url,
            created_at=current_datetime
        )
        user_link_counts[user_ip]['count'] += 1
        return LinkResponse(short_url=new_link.short_url)


@app.get("/short/{short_url}",
         description="Получает полный URL по короткой ссылке. Возвращает ошибку, если ссылка не найдена или срок ее действия истёк")
async def get_full_url(short_url: str):
    """
    Получение полного URL по короткому коду.

    - **short_url**: Короткий код URL.
    - **Returns**: Полный URL в формате JSON.
    """
    link = get_full_link_by_short_code(short_url)

    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    if (datetime.utcnow() - link.created_at).total_seconds() > link.ttl:
        raise HTTPException(status_code=404, detail="Срок действия ссылки истек")

    return {"full_url": link.full_url}


@app.get("/redir/{short_url}",
         description="Переадресовывает на полный URL по короткой ссылке. Возвращает ошибку, если ссылка не найдена или срок ее действия истёк")
async def redirect_to_full_url(short_url: str):
    """
    Переадресация по короткому URL.

    - **short_url**: Короткий код URL для переадресации.
    - **Returns**: Переадресация на полный URL.
    """
    link = get_full_link_by_short_code(short_url)

    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    if (datetime.utcnow() - link.created_at).total_seconds() > link.ttl:
        raise HTTPException(status_code=404, detail="Срок действия ссылки истек")

    if not link.full_url.startswith("http://") and not link.full_url.startswith("https://"):
        link.full_url = "http://" + link.full_url
    return RedirectResponse(url=link.full_url)


@app.get("/error", description="Тестовая функция для генерации ошибки")
async def test_error():
    """
    Тестирование обработки ошибок.

    - **Returns**: Ошибка деления на ноль.
    """
    result = 1 / 0
    return {"result": result}


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
