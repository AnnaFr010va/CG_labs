import math


def rnd(v):
    """Математическое округление (round() в Python округляет 0.5 «к чётному»)."""
    return math.floor(v + 0.5)


def step_by_step(x1, y1, x2, y2, log=None):
    """Пошаговый алгоритм: y = kx + b, шаг 1 по ведущей оси, округление результата."""
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return [(x1, y1)]
    pts = []
    if abs(dx) >= abs(dy):                      # пологий: шаг по x, y = kx + b
        k = dy / dx
        b = y1 - k * x1
        if log is not None:
            log.append(f"|Dx| >= |Dy| -> шаг по X")
            log.append(f"y = kx + b,  k = {dy}/{dx} = {k:.4f},  b = {b:.4f}")
        s = 1 if dx > 0 else -1
        for x in range(x1, x2 + s, s):
            y = k * x + b
            pts.append((x, rnd(y)))
            if log is not None:
                log.append(f"x={x}: y = {k:.4f}*{x} + {b:.4f} = {y:.4f} -> {rnd(y)}")
    else:                                       # крутой: шаг по y, x = ky + b
        k = dx / dy
        b = x1 - k * y1
        if log is not None:
            log.append(f"|Dy| > |Dx| -> шаг по Y")
            log.append(f"x = ky + b,  k = {dx}/{dy} = {k:.4f},  b = {b:.4f}")
        s = 1 if dy > 0 else -1
        for y in range(y1, y2 + s, s):
            x = k * y + b
            pts.append((rnd(x), y))
            if log is not None:
                log.append(f"y={y}: x = {k:.4f}*{y} + {b:.4f} = {x:.4f} -> {rnd(x)}")
    return pts


def dda(x1, y1, x2, y2, log=None):
    """Симметричный ЦДА: L = max(|Dx|, |Dy|) шагов, приращения Dx/L и Dy/L."""
    dx, dy = x2 - x1, y2 - y1
    L = max(abs(dx), abs(dy))
    if L == 0:
        return [(x1, y1)]
    x_inc, y_inc = dx / L, dy / L
    if log is not None:
        log.append(f"L = max(|{dx}|, |{dy}|) = {L}")
        log.append(f"dx/L = {x_inc:.4f},  dy/L = {y_inc:.4f}")
    pts = []
    x, y = float(x1), float(y1)
    for i in range(L + 1):
        pts.append((rnd(x), rnd(y)))
        if log is not None:
            log.append(f"i={i}: x = {x:.4f}, y = {y:.4f} -> ({rnd(x)}, {rnd(y)})")
        x += x_inc
        y += y_inc
    return pts


def bresenham_line(x1, y1, x2, y2, log=None):
    """Целочисленный Брезенхем для отрезка (все октанты: ведущая ось + знаки шагов)."""
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x2 >= x1 else -1
    sy = 1 if y2 >= y1 else -1
    steep = dy > dx
    if steep:                                   # ведущая ось — Y: меняем роли dx и dy
        dx, dy = dy, dx
    e = 2 * dy - dx                             # E' = 2*Dy - Dx
    if log is not None:
        log.append(f"Ведущая ось {'Y' if steep else 'X'}; сведено к I октанту:")
        log.append(f"Dx = {dx}, Dy = {dy},  E' = 2*Dy - Dx = {e}")
        log.append(f"E' >= 0: E' += 2(Dy-Dx) = {2 * (dy - dx)}")
        log.append(f"E' <  0: E' += 2Dy = {2 * dy}")
    x, y = x1, y1
    pts = []
    for i in range(dx + 1):
        pts.append((x, y))
        if log is not None:
            log.append(f"шаг {i:3}:  ({x}, {y}),  E' = {e}")
        if e >= 0:                              # шаг по обеим осям
            if steep:
                x += sx
            else:
                y += sy
            e -= 2 * dx
        if steep:                               # шаг по ведущей оси
            y += sy
        else:
            x += sx
        e += 2 * dy
    return pts


def bresenham_circle(cx, cy, r, log=None):
    """Целочисленный Брезенхем для окружности: дуга II октанта + 8-кратная симметрия."""
    x, y = 0, r
    e = 3 - 2 * r
    if log is not None:
        log.append(f"R = {r};  старт (0, R),  E = 3 - 2R = {e}")
    pts = set()
    while x <= y:
        if log is not None:
            log.append(f"({x}, {y}), E = {e} -> "
                       + ("диагональ, E += 4(x-y)+10" if e >= 0 else "вправо, E += 4x+6"))
        for px, py in ((x, y), (y, x), (-x, y), (-y, x), (x, -y), (y, -x), (-x, -y), (-y, -x)):
            pts.add((cx + px, cy + py))         # set убирает совпадающие точки на осях симметрии
        if e >= 0:
            e += 4 * (x - y) + 10
            y -= 1
        else:
            e += 4 * x + 6
        x += 1
    return sorted(pts)
