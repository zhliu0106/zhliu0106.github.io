# -*- coding: utf-8 -*-

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable, Tuple
import unicodedata
import arxiv


KEYS = {
    # Large language model related
    "large language model": "Large Language Model",
    "large language models": "Large Language Model",
    "LLM": "Large Language Model",
    "LLMs": "Large Language Model",
    # Agent related
    "agent": "Agent",
    "agents": "Agent",
    "Agent": "Agent",
    "Agents": "Agent",
    "multi-agent": "Agent",
    "Multi-agent": "Agent",
    "multi-agents": "Agent",
    "Multi-agents": "Agent",
    "Multi-Agent": "Agent",
    "Multi-Agents": "Agent",
    # Safety related
    "safety": "Safety",
    "safe": "Safety",
    "Safety": "Safety",
    "Safe": "Safety",
    "security": "Safety",
    "Security": "Safety",
    # Trustworthy related
    "trustworthy": "Trustworthy",
    "trust": "Trustworthy",
    "Trustworthy": "Trustworthy",
    "Trust": "Trustworthy",
    "Trustworthiness": "Trustworthy",
    "trustworthiness": "Trustworthy",
    # Privacy related
    "privacy": "Privacy",
    "private": "Privacy",
    "Privacy": "Privacy",
    "Private": "Privacy",
    # Unlearning related
    "unlearning": "Unlearning",
    "Unlearning": "Unlearning",
    "Machine Unlearning": "Unlearning",
    "machine unlearning": "Unlearning",
}


AUTHORS = [
    "Yang Zhang",
    "Nicholas Carlini",
    "Andy Zou",
    "Lianmin Zheng",
    "Danqi Chen",
    "Zico Kolter",
    "Dawn Song",
    "Bo Li",
    "Percy Liang",
    "David Wagner",
    "Dan Hendrycks",
]


CONFS = {
    "ACL": "ACL",
    "EMNLP": "EMNLP",
    "NAACL": "NAACL",
    "COLING": "COLING",
    "ICLR": "ICLR",
    "NIPS": "NeurIPS",
    "NEURIPS": "NeurIPS",
    "ICML": "ICML",
    "JMLR": "JMLR",
}

CLASSES = ["cs.CL", "cs.LG", "cs.AI"]


def red(t: str) -> str:
    return f'<strong class="highlight"><em>{t}</em></strong>'


def text_title(t: str) -> str:
    return f'<code class="title">{t}</code>'


def texttt(t: str) -> str:
    return f"<code>{t}</code>"


def link(t: str) -> str:
    # return f'[{t}]({t})'
    return f'<a href="{t}">{t}</a>'


def normalize_id(t: str) -> str:
    t = unicodedata.normalize("NFD", t)
    t = "".join([c for c in t if not unicodedata.combining(c)])
    t = t.lower()
    # remove "." and ","
    t = t.replace(".", "")
    t = t.replace(",", "")
    # space to _
    t = re.sub(r"\s+", "_", t)
    # check if start with number
    if str.isdigit(t[0]):
        t = "N" + t
    return t


def upper_first(t: str) -> str:
    return t[0].upper() + t[1:]


def match(t: str, keys: Iterable) -> Tuple[str, bool]:
    # raw = t
    matched_keys = []
    for key in keys:
        if re.search(rf"\b{key}\b", t, flags=re.I):
            if isinstance(keys, dict):
                matched_keys.append(keys[key])
            else:
                matched_keys.append(key)
            t = re.sub(rf"\b{key}\b", lambda m: red(m.group()), t, flags=re.I)
    return t, matched_keys


def cover_timezones(date: datetime) -> datetime:
    # to UTF+8
    return date.astimezone(timezone(timedelta(hours=8)))


