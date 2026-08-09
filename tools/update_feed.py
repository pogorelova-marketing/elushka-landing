#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновляет каталог Ёлушки из фида Max Christmas.

Запуск:  python3 tools/update_feed.py
         python3 tools/update_feed.py путь/к/локальному/FID_ELUSHKA.xml

Что делает:
  1. Тянет YML-фид (или читает локальный файл, если путь передан аргументом)
  2. Группирует офферы в модельные ряды: одна модель = несколько высот
  3. Пишет data/models.json — на случай, если данные понадобятся отдельно
  4. Вставляет те же данные ПРЯМО в index.html, между маркерами MODELS-DATA.
     Так каталог отображается всегда: и на хостинге, и при открытии файла
     с диска, и в панели предпросмотра — внешние загрузки не нужны.

Зависимостей нет, только стандартная библиотека.
"""

import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime

FEED_URL = "https://maxchristmas-store.ru/bitrix/catalog_export/FID_ELUSHKA.xml"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "models.json")
INDEX = os.path.join(ROOT, "index.html")

BEGIN = "/* MODELS-DATA:BEGIN */"
END = "/* MODELS-DATA:END */"

# Витрина: как модель зовётся в фиде → как показываем → короткое пояснение.
# Порядок здесь = порядок на странице.
SHOWCASE = [
    ("Уральская",                                "Уральская",               "Классический русский силуэт"),
    ("Донская",                                  "Донская",                 "Пышная, с широким низом"),
    ("Королевская",                              "Королевская",             "Крупная хвоя, плотный ярус"),
    ("Алёнушка",                                 "Алёнушка",                "Стройная, для небольших комнат"),
    ("Заснеженная литая елка Уральская",         "Уральская заснеженная",   "Как после первого снега"),
    ("Заснеженная литая елка Донская",           "Донская заснеженная",     "Заснеженная хвоя, широкий низ"),
    ("Королевская заснеженная",                  "Королевская заснеженная", "Заснеженная, крупная хвоя"),
    ("Елка искусственная Сказочная заснеженная", "Сказочная заснеженная",   "Пышная, праздничная"),
    ("Люблинская",                               "Люблинская",              "Лёгкая и самая доступная"),
    ("Ивановская",                               "Ивановская",              "Мягкий силуэт"),
    ("Марьинская",                               "Марьинская",              "Густая крона"),
    ("Подольская",                               "Подольская",              "Ровный конус"),
    ("Лозанна",                                  "Лозанна",                 "Тонкая проработка веток"),
    ("Фаворит",                                  "Фаворит",                 "Объёмная, парадная"),
    ("Сибирская широкая",                        "Сибирская широкая",       "Для просторных комнат"),
    ("Елка искусственная Сказочная премиум",     "Сказочная премиум",       "Плотная крона, крупная хвоя"),
    ("Ель искусственная литая Криель",           "Криель",                  "Узкая, под ёлочный угол"),
    ("Ель настольная Уральская",                 "Уральская настольная",    "На стол, полку, подоконник"),
    ("Ель настольная Пряная",                    "Пряная настольная",       "Компактная"),
    ("Ель настольная Венецианская",              "Венецианская настольная", "Для небольшой квартиры"),
]


def family_of(model_name):
    """«Елка литая Уральская 1.8 м» → «Уральская»."""
    s = re.sub(r"\s*\d+[.,]\d+\s*м.*$", "", model_name).strip()
    s = re.sub(r"\s*\d+\s*м$", "", s).strip()
    s = re.sub(r"^Елка литая\s*", "", s).strip()
    return s


def height_m(h):
    """«1.8 м» → 1.8; «60 см» → 0.6. Нужно для сортировки и слайдера высот."""
    if not h:
        return 0.0
    t = h.replace(",", ".").lower()
    num = re.search(r"[\d.]+", t)
    if not num:
        return 0.0
    v = float(num.group(0))
    return v / 100 if "см" in t else v


def kind_of(title, subtitle):
    t = (title + " " + subtitle).lower()
    if "настольн" in t:
        return "table"
    if "заснеж" in t:
        return "snow"
    return "green"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        raw = open(src, "rb").read()
        origin = os.path.abspath(src)
    else:
        with urllib.request.urlopen(FEED_URL, timeout=60) as r:
            raw = r.read()
        origin = FEED_URL

    root = ET.fromstring(raw)
    groups = OrderedDict()

    for o in root.findall(".//offer"):
        def txt(tag, default=""):
            e = o.find(tag)
            return e.text if e is not None and e.text else default

        model = txt("model")
        if not model:
            continue

        h = ""
        for p in o.findall("param"):
            if p.get("name") == "Высота":
                h = (p.text or "").strip()

        diam = ""
        for p in o.findall("param"):
            if p.get("name", "").startswith("Диаметр"):
                diam = (p.text or "").strip()

        fam = family_of(model)
        # полное название как в фиде, но без высоты: «Елка литая Уральская 1.8 м» → «Елка литая Уральская»
        full = re.sub(r"\s*\d+[.,]?\d*\s*(м|см)\s*$", "", model).strip()
        g = groups.setdefault(fam, {
            "family": fam,
            "full_name": full,
            "picture": txt("picture"),
            "url": txt("url").split("?")[0],
            "heights": [],
        })
        old = txt("oldprice")
        g["heights"].append({
            "h": h,
            "m": height_m(h),
            "d": diam,
            "price": int(float(txt("price", "0") or 0)),
            "oldprice": int(float(old)) if old else None,
            "url": txt("url"),
        })

    for g in groups.values():
        # уникальные высоты, по возрастанию
        seen = {}
        for item in g["heights"]:
            seen[item["h"]] = item
        g["heights"] = sorted(seen.values(), key=lambda x: x["m"])
        g["price_from"] = g["heights"][0]["price"]
        g["m_min"] = g["heights"][0]["m"]
        g["m_max"] = g["heights"][-1]["m"]

    showcase = []
    for feed_name, title, subtitle in SHOWCASE:
        g = groups.get(feed_name)
        if not g:
            print(f"  ! пропущено (нет в фиде): {feed_name}")
            continue
        item = dict(g)
        item["title"] = title
        item["subtitle"] = subtitle
        item["kind"] = kind_of(title, subtitle)
        showcase.append(item)

    data = {
        "updated": datetime.now().strftime("%d.%m.%Y"),
        "source": origin,
        "min_price": min(g["price_from"] for g in groups.values()),
        "models_total": len(groups),
        "showcase": showcase,
    }

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    # вшиваем данные прямо в страницу
    html = open(INDEX, encoding="utf-8").read()
    payload = BEGIN + "\nwindow.ELUSHKA = " + json.dumps(data, ensure_ascii=False) + ";\n" + END
    if BEGIN not in html:
        print("!! В index.html нет маркеров MODELS-DATA — данные не вшиты")
    else:
        html = re.sub(
            re.escape(BEGIN) + r".*?" + re.escape(END),
            lambda _: payload,
            html,
            flags=re.S,
        )
        open(INDEX, "w", encoding="utf-8").write(html)

    print(f"OK: {len(showcase)} моделей на витрине, в фиде {len(groups)}. "
          f"Минимальная цена {data['min_price']} ₽.")
    print(f"    источник: {origin}")
    print(f"    записано: {OUT_JSON} + index.html")


if __name__ == "__main__":
    main()
