# LeoRent Backend


Цей проект використовує [Poetry](https://python-poetry.org/) для керування залежностями та віртуальним середовищем.

---

## Prerequisites (Вимоги)

Перед початком переконайся, що в тебе встановлено:
- **Python**: версія `^3.14` (саме так вказано в нашому `pyproject.toml`)
- **Poetry**: основний інструмент для керування проектом.

Якщо Poetry ще немає, його можна встановити цією командою:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

---

##  Інструкція зі встановлення

1. **Клонуй репозиторій:**
   ```bash
   git clone <repository_url>
   cd LeoRent_Backend/LeoRent_backend
   ```

2. **Налаштування віртуального середовища:**
   Щоб Poetry створював `.venv` прямо в папці проекту (це дуже зручно для VS Code та інших IDE), виконай:
   ```bash
   poetry config virtualenvs.in-project true
   ```

3. **Створення env та встановлення залежностей:**
   Ця команда автоматично створить віртуальне середовище та встановить усі бібліотеки:
   ```bash
   poetry install
   ```
   *Підказка: якщо потрібно встановити без dev-залежностей (якщо вони будуть), використовуй `poetry install --only main`.*

---

##  Використання (Usage)

### Активація середовища
Щоб увійти у віртуальне середовище:
```bash
poetry shell
```

### Запуск команд
Ти можеш запускати скрипти без прямої активації shell:
```bash
poetry run <command>
```
Наприклад, для запуску сервера (за умови, що `main.py` знаходиться в пакеті):
```bash
poetry run uvicorn src.leorent_backend.main:app --reload
```

---

## Корисні команди Poetry

- **Додати нову бібліотеку:**
  ```bash
  poetry add <package_name>
  ```
- **Оновити залежності:**
  ```bash
  poetry update
  ```
- **Видалити пакет:**
  ```bash
  poetry remove <package_name>
  ```
- **Переглянути інформацію про env:**
  ```bash
  poetry env info
  ```
