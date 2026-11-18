EPS = 1e-3   # «размер пикселя» для алгоритма средней точки

def parse_input(path):
    """Формат (строки с '#' — комментарии):
        n
        x1 y1 x2 y2          (n строк — отрезки)
        Xmin Ymin Xmax Ymax  (прямоугольное окно, часть 1)
        m                    (необязательно: число вершин многоугольника, часть 2)
        x y                  (m строк — вершины выпуклого многоугольника)
    Возвращает (segments, (xmin, ymin, xmax, ymax), polygon | None)."""
    tokens = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            tokens += line.split("#", 1)[0].split()
    nums = iter(tokens)

    n = int(next(nums))
    segments = []
    for _ in range(n):
        x1, y1, x2, y2 = (float(next(nums)) for _ in range(4))
        segments.append(((x1, y1), (x2, y2)))
    xmin, ymin, xmax, ymax = (float(next(nums)) for _ in range(4))
    if xmin > xmax:
        xmin, xmax = xmax, xmin
    if ymin > ymax:
        ymin, ymax = ymax, ymin

    polygon = None
    m = next(nums, None)
    if m is not None:
        polygon = [(float(next(nums)), float(next(nums))) for _ in range(int(m))]
    return segments, (xmin, ymin, xmax, ymax), polygon


# Часть 1. Алгоритм средней точки

def out_code(p, xmin, ymin, xmax, ymax):
    x, y = p
    code = 0
    if y > ymax: code |= 0b1000
    if y < ymin: code |= 0b0100
    if x > xmax: code |= 0b0010
    if x < xmin: code |= 0b0001
    return code


def midpoint_clip(p1, p2, xmin, ymin, xmax, ymax, eps=EPS):
    pieces = []

    def clip(a, b):
        if abs(b[0] - a[0]) < eps and abs(b[1] - a[1]) < eps:   # короче «пикселя»
            return
        ca = out_code(a, xmin, ymin, xmax, ymax)
        cb = out_code(b, xmin, ymin, xmax, ymax)
        if ca & cb:                       # целиком вне окна
            return
        if ca == 0 and cb == 0:           # целиком внутри окна
            pieces.append((a, b))
            return
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        clip(a, mid)
        clip(mid, b)

    clip(p1, p2)
    if not pieces:
        return None
    return pieces[0][0], pieces[-1][1]


# Часть 2. Алгоритм Кируса-Бека

def cross(o, a, b):
    """z-компонента векторного произведения OA x OB (>0 — поворот влево)."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def prepare_polygon(polygon):
    """Проверить выпуклость и вернуть вершины в порядке против часовой стрелки."""
    n = len(polygon)
    if n < 3:
        raise ValueError("многоугольник должен иметь не меньше 3 вершин")
    turns = [cross(polygon[i], polygon[(i + 1) % n], polygon[(i + 2) % n]) for i in range(n)]
    if not (all(t >= 0 for t in turns) or all(t <= 0 for t in turns)):
        raise ValueError("многоугольник не выпуклый")
    area2 = sum(polygon[i][0] * polygon[(i + 1) % n][1] - polygon[(i + 1) % n][0] * polygon[i][1]
                for i in range(n))
    if area2 == 0:
        raise ValueError("многоугольник вырожден")
    return list(polygon) if area2 > 0 else list(reversed(polygon))


def cyrus_beck_clip(p1, p2, polygon):
    """Отсечь отрезок P1P2 выпуклым многоугольником (вершины против часовой стрелки).

    P(t) = P1 + t·D, D = P2 - P1, 0 <= t <= 1.
    Для ребра Ei = A->B внутренняя нормаль N = (-(By-Ay), Bx-Ax).
    Точка P(t) на видимой стороне ребра, если (P(t) - A)·N >= 0, т.е.
        Q + t·S >= 0,  где Q = (P1 - A)·N,  S = D·N.
    S > 0 — отрезок входит через ребро, S < 0 — выходит, S = 0 — параллелен.
    Возвращает видимую часть (отрезок) или None."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    t_in, t_out = 0.0, 1.0
    n = len(polygon)
    for i in range(n):
        a, b = polygon[i], polygon[(i + 1) % n]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]           # внутренняя нормаль
        s = dx * nx + dy * ny
        q = (p1[0] - a[0]) * nx + (p1[1] - a[1]) * ny
        if s == 0:
            if q < 0:                    # параллелен ребру и снаружи
                return None
            continue                     # параллелен ребру и внутри
        t = -q / s
        if s > 0:
            t_in = max(t_in, t)          # потенциальная точка входа
        else:
            t_out = min(t_out, t)        # потенциальная точка выхода
        if t_in > t_out:
            return None
    pin = (p1[0] + t_in * dx, p1[1] + t_in * dy)
    pout = (p1[0] + t_out * dx, p1[1] + t_out * dy)
    return pin, pout
