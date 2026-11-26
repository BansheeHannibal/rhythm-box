# -*- coding: utf-8 -*-
"""
行星角色精灵图生成脚本（11 个角色，含太阳/月球/冥王星）。

来源：参考图 7264799947083474547.jpg（11 个拟人行星角色横排）。
思路：
1. 以纯色夜空 (4,17,34) 为背景色做距离判定得到前景掩膜；
2. 6 圈腐蚀生成种子 + 测地分水岭拆分相邻角色；
3. 头/身按 x 区间重叠率合并；
4. 宽度过大的分组按列密度最小值竖切；
5. 针对土星环跨到木星/天王星的特殊情况做定向修正；
6. 每个角色生成 6 帧「压扁—拉伸」微动，横向拼成 6 帧精灵图。

关键改动：
- 输出 11 个角色（太阳、水星、金星、地球、月球、火星、木星、土星、天王星、海王星、冥王星）。
- 缩放时同时预留左右/上下安全边距（并考虑微动最大缩放），
  保证土星环等超宽造型也完整落在单帧内、不被裁切。
"""
import os
from collections import deque
from PIL import Image

SRC = r'c:\Users\chen.sicong\Documents\WXWork\1688854796699594\Cache\Image\2026-11\7264799947083474547.jpg'
OUT_DIR = r'd:\personal\rhythm-box\assets\planets'
PREVIEW = r'd:\personal\rhythm-box\_preview.png'

BG = (4, 17, 34)
# 夜空实测为纯色；角色描边与之距离约 25 以上，取 24 既保留描边又滤掉淡辉光
BG_TOL = 24
Y_TOP, Y_BOT = 350, 760

CELL_W, CELL_H = 320, 320
FRAMES = 6

# 单帧内最小安全边距（像素）。左右留一些，避免土星环等宽造型贴边看着像被切
MAR_X, MAR_TOP, MAR_BOTTOM = 8, 10, 8

# 6 帧微动：(横向缩放, 纵向缩放, 垂直位移占格高比例，负值向上)
MOTION = [
    (1.00, 1.00, 0.000),
    (0.98, 1.04, -0.012),
    (0.96, 1.07, -0.020),
    (1.03, 0.94, 0.012),
    (1.01, 0.97, 0.005),
    (1.00, 1.00, 0.000),
]

# (参考图中从左到右的 0 基索引, 文件名, 中文名)
PICK = [
    (0,  'sun',     '太阳'),
    (1,  'mercury', '水星'),
    (2,  'venus',   '金星'),
    (3,  'earth',   '地球'),
    (4,  'moon',    '月球'),
    (5,  'mars',    '火星'),
    (6,  'jupiter', '木星'),
    (7,  'saturn',  '土星'),
    (8,  'uranus',  '天王星'),
    (9,  'neptune', '海王星'),
    (10, 'pluto',   '冥王星'),
]


