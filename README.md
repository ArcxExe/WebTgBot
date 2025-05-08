
Создать .env файл в корне и заполнить 
TELEGRAM_BOT_TOKEN=<YOUR_ACTUAL_BOT_TOKEN>
SESSION_SECRET_KEY=<a-very-secure-random-string-please-change>

Как создать
```python
import secrets
print(secrets.token_hex(32))
```
