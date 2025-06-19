#!/usr/bin/env python3

import newspaper
import feedparser
import subprocess

def speak(text):
    subprocess.run(["python3", "scripts/say.py", text])

def scrape_top_articles(feed_url, max_articles=3):
    articles = []
    feed = feedparser.parse(feed_url)
    for entry in feed.entries[:max_articles]:
        article = newspaper.Article(entry.link)
        try:
            article.download()
            article.parse()
        except:
            continue  # skip if article fails to load

        articles.append({
            'title': article.title,
            'summary': article.text[:200].strip().replace('\n', ' ') + "...",  # first ~200 chars
        })
    return articles

feed_url = 'http://feeds.arstechnica.com/arstechnica/index'
articles = scrape_top_articles(feed_url)

# Speak and display the top 3 headlines
speak("Here are the top 3 headlines from Ars Technica today.")
print("\n📰 Top 3 Ars Technica Headlines:\n")

for i, article in enumerate(articles, start=1):
    print(f"{i}. {article['title']}")
    print(article['summary'])
    print()

    speak(f"Headline {i}: {article['title']}")
