# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / "系统骨架工程目录拓扑图.png"


def load_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\Dengb.ttf" if bold else r"C:\Windows\Fonts\Deng.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for item in candidates:
        if item and Path(item).exists():
            return ImageFont.truetype(item, size=size)
    return ImageFont.load_default()


FONT_TITLE = load_font(50, True)
FONT_SUBTITLE = load_font(25)
FONT_H2 = load_font(30, True)
FONT_H3 = load_font(24, True)
FONT_BODY = load_font(21)
FONT_SMALL = load_font(17)
FONT_TINY = load_font(16)


PALETTE = {
    "bg": "#f6f8fb",
    "ink": "#263238",
    "muted": "#5f6c72",
    "line": "#90a4ae",
    "root": "#ffffff",
    "runtime": "#e8f5e9",
    "app": "#e3f2fd",
    "view": "#fff8e1",
    "data": "#fce4ec",
    "verify": "#ede7f6",
    "injury": "#ffecb3",
    "accent": "#00897b",
    "accent2": "#ef6c00",
    "border": "#b0bec5",
}


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw, text, font, max_width):
    lines = []
    for raw in text.split("\n"):
        line = ""
        for char in raw:
            test = line + char
            if text_size(draw, test, font)[0] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = char
        if line:
            lines.append(line)
    return lines or [""]


def rounded_box(draw, xy, fill, outline=None, radius=18, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline or PALETTE["border"], width=width)


def draw_centered_text(draw, box, text, font, fill=PALETTE["ink"], line_gap=7):
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, font, x2 - x1 - 30)
    total_h = sum(text_size(draw, line, font)[1] for line in lines) + line_gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line in lines:
        w, h = text_size(draw, line, font)
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=font, fill=fill)
        y += h + line_gap


def draw_card(draw, x, y, w, h, title, items, fill, border=None, title_fill=PALETTE["ink"]):
    rounded_box(draw, (x, y, x + w, y + h), fill, outline=border or PALETTE["border"], radius=16, width=2)
    draw.text((x + 22, y + 18), title, font=FONT_H3, fill=title_fill)
    draw.line((x + 20, y + 56, x + w - 20, y + 56), fill=border or PALETTE["border"], width=2)
    yy = y + 74
    for item in items:
        marker_box = (x + 24, yy + 7, x + 34, yy + 17)
        draw.rounded_rectangle(marker_box, radius=3, fill=title_fill if title_fill != PALETTE["ink"] else PALETTE["accent"])
        for line in wrap_text(draw, item, FONT_BODY, w - 70):
            draw.text((x + 46, yy), line, font=FONT_BODY, fill=PALETTE["ink"])
            yy += 28
        yy += 7


def arrow(draw, start, end, fill=PALETTE["line"], width=3):
    draw.line((start, end), fill=fill, width=width)
    sx, sy = start
    ex, ey = end
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex >= sx else -1
        points = [(ex, ey), (ex - 12 * direction, ey - 7), (ex - 12 * direction, ey + 7)]
    else:
        direction = 1 if ey >= sy else -1
        points = [(ex, ey), (ex - 7, ey - 12 * direction), (ex + 7, ey - 12 * direction)]
    draw.polygon(points, fill=fill)


