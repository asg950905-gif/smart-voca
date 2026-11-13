#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 기술 스택·설계 이유 설명용 발표자료(.pptx) 생성
# 파일 위치: ai-agent/scripts/발표자료생성.py
# 2026-11-09 갱신: 현재 UI·수치 반영, 이모지 제거(앱이 Lucide SVG 로 교체됨), 쪽번호 자동화, '향후 계획' 장표 추가
#
# 사용법: python ai-agent/scripts/발표자료생성.py [출력경로.pptx] [스크린샷폴더]
#   기본 출력: 바탕화면/smart-voca_기술설명_발표자료.pptx
#   스크린샷 폴더에 02_user_home.png, 04_study_back.png, 12_report_dark.png, 20_admin_dashboard.png, 13_mobile_home.png 가 있으면 12장(화면 미리보기)에,
#   design_desktop.png, design_mobile.png (design/index.html 캡처) 가 있으면 16장(향후 계획)에 삽입. 없으면 '(스크린샷 없음)' 칸으로 남는다
# 내용을 고치고 싶으면 이 파일의 SLIDES 정의(텍스트)만 수정하고 다시 실행한다.

import sys
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

FONT = 'Malgun Gothic'
INDIGO, INDIGO_DARK, INDIGO_SOFT = RGBColor(0x5B, 0x5B, 0xD6), RGBColor(0x46, 0x46, 0xC0), RGBColor(0xEC, 0xEB, 0xFF)
TEAL, TEAL_SOFT = RGBColor(0x0E, 0x9F, 0x8E), RGBColor(0xDC, 0xF5, 0xF1)
INK, MUTED, BG = RGBColor(0x1B, 0x1F, 0x3B), RGBColor(0x6B, 0x71, 0x94), RGBColor(0xF6, 0xF7, 0xFB)
WHITE, BORDER = RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xE4, 0xE7, 0xF2)
RED, RED_SOFT = RGBColor(0xE5, 0x48, 0x4D), RGBColor(0xFD, 0xEA, 0xEA)
GREEN, GREEN_SOFT = RGBColor(0x12, 0xA3, 0x7A), RGBColor(0xE0, 0xF6, 0xEE)
AMBER_SOFT = RGBColor(0xFF, 0xF3, 0xDC)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 17


# ---------------------------------------------------------------- 도우미
def set_font(run, size, bold=False, color=INK):
    run.font.size, run.font.bold, run.font.name = Pt(size), bold, FONT
    run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()  # 한글 글리프용 East Asian 글꼴도 지정
    for tag in ('a:ea', 'a:cs'):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set('typeface', FONT)


