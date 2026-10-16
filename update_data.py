#!/usr/bin/env python3
"""Публичные данные для веб-версии Buy&Sell (запускает задача GitHub раз в 6 часов):
fx.json   — курсы по дням с 2023 года: ЦБ РФ (рублей за 1 USD, EUR, CNY) и ЕЦБ (поле "X": единиц валюты за 1 USD, через api.frankfurter.dev);
            cbr.ru не отдаёт их страницам напрямую;
news.json — заголовки Holder.io (RSS);
rates.json — ставки OKX Simple Earn (публичная сводка; OKX не отдаёт её страницам напрямую). Ни ключей, ни личных данных здесь нет."""
import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 BuySell-site/1.0"
CODES = {"USD": "R01235", "EUR": "R01239", "CNY": "R01375"}
# валюты ЕЦБ для пользователей из других стран (рубль — по ЦБ РФ)
ECB = "EUR,GBP,CHF,JPY,CNY,AUD,CAD,BRL,MXN,INR,KRW,TRY,PLN,SGD,HKD,ZAR"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
        return r.read()


def fx():
    path = os.path.join(HERE, "fx.json")
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    start = max(data) if data else "2023-01-01"
    d1 = (dt.date.fromisoformat(start) - dt.timedelta(days=10)).strftime("%d/%m/%Y")
    d2 = (dt.date.today() + dt.timedelta(days=3)).strftime("%d/%m/%Y")  # ЦБ публикует курс на завтра
    for ccy, code in CODES.items():
        root = ET.fromstring(get("https://www.cbr.ru/scripts/XML_dynamic.asp?" + urllib.parse.urlencode({"date_req1": d1, "date_req2": d2, "VAL_NM_RQ": code})))
        for rec in root.findall("Record"):
            day = dt.datetime.strptime(rec.get("Date"), "%d.%m.%Y").strftime("%Y-%m-%d")
            val = float(rec.findtext("Value", "0").replace(",", ".")) / (float(rec.findtext("Nominal", "1").replace(",", ".")) or 1)
            data.setdefault(day, {})[ccy] = round(val, 4)
    try:
        ecb(data)
    except Exception as e:  # ЕЦБ недоступен — курсы ЦБ всё равно сохраняем
        print("fail ecb", e)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(data.items())), fh, separators=(",", ":"))


def ecb(data):
    """Официальные курсы ЕЦБ по рабочим дням: data[день]["X"] = {валюта: единиц за 1 USD}."""
    have = [d for d in data if "X" in data[d]]
    start = (dt.date.fromisoformat(max(have)) - dt.timedelta(days=10)).isoformat() if have else "2023-01-01"
    d = json.loads(get("https://api.frankfurter.dev/v1/%s..?base=USD&symbols=%s" % (start, ECB)))
    for day, rates in (d.get("rates") or {}).items():
        data.setdefault(day, {})["X"] = {k: float("%.5g" % v) for k, v in rates.items()}


def news():
    x = get("https://holder.io/feed/").decode("utf-8", "replace")
    out = []
    for it in re.findall(r"<item>(.*?)</item>", x, re.S)[:15]:
        g = lambda tag: (re.search(r"<%s>(.*?)</%s>" % (tag, tag), it, re.S) or [None, ""])[1]
        title = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", g("title"))).strip()
        link = g("link").strip()
        if title and link.startswith("https://holder.io/"):
            try:
                ts = int(dt.datetime.strptime(g("pubDate").strip(), "%a, %d %b %Y %H:%M:%S %z").timestamp() * 1000)
            except Exception:
                ts = 0
            out.append({"title": title, "link": link, "ts": ts})
    with open(os.path.join(HERE, "news.json"), "w", encoding="utf-8") as fh:
        json.dump({"items": out}, fh, ensure_ascii=False)


def rates():
    d = json.loads(get("https://www.okx.com/api/v5/finance/savings/lending-rate-summary"))
    if str(d.get("code")) != "0":
        raise RuntimeError(d.get("msg"))
    out = [{"ccy": r.get("ccy"), "rate": float(r.get("estRate") or r.get("avgRate") or 0)} for r in d.get("data") or [] if r.get("ccy")]
    with open(os.path.join(HERE, "rates.json"), "w", encoding="utf-8") as fh:
        json.dump({"ts": int(dt.datetime.now().timestamp() * 1000), "rates": out}, fh, separators=(",", ":"))


if __name__ == "__main__":
    for fn in (fx, news, rates):
        try:
            fn()
            print("ok", fn.__name__)
        except Exception as e:  # один источник недоступен — другой всё равно обновляем
            print("fail", fn.__name__, e)