papers = defaultdict(lambda: defaultdict(dict))
papers_by_date = defaultdict(dict)
max_day = 7
new_day = 2
available_tabs = set()
tabs_info = defaultdict(dict)
new_date = cover_timezones(datetime.now() - timedelta(new_day)).strftime("%Y %b %d, %a")
client = arxiv.Client(num_retries=10, page_size=500)
for name in CLASSES:
    search = arxiv.Search(query=name, sort_by=arxiv.SortCriterion.SubmittedDate)
    results = client.results(search)
    # for paper in search.results():
    max_iter = 1000
    while True:
        try:
            paper = next(results)
        except StopIteration:
            break
        except arxiv.UnexpectedEmptyPageError:
            continue
        max_iter -= 1
        if max_iter < 0:
            break
        date = datetime.now(paper.published.tzinfo) - timedelta(max_day)
        print(f"Find paper {paper.entry_id} {paper.title} {paper.published}")
        if paper.published.date() < date.date():
            break
        # Convert to UTC+8
        date = cover_timezones(paper.published).strftime("%Y %b %d, %a")
        any_match = []
        title, matched = match(paper.title, KEYS)
        any_match.extend(matched)
        authors, matched = match(
            ", ".join([f"{author}" for author in paper.authors]), AUTHORS
        )
        any_match.extend(matched)
        abstract, matched = match(paper.summary, KEYS)
        any_match.extend(matched)
        comments, comment_matched = match(paper.comment or "", CONFS)
        any_match.extend(comment_matched)
        if len(any_match) == 0:
            continue
        available_tabs.update(any_match)
        paper_content = f"<strong>{title}</strong><br>\n"
        paper_content += f'{text_title("[AUTHORS]")}{authors} <br>\n'
        paper_content += f'{text_title("[ABSTRACT]")}{abstract} <br>\n'
        if comments:
            paper_content += f'{text_title("[COMMENTS]")}{comments} <br>\n'
        paper_content += f'{text_title("[LINK]")}{link(paper.entry_id)} <br>\n'
        paper_content += (
            f'{text_title("[DATE]")}{cover_timezones(paper.published)} <br>\n'
        )
        categories = "    ".join([texttt(c) for c in paper.categories if c in CLASSES])
        paper_content += f'{text_title("[CATEGORIES]")}{categories} <br>\n'
        for key in any_match:
            if date >= new_date:
                tabs_info[key]["new"] = True
            papers[key][date][paper.title] = paper_content
            papers_by_date[date][paper.title] = paper_content

with open("arxiv.md", "w") as f:
    f.write("---\nlayout: default\n---\n\n")
    f.write('<ul class="tab-nav">\n')
    for i, domain in enumerate([KEYS, AUTHORS, CONFS]):
        if isinstance(domain, dict):
            domain = set(domain.values())
        for i, tab in enumerate(sorted(available_tabs)):
            if tab not in domain:
                continue
            f.write(
                f'<li><a class="button" href="#{normalize_id(tab)}">{upper_first(tab)}</a>'
            )
            if tabs_info[tab].get("new", False):
                f.write('<span class="new-dot"> </span>')
            f.write("</li>\n")
        f.write('<li style="margin-right: auto;"><div></div></li>\n')
        f.write(f'<hr class="tab-nav-divider {" last" if i == 2 else ""}">\n')
    for i, date in enumerate(sorted(papers_by_date.keys(), reverse=True)):
        f.write(
            f'<li><a class="button{" active" if i == 0 else ""}" href="#{normalize_id(date)}">{date}</a></li>\n'
        )
    f.write("</ul>\n\n")
    f.write(f"<hr>\n")

    f.write('<div class="tab-content">\n')
    for i, tab in enumerate(sorted(available_tabs)):
        f.write(f'<div class="tab-pane" id="{normalize_id(tab)}">\n')
        for j, date in enumerate(sorted(papers[tab].keys(), reverse=True)):
            f.write(
                f'<details {"open" if j == 0 else ""}><summary class="date">{date}</summary>\n\n'
            )
            f.write("<ul>\n")
            for title, paper in papers[tab][date].items():
                f.write('<li class="arxiv-paper">\n')
                f.write(paper.replace("{", "\{").replace("}", "\}") + "\n\n")
                f.write("</li>\n")
            f.write("</ul>\n")
            f.write("</details>\n\n")
        f.write("</div>\n")
    for i, date in enumerate(sorted(papers_by_date.keys(), reverse=True)):
        f.write(
            f'<div class="tab-pane{" active" if i == 0 else ""}" id="{normalize_id(date)}">\n'
        )
        f.write("<ul>\n")
        for title, paper in papers_by_date[date].items():
            f.write('<li class="arxiv-paper">\n')
            f.write(paper.replace("{", "\{").replace("}", "\}") + "\n\n")
            f.write("</li>\n")
        f.write("</ul>\n")
        f.write("</div>\n")
    f.write("</div>\n")
