#!/usr/bin/env python3
"""prompts/ と data/ と examples/ の md から、GitHub Pages 用の index.html を作る。

使い方：python3 build.py
md を直したら、これを回してから push する。
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SITE = "https://a-tozak.github.io/fukai-wadai-prompts/"
TITLE = "「深いね」と言われる親子の話題プロンプト集"
DESC = "中学生の子どもと親が、夕食や車の中で少しだけ深い話をするためのAI用プロンプト集です。毎日3つの話題を、政治・経済・恋愛・友だち・成長・部活など10種類から日替わりで出します。"


# ---------- 小さな md 変換（このリポジトリで使う書き方だけ） ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def link(m):
        text, href = m.group(1), m.group(2)
        if href.endswith(".md") or href in ("LICENSE",):
            # リポジトリ内の md はページ内の節へ
            slug = Path(href).stem
            return f'<a href="#{anchor(slug)}">{text}</a>'
        return f'<a href="{href}" rel="noopener">{text}</a>'

    s = re.sub(r"\[(.+?)\]\((.+?)\)", link, s)
    s = re.sub(r"(?<![\"=>])(https?://[^\s<|）)]+)", r'<a class="code-url" href="\1" rel="noopener">\1</a>', s)
    return s


def anchor(stem):
    return "s-" + re.sub(r"[^0-9A-Za-z]+", "", stem.encode("utf-8").hex())[:16]


def md_to_html(text, h_shift=1):
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip() or ln.strip() == "---":
            i += 1
            continue
        if ln.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(prompt_box("\n".join(buf)))
            continue
        m = re.match(r"^(#{1,4}) (.+)", ln)
        if m:
            lv = min(len(m.group(1)) + h_shift, 6)
            out.append(f'<h{lv} class="ja-phrase">{inline(m.group(2))}</h{lv}>')
            i += 1
            continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head, body = rows[0], rows[1:]
            t = '<div class="tbl"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            for r in body:
                t += "<tr>" + "".join(f'<td data-h="{html.escape(h)}">{inline(c)}</td>' for h, c in zip(head, r)) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        if re.match(r"^\s*(- |\d+\. )", ln):
            ordered = bool(re.match(r"^\d+\. ", ln))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*(- |\d+\. )", lines[i]):
                raw = lines[i]
                depth = len(raw) - len(raw.lstrip())
                body = re.sub(r"^\s*(- |\d+\. )", "", raw)
                if depth and items:
                    items[-1] += f"<br><span class=\"sub\">{inline(body)}</span>"
                else:
                    items.append(inline(body))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{x}</li>" for x in items) + f"</{tag}>")
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```|\s*- |\d+\. |---)", lines[i]):
            buf.append(inline(lines[i]))
            i += 1
        out.append("<p>" + "<br>".join(buf) + "</p>")
    return "\n".join(out)


def prompt_box(code):
    return (
        '<div class="prompt"><div class="prompt-bar"><span>プロンプト（[ ] の中を書きかえて使います）</span>'
        '<button type="button" class="copy">コピーする</button></div>'
        f"<pre><code>{html.escape(code)}</code></pre></div>"
    )


# ---------- 問いの種を JS 用のデータに ----------
def seed_bank():
    bank, cur = {}, None
    for ln in (ROOT / "data/問いの種.md").read_text().splitlines():
        m = re.match(r"^## ([A-J]) (.+)", ln)
        if m:
            cur = m.group(1)
            bank[cur] = {"name": m.group(2), "qs": []}
            continue
        m = re.match(r"^\d+\. (.+)", ln)
        if m and cur:
            bank[cur]["qs"].append(m.group(1))
    return bank


def main():
    prompts = sorted((ROOT / "prompts").glob("*.md"))
    nav, sections = [], []
    for p in prompts:
        text = p.read_text()
        title = re.match(r"^# (.+)", text).group(1)
        body = re.sub(r"^# .+\n", "", text, count=1)
        aid = anchor(p.stem)
        nav.append(f'<li><a href="#{aid}">{html.escape(title)}</a></li>')
        sections.append(f'<section class="card" id="{aid}"><h3 class="ja-phrase">{html.escape(title)}</h3>{md_to_html(body, h_shift=2)}</section>')

    def page_part(path, h_shift=1):
        text = (ROOT / path).read_text()
        title = re.match(r"^# (.+)", text).group(1)
        body = re.sub(r"^# .+\n", "", text, count=1)
        return title, md_to_html(body, h_shift=h_shift)

    ex_t, ex_h = page_part("examples/出力例_土曜日.md", 2)
    src_t, src_h = page_part("data/参考資料.md", 1)
    seed_t, seed_h = page_part("data/問いの種.md", 1)
    bank = seed_bank()

    ld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": TITLE,
        "description": DESC,
        "url": SITE,
        "inLanguage": "ja",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "audience": {"@type": "Audience", "audienceType": "中学生の保護者"},
    }

    out = TEMPLATE
    for k, v in {
        "{{TITLE}}": html.escape(TITLE),
        "{{DESC}}": html.escape(DESC),
        "{{SITE}}": SITE,
        "{{LD}}": json.dumps(ld, ensure_ascii=False),
        "{{NAV}}": "\n".join(nav),
        "{{PROMPTS}}": "\n".join(sections),
        "{{EX_T}}": html.escape(ex_t),
        "{{EX}}": ex_h,
        "{{SEED_ID}}": anchor("問いの種"),
        "{{SEED}}": seed_h,
        "{{SRC_ID}}": anchor("参考資料"),
        "{{SRC}}": src_h,
        "{{EX_ID}}": anchor("出力例_土曜日"),
        "{{BANK}}": json.dumps(bank, ensure_ascii=False),
    }.items():
        out = out.replace(k, v)
    (ROOT / "index.html").write_text(out)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE}</loc></url>\n</urlset>\n"
    )
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
    print("index.html を書き出しました")


TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<meta name="description" content="{{DESC}}">
<link rel="canonical" href="{{SITE}}">
<meta property="og:type" content="website">
<meta property="og:title" content="{{TITLE}}">
<meta property="og:description" content="{{DESC}}">
<meta property="og:url" content="{{SITE}}">
<meta property="og:image" content="{{SITE}}og.png">
<meta property="og:locale" content="ja_JP">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{{LD}}</script>
<style>
:root{
  --ink:#15181c;--black:#0e0f11;--paper:#fff;--wash:#f6f6f4;--line:#e6e6e3;--sub:#666b73;--accent:#2b5fd9;--accent-wash:#eef3fd;
  --font-ja:"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic Medium",sans-serif;
  --font-mono:"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --ink:#e8e9eb;--black:#fff;--paper:#16181b;--wash:#1e2125;--line:#2e3238;--sub:#a3a8b0;--accent:#7ea2ff;--accent-wash:#1f2a44;
}}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font-ja);line-height:1.85;font-size:16px;-webkit-text-size-adjust:100%}
a{color:var(--accent)}
.wrap{max-width:820px;margin:0 auto;padding:0 16px}
.ja-phrase{word-break:auto-phrase;text-wrap:pretty}
.code-url{word-break:break-all}
header.hero{background:var(--wash);border-bottom:1px solid var(--line);padding:56px 0 40px}
.eyebrow{font-size:13px;color:var(--sub);letter-spacing:.08em;margin:0 0 10px}
h1{font-size:clamp(26px,5.4vw,38px);line-height:1.4;margin:0 0 16px;color:var(--black);word-break:auto-phrase;text-wrap:balance}
.lead{font-size:17px;margin:0}
h2{font-size:24px;line-height:1.5;margin:64px 0 16px;color:var(--black);padding-top:8px;border-top:2px solid var(--black)}
h3{font-size:20px;line-height:1.5;margin:0 0 12px;color:var(--black)}
h4{font-size:17px;margin:24px 0 8px}
h5,h6{font-size:16px;margin:20px 0 6px}
.steps{counter-reset:s;list-style:none;padding:0;margin:20px 0 0;display:grid;gap:12px}
.steps li{counter-increment:s;background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:14px 16px 14px 56px;position:relative}
.steps li::before{content:counter(s);position:absolute;left:16px;top:14px;width:28px;height:28px;border-radius:50%;background:var(--black);color:var(--paper);font-weight:700;display:grid;place-items:center;font-size:14px}
nav.toc ul{padding-left:1.2em;margin:8px 0}
.card{border-top:1px solid var(--line);padding:32px 0}
.prompt{border:1px solid var(--line);border-radius:10px;overflow:hidden;margin:16px 0;background:var(--wash)}
.prompt-bar{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 12px;border-bottom:1px solid var(--line);font-size:13px;color:var(--sub)}
.prompt pre{margin:0;padding:14px 16px;max-height:340px;overflow:auto;font-family:var(--font-mono);font-size:13px;line-height:1.7;white-space:pre-wrap;word-break:break-word}
button{font:inherit;cursor:pointer}
.copy{background:var(--black);color:var(--paper);border:0;border-radius:6px;padding:6px 14px;font-size:14px;white-space:nowrap}
.copy.done{background:var(--accent)}
.tbl{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left;vertical-align:top}
th{font-size:13px;color:var(--sub);font-weight:600}
@media (max-width:640px){
  .tbl table,.tbl tbody,.tbl tr,.tbl td{display:block;width:100%}
  .tbl thead{display:none}
  .tbl tr{border-bottom:1px solid var(--line);padding:8px 0}
  .tbl td{border:0;padding:4px 0}
  .tbl td::before{content:attr(data-h);display:block;font-size:12px;color:var(--sub)}
}
.sub{color:var(--sub)}
/* その場で引く */
.draw{background:var(--accent-wash);border-radius:12px;padding:24px 20px;margin:24px 0}
.draw p{margin:0 0 12px}
.draw-btn{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:10px 20px;font-size:16px;font-weight:600}
.draw-list{list-style:none;padding:0;margin:16px 0 0;display:grid;gap:10px}
.draw-list li{background:var(--paper);border-radius:8px;padding:12px 14px}
.draw-list .tag{display:inline-block;font-size:12px;color:var(--sub);margin-bottom:2px}
details{border-top:1px solid var(--line);padding:12px 0}
summary{cursor:pointer;font-weight:600}
footer{border-top:1px solid var(--line);margin-top:64px;padding:24px 0 48px;font-size:14px;color:var(--sub)}
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <p class="eyebrow">中学生の子どもと話す、AI用プロンプト集</p>
    <h1>「深いね」と言われる<br>親子の話題プロンプト集</h1>
    <p class="lead">AIが毎日3つの話題を「軽め」「中くらい」「深め」の順に出します。話題は、政治・社会、経済・お金、恋愛、友だち、成長、部活、将来、テクノロジー、生き方、家族の10種類から、曜日ごとに入れかわります。ChatGPT・Gemini・Claude のどれでも使えます。</p>
  </div>
</header>

<main class="wrap">
  <h2 class="ja-phrase">使い方</h2>
  <ol class="steps">
    <li>下の「00 最初に1回だけ設定する」のプロンプトをコピーし、AIの「プロジェクト」や「Gem」に貼ります。[ ] の中は自分の家庭に合わせて書きかえます。</li>
    <li>毎日、AIに「今日の3つ」と送ります。</li>
    <li>出てきた3つのうち、その日の子どもの様子に合う1つだけを話します。子どもが答えたら「なんでそう思ったの？」を一度だけ返します。</li>
  </ol>

  <div class="draw" id="draw">
    <p><strong>AIを使わずに、いまここで3つ引く</strong><br><span class="sub">今日の曜日の割り当てから、問いの種80問の中の3つを選びます。</span></p>
    <button type="button" class="draw-btn" id="drawBtn">今日の3つを引く</button>
    <ul class="draw-list" id="drawList"></ul>
  </div>

  <nav class="toc">
    <h2 class="ja-phrase">プロンプト一覧</h2>
    <ul>
{{NAV}}
      <li><a href="#{{EX_ID}}">出力例（土曜日）</a></li>
      <li><a href="#{{SEED_ID}}">問いの種（80問）</a></li>
      <li><a href="#{{SRC_ID}}">参考資料</a></li>
    </ul>
  </nav>

{{PROMPTS}}

  <h2 class="ja-phrase" id="{{EX_ID}}">{{EX_T}}</h2>
  {{EX}}

  <h2 class="ja-phrase" id="{{SEED_ID}}">問いの種（10カテゴリ×8問）</h2>
  <details><summary>80問をひらく</summary>
  {{SEED}}
  </details>

  <h2 class="ja-phrase" id="{{SRC_ID}}">参考資料（話題の元データ）</h2>
  {{SRC}}

  <h2 class="ja-phrase">大事にしていること</h2>
  <ul>
    <li><strong>親が答えを言わない</strong>ことを前提にしています。</li>
    <li>政治の話題では、特定の政党・政治家・宗教の良し悪しを言わず、両側の理由を並べるようにAIに指示しています。</li>
    <li>恋愛の話題では、子ども本人の恋愛を聞き出さず、物語や「もし友だちが〜だったら」から入るようにしています。</li>
    <li>テスト前や落ち込んでいる日は、話題を軽くします。話さない日があっても大丈夫です。</li>
  </ul>
</main>

<footer>
  <div class="wrap">
    <p>小学校教員の父親が、中学生の娘との会話のために作りました。<br>
    文章は <a href="https://creativecommons.org/licenses/by/4.0/deed.ja" rel="noopener">CC BY 4.0</a> です。出典を書けば、家庭・学校・研修で自由に使い、書きかえて配ることができます。参考資料に挙げた各資料の著作権は、それぞれの発行元にあります。<br>
    <a href="https://github.com/A-TOZAK/fukai-wadai-prompts" rel="noopener">GitHubのリポジトリ</a></p>
  </div>
</footer>

<script>
document.querySelectorAll('.copy').forEach(function(b){
  b.addEventListener('click',function(){
    var t=b.closest('.prompt').querySelector('code').textContent;
    var ok=function(){b.textContent='コピーしました';b.classList.add('done');setTimeout(function(){b.textContent='コピーする';b.classList.remove('done')},1800)};
    if(navigator.clipboard){navigator.clipboard.writeText(t).then(ok,function(){fallback(t);ok()})}else{fallback(t);ok()}
  });
});
function fallback(t){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy')}catch(e){}a.remove()}

var BANK={{BANK}};
var ROT={0:['J','E','A'],1:['F','B','I'],2:['D','A','H'],3:['E','C','B'],4:['F','J','A'],5:['C','G','I'],6:['H','D','G']};
var DAYS=['日','月','火','水','木','金','土'];
var shift=0;
function draw(){
  var d=new Date(),seed=d.getFullYear()*1000+Math.floor((d-new Date(d.getFullYear(),0,0))/864e5)+shift*7;
  var list=document.getElementById('drawList');list.innerHTML='';
  ROT[d.getDay()].forEach(function(k,i){
    var c=BANK[k],q=c.qs[(seed*(i+3)+i*5)%c.qs.length];
    var li=document.createElement('li');
    li.innerHTML='<span class="tag">'+c.name+'</span><br>'+q;
    list.appendChild(li);
  });
  document.getElementById('drawBtn').textContent=DAYS[d.getDay()]+'曜日の3つを引き直す';
  shift++;
}
document.getElementById('drawBtn').addEventListener('click',draw);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
