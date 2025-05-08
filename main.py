# main.py
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0") # Важно для доступности извне

    # Для продакшена:
    uvicorn.run(
        "src.app:app",
        host=host,
        port=port,
        workers=int(os.getenv("WEB_CONCURRENCY", 4)) # Количество воркеров
        # proxy_headers=True, # Если за Nginx/Traefik и т.д.
        # forward_allow_ips='*' # Осторожно с этим, если не за прокси
    )
    # Для разработки можно оставить:
    # uvicorn.run("src.app:app", host="127.0.0.1", port=port, reload=True)