def is_fg(px, x, y):
    """判断像素是否属于前景（与夜空背景色距离超过阈值）。"""
    r, g, b = px[x, y]
    return (r - BG[0]) ** 2 + (g - BG[1]) ** 2 + (b - BG[2]) ** 2 > BG_TOL * BG_TOL


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    im = Image.open(SRC).convert('RGB')
    W, H = im.size
    px = im.load()

    # ---------- 1. 前景掩膜 ----------
    hgt = Y_BOT - Y_TOP
    mask = bytearray(W * hgt)
    for y in range(Y_TOP, Y_BOT):
        base = (y - Y_TOP) * W
        for x in range(W):
            if is_fg(px, x, y):
                mask[base + x] = 1

    # 从区域四边泛洪，去掉与边界连通的夜空（保留被角色包围的深色区域）
    bgm = bytearray(W * hgt)
    dq = deque()
    for x in range(W):
        for y in (0, hgt - 1):
            i = y * W + x
            if mask[i] and not bgm[i]:
                bgm[i] = 1
                dq.append(i)
    for y in range(hgt):
        for x in (0, W - 1):
            i = y * W + x
            if mask[i] and not bgm[i]:
                bgm[i] = 1
                dq.append(i)
    while dq:
        i = dq.popleft()
        y, x = divmod(i, W)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 0 <= ny < hgt:
                j = ny * W + nx
                if mask[j] and not bgm[j] and not is_fg(px, nx, ny + Y_TOP):
                    bgm[j] = 1
                    dq.append(j)
    for i in range(W * hgt):
        if bgm[i]:
            mask[i] = 0

    # ---------- 2. 腐蚀得到种子 ----------
    er = bytearray(mask)
    for _ in range(6):
        nxt = bytearray(er)
        for y in range(1, hgt - 1):
            row = y * W
            for x in range(1, W - 1):
                i = row + x
                if er[i] and not (er[i - 1] and er[i + 1] and er[i - W] and er[i + W]):
                    nxt[i] = 0
        er = nxt

    # 种子连通域
    labels = [0] * (W * hgt)
    nlab = 0
    seeds = []
    for start in range(W * hgt):
        if not er[start] or labels[start]:
            continue
        nlab += 1
        cnt = 0
        minx, maxx, miny, maxy = W, -1, hgt, -1
        q = deque([start])
        labels[start] = nlab
        while q:
            i = q.popleft()
            cnt += 1
            y, x = divmod(i, W)
            if x < minx: minx = x
            if x > maxx: maxx = x
            if y < miny: miny = y
            if y > maxy: maxy = y
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < W and 0 <= ny < hgt:
                    j = ny * W + nx
                    if er[j] and not labels[j]:
                        labels[j] = nlab
                        q.append(j)
        if cnt >= 300:
            seeds.append([nlab, minx, maxx, miny, maxy, cnt])
        else:
            for i in range(W * hgt):
                if labels[i] == nlab:
                    labels[i] = 0

    # ---------- 3. 测地分水岭：把掩膜像素分给最近的种子 ----------
    q = deque()
    for i in range(W * hgt):
        if labels[i]:
            q.append(i)
    while q:
        i = q.popleft()
        lab = labels[i]
        y, x = divmod(i, W)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 0 <= ny < hgt:
                j = ny * W + nx
                if mask[j] and not labels[j]:
                    labels[j] = lab
                    q.append(j)

    # ---------- 4. 合并同一角色的头/身 ----------
    parent = list(range(nlab + 1))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    info = {s[0]: s for s in seeds}
    ids = list(info.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = info[ids[i]], info[ids[j]]
            ox = min(a[2], b[2]) - max(a[1], b[1])
            wa, wb = a[2] - a[1] + 1, b[2] - b[1] + 1
            # 同一角色的头与身竖着叠放，x 区间几乎完全重合；
            # 并排的角色 x 区间基本不重叠，所以只按 x 重合率判断
            if ox > 0 and ox / min(wa, wb) > 0.7:
                union(ids[i], ids[j])

    groups = {}
    for i in range(W * hgt):
        if labels[i]:
            r = find(labels[i])
            d = groups.get(r)
            if d is None:
                d = groups[r] = [W, -1, hgt, -1, []]
            y, x = divmod(i, W)
            if x < d[0]: d[0] = x
            if x > d[1]: d[1] = x
            if d[2] > y: d[2] = y
            if d[3] < y: d[3] = y
            d[4].append(i)

    chars = [v for v in groups.values() if len(v[4]) >= 5000]

    def split_wide(items):
        """宽度超过 300 的分组按列方向像素密度最稀疏处竖切。"""
        out = []
        for item in items:
            minx, maxx, miny, maxy, pix = item
            if maxx - minx <= 300:
                out.append(item)
                continue
            hist = {}
            for i in pix:
                x = i % W
                hist[x] = hist.get(x, 0) + 1
            lo = minx + int((maxx - minx) * 0.35)
            hi = minx + int((maxx - minx) * 0.65)
            sx = min(range(lo, hi + 1), key=lambda k: hist.get(k, 0))
            left = [i for i in pix if i % W < sx]
            right = [i for i in pix if i % W >= sx]
            for part in (left, right):
                if len(part) < 3000:
                    continue
                xs = [i % W for i in part]
                ys = [i // W for i in part]
                out.append([min(xs), max(xs), min(ys), max(ys), part])
        return out

    chars = split_wide(chars)
    chars.sort(key=lambda c: (c[0] + c[1]) / 2)

    def split_components(pix):
        """把像素集合拆成最大连通块与其余碎块。"""
        s = set(pix)
        seen2 = set()
        comps = []
        for start in pix:
            if start in seen2:
                continue
            comp = []
            dq2 = deque([start])
            seen2.add(start)
            while dq2:
                i = dq2.popleft()
                comp.append(i)
                y, x = divmod(i, W)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    j = ny * W + nx
                    if j in s and j not in seen2:
                        seen2.add(j)
                        dq2.append(j)
            comps.append(comp)
        if not comps:
            return [], []
        main = max(comps, key=len)
        rest = [i for c in comps if c is not main for i in c]
        return main, rest

    def rebbox(item):
        xs = [i % W for i in item[4]]
        ys = [i // W for i in item[4]]
        item[0], item[1] = min(xs), max(xs)
        item[2], item[3] = min(ys), max(ys)

    def keep_large_components(pix, minarea):
        """只保留面积 >= minarea 的连通块，清掉极细小的游离线头。"""
        s = set(pix)
        seen = set()
        out = []
        for start in pix:
            if start in seen:
                continue
            comp = []
            dq4 = deque([start])
            seen.add(start)
            while dq4:
                i = dq4.popleft()
                comp.append(i)
                y, x = divmod(i, W)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    j = ny * W + nx
                    if j in s and j not in seen:
                        seen.add(j)
                        dq4.append(j)
            if len(comp) >= minarea:
                out.extend(comp)
        return out

    # 土星：剔除被裹进来的天王星左手套，还给天王星
    main, rest = split_components(chars[7][4])
    chars[7][4] = main
    rebbox(chars[7])
    chars[8][4].extend(rest)
    rebbox(chars[8])

    # 木星：球体右下角粘着一段「土星环左端」。这段本是土星环的一部分，
    # 因环很薄、腐蚀后没有独立种子，被分水岭误分给了木星。
    # 用球体外接圆把它从木星剥离出来，并「归还给土星」，补全土星环左侧。
    # （球心约 (1104,513)，外沿描边半径约 107）
    JCX, JCY, JR = 1104, 513, 109
    mine, to_saturn = [], []
    for i in chars[6][4]:
        x = i % W
        y_abs = i // W + Y_TOP
        outside = (x - JCX) ** 2 + (y_abs - JCY) ** 2 > JR * JR
        if x >= 1150 and y_abs <= 665 and outside:
            to_saturn.append(i)
        else:
            mine.append(i)
    chars[6][4] = mine
    rebbox(chars[6])
    chars[7][4].extend(to_saturn)
    rebbox(chars[7])
    # 归还的左端可能带入极细的游离线头，按面积阈值清掉（保留本体与手套）
    chars[7][4] = keep_large_components(chars[7][4], 500)
    rebbox(chars[7])
    print('木星剥离环左端像素并归还土星：', len(to_saturn))

    print('识别到角色数量：', len(chars))
    for k, c in enumerate(chars):
        print('  #%d x=%d..%d y=%d..%d 面积=%d' % (
            k, c[0], c[1], c[2] + Y_TOP, c[3] + Y_TOP, len(c[4])))

    def to_rgba(item, pad=8):
        """把像素集合转成裁切后的 RGBA 图（含描边补全）。"""
        minx, maxx, miny, maxy, pix = item
        minx = max(0, minx - pad); maxx = min(W - 1, maxx + pad)
        miny = max(0, miny - pad); maxy = min(hgt - 1, maxy + pad)
        cw, ch = maxx - minx + 1, maxy - miny + 1
        m = bytearray(cw * ch)
        for i in pix:
            y, x = divmod(i, W)
            if minx <= x <= maxx and miny <= y <= maxy:
                m[(y - miny) * cw + (x - minx)] = 1
        # 膨胀 2 圈补回描边
        for _ in range(2):
            nxt = bytearray(m)
            for y in range(ch):
                for x in range(cw):
                    k = y * cw + x
                    if m[k]:
                        continue
                    if ((x > 0 and m[k - 1]) or (x < cw - 1 and m[k + 1]) or
                            (y > 0 and m[k - cw]) or (y < ch - 1 and m[k + cw])):
                        nxt[k] = 1
            m = nxt
        out = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
        op = out.load()
        for y in range(ch):
            for x in range(cw):
                if m[y * cw + x]:
                    r, g, b = px[minx + x, miny + y + Y_TOP]
                    op[x, y] = (r, g, b, 255)
        return out.crop(out.getbbox())

    # 微动过程中的最大缩放，用于预留安全边距
    max_sx = max(m[0] for m in MOTION)
    max_sy = max(m[1] for m in MOTION)
    fit_w = (CELL_W - 2 * MAR_X) / max_sx
    fit_h = (CELL_H - MAR_TOP - MAR_BOTTOM) / max_sy

    def build_sheet(ch_img):
        sheet = Image.new('RGBA', (CELL_W * FRAMES, CELL_H), (0, 0, 0, 0))
        cw, chh = ch_img.size
        # 同时满足宽/高上限，等比缩放到「安全区」内
        scale = min(fit_w / cw, fit_h / chh)
        base_w = max(1, int(cw * scale))
        base_h = max(1, int(chh * scale))
        for i, (sx, sy, dy) in enumerate(MOTION):
            fw, fh = max(1, int(base_w * sx)), max(1, int(base_h * sy))
            fr = ch_img.resize((fw, fh), Image.LANCZOS)
            # 水平居中 + 底部对齐（脚底锚定），并叠加垂直位移
            bottom = CELL_H - MAR_BOTTOM + int(CELL_H * dy)
            sheet.paste(fr, ((CELL_W - fw) // 2 + i * CELL_W, bottom - fh), fr)
        return sheet

    preview = Image.new('RGBA', (CELL_W * len(PICK), CELL_H), (255, 0, 255, 255))
    for slot, (idx, key, name) in enumerate(PICK):
        if idx >= len(chars):
            print('缺少角色', key)
            continue
        ch_img = to_rgba(chars[idx])
        sheet = build_sheet(ch_img)
        try:
            q = sheet.quantize(colors=256, method=Image.FASTOCTREE)
            q.save(os.path.join(OUT_DIR, key + '.png'), optimize=True)
        except Exception:
            sheet.save(os.path.join(OUT_DIR, key + '.png'), optimize=True)
        print('%-8s %-6s 裁切=%dx%d 精灵图=%dx%d' % (
            key, name, ch_img.size[0], ch_img.size[1], sheet.size[0], sheet.size[1]))
        ph = int(CELL_H * 0.9)
        pw = max(1, int(ch_img.size[0] * ph / ch_img.size[1]))
        pv = ch_img.resize((pw, ph), Image.LANCZOS)
        preview.paste(pv, (slot * CELL_W + (CELL_W - pw) // 2, CELL_H - 15 - ph), pv)

    preview.save(PREVIEW)
    print('preview ->', PREVIEW)


if __name__ == '__main__':
    main()
