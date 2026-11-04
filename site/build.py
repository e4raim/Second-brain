#!/usr/bin/env python3
"""Собирает сайт базы знаний для стажёров и агентов: site/baza.html.
Берёт только темы с ролями «стажер» или «агент», вырезает блоки для руководителя
и внутренние пометки. Запуск: python3 site/build.py"""
import re, json, os, glob, html
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OK_ROLES = {"стажер", "стажёр", "агент"}
SECTIONS = {"01-company": "Компания", "02-product": "Продукт и ЖК", "03-sales": "Продажи",
            "04-objections": "Возражения", "05-scripts": "Скрипты", "06-dialog-reviews": "Разборы",
            "07-management": "Рост и мышление", "08-self-management": "Личная эффективность"}

def parse(path):
    s = open(path, encoding="utf-8").read()
    fm, body = {}, s
    m = re.match(r"---\n(.*?)\n---\n", s, re.S)
    if m:
        body = s[m.end():]
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1); fm[k.strip()] = v.strip().strip('"')
    return fm, body

def roles(fm):
    return {r.strip() for r in fm.get("roles", "").strip("[]").split(",") if r.strip()}

def clean(body):
    # убрать разделы для руководителя и внутренние ⚠️-блоки
    body = re.sub(r"\n## (Для руководителя|⚠️[^\n]*)\n.*?(?=\n## |\Z)", "\n", body, flags=re.S)
    lines = [l for l in body.splitlines() if not re.search(r"Вопрос автору|inbox/|sources/|\*\*Пришли", l)]
    return "\n".join(lines).strip()

docs, order = {}, []
PREFERRED = ["o-kompanii", "dengi-agenta", "grafik-i-normy", "crm-i-rasporyadok-dnya",
    "rynok-osnovy", "segment-i-klient", "rabota-po-odnomu-zhk", "kommercheskaya-nedvizhimost",
    "put-sdelki", "istochniki-obektov", "zvonok-sobstvenniku", "tri-dogovorennosti", "vstrecha-s-sobstvennikom",
    "obekt-v-praise", "podgotovka-obekta-k-pokazu", "pokupateli-i-pokaz", "cena-i-snizhenie",
    "rabota-na-perspektivu", "strategii-prodazhi-obekta", "obyavlenie-i-foto", "kommentarii-v-crm",
    "dozhim-i-zakrytie", "yuridicheskaya-baza", "kross-prodazhi",
    "vozrazheniya-sobstvennika", "vozrazheniya-pri-zvonke-na-pokupku",
    "skript-zvonka-sobstvenniku", "skript-perepiski-s-sobstvennikom", "skript-kross-prodazhi",
    "strah-i-otkazy", "plan-dnya", "otdyh-i-vosstanovlenie", "kakim-byt-minus-odin"]
def rank(p):
    slug = os.path.splitext(os.path.basename(p))[0]
    return (os.path.basename(os.path.dirname(p)), PREFERRED.index(slug) if slug in PREFERRED else 999, slug)
for path in sorted(glob.glob(os.path.join(ROOT, "knowledge", "*", "*.md")), key=rank):
    sec = os.path.basename(os.path.dirname(path))
    fm, body = parse(path)
    if sec == "05-scripts" or roles(fm) & OK_ROLES:
        slug = os.path.splitext(os.path.basename(path))[0]
        title = fm.get("title") or re.search(r"^# (.+)$", body, re.M).group(1)
        body = re.sub(r"^# .+\n", "", body, count=1, flags=re.M)
        qs = re.findall(r"^- (.+\?)$", body.split("**Коротко", 1)[0], re.M)
        docs[slug] = {"t": title, "n": re.split(r"[:(]", title)[0].strip(), "sec": sec,
                      "md": clean(body), "q": qs, "path": os.path.relpath(path, ROOT)}
        order.append(slug)

def fix_links(md, base_dir):
    def rep(m):
        text, target = m.group(1), m.group(2).split("#")[0]
        full = os.path.normpath(os.path.join(base_dir, target))
        slug = os.path.splitext(os.path.basename(full))[0]
        if full.endswith(".md") and "/knowledge/" in full and slug in docs:
            if text.endswith(".md"): text = docs[slug]["n"]
            return f"[{text}](#{slug})"
        if full.endswith("tracks/intern.md"): return f"[{text}](#track-intern)"
        if full.endswith("tracks/agent.md"): return f"[{text}](#track-agent)"
        if full.endswith("FAQ.md"): return f"[{text}](#home)"
        return text
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", rep, md)

for slug in order:
    d = docs[slug]
    d["md"] = fix_links(d["md"], os.path.join(ROOT, os.path.dirname(d["path"])))
    del d["path"]

tracks = {}
for key, name in (("intern", "Стажёр"), ("agent", "Агент")):
    _, body = parse(os.path.join(ROOT, "tracks", f"{key}.md"))
    body = re.sub(r"^# .+\n", "", body, count=1, flags=re.M)
    body = "\n".join(l for l in body.splitlines() if "../tracks/" not in l or "intern" in l)
    tracks[key] = {"t": f"Трек: {name}", "md": fix_links(clean(body), os.path.join(ROOT, "tracks"))}

# FAQ: только вопросы, ведущие на опубликованные темы
faq, cur = [], None
for line in open(os.path.join(ROOT, "FAQ.md"), encoding="utf-8"):
    line = line.rstrip()
    if line.startswith("## "):
        cur = {"h": line[3:], "items": []}; faq.append(cur)
    elif line.startswith("- ") and cur is not None:
        q = re.match(r"- (.+?) →", line)
        links = [os.path.splitext(os.path.basename(t))[0] for t in re.findall(r"\]\(([^)#]+)", line)]
        targets = [l for l in links if l in docs]
        if q and targets:
            cur["items"].append({"q": q.group(1), "to": targets[0],
                                 "names": [docs[t]["t"] for t in dict.fromkeys(targets)]})
faq = [g for g in faq if g["items"] and not re.search(r"РОП|руководител", g["h"], re.I)]

data = {"docs": docs, "order": order, "sections": SECTIONS, "tracks": tracks, "faq": faq}
tpl = open(os.path.join(ROOT, "site", "template.html"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
open(os.path.join(ROOT, "site", "baza.html"), "w", encoding="utf-8").write(out)
print(f"тем: {len(order)}, вопросов в FAQ: {sum(len(g['items']) for g in faq)}, размер: {len(out)//1024} КБ")