def add_text(slide, x, y, w, h, text, size=16, bold=False, color=INK, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, line_spacing=1.15):
    """text 는 문자열 또는 (문자열, 옵션dict) 단락 리스트."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    paragraphs = text if isinstance(text, list) else [text]
    for i, item in enumerate(paragraphs):
        content, opt = (item, {}) if isinstance(item, str) else item
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment, p.line_spacing = opt.get('align', align), line_spacing
        p.space_after = Pt(opt.get('after', 4))
        run = p.add_run()
        run.text = content
        set_font(run, opt.get('size', size), opt.get('bold', bold), opt.get('color', color))
    return box


def add_rect(slide, x, y, w, h, fill=WHITE, line=BORDER, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.shadow.inherit = False
    return s


def card(slide, x, y, w, h, heading=None, body=None, fill=WHITE, accent=INDIGO, body_size=14, head_size=16):
    add_rect(slide, x, y, w, h, fill=fill)
    cy = y + 0.15
    if heading:
        add_text(slide, x + 0.2, cy, w - 0.4, 0.4, heading, size=head_size, bold=True, color=accent)
        cy += 0.5
    if body:
        add_text(slide, x + 0.2, cy, w - 0.4, h - (cy - y) - 0.1, body, size=body_size, color=INK, line_spacing=1.2)


def bullets(items, size=15, color=INK):
    return [("•  " + t, {'size': size, 'color': color, 'after': 6}) for t in items]


def tag(slide, x, y, text, fill=INDIGO_SOFT, color=INDIGO_DARK, w=None, size=12):
    w = w or (0.4 + 0.19 * len(text))  # 한글은 글자 폭이 넓어 여유를 둔다
    s = add_rect(slide, x, y, w, 0.34, fill=fill, line=None, radius=0.5)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text; set_font(r, size, True, color)


def new_slide(title, kicker=None, notes=''):
    number = len(prs.slides) + 1   # 쪽번호는 자동 (장표 순서가 바뀌어도 번호가 틀리지 않게)
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid(); s.background.fill.fore_color.rgb = BG
    add_rect(s, 0, 0, 0.18, 7.5, fill=INDIGO, line=None, shape=MSO_SHAPE.RECTANGLE)
    if kicker:
        add_text(s, 0.6, 0.35, 8, 0.3, kicker, size=12, bold=True, color=INDIGO)
    add_text(s, 0.6, 0.62, 12, 0.8, title, size=30, bold=True)
    add_text(s, 11.8, 7.0, 1.3, 0.3, f"{number} / {TOTAL}", size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    add_text(s, 0.6, 7.0, 6, 0.3, "smart-voca · 기술 스택과 설계 이유", size=11, color=MUTED)
    s.notes_slide.notes_text_frame.text = notes.strip()
    return s


def table(slide, x, y, widths, rows, size=13, row_h=0.5, header_fill=INDIGO):
    n_rows, n_cols = len(rows), len(widths)
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y), Inches(sum(widths)), Inches(row_h * n_rows))
    tbl = shape.table
    tblPr = shape._element.graphic.graphicData.tbl.tblPr
    tblPr.set('firstRow', '0'); tblPr.set('bandRow', '0')  # 기본 스타일 줄무늬 제거 (직접 색을 지정)
    for i, w in enumerate(widths):
        tbl.columns[i].width = Inches(w)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (WHITE if r % 2 else RGBColor(0xF1, 0xF2, 0xFA))
            tf = cell.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            run = p.add_run(); run.text = value
            set_font(run, size, bold=(r == 0 or c == 0), color=WHITE if r == 0 else INK)
    return tbl


def arrow(slide, x, y, w=0.45, h=0.4, color=INDIGO):
    a = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    a.fill.solid(); a.fill.fore_color.rgb = color; a.line.fill.background()
    return a


def picture(slide, path, x, y, w, h, crop=False):
    """비율을 유지하며 (x,y,w,h) 칸 안에 맞춰 넣는다. crop=True 면 칸 비율로 위쪽 기준 잘라 칸을 꽉 채운다."""
    if not path or not Path(path).exists():
        add_rect(slide, x, y, w, h, fill=WHITE)
        add_text(slide, x, y + h / 2 - 0.2, w, 0.4, "(스크린샷 없음)", size=12, color=MUTED, align=PP_ALIGN.CENTER)
        return
    from PIL import Image
    import tempfile
    img = Image.open(path)
    if crop:
        target = w / h
        iw0, ih0 = img.size
        if iw0 / ih0 > target:   # 너무 넓음 → 좌우를 자름
            nw = int(ih0 * target); left = (iw0 - nw) // 2
            img = img.crop((left, 0, left + nw, ih0))
        else:                    # 너무 높음 → 아래를 자름 (화면 위쪽이 가장 정보가 많음)
            img = img.crop((0, 0, iw0, int(iw0 / target)))
        tmp = Path(tempfile.mkdtemp()) / 'crop.png'
        img.save(tmp); path = tmp
    iw, ih = img.size
    scale = min(w / iw, h / ih)
    pw, ph = iw * scale, ih * scale
    add_rect(slide, x + (w - pw) / 2 - 0.03, y + (h - ph) / 2 - 0.03, pw + 0.06, ph + 0.06, fill=WHITE, radius=0.02)
    slide.shapes.add_picture(str(path), Inches(x + (w - pw) / 2), Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


# ---------------------------------------------------------------- 경로
desktop = Path.home() / 'OneDrive' / 'Desktop'
if not desktop.exists():
    desktop = Path.home() / 'Desktop'
out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else desktop / 'smart-voca_기술설명_발표자료.pptx'
shots = Path(sys.argv[2]) if len(sys.argv) > 2 else None
shot = lambda name: (shots / name) if shots else None

# ================================================================ 1. 표지
s = prs.slides.add_slide(BLANK)
s.background.fill.solid(); s.background.fill.fore_color.rgb = INDIGO_DARK
add_rect(s, 8.6, -1.2, 6.5, 6.5, fill=INDIGO, line=None, shape=MSO_SHAPE.OVAL)
add_rect(s, 10.4, 3.9, 4.2, 4.2, fill=RGBColor(0x56, 0x56, 0xCF), line=None, shape=MSO_SHAPE.OVAL)
add_text(s, 0.9, 1.6, 9, 0.5, "개인 역량 점검 발표", size=18, bold=True, color=RGBColor(0xC9, 0xC9, 0xFF))
add_text(s, 0.9, 2.2, 9.5, 1.4, "스마트 보카", size=60, bold=True, color=WHITE)
add_text(s, 0.9, 3.55, 9.5, 1.0, "웹 기반 영어 단어 학습 플랫폼\n기술 스택과 그렇게 선택한 이유", size=24, color=WHITE, line_spacing=1.3)
add_text(s, 0.9, 5.7, 9, 0.4, "발표자: ○○○  ·  smart-voca  ·  2026.11", size=15, color=RGBColor(0xC9, 0xC9, 0xFF))
s.notes_slide.notes_text_frame.text = (
    "안녕하세요. 제가 개인으로 진행한 '스마트 보카' 프로젝트를 소개하겠습니다.\n"
    "오늘은 기능 소개보다 '어떤 기술을 썼고, 왜 그렇게 선택했는지'에 초점을 맞춰 설명드리겠습니다.\n"
    "[준비] 표지의 발표자 이름(○○○)을 본인 이름으로 바꾸세요.")

# ================================================================ 2. 개요
s = new_slide("프로젝트 한눈에 보기", "OVERVIEW", notes=(
    "스마트 보카는 영어 단어를 매일 학습하고 시험으로 점검하는 웹 서비스입니다.\n"
    "사용자는 가입 후 플립카드로 학습하고 시험을 봅니다. 관리자는 단어와 사용자를 관리하고 전체 통계를 봅니다.\n"
    "숫자로 보면 화면 13개, 역할 2개, 자동 테스트 27개, 파이썬 코드 약 2,000줄(테스트 포함, 앱 코드만 약 1,600줄)입니다.\n"
    "학습하면 XP와 레벨이 쌓이고 주간 리그 순위가 매겨지는 게임화 요소와, 단어 발음 듣기도 있습니다.\n"
    "핵심은 '사용자별로 기록이 분리되는 다중 사용자 구조'이고, 이 때문에 데이터 저장 방식을 바꿨습니다(6번 슬라이드)."))
add_text(s, 0.6, 1.45, 12, 0.5, "매일 10분 단어 암기 → 시험으로 점검 → 통계로 약점 확인", size=20, color=MUTED)
for i, (num, label) in enumerate([("13", "화면 (템플릿)"), ("2", "역할 (사용자 / 관리자)"), ("27", "자동 테스트"), ("≈2,000", "줄 Python (테스트 포함)")]):
    x = 0.6 + i * 3.1
    add_rect(s, x, 2.2, 2.9, 1.5, fill=WHITE)
    add_text(s, x, 2.3, 2.9, 0.8, num, size=40, bold=True, color=INDIGO, align=PP_ALIGN.CENTER)
    add_text(s, x, 3.15, 2.9, 0.4, label, size=14, color=MUTED, align=PP_ALIGN.CENTER)
card(s, 0.6, 4.05, 5.95, 2.75, "사용자 화면", bullets(["회원가입·로그인 + 랜딩의 빈칸 퀴즈 체험", "플립카드 학습, 발음 듣기(TTS)", "시험: 4지선다 · OX · 단답 · 빈칸 채우기", "XP·레벨·주간 리그로 학습 동기 부여", "통계 차트, 다크모드, 모바일 대응"], 14))
card(s, 6.75, 4.05, 5.95, 2.75, "관리자 화면", bullets(["전체 사용자 활동·점수 대시보드", "단어 추가·수정·삭제, CSV 가져오기/내보내기", "사용자 역할·활성화·비밀번호 관리", "시험·학습 전역 설정"], 15), accent=TEAL)

# ================================================================ 3. 아키텍처
s = new_slide("전체 구조: 4개 계층으로 책임을 나눴습니다", "ARCHITECTURE", notes=(
    "구조는 4계층입니다. 브라우저, web, business, data 순서입니다.\n"
    "web 계층은 HTTP 요청을 받고 권한을 확인합니다. business 계층은 학습·시험 같은 업무 규칙만 담고, HTTP나 화면을 전혀 모릅니다. "
    "data 계층은 SQLite 접속을 한곳에 모았습니다.\n"
    "이렇게 나눈 이유는 두 가지입니다. 첫째, 계층별로 설명과 수정이 쉽습니다. 둘째, 화면 없이도 business를 테스트할 수 있습니다.\n"
    "아래 예시처럼 시험 답안 하나가 제출되면 이 계층을 위에서 아래로 지나갑니다."))
layers = [
    ("브라우저", "templates/ · static/", "Jinja2 화면\nVanilla JS · Chart.js", INDIGO_SOFT, INDIGO_DARK),
    ("web 계층", "src/web/ · app.py", "Blueprint 라우트\n권한 · CSRF · 보안", RGBColor(0xE2, 0xE8, 0xFF), INDIGO_DARK),
    ("business 계층", "src/business/", "인증 · 단어 · 학습 · 시험\n통계 · 게임화(XP·리그)\n(순수 로직)", TEAL_SOFT, TEAL),
    ("data 계층", "src/data/", "SQLite (표준 sqlite3)\n트랜잭션 · 스키마", GREEN_SOFT, GREEN),
]
for i, (name, path, desc, fill, col) in enumerate(layers):
    x = 0.6 + i * 3.15
    add_rect(s, x, 1.75, 2.75, 2.7, fill=fill, line=None)
    add_text(s, x, 1.9, 2.75, 0.45, name, size=19, bold=True, color=col, align=PP_ALIGN.CENTER)
    add_text(s, x, 2.4, 2.75, 0.4, path, size=12, color=MUTED, align=PP_ALIGN.CENTER)
    add_text(s, x + 0.15, 2.95, 2.45, 1.3, desc, size=15, color=INK, align=PP_ALIGN.CENTER, line_spacing=1.3)
    if i < 3:
        arrow(s, x + 2.78, 2.9, 0.36, 0.4, INDIGO)
add_text(s, 0.6, 4.75, 12, 0.4, "예) 시험 답안 제출 한 번이 지나가는 길", size=16, bold=True, color=INDIGO)
steps = ["fetch POST\n/api/test/answer", "CSRF 검사\n로그인 확인", "TestEngine\n.grade_answer", "test_sessions\nJSON 갱신", "채점 결과\nJSON 응답"]
for i, t in enumerate(steps):
    x = 0.6 + i * 2.5
    add_rect(s, x, 5.25, 2.15, 1.1, fill=WHITE)
    add_text(s, x, 5.3, 2.15, 1.0, t, size=13, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.2)
    if i < 4:
        arrow(s, x + 2.17, 5.6, 0.3, 0.3, MUTED)

# ================================================================ 4. 기술 스택
s = new_slide("기술 스택과 선택 이유 (요약)", "TECH STACK", notes=(
    "사용한 기술과 이유를 한 장으로 정리했습니다.\n"
    "공통 원칙은 '의존성을 최소화하고, 실행이 쉽고, 제가 원리를 설명할 수 있는 것'을 골랐다는 점입니다.\n"
    "requirements.txt에는 Flask, Werkzeug, Jinja2 세 줄뿐입니다. DB는 파이썬 표준 라이브러리 sqlite3를 쓰고, 화면은 Node 같은 빌드 도구 없이 Flask 하나로 실행됩니다.\n"
    "각 항목의 자세한 비교는 다음 슬라이드들에서 설명드립니다."))
table(s, 0.6, 1.6, [2.0, 3.3, 7.2], [
    ["영역", "기술", "선택 이유"],
    ["언어", "Python 3", "문법이 단순하고 데이터·교육용으로 널리 쓰임. 표준 라이브러리가 풍부함"],
    ["웹 프레임워크", "Flask 3", "경량·구조 자유. 계층 설계를 직접 하며 원리를 설명하기 좋음"],
    ["데이터베이스", "SQLite (sqlite3)", "추가 설치 없음, 파일 1개, 백업·시연 환경 이동이 쉬움"],
    ["화면", "Jinja2 + Vanilla JS + CSS", "빌드 도구 없이 단일 실행. 코드가 곧 동작 원리"],
    ["차트", "Chart.js 4 (로컬 파일)", "가볍고, 인터넷이 없는 시연 환경에서도 동작"],
    ["아이콘", "Lucide SVG 스프라이트 (로컬)", "OS마다 달라 보이는 이모지 대신 SVG, 테마 색 적용"],
    ["인증·보안", "세션 + Werkzeug 해시", "서버 렌더링 웹앱에 적합, 계정 비활성화 시 즉시 로그아웃 가능"],
    ["테스트", "pytest, Playwright(Edge)", "API 전 경로 자동 검증 + 브라우저 리허설로 화면 확인"],
], size=13, row_h=0.55)
add_text(s, 0.6, 6.6, 12, 0.35, "requirements.txt = Flask · Werkzeug · Jinja2  (3줄)", size=13, color=MUTED)

# ================================================================ 5. 왜 Flask
s = new_slide("왜 Flask인가? (Django·FastAPI와 비교)", "TECH DECISION 1", notes=(
    "웹 프레임워크 후보는 Flask, Django, FastAPI였습니다.\n"
    "Django는 인증·관리자 화면·ORM이 다 들어 있어 빠르지만, 이번 프로젝트의 목적은 인증과 관리자 기능을 직접 설계하며 원리를 이해하는 것이었습니다. 규모에도 과합니다.\n"
    "FastAPI는 API 서버에 강하지만, 저는 서버가 HTML을 만들어 주는 화면 중심 서비스라 Jinja2 템플릿과 세션이 자연스러운 Flask가 맞았습니다.\n"
    "Flask를 선택한 초기 설계 문서의 이유는 '경량이고 배우기 쉽다'였고, 지금은 그 외에 계층 구조를 직접 결정할 수 있어서라는 점을 추가로 말씀드릴 수 있습니다.\n"
    "솔직한 단점도 있습니다. 구조를 규율하지 않으면 코드가 흐트러지는데, 그래서 Blueprint와 앱 팩토리로 구조를 잡았습니다."))
card(s, 0.6, 1.7, 3.95, 4.1, "Flask  (선택)", bullets(["마이크로 프레임워크: 필요한 것만 직접 조립", "Jinja2 템플릿·세션이 기본 내장", "구조를 직접 설계 → 원리를 설명 가능", "의존성이 적어 배포·시연이 가벼움"], 16), fill=INDIGO_SOFT)
card(s, 4.7, 1.7, 3.95, 4.1, "Django", bullets(["ORM·인증·관리자 화면 내장 (빠름)", "하지만 이번 목적은 인증·관리자를 직접 설계해 이해하는 것", "프로젝트 규모 대비 과함"], 16), accent=MUTED)
card(s, 8.8, 1.7, 3.95, 4.1, "FastAPI", bullets(["API(JSON) 서버·비동기에 강점", "우리는 서버가 HTML을 만드는 화면 중심 구조", "템플릿·세션을 따로 구성해야 함"], 16), accent=MUTED)
add_rect(s, 0.6, 6.0, 12.15, 0.8, fill=AMBER_SOFT, line=None)
add_text(s, 0.8, 6.05, 11.8, 0.7, "단점과 보완: 구조를 규율하지 않으면 코드가 흐트러진다 → Blueprint로 기능 분리, 앱 팩토리(create_app)로 테스트마다 새 앱 생성",
         size=14, anchor=MSO_ANCHOR.MIDDLE)

# ================================================================ 6. 왜 SQLite
s = new_slide("왜 CSV에서 SQLite로 바꿨나? (ADR-001)", "TECH DECISION 2", notes=(
    "가장 중요한 설계 결정입니다. 원래는 CSV와 JSON 파일에 저장했습니다.\n"
    "문제는 두 가지였습니다. 첫째, 학습·시험 상태를 서버의 전역 변수 하나에 두었기 때문에 두 사람이 동시에 시험을 보면 문제가 섞일 수 있었습니다. "
    "둘째, 한 파일을 여러 요청이 동시에 덮어쓰면 기록이 깨지고, 사용자별·전체 통계를 계산하기 어려웠습니다.\n"
    "대안은 CSV 유지, SQLite, PostgreSQL이었습니다. PostgreSQL은 기능은 좋지만 소규모 팀 테스트에 설치·운영 부담이 큽니다. "
    "SQLite는 파이썬 표준 라이브러리만으로 되고 파일 하나라 시연 환경 이동이 쉬워 선택했습니다.\n"
    "이 결정을 ADR, 즉 '결정 기록'으로 문서화했고, 나중에 DB를 바꿀 때를 대비해 DB 접근을 data 계층 한 곳에 모았습니다."))
card(s, 0.6, 1.7, 4.0, 2.2, "변경 전 (문제)", bullets(["전역 변수 하나를 모든 요청이 공유", "동시 접속 시 시험·기록이 섞임", "CSV 동시 쓰기 충돌, 통계 집계 불편"], 14), fill=RED_SOFT, accent=RED)
card(s, 0.6, 4.1, 4.0, 2.7, "변경 후", bullets(["사용자별 상태를 DB에 저장", "시험 진행 상태도 test_sessions 테이블", "SQL로 사용자·전체 통계를 바로 집계"], 14), fill=GREEN_SOFT, accent=GREEN)
table(s, 4.9, 1.7, [2.4, 1.95, 1.95, 1.55], [
    ["비교", "CSV/JSON 유지", "SQLite  (선택)", "PostgreSQL"],
    ["동시 접속 안전성", "낮음", "중간 이상(WAL)", "높음"],
    ["설치·운영", "없음", "없음 (표준)", "서버 설치 필요"],
    ["통계 집계", "코드로 직접", "SQL 한 줄", "SQL 한 줄"],
    ["백업·이동", "파일 여러 개", "파일 1개", "덤프/복원"],
    ["이번 규모 적합", "부족", "적합", "과함"],
], size=13, row_h=0.66)
add_text(s, 4.9, 5.85, 7.9, 0.9, "결정 근거: 설치 없이 다중 사용자 요구를 만족하는 가장 단순한 선택. 접근 코드를 src/data 한 곳에 모아 서버형 DB로 교체할 여지를 남김.",
         size=14, color=MUTED, line_spacing=1.25)

# ================================================================ 7. 데이터 모델
s = new_slide("데이터 모델: 공용 단어장 + 사용자별 학습 상태", "DATA MODEL", notes=(
    "테이블은 7개입니다. 핵심 아이디어는 '단어는 공용, 학습 상태는 사용자별'입니다.\n"
    "words 테이블은 관리자가 관리하는 공용 단어장이고, user_word_stats가 사용자와 단어를 잇는 테이블로 사용자마다 정답·오답 횟수와 복습 가중치를 따로 가집니다.\n"
    "그래서 같은 단어도 사용자마다 다르게 출제됩니다. 사용자나 단어를 삭제하면 외래키 CASCADE로 관련 기록이 함께 지워집니다.\n"
    "시험 진행 상태는 test_sessions에 사용자당 한 줄로 저장해, 동시에 시험을 봐도 섞이지 않습니다."))
add_rect(s, 5.2, 2.6, 2.9, 1.6, fill=INDIGO, line=None)
add_text(s, 5.2, 2.7, 2.9, 0.45, "users", size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
add_text(s, 5.25, 3.2, 2.8, 1.0, "username · password_hash\nrole · active\ndaily_target · theme", size=12, color=WHITE, align=PP_ALIGN.CENTER)
add_rect(s, 0.6, 1.75, 3.6, 1.35, fill=WHITE)
add_text(s, 0.6, 1.8, 3.6, 0.4, "words  (공용)", size=16, bold=True, color=TEAL, align=PP_ALIGN.CENTER)
add_text(s, 0.65, 2.25, 3.5, 0.8, "english(UNIQUE) · korean\npart_of_speech · example", size=12, color=MUTED, align=PP_ALIGN.CENTER)
add_rect(s, 0.6, 3.75, 3.6, 1.6, fill=WHITE)
add_text(s, 0.6, 3.8, 3.6, 0.4, "user_word_stats", size=16, bold=True, color=INDIGO, align=PP_ALIGN.CENTER)
add_text(s, 0.65, 4.25, 3.5, 1.1, "PK(user_id, word_id)\nweight · success_count\nfail_count · last_studied", size=12, color=MUTED, align=PP_ALIGN.CENTER)
for (x, y, name, desc) in [(9.1, 1.75, "study_logs", "date · words_count\ncorrect_count · success_rate"),
                           (9.1, 3.6, "test_logs", "date · mode · format\ntotal_problems · score"),
                           (9.1, 5.45, "test_sessions", "user_id(PK) · state_json\n(진행 중인 시험 1개)")]:
    add_rect(s, x, y, 3.65, 1.4, fill=WHITE)
    add_text(s, x, y + 0.05, 3.65, 0.4, name, size=16, bold=True, color=INDIGO, align=PP_ALIGN.CENTER)
    add_text(s, x + 0.05, y + 0.5, 3.55, 0.8, desc, size=12, color=MUTED, align=PP_ALIGN.CENTER)
down = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(2.15), Inches(3.15), Inches(0.4), Inches(0.55))
down.fill.solid(); down.fill.fore_color.rgb = TEAL; down.line.fill.background()
left = s.shapes.add_shape(MSO_SHAPE.LEFT_ARROW, Inches(4.3), Inches(3.9), Inches(0.8), Inches(0.4))
left.fill.solid(); left.fill.fore_color.rgb = INDIGO; left.line.fill.background()
arrow(s, 8.2, 3.1, 0.8, 0.4, INDIGO)
add_rect(s, 5.2, 4.9, 3.6, 1.9, fill=INDIGO_SOFT, line=None)
add_text(s, 5.3, 4.95, 3.4, 1.8, [("설계 포인트", {'bold': True, 'color': INDIGO_DARK, 'size': 14}),
         ("• 단어는 공용, 학습 상태는 사용자별", {'size': 12}), ("• ON DELETE CASCADE로 기록 정리", {'size': 12}),
         ("• 모든 SQL은 ? 자리표시자 (인젝션 방지)", {'size': 12}), ("• 트랜잭션으로 통계+로그를 한 번에", {'size': 12}), ("• XP·레벨은 로그에서 계산 (테이블 없음)", {'size': 12})], line_spacing=1.1)

# ================================================================ 8. 핵심 로직
s = new_slide("핵심 로직: 학습 선택과 시험 출제", "CORE LOGIC", notes=(
    "두 가지 핵심 로직을 설명드리겠습니다.\n"
    "첫째 학습 단어 선택입니다. 오답이 많은 단어를 먼저, 그다음 아직 안 본 단어, 오래전에 본 단어, 마지막으로 무작위 순서로 고릅니다. "
    "정답이면 가중치를 1 줄이고 오답이면 1 늘리는 간단한 간격 반복 원리입니다. 한계는 망각 곡선을 반영하지 않는다는 점이고, SM-2 같은 알고리즘이 향후 과제입니다.\n"
    "둘째 시험입니다. 가장 중요한 점은 정답을 서버만 가지고 있다는 것입니다. 문제를 보낼 때 정답을 빼고, 채점한 뒤에만 알려줍니다. "
    "개발자도구로 정답을 훔쳐볼 수 없습니다. 그리고 시험 상태를 DB에 저장해서 동시 응시를 지원합니다.\n"
    "형식은 4지선다·OX·단답에 더해 예문에서 정답 단어를 가리는 빈칸 채우기가 있습니다. 예문에 단어가 변형되어 나오면(includes 등) 4지선다로 대체되는 한계가 있어 이슈 #6으로 남겼습니다.\n"
    "맞힌 만큼 XP가 쌓이는데, XP와 레벨은 별도 테이블 없이 학습·시험 기록에서 계산합니다."))
card(s, 0.6, 1.7, 6.0, 5.1, "오늘의 학습 단어 선택", [
    ("정렬 우선순위", {'bold': True, 'size': 16, 'color': INDIGO_DARK}),
    ("1) 오답 가중치(weight) 높은 단어", {'size': 16}), ("2) 아직 학습하지 않은 단어", {'size': 16}),
    ("3) 오래전에 학습한 단어  4) 무작위", {'size': 16, 'after': 12}),
    ("가중치 규칙", {'bold': True, 'size': 16, 'color': INDIGO_DARK}),
    ("정답 → weight −1 (최소 0)", {'size': 16, 'color': GREEN}), ("오답 → weight +1", {'size': 16, 'color': RED, 'after': 12}),
    ("의미: 틀린 단어를 더 자주 복습시키는 간단한 간격 반복", {'size': 15, 'color': MUTED}),
    ("한계: 망각 곡선 미반영 → SM-2 등은 향후 과제", {'size': 15, 'color': MUTED, 'after': 10}),
    ("XP: 학습 정답 +10·오답 +2, 시험 정답 +15·오답 +3 → 기록에서 레벨·주간 리그 계산", {'size': 15, 'color': TEAL})])
card(s, 6.8, 1.7, 5.95, 5.1, "시험 출제·채점", [
    ("형식 4가지: 4지선다 · OX · 단답 · 빈칸  /  방향: 영→한 · 한→영 · 혼합", {'size': 15, 'color': MUTED, 'after': 10}),
    ("정답은 서버에만 존재", {'bold': True, 'size': 18, 'color': TEAL}),
    ("문제 전송 시 정답 제외 → 채점 후에만 공개", {'size': 16, 'after': 10}),
    ("시험 상태를 DB(test_sessions)에 저장", {'bold': True, 'size': 18, 'color': TEAL}),
    ("전역 변수 방식은 동시 응시 시 문제가 섞였음", {'size': 16, 'after': 10}),
    ("보기를 못 만들면 자동 대체", {'bold': True, 'size': 18, 'color': TEAL}),
    ("단어가 부족하면 OX·단답으로, 빈칸형은 변형 단어면 4지선다로(#6)", {'size': 16, 'after': 10}),
    ("종료 시 트랜잭션으로 기록·통계 반영", {'bold': True, 'size': 18, 'color': TEAL})], accent=TEAL)

# ================================================================ 9. 보안
s = new_slide("보안: 어떤 위협에 어떻게 대응했나", "SECURITY", notes=(
    "다중 사용자 서비스라 보안을 처음부터 넣었습니다. 위협과 대응을 짝지어 말씀드리겠습니다.\n"
    "비밀번호는 해시로 저장해 원문을 알 수 없고, 로그인 실패 메시지는 아이디 존재 여부를 알려주지 않습니다. "
    "CSRF는 세션 토큰을 모든 상태 변경 요청에서 검증합니다. 무차별 대입은 5회 실패 시 5분 잠급니다.\n"
    "권한은 화면과 API 모두 서버에서 검사합니다. 버튼을 숨기는 것만으로는 막을 수 없기 때문입니다. "
    "또 매 요청마다 DB로 사용자 상태를 확인해서, 관리자가 계정을 비활성화하면 이미 로그인된 사용자도 바로 로그아웃됩니다.\n"
    "XSS는 서버 템플릿 자동 이스케이프와 JS의 esc() 함수로 막고, 실제로 스크립트가 든 단어를 넣어 실행되지 않음을 브라우저로 확인했습니다.\n"
    "한계도 말씀드리면, 로그인 잠금은 서버 메모리라 서버를 여러 개 띄우면 공유되지 않습니다."))
table(s, 0.6, 1.5, [3.6, 5.2, 3.35], [
    ["위협", "대응", "구현 위치"],
    ["비밀번호 유출", "해시 저장, 로그인 실패 메시지 통일", "AuthManager"],
    ["CSRF", "세션 토큰을 폼·헤더로 검증", "security.check_csrf"],
    ["무차별 대입", "같은 IP+아이디 5회 실패 시 5분 잠금", "security.login_blocked"],
    ["권한 우회", "화면·API 모두 서버에서 역할 검사(401/403)", "@login_required / @admin_required"],
    ["이미 로그인한 계정 비활성화", "매 요청 DB 확인 후 즉시 세션 무효화", "app.load_user"],
    ["XSS (스크립트 삽입)", "Jinja 자동 이스케이프 + JS esc()", "templates · main.js"],
    ["오픈 리다이렉트·세션 고정", "next는 상대경로만, 로그인 시 세션 재생성", "auth_routes"],
    ["업로드·정보 노출", "CSV 2MB·형식 제한, 보안 헤더, 일반 오류 메시지", "admin_routes · app.py"],
], size=12, row_h=0.5)
add_text(s, 0.6, 6.4, 12.1, 0.5, "한계: 로그인 잠금은 서버 메모리 기반 → 다중 프로세스 배포 시 DB/Redis로 이전 필요. HTTPS 배포 시 SESSION_COOKIE_SECURE=1.", size=13, color=MUTED)

# ================================================================ 10. 사용자 vs 관리자
s = new_slide("사용자 화면과 관리자 화면의 분리", "ROLES", notes=(
    "역할은 user와 admin 두 가지이고, 가입하는 사람은 항상 일반 사용자입니다. 관리자 승격은 관리자만 할 수 있습니다.\n"
    "관리자 영역은 /admin 아래에 모았고, 화면 색을 청록색과 ADMIN 배지로 달리해서 어느 영역인지 바로 보이게 했습니다.\n"
    "관리자에게도 안전장치를 뒀습니다. 자기 자신의 역할 변경, 비활성화, 삭제는 막아서 관리자가 0명이 되는 사고를 방지합니다.\n"
    "리허설에서 일반 사용자가 /admin에 들어가면 403 화면에 관리자 메뉴가 보이는 문제를 발견해 고쳤고, 회귀 테스트로 남겼습니다."))
table(s, 0.6, 1.65, [2.0, 5.0, 5.15], [
    ["", "사용자  (indigo)", "관리자  (teal · ADMIN 배지)"],
    ["진입", "/ (로그아웃 시 랜딩) · /study · /test · /league · /report · /settings", "/admin/  대시보드 · words · users · settings"],
    ["핵심 기능", "플립카드 학습, 시험, 주간 리그, 개인 통계, 설정", "전체 활동·점수 통계, 단어 CRUD·CSV, 사용자 관리, 전역 설정"],
    ["데이터 범위", "내 기록만", "전체 사용자 집계 (개별 기록 삭제 권한 포함)"],
    ["권한 검사", "@login_required (비로그인 → 로그인 화면/401)", "@admin_required (일반 사용자 → 403)"],
], size=14, row_h=0.68)
card(s, 0.6, 5.4, 5.95, 1.4, "관리자 안전장치", ["자기 자신의 역할 변경·비활성화·삭제 불가 (관리자 0명 방지)"], body_size=14, accent=TEAL)
card(s, 6.75, 5.4, 5.95, 1.4, "리허설에서 발견·수정", ["일반 사용자의 403 화면에 관리자 메뉴가 보이던 문제 → 회귀 테스트 추가"], body_size=14)

# ================================================================ 11. UI/UX
s = new_slide("UI/UX: 무엇을, 왜 그렇게 만들었나", "UI / UX", notes=(
    "화면은 React 같은 프레임워크 없이 Vanilla JS와 CSS로 만들었습니다. 13개 화면 규모에서는 빌드 도구가 오히려 복잡도만 늘리기 때문입니다.\n"
    "디자인은 색·간격·모서리를 CSS 변수, 즉 디자인 토큰으로 정의했습니다. 그래서 다크모드는 변수 값만 덮어써서 구현됩니다. 관리자 영역의 청록색도 같은 원리입니다.\n"
    "모바일에서는 상단 메뉴 대신 하단 탭바를 보여줍니다. 엄지로 누르기 쉽기 때문입니다.\n"
    "키보드 단축키와 포커스 표시 등 접근성도 챙겼습니다. 다만 스킵 링크·aria-live·색 대비 검증은 아직 부족해서 이슈 #4로 남겼습니다. 아이콘은 이모지 대신 Lucide SVG를 로컬 파일로 넣었고, 차트 라이브러리도 로컬이라 인터넷이 없어도 시연이 됩니다.\n"
    "솔직한 한계는 설치형 앱이 아니라 반응형 웹이라는 점입니다. PWA는 향후 과제입니다."))
for i, (head, body) in enumerate([
    ("디자인 토큰", "색·간격·반경을 CSS 변수로 정의\n→ 다크모드는 값만 덮어쓰기\n→ 관리자 영역은 포인트 색만 교체"),
    ("다크모드", "시스템 설정 / 라이트 / 다크 선택\n첫 페인트 전에 적용해 깜빡임 방지\n차트 색도 테마에 맞춰 다시 그림"),
    ("반응형", "700px 이하: 상단 메뉴 → 하단 탭바\n카드 그리드가 1~2열로 재배치\n※ 설치형 앱이 아닌 반응형 웹"),
    ("접근성·편의", "학습: Space·←·→·P / 시험: Enter\n포커스 표시, aria-label, 모션 줄이기 존중\n※ 스킵 링크·aria-live 는 향후(#4)"),
    ("가벼운 구성", "Vanilla JS: 빌드 도구·Node 불필요\nChart.js·Lucide 아이콘 로컬 번들 → 오프라인 시연\nfetch 래퍼 api()가 CSRF 자동 처리"),
    ("피드백 UX", "토스트 알림, 확인 모달, 빈 상태 안내\n시험 즉시 정답 피드백, 정답 발음 듣기\n랜딩에서 가입 없이 빈칸 퀴즈 체험"),
]):
    x, y = 0.6 + (i % 3) * 4.15, 1.7 + (i // 3) * 2.6
    card(s, x, y, 3.95, 2.4, head, [(body, {'size': 13})], body_size=13)

# ================================================================ 12. 화면 미리보기
s = new_slide("화면 미리보기", "SCREENS", notes=(
    "실제 동작 화면입니다. 왼쪽 위는 사용자 홈으로 연속 학습일과 진도 링이 보입니다. 오른쪽 위는 관리자 대시보드로 청록색으로 구분됩니다.\n"
    "아래쪽은 다크모드의 통계 화면과 모바일 화면입니다. 시연에서는 이 화면들을 직접 보여드리겠습니다.\n"
    "[참고] 화면은 11/9 기준 현재 UI(Lucide 아이콘 적용, 시연 데이터 학습자 5명)로 다시 촬영했습니다."))
# 라벨 태그는 캡처 위에 얹으면 화면 제목을 가리므로 캡처 아래 가운데에 둔다
PIC_H, TAG_GAP = 2.25, 0.05
grid = [("02_user_home.png", 0.6, 1.5, "사용자 홈"), ("04_study_back.png", 4.95, 1.5, "플립카드 학습"),
        ("20_admin_dashboard.png", 0.6, 4.25, "관리자 대시보드"), ("12_report_dark.png", 4.95, 4.25, "통계 (다크모드)")]
for name, gx, gy, cap in grid:
    picture(s, shot(name), gx, gy, 4.16, PIC_H, crop=True)
    tw = 0.4 + 0.19 * len(cap)
    tag(s, gx + (4.16 - tw) / 2, gy + PIC_H + TAG_GAP, cap, fill=INDIGO, color=WHITE, size=11, w=tw)
picture(s, shot('13_mobile_home.png'), 9.4, 1.5, 3.35, 5.0)
tag(s, 9.4 + (3.35 - 1.16) / 2, 1.5 + 5.0 + TAG_GAP, "모바일", fill=INDIGO, color=WHITE, size=11, w=1.16)

# ================================================================ 13. 품질
s = new_slide("품질 확인: 테스트와 리허설", "QUALITY", notes=(
    "테스트는 두 층으로 했습니다. 첫째 pytest 27개로 인증, 권한, CSRF, 단어 CRUD, 학습·시험 흐름, 그리고 '사용자 A의 기록이 B에게 보이지 않는지'까지 검증합니다. "
    "시험 중 정답이 클라이언트에 노출되지 않는지도 테스트합니다.\n"
    "둘째 브라우저 리허설입니다. Edge를 자동으로 조작해 시연 시나리오 전체를 돌렸습니다. 11/2 첫 리허설에서 문제 4개를, 11/9 재리허설(시나리오 v1.1, 56개 항목)에서 2개를 더 찾아 고쳤습니다. 모두 테스트만으로는 못 찾는 화면·데이터 문제였습니다. 빈칸형 변형 단어 문제는 이슈 #6으로 등록해 시연 이후에 처리합니다.\n"
    "한계도 있습니다. 부하 테스트(동시 접속 수십 명)는 하지 않았습니다."))
card(s, 0.6, 1.5, 5.95, 2.0, "pytest 27개", bullets(["인증·권한·CSRF·로그인 잠금", "단어 CRUD·CSV 가져오기, 사용자 관리", "학습·시험 전 과정, 정답 비노출", "사용자 간 데이터 격리, 모든 화면 200"], 12), fill=GREEN_SOFT, accent=GREEN)
card(s, 6.75, 1.5, 5.95, 2.0, "브라우저 리허설 (Edge 자동화)", bullets(["시연 시나리오 12단계(0~11), 사용자·관리자 창 분리", "모바일 폭·다크모드·XSS 페이로드 확인", "11/9 재리허설: 56개 항목 중 54개 → 수정 후 56개 정상"], 12), accent=TEAL)
add_text(s, 0.6, 3.6, 12, 0.4, "리허설에서 발견한 문제와 처리", size=17, bold=True, color=INDIGO)
table(s, 0.6, 4.05, [5.6, 4.6, 1.95], [
    ["문제", "처리", "검증"],
    ["모바일 관리자 상단바 깨짐 (11/2)", "좁은 화면에서 로고+배지만 표시", "화면 캡처"],
    ["일반 사용자 403 화면에 관리자 메뉴 노출 (11/2)", "실제 관리자에게만 관리자 영역 표시", "회귀 테스트"],
    ["비활성화된 사용자가 이유 없이 로그아웃 (11/2)", "로그인 화면에 사유 안내", "회귀 테스트"],
    ["시험 결과에 정답 라벨 없음 (11/2)", "'정답: … · 내 답: …' 표기", "화면 캡처"],
    ["랜딩 캡처 옛 UI · 관리자 TOP 5 가 3행 (11/9)", "캡처 재촬영 · 시연 데이터 학습자 2명 추가", "리허설 재실행"],
    ["빈칸형: 변형 단어가 4지선다로 대체 (11/9)", "이슈 #6 등록 (시연 후 처리)", "미수정"],
], size=12, row_h=0.4)

# ================================================================ 14. 개발 프로세스
s = new_slide("개발 방식: 문서 기반 + 단계별 검증", "PROCESS", notes=(
    "개발은 문서를 먼저 쓰고 구현하는 순서로 했습니다. 방법론 문서에 산출물 종류와 ADR, 요구사항 ID 규칙을 정의했습니다.\n"
    "git은 커밋을 기능 단위로 잘게 나눴고, 개인 노트북과 학교 실습실을 번갈아 쓰기 때문에 일지를 인수인계 문서로 사용했습니다.\n"
    "[솔직하게 말씀드릴 부분] 이 프로젝트는 AI 코딩 에이전트와 협업했습니다. CLAUDE.md라는 지침 파일로 규칙을 정하고, 제가 방향과 결정을 내리고, "
    "AI가 만든 코드를 테스트와 브라우저 확인으로 검증하는 방식이었습니다. 그래서 오늘 발표는 '왜 이 기술을 골랐는지, 코드가 어떻게 동작하는지'를 제가 설명할 수 있는 데 초점을 뒀습니다.\n"
    "[준비] 이 슬라이드의 AI 협업 문구는 팀의 평가 기준에 맞게 본인 판단으로 유지하거나 수정하세요."))
card(s, 0.6, 1.7, 5.95, 2.45, "문서 우선 (SDLC)", bullets(["방법론: 산출물·요구사항 ID·ADR·BDD 템플릿", "분석 → 설계 → 구현 → 테스트를 한 사이클로", "결정은 ADR(배경/대안/결정/결과)로 기록"], 16))
card(s, 6.75, 1.7, 5.95, 2.45, "Git 워크플로", bullets(["Conventional Commits, 잘게 커밋", "노트북 ↔ 실습실: pull → 작업 → 일지 → push", "비밀정보(.env, DB, 키)는 .gitignore", "GitHub 이슈 #1~#6 으로 후속 과제 추적"], 15), accent=TEAL)
card(s, 0.6, 4.35, 5.95, 2.45, "AI 에이전트 협업 방식", bullets(["CLAUDE.md 지침으로 규칙·승인 범위를 명시", "방향·결정은 사람이, 구현 초안은 AI가", "결과는 pytest + 브라우저 확인으로 검증"], 16), fill=INDIGO_SOFT)
card(s, 6.75, 4.35, 5.95, 2.45, "문서화", bullets(["모듈별 README: 역할·설계 이유·예상 질문", "일지·작업계획서·시연 시나리오", "설계 문서와 코드를 함께 갱신"], 16), accent=TEAL)

# ================================================================ 15. 한계와 향후
s = new_slide("한계와 개선 과제", "LIMITATIONS", notes=(
    "아직 부족한 점을 정직하게 정리했습니다.\n"
    "DB 스키마가 바뀔 때 기존 데이터를 옮겨 줄 마이그레이션 도구가 없습니다. 로그인 잠금은 메모리 기반입니다. 학습 알고리즘은 단순 가중치입니다. 부하 테스트를 하지 않았고, 설치형 앱이 아닌 반응형 웹입니다.\n"
    "가장 가까운 계획은 11월 16일 배포입니다. 배포한 뒤 사용자 5명에게 완성된 웹을 공유하고 사용 피드백을 받습니다. 배포 서버, HTTPS, 환경변수, DB 백업을 확정해야 합니다.\n"
    "그 이후에는 PWA로 홈 화면 설치를 지원하고, 학습 알고리즘을 개선하는 것을 고려하고 있습니다.\n"
    "시연 이후의 구체적인 계획은 다음 장표에서 이슈 번호와 함께 말씀드리겠습니다."))
table(s, 0.6, 1.7, [4.4, 7.75], [
    ["현재 한계", "개선 방향"],
    ["스키마 변경 시 마이그레이션 도구 없음", "Alembic 등 마이그레이션 도입, 배포 DB 백업 절차"],
    ["로그인 잠금이 서버 메모리 기반", "DB 또는 Redis로 이전 (다중 프로세스 대응)"],
    ["학습 알고리즘이 단순 가중치", "SM-2 등 간격 반복 알고리즘 적용 검토"],
    ["동시 접속 부하 테스트 미수행", "locust 등으로 부하 테스트"],
    ["반응형 웹 (설치형 앱 아님)", "PWA(홈 화면 추가, HTTPS 필요) 검토"],
], size=14, row_h=0.72)
add_rect(s, 0.6, 6.2, 12.15, 0.6, fill=AMBER_SOFT, line=None)
add_text(s, 0.8, 6.22, 11.8, 0.56, "다음 일정: 11/13 시연 완료 → 11/16 배포·사용자 5명 공유(피드백 수집) (서버·HTTPS·환경변수·DB 백업 확정 필요)", size=14, bold=True, anchor=MSO_ANCHOR.MIDDLE)

# ================================================================ 16. 향후 계획 (신규, 시연 이후)
s = new_slide("향후 계획: 시연 이후 이슈로 관리합니다", "NEXT STEPS", notes=(
    "시연(11/13) 이후의 계획입니다. 전부 GitHub 이슈로 등록해서 추적하고 있습니다.\n"
    "왼쪽은 랜딩 페이지 리디자인 시안입니다. 색은 기존 CSS 변수 구조를 그대로 쓰고 섹션 구성도 유지했습니다. 모바일 헤더를 햄버거로 줄이고(158px→65px), 스킵 링크·포커스 링·대비를 개선하고, 글꼴을 로컬로 번들해 오프라인에서도 같은 모양이 나오게 했습니다. "
    "아직 앱에 이식하지 않았고, 다른 페이지 시안이 나오면 함께 이식할 계획입니다.\n"
    "오른쪽 첫째, 이슈 4번 접근성 보완입니다. 시안에서 검증한 패턴을 앱의 base.html, style.css, main.js로 옮깁니다. 사용자 피드백 수집은 아직 시작하지 않았습니다.\n"
    "둘째, 이슈 5번입니다. 요구사항에 있었지만 구현하지 못한 파이 차트, 폰트 크기 설정, 데이터 초기화를 구현할지 폐기할지 판단합니다. 파이 차트는 통과 기준 점수를 먼저 정해야 합니다.\n"
    "셋째, 이슈 6번입니다. 빈칸 문제에서 예문 속 단어가 includes처럼 변형되어 있으면 빈칸으로 만들지 못하고 4지선다로 대체되는 문제였습니다. 이후 토익 단어 2,283개로 교체하면서 예문에 단어 원형이 들어가도록 정비해, 대체되는 단어는 0개가 되었습니다."))
add_text(s, 0.6, 1.45, 5.8, 0.4, "랜딩 리디자인 시안  (design/index.html)", size=16, bold=True, color=INDIGO)
picture(s, shot('design_desktop.png'), 0.6, 1.9, 4.4, 2.75, crop=True)
picture(s, shot('design_mobile.png'), 5.15, 1.9, 1.27, 2.75)
tag(s, 0.72, 2.02, "데스크톱", fill=INDIGO, color=WHITE, size=11)
tag(s, 5.2, 2.02, "390px", fill=INDIGO, color=WHITE, size=11)
card(s, 0.6, 4.85, 5.8, 1.95, None, bullets([
    "색은 :root 변수 구조 그대로, 섹션 구성 유지",
    "모바일 햄버거 헤더(158→65px), 퀵메뉴 정리",
    "스킵 링크·포커스 링·대비 개선, 폰트 로컬 번들",
    "앱 이식은 다른 페이지 시안이 나온 뒤 함께"], 13))
card(s, 6.7, 1.5, 6.05, 1.65, "#4  접근성 보완 (앱 이식)", bullets([
    "스킵 링크·aria-live·포커스 링·대비 패턴(시안에서 검증)을 앱에 이식",
    "대상: base.html · style.css · main.js, 피드백 수집은 미진행"], 12), head_size=15)
card(s, 6.7, 3.3, 6.05, 1.65, "#5  미구현 3건 검토 (시연 이후)", bullets([
    "파이 차트(FR-504)·폰트 크기(FR-703)·데이터 초기화(FR-704)",
    "구현·폐기를 판단해 요구사항명세서에 반영, 파이 차트는 통과 기준 점수가 먼저"], 12), accent=TEAL, head_size=15)
card(s, 6.7, 5.1, 6.05, 1.65, "#6  빈칸형 변형 단어 처리 (예문 정비로 해소)", bullets([
    "예문 정비로 대체 단어 0개 (토익 단어 2,283개 기준, 11/13)",
    "앱의 대체 동작(test_engine.py:97)은 유지, 변형 예문이 다시 생기면 변형 매칭 설계"], 12), head_size=15)

# ================================================================ 17. Q&A
s = new_slide("예상 질문과 답변", "Q & A", notes=(
    "자주 나올 만한 질문과 답변 요지입니다. 그대로 외우기보다 각 모듈 README의 '예상 질문'을 읽고 본인의 말로 바꿔 보세요.\n"
    "질문을 받았을 때 모르는 부분은 아는 척하지 말고 '그 부분은 한계로 인지하고 있고 이런 방향으로 개선할 계획입니다'라고 답하는 편이 좋습니다."))
qa = [
    ("왜 Flask이고 Django가 아닌가요?", "인증·관리자를 직접 설계해 원리를 이해하는 게 목적이었고 규모에 Django는 과했습니다. 단점은 구조 규율을 Blueprint·앱 팩토리로 보완했습니다."),
    ("동시에 여러 명이 쓰면 기록이 섞이지 않나요?", "사용자별 상태를 모두 DB에 두었고(시험 진행 상태 포함) 'A 기록이 B에게 안 보임'을 자동 테스트로 검증했습니다."),
    ("시험 정답을 브라우저에서 볼 수 있지 않나요?", "정답은 서버에만 있고 문제 전송 시 제외, 채점 후에만 공개합니다. 테스트로 비노출을 검증했습니다."),
    ("보안은 어떻게 했나요?", "비밀번호 해시, CSRF 토큰, 5회 실패 잠금, 서버측 권한 검사, XSS 이스케이프, 즉시 세션 무효화. 한계는 잠금이 메모리 기반이라는 점입니다."),
    ("규모가 커지면 어떻게 하나요?", "DB 접근을 data 계층에 모아 서버형 DB로 교체 가능하고, 마이그레이션 도구·부하 테스트·로그인 잠금 외부화가 다음 과제입니다."),
    ("React 같은 프레임워크는 왜 안 썼나요?", "화면 13개 규모에서 빌드 도구는 복잡도만 늘립니다. 화면이 훨씬 복잡해지면 도입을 검토합니다."),
]
for i, (q, a) in enumerate(qa):
    x, y = 0.6 + (i % 2) * 6.15, 1.6 + (i // 2) * 1.75
    add_rect(s, x, y, 5.95, 1.6, fill=WHITE)
    add_text(s, x + 0.15, y + 0.08, 5.65, 0.4, "Q. " + q, size=14, bold=True, color=INDIGO_DARK)
    add_text(s, x + 0.15, y + 0.52, 5.65, 1.05, a, size=12, color=INK, line_spacing=1.15)

assert len(prs.slides) == TOTAL, f"슬라이드 수 {len(prs.slides)} != TOTAL {TOTAL}"
out_path.parent.mkdir(parents=True, exist_ok=True)
prs.save(str(out_path))
print(f"저장 완료: {out_path} ({len(prs.slides)}장)")
