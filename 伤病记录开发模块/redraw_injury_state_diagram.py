from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont


out_dir = Path(__file__).resolve().parent
out_path = out_dir / "伤病状态更新触发器状态迁移图.png"

W, H = 2200, 1450
img = Image.new("RGB", (W, H), "#f6f8fb")
d = ImageDraw.Draw(img)


def font(size, bold=False):
    for path in [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf" if bold else "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


F_TITLE = font(48, True)
F_SUB = font(24)
F_H = font(28, True)
F = font(23)
F_SMALL = font(19)
F_TINY = font(17)


def rounded_rect(xy, fill, outline="#cbd5e1", width=2, radius=22):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text_center(xy, text, fnt=F, fill="#0f172a", line_gap=6):
    x1, y1, x2, y2 = xy
    lines = text.split("\n")
    sizes = []
    for line in lines:
        box = d.textbbox((0, 0), line, font=fnt)
        sizes.append((box[2] - box[0], box[3] - box[1]))
    total_h = sum(h for _, h in sizes) + line_gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line, (w, h) in zip(lines, sizes):
        d.text((x1 + (x2 - x1 - w) / 2, y), line, font=fnt, fill=fill)
        y += h + line_gap


def text_left(x, y, text, fnt=F, fill="#0f172a", line_gap=8):
    for line in text.split("\n"):
        d.text((x, y), line, font=fnt, fill=fill)
        box = d.textbbox((0, 0), line, font=fnt)
        y += (box[3] - box[1]) + line_gap
    return y


def arrow(start, end, color="#334155", width=4, head=16):
    x1, y1 = start
    x2, y2 = end
    d.line((x1, y1, x2, y2), fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    points = []
    for a in [angle + math.pi * 0.82, angle - math.pi * 0.82]:
        points.append((x2 + head * math.cos(a), y2 + head * math.sin(a)))
    d.polygon([(x2, y2), points[0], points[1]], fill=color)


def connector_label(x, y, text, fill="#475569", font_obj=F_TINY):
    box = d.textbbox((0, 0), text, font=font_obj)
    pad = 7
    d.rounded_rectangle(
        (x, y, x + box[2] - box[0] + pad * 2, y + box[3] - box[1] + pad * 2),
        radius=8,
        fill="#ffffff",
        outline="#cbd5e1",
    )
    d.text((x + pad, y + pad), text, font=font_obj, fill=fill)


def pill(x, y, text, fill, outline):
    box = d.textbbox((0, 0), text, font=F_SMALL)
    w = box[2] - box[0] + 34
    h = box[3] - box[1] + 18
    d.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=fill, outline=outline, width=2)
    d.text((x + 17, y + 9), text, font=F_SMALL, fill="#0f172a")
    return x + w


rounded_rect((60, 40, W - 60, 150), "#0f3d66", outline="#0f3d66", radius=26)
text_center((60, 48, W - 60, 102), "伤病状态更新触发器状态迁移图", F_TITLE, "#ffffff")
text_center((60, 102, W - 60, 144), "伤病记录模块 · injury_record 触发器联动 athlete.injury_status", F_SUB, "#dbeafe")

sections = [
    ((90, 210, 420, 340), "业务操作层", "新增 / 修改 / 作废\n伤病记录"),
    ((520, 210, 850, 340), "触发器层", "AFTER INSERT\nAFTER UPDATE\nAFTER DELETE / 作废过程"),
    ((950, 210, 1280, 340), "状态刷新层", "sp_refresh_athlete_injury_status\nrefresh_athlete_injury_status()"),
    ((1380, 210, 1710, 340), "规则判定层", "按有效伤病记录\n计算最高风险状态"),
    ((1810, 210, 2110, 340), "数据落库层", "UPDATE athlete\nSET injury_status = ?"),
]
for xy, title, body in sections:
    rounded_rect(xy, "#ffffff", "#94a3b8", 2, 20)
    d.text((xy[0] + 24, xy[1] + 18), title, font=F_H, fill="#0f3d66")
    text_center((xy[0] + 20, xy[1] + 58, xy[2] - 20, xy[3] - 16), body, F, "#1e293b")

for i in range(len(sections) - 1):
    arrow((sections[i][0][2], 275), (sections[i + 1][0][0], 275), "#1769aa", 5)
connector_label(430, 235, "触发")
connector_label(862, 235, "调用")
connector_label(1292, 235, "读取")
connector_label(1722, 235, "写回")

rounded_rect((70, 410, 2130, 1285), "#ffffff", "#cbd5e1", 2, 26)
d.text((110, 440), "状态迁移判定优先级", font=F_H, fill="#0f172a")
d.text((110, 478), "系统只统计未作废且 recovery_status 属于“治疗中 / 康复中”的有效伤病记录，按风险优先级刷新运动员健康状态。", font=F, fill="#475569")

nodes = {
    "start": (150, 575, 430, 675, "#e0f2fe", "#0284c7", "开始刷新\n运动员健康状态"),
    "d1": (530, 545, 910, 705, "#fff7ed", "#f97316", "是否存在：\n严重 + 治疗中\n有效伤病记录？"),
    "injured": (1110, 545, 1430, 705, "#fee2e2", "#dc2626", "状态：伤病中\ninjured"),
    "d2": (530, 765, 910, 925, "#fefce8", "#ca8a04", "是否存在：\n治疗中\n有效伤病记录？"),
    "observe": (1110, 765, 1430, 925, "#fef3c7", "#d97706", "状态：观察中\nobserve"),
    "d3": (530, 985, 910, 1145, "#ecfeff", "#0891b2", "是否存在：\n康复中\n有效伤病记录？"),
    "rehab": (1110, 985, 1430, 1145, "#dbeafe", "#2563eb", "状态：康复中\nrehab"),
    "healthy": (1110, 1185, 1430, 1265, "#dcfce7", "#16a34a", "状态：健康\nhealthy"),
    "update": (1600, 765, 2030, 925, "#f8fafc", "#64748b", "统一写回 athlete 表\n同步前端运动员档案状态"),
}
for key, (x1, y1, x2, y2, fill, outline, label) in nodes.items():
    rounded_rect((x1, y1, x2, y2), fill, outline, 3, 22)
    text_center((x1 + 12, y1 + 10, x2 - 12, y2 - 10), label, F_H if key in {"injured", "observe", "rehab", "healthy"} else F, "#0f172a")

arrow((430, 625), (530, 625), "#334155", 4)
connector_label(215, 532, "读取当前 athlete_id 的有效伤病记录")
arrow((910, 625), (1110, 625), "#dc2626", 5)
connector_label(968, 579, "是 · 最高优先级")
arrow((720, 705), (720, 765), "#334155", 4)
connector_label(735, 720, "否")
arrow((910, 845), (1110, 845), "#d97706", 5)
connector_label(950, 805, "是")
arrow((720, 925), (720, 985), "#334155", 4)
connector_label(735, 940, "否")
arrow((910, 1065), (1110, 1065), "#2563eb", 5)
connector_label(950, 1025, "是")
arrow((720, 1145), (1110, 1225), "#16a34a", 5)
connector_label(820, 1150, "否 · 无未恢复有效记录")

for key, y in [("injured", 625), ("observe", 845), ("rehab", 1065), ("healthy", 1225)]:
    x2 = nodes[key][2]
    arrow((x2, y), (1600, 885 if key == "healthy" else 845), "#64748b", 4)

rounded_rect((1550, 515, 2070, 695), "#f1f5f9", "#94a3b8", 2, 18)
d.text((1580, 540), "有效记录口径", font=F_H, fill="#0f3d66")
text_left(1580, 582, "1. is_deleted = 0\n2. recovery_status IN (治疗中, 康复中)\n3. athlete_id = 当前被触发运动员", F_SMALL, "#334155")

rounded_rect((1550, 1010, 2070, 1210), "#f8fafc", "#94a3b8", 2, 18)
d.text((1580, 1035), "触发场景", font=F_H, fill="#0f3d66")
text_left(1580, 1078, "• 新增伤病记录：AFTER INSERT\n• 修改恢复状态/严重程度：AFTER UPDATE\n• 删除或作废归档：刷新原运动员状态\n• 运动员变更：新旧 athlete_id 均刷新", F_SMALL, "#334155")

rounded_rect((90, 1320, 2110, 1405), "#ffffff", "#cbd5e1", 2, 18)
d.text((120, 1345), "状态图例：", font=F_H, fill="#0f172a")
x = 270
x = pill(x, 1342, "伤病中：严重治疗中，禁止高强度训练", "#fee2e2", "#dc2626") + 25
x = pill(x, 1342, "观察中：普通治疗中，降低训练负荷", "#fef3c7", "#d97706") + 25
x = pill(x, 1342, "康复中：恢复过渡，限制对抗训练", "#dbeafe", "#2563eb") + 25
pill(x, 1342, "健康：无有效未恢复伤病", "#dcfce7", "#16a34a")

img.save(out_path, quality=95)
print(out_path)
