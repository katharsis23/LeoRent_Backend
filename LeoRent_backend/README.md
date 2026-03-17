
# LeoRent Backend

## Installation

1. Клонуй репозиторій

```bash
   git clone <repository_url>
   cd LeoRent_Backend/LeoRent_backend
```

2. Завантаж poetry

3. Налаштування poetry

```bash
   poetry config virtualenvs.in-project true
   
   poetry install
```

4. Налаштування pre-commit хука(необхідно при contribution)

   ```bash
   cp ../scripts/pre-commit.bash ../.git/hooks/pre-commit
   chmod +x ../.git/hooks/pre-commit
   ```

   ```bash
   cp ../scripts/pre-commit.bash ../.git/hooks/pre-commit
   chmod +x ../.git/hooks/pre-commit
   ```

---

## Запуск проекту (Running)

Ми використовуємо **Invoke** для зручного запуску команд. Тобі не потрібно пам'ятати довгі прапорці uvicorn!

### Запуск сервера
```bash
poetry run inv dev
```
*Це запустить сервер за адресою `http://0.0.0.0:8000` з автоматичним перезавантаженням при зміні коду! *

---

## 🛠 Корисні команди (Invoke Tasks)

Ми маємо спеціальний файл `tasks.py` з набором команд:

- **`poetry run inv lint`** — перевірка коду лінтером (flake8).
- **`poetry run inv test`** — запуск усіх тестів (pytest).
- **`poetry run inv check`** — запуск лінтера та тестів одночасно (ідеально перед комітом!). 
- **`poetry run inv clean`** — очищення кешу, тимчасових файлів та __pycache__.
- **`poetry run inv --list`** — переглянути всі доступні команди.

---

## Керування залежностями (Poetry)

- **Додати пакет:** `poetry add <package_name>`
- **Додати dev-пакет:** `poetry add --group dev <package_name>`
- **Оновити все:** `poetry update`
- **Інфо про env:** `poetry env info`

---

## Тестування

Всі тести знаходяться в папці `tests/`. Ти можеш запустити їх через invoke:
```bash
poetry run inv test
```