def draw_project_tree(draw):
    x, y, w, h = 70, 255, 760, 1170
    rounded_box(draw, (x, y, x + w, y + h), PALETTE["root"], outline="#78909c", radius=22, width=3)
    draw.text((x + 28, y + 24), "项目根目录：乒乓球运动员综合训练监控管理系统", font=FONT_H2, fill=PALETTE["ink"])
    draw.text((x + 30, y + 66), str(ROOT), font=FONT_TINY, fill=PALETTE["muted"])

    tree_lines = [
        ("app.py", "Flask 应用入口；Blueprint 路由；登录权限；业务函数"),
        ("requirements.txt", "Flask / Jinja2 / PyMySQL / pandas / pytest 依赖"),
        (".env.example", "环境变量模板与数据库连接配置约定"),
        ("run_server.bat", "Windows 本地启动脚本"),
        ("templates/", "Jinja2 页面模板层"),
        ("  base.html / index.html", "统一布局、导航、综合看板"),
        ("  auth/", "登录、用户权限、403 页面"),
        ("  players/", "运动员档案页面"),
        ("  training/", "训练计划与批量导入页面"),
        ("  fitness/", "体能测试页面"),
        ("  injuries/", "伤病记录列表与历史追踪页面"),
        ("sql/", "数据库建库、约束、安全对象与伤病业务 SQL"),
        ("  pingpang_db.sql", "基础库表与初始数据"),
        ("  member2_advanced_database.sql", "约束、触发器、过程与低权限账号"),
        ("  member8_injury_records.sql", "伤病记录、复诊、归档、视图与过程"),
        ("tests/", "自动化验证"),
        ("  test_injuries.py", "伤病模块页面、权限、校验、归档、历史测试"),
        ("docs/", "数据库设计交接与高级对象说明"),
        ("伤病记录开发模块/", "课程报告、状态迁移图、优化建议、架构图脚本与图片"),
    ]

    yy = y + 120
    for name, desc in tree_lines:
        if name.endswith("/"):
            fill = "#eceff1" if name != "伤病记录开发模块/" else PALETTE["injury"]
            rounded_box(draw, (x + 26, yy - 4, x + w - 26, yy + 48), fill, outline="#cfd8dc", radius=10, width=1)
            draw.text((x + 44, yy + 6), name, font=FONT_H3, fill=PALETTE["ink"])
            draw.text((x + 250, yy + 9), desc, font=FONT_SMALL, fill=PALETTE["muted"])
            yy += 62
        else:
            name_font = FONT_BODY
            desc_font = FONT_SMALL
            name_x = x + 54 if name.startswith("  ") else x + 42
            marker_x = x + 34 if not name.startswith("  ") else x + 48
            draw.ellipse((marker_x, yy + 8, marker_x + 8, yy + 16), fill=PALETTE["accent"])
            name_lines = wrap_text(draw, name, name_font, 248)
            desc_lines = wrap_text(draw, desc, desc_font, 360)
            row_lines = max(len(name_lines), len(desc_lines))
            line_h = 25
            for i, line in enumerate(name_lines):
                draw.text((name_x, yy + i * line_h), line, font=name_font, fill=PALETTE["ink"])
            for i, line in enumerate(desc_lines):
                draw.text((x + 360, yy + 2 + i * line_h), line, font=desc_font, fill=PALETTE["muted"])
            yy += max(38, row_lines * line_h + 12)


def draw_architecture_layers(draw):
    cards = [
        (
            900,
            255,
            610,
            235,
            "1. 运行与入口层",
            [
                "浏览器访问 http://localhost:5000",
                "run_server.bat 调用 Python 启动 app.py",
                "requirements.txt 锁定运行依赖范围",
            ],
            PALETTE["runtime"],
            "#81c784",
        ),
        (
            1580,
            255,
            610,
            235,
            "2. Web 应用层",
            [
                "create_app() 注册 Flask 实例",
                "Blueprint 划分 players / training / injuries / fitness / rehab / matches / auth / settings",
                "session 登录态 + role_required 角色访问控制",
            ],
            PALETTE["app"],
            "#64b5f6",
        ),
        (
            900,
            550,
            610,
            260,
            "3. 前端模板层",
            [
                "templates/base.html 提供统一导航与布局",
                "模块页面按业务目录归档",
                "injuries/list.html 与 history.html 承载伤病登记、筛选、复诊和历史",
            ],
            PALETTE["view"],
            "#ffb300",
        ),
        (
            1580,
            550,
            610,
            260,
            "4. 数据与事务层",
            [
                "sql/pingpang_db.sql 建立基础表",
                "member2_advanced_database.sql 提供约束、触发器和过程",
                "member8_injury_records.sql 补充伤病视图、复诊表、归档过程和验证语句",
            ],
            PALETTE["data"],
            "#f06292",
        ),
        (
            900,
            870,
            610,
            260,
            "5. 测试与质量层",
            [
                "tests/test_injuries.py 覆盖伤病页面可用性",
                "校验非法编号、角色权限、严重伤病审批、归档联动状态",
                "pytest 用于回归验证",
            ],
            PALETTE["verify"],
            "#9575cd",
        ),
        (
            1580,
            870,
            610,
            260,
            "6. 文档与交付层",
            [
                "docs 保存数据库设计交接说明",
                "伤病记录开发模块保存报告、图、优化建议",
                "本图与生成脚本作为模块交付物留存",
            ],
            "#e0f2f1",
            "#26a69a",
        ),
    ]

    for card in cards:
        draw_card(draw, *card)

    arrow(draw, (1510, 372), (1580, 372), fill="#546e7a")
    arrow(draw, (1205, 490), (1205, 550), fill="#546e7a")
    arrow(draw, (1885, 490), (1885, 550), fill="#546e7a")
    arrow(draw, (1510, 680), (1580, 680), fill="#546e7a")
    arrow(draw, (1205, 810), (1205, 870), fill="#546e7a")
    arrow(draw, (1885, 810), (1885, 870), fill="#546e7a")


