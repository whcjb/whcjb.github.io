# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Jekyll-based static blog site for 南山圣約归正教会 (Nanshan Covenant Reformed Church), hosted on GitHub Pages at `whcjb.github.io`. The site is a Reformed/Calvinist church website with posts in Chinese.

## Local Development

```bash
# Install Ruby dependencies
bundle install

# Serve locally with live reload
bundle exec jekyll serve

# Build static site
bundle exec jekyll build
```

For CSS/JS asset compilation (requires Node.js):
```bash
npm install
grunt          # compile LESS → CSS and minify JS
grunt watch    # watch for changes
```

## Adding Content

### New Blog Post

Create a file in `_posts/` named `YYYY-MM-DD-title.md` with front matter:

```yaml
---
layout:     post
title:      文章标题
subtitle:   副标题
date:       YYYY-MM-DD
header-img: img/post-bg-2015.jpg
catalog:    true        # show sidebar table of contents
tags:
    - 标签名
---
```

### Audio/Index Posts

Posts with `.index` extension (e.g. `_posts/2018-09-24-*.index`) appear to be sermon audio listings — check existing ones for the format.

## Architecture

- **`_config.yml`** — site-wide settings: title, Gitalk comments config, pagination, friends links
- **`_layouts/`** — page templates (`default`, `post`, `page`, `keynote`)
- **`_includes/`** — reusable partials (`head.html`, `nav.html`, `footer.html`)
- **`_posts/`** — blog content in Markdown
- **`less/`** — LESS source files compiled to `css/hux-blog.css` and `css/hux-blog.min.css`
- **`js/`** — JavaScript source; `Gruntfile.js` compiles and minifies

## Comments

Comments use **Gitalk** (GitHub Issues–backed). Config is in `_config.yml` under `gitalk:`. The `clientSecret` is committed in plain text — treat it as already public.

## Deployment

Push to `master` branch → GitHub Pages auto-builds and deploys. No CI needed.

## Content Conventions

- **date 字段必须精确到分钟**：所有 reading 章节（`reading/*/` 下的 `.md` 文件）和 calvin 章节的 front matter `date` 字段格式固定为 `YYYY-MM-DD HH:MM`，不得只写日期。生成或修改这类文件时无需用户提醒，直接写入分钟级别时间戳。
- **date 字段必须使用真实时间**：新建文件时，`date` 字段必须使用当前的真实时间（通过 `date '+%Y-%m-%d %H:%M'` 获取），不得使用虚假或固定的时间戳。已有文件的时间不要修改。
- **date 是「这一章译完/做完的时刻」，不是「发布脚本跑起来的时刻」**：批量发布脚本若直接用 `date` 取当前时间，一次发布 N 章会写出 N 个一模一样的时间戳，等于没有信息。发布脚本必须从翻译侧记录的时间取值——翻译脚本每译完一章就把时刻落进 `<book>_raw/<book>/zh_meta.json`（`{章名: "YYYY-MM-DD HH:MM"}`），发布时按章查表。不要依赖文件 mtime：重出产物、`sed -i` 批量替换都会把它抹平。
- **新书卷的 layout 必须接上经文引用弹层**：`{% include scripture-popup.html container_selector=".<书>-content" accent="#xxx" vnum="#xxx" slide="down" %}`，只给中文页（该模块认的是中文书卷名，英文页挂了也匹配不上）。calvin / mhenry / hodge / owen / manton / bridges 都已接，新开一本书时容易漏。
