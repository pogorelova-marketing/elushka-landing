# Ёлушка — лендинг-визитка

Одностраничник бренда **Ёлушка by Max Christmas**: доносит характер бренда
и ведёт покупателя в удобный маршрут покупки (магазин Max Christmas,
Wildberries, Ozon, оптовый прайс).

**Превью:** https://pogorelova-marketing.github.io/elushka-landing/

## Что внутри

```
index.html            вся страница: разметка, стили, скрипты и данные каталога
data/models.json      выгрузка каталога из фида Max Christmas
tools/update_feed.py  обновляет каталог и вшивает его в index.html
assets/               шрифт, логотипы, фото, отзывы, видео
```

## Локальный запуск

```bash
python3 -m http.server 8811
# http://localhost:8811
```

## Обновление цен и моделей

```bash
python3 tools/update_feed.py                        # из живого фида
python3 tools/update_feed.py путь/к/FID_ELUSHKA.xml # из локального файла
```

Скрипт группирует офферы в модельные ряды и вписывает данные прямо в `index.html`
между маркерами `MODELS-DATA` — внешних загрузок нет, каталог работает везде.

Статика, без сборки и бэкенда: папку можно положить на любой хостинг как есть.