def draw_injury_vertical_slice(draw):
    x, y, w, h = 900, 1180, 1290, 265
    rounded_box(draw, (x, y, x + w, y + h), "#fff3e0", outline=PALETTE["accent2"], radius=20, width=3)
    draw.text((x + 28, y + 20), "伤病记录模块工程落点（纵向业务切片）", font=FONT_H2, fill=PALETTE["accent2"])

    steps = [
        ("路由", "app.py\n/injuries\n/history"),
        ("页面", "templates\ninjuries\n列表/历史"),
        ("业务", "登记编辑\n筛选统计\n归档复诊"),
        ("数据", "member8 SQL\n视图过程\n状态联动"),
        ("验证", "pytest\n权限校验\n回归测试"),
        ("交付", "开发模块\n报告图片\n生成脚本"),
    ]
    box_w = 184
    gap = 24
    sx = x + 36
    sy = y + 86
    for idx, (title, body) in enumerate(steps):
        bx = sx + idx * (box_w + gap)
        rounded_box(draw, (bx, sy, bx + box_w, sy + 132), "#ffffff", outline="#ffb74d", radius=14, width=2)
        draw_centered_text(draw, (bx + 8, sy + 10, bx + box_w - 8, sy + 43), title, FONT_H3, fill=PALETTE["accent2"])
        draw_centered_text(draw, (bx + 8, sy + 47, bx + box_w - 8, sy + 122), body, FONT_SMALL, fill=PALETTE["ink"], line_gap=5)
        if idx < len(steps) - 1:
            arrow(draw, (bx + box_w + 4, sy + 66), (bx + box_w + gap - 4, sy + 66), fill=PALETTE["accent2"], width=3)


def draw_footer(draw):
    footer = "生成文件：伤病记录开发模块/系统骨架工程目录拓扑图.png    脚本：伤病记录开发模块/generate_system_skeleton_topology.py"
    draw.text((72, 1480), footer, font=FONT_SMALL, fill=PALETTE["muted"])


def main():
    img = Image.new("RGB", (2260, 1530), PALETTE["bg"])
    draw = ImageDraw.Draw(img)

    draw.text((70, 54), "系统骨架工程目录拓扑图", font=FONT_TITLE, fill=PALETTE["ink"])
    draw.text(
        (72, 125),
        "项目级视角：目录组织、运行入口、Web 分层、数据库脚本、测试验证与伤病记录模块交付物",
        font=FONT_SUBTITLE,
        fill=PALETTE["muted"],
    )
    draw.rounded_rectangle((70, 190, 2190, 204), radius=7, fill=PALETTE["accent"])

    draw_project_tree(draw)
    draw_architecture_layers(draw)
    draw_injury_vertical_slice(draw)
    draw_footer(draw)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_FILE, "PNG", optimize=True)
    print(OUT_FILE)


if __name__ == "__main__":
    main()
