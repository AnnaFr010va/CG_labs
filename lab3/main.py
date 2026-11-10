import math
import sys
import time

from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QTextEdit,
)

import raster_algorithms as ra

ALGORITHMS = [
    ("Пошаговый", ra.step_by_step),
    ("ЦДА", ra.dda),
    ("Брезенхем (отрезок)", ra.bresenham_line),
    ("Брезенхем (окружность)", ra.bresenham_circle),
]
NICE_STEPS = [m * 10 ** e for e in range(7) for m in (1, 2, 5)]  # 1, 2, 5, 10, 20, 50, ...


def avg_time(func, args):
    """Среднее время одного вызова (с). Один вызов длится микросекунды, поэтому
    функция повторяется столько раз, чтобы суммарно набралось ~0.05 с."""
    n, total = 1, 0.0
    while total < 0.05:
        t0 = time.perf_counter()
        for _ in range(n):
            func(*args)
        total = time.perf_counter() - t0
        n *= 2
    return total / (n // 2)


class Canvas(QWidget):
    """Сетка, оси, подписи, пиксели и идеальная фигура. ЛКМ — сдвиг, колесо — масштаб."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.cell = 25.0                    # размер пикселя-клетки на экране, px
        self.ox = self.oy = 0.0             # сдвиг начала координат от центра виджета, px
        self.pixels, self.shape = [], None
        self.hover = None
        self._drag = None

    # --- преобразование координат ---
    def origin(self):
        return self.width() / 2 + self.ox, self.height() / 2 + self.oy

    def to_screen(self, x, y):
        x0, y0 = self.origin()
        return x0 + x * self.cell, y0 - y * self.cell

    # --- управление видом ---
    def set_figure(self, pixels, shape):
        """Новая фигура: масштаб и сдвиг подбираются так, чтобы она целиком помещалась."""
        self.pixels, self.shape = pixels, shape
        xs = [p[0] for p in pixels]
        ys = [p[1] for p in pixels]
        bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        self.cell = max(1.0, min(60.0, (self.width() - 120) / bw, (self.height() - 120) / bh))
        self.ox = -(min(xs) + max(xs)) / 2 * self.cell
        self.oy = (min(ys) + max(ys)) / 2 * self.cell
        self.update()

    # --- мышь ---
    def wheelEvent(self, e):
        """Масштаб колесом относительно курсора — точка под курсором остаётся на месте."""
        new = max(1.0, min(150.0, self.cell * 1.15 ** (e.angleDelta().y() / 120)))
        x0, y0 = self.origin()
        k = new / self.cell
        self.ox += (e.x() - x0) * (1 - k)
        self.oy += (e.y() - y0) * (1 - k)
        self.cell = new
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = (e.x() - self.ox, e.y() - self.oy)
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag:
            self.ox, self.oy = e.x() - self._drag[0], e.y() - self._drag[1]
        x0, y0 = self.origin()
        self.hover = (ra.rnd((e.x() - x0) / self.cell), ra.rnd((y0 - e.y()) / self.cell))
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(Qt.ArrowCursor)

    # --- отрисовка ---
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, c = self.width(), self.height(), self.cell
        x0, y0 = self.origin()
        p.fillRect(self.rect(), Qt.white)

        # видимый диапазон координат
        xmin, xmax = math.floor(-x0 / c) - 1, math.ceil((w - x0) / c) + 1
        ymin, ymax = math.floor((y0 - h) / c) - 1, math.ceil(y0 / c) + 1

        # сетка: границы пикселей на полуцелых координатах (если клетки не слишком мелкие)
        if c >= 6:
            p.setPen(QPen(QColor(220, 220, 220), 1))
            for i in range(xmin, xmax + 1):
                sx = x0 + (i - 0.5) * c
                p.drawLine(QLineF(sx, 0, sx, h))
            for j in range(ymin, ymax + 1):
                sy = y0 - (j - 0.5) * c
                p.drawLine(QLineF(0, sy, w, sy))

        # пиксели: клетка c центром в (x, y)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 110, 210, 170))
        for x, y in self.pixels:
            sx, sy = self.to_screen(x, y)
            p.drawRect(QRectF(sx - c / 2, sy - c / 2, c, c))

        # оси со стрелками
        p.setPen(QPen(Qt.black, 1.5))
        p.setBrush(Qt.black)
        if 0 <= y0 <= h:
            p.drawLine(QLineF(0, y0, w, y0))
            p.drawPolygon(QPointF(w - 1, y0), QPointF(w - 11, y0 - 4), QPointF(w - 11, y0 + 4))
            p.drawText(QPointF(w - 14, y0 - 8), "X")
        if 0 <= x0 <= w:
            p.drawLine(QLineF(x0, 0, x0, h))
            p.drawPolygon(QPointF(x0, 1), QPointF(x0 - 4, 11), QPointF(x0 + 4, 11))
            p.drawText(QPointF(x0 + 8, 34), "Y")

        # идеальная (непрерывная) фигура поверх пикселей
        p.setPen(QPen(QColor(220, 40, 40), 2 if c >= 6 else 1))
        p.setBrush(Qt.NoBrush)
        if self.shape and self.shape[0] == "line":
            _, ax, ay, bx, by = self.shape
            p.drawLine(QLineF(*self.to_screen(ax, ay), *self.to_screen(bx, by)))
        elif self.shape:
            _, cx, cy, r = self.shape
            p.drawEllipse(QPointF(*self.to_screen(cx, cy)), r * c, r * c)

        self._draw_labels(p, w, h, x0, y0, xmin, xmax, ymin, ymax)

        # информационная строка
        info = f"1 пиксель = {c:.1f} px экрана"
        if self.hover:
            info += f"   |   курсор над пикселем ({self.hover[0]}, {self.hover[1]})"
        p.setPen(Qt.black)
        p.fillRect(QRectF(0, h - 22, w, 22), QColor(255, 255, 255, 220))
        p.drawText(QRectF(8, h - 22, w, 22), Qt.AlignVCenter, info)

    def _draw_labels(self, p, w, h, x0, y0, xmin, xmax, ymin, ymax):
        """Подписи делений. Шаг подбирается так, чтобы подписи не налезали друг на друга;
        если ось ушла за край окна, подписи прижимаются к краю и остаются видимыми."""
        p.setFont(QFont("Arial", 9))
        fm = QFontMetrics(p.font())
        fh = fm.height()
        widest = max(fm.horizontalAdvance(str(v)) for v in (xmin, xmax, ymin, ymax))
        c = self.cell
        step_x = next(s for s in NICE_STEPS if s * c >= widest + 12)
        step_y = next(s for s in NICE_STEPS if s * c >= fh + 6)

        ly = min(max(y0 + 4, 2), h - fh - 26)          # строка подписей оси X
        rx = min(max(x0 - 6, widest + 4), w - 4)       # правый край подписей оси Y
        p.setPen(Qt.black)
        for i in range(math.ceil(xmin / step_x) * step_x, xmax + 1, step_x):
            sx = x0 + i * c
            half = fm.horizontalAdvance(str(i)) / 2
            if i != 0 and half <= sx <= w - half:          # подпись целиком помещается
                p.drawLine(QLineF(sx, y0 - 3, sx, y0 + 3))
                p.drawText(QRectF(sx - 40, ly, 80, fh), Qt.AlignHCenter, str(i))
        for j in range(math.ceil(ymin / step_y) * step_y, ymax + 1, step_y):
            sy = y0 - j * c
            if j != 0 and 40 <= sy <= h - 26:
                p.drawLine(QLineF(x0 - 3, sy, x0 + 3, sy))
                p.drawText(QRectF(rx - 80, sy - fh / 2, 80, fh), Qt.AlignRight | Qt.AlignVCenter, str(j))
        if 0 <= x0 <= w and 0 <= y0 <= h:
            p.drawText(QRectF(x0 - 86, y0 + 4, 80, fh), Qt.AlignRight, "0")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Базовые растровые алгоритмы")
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.9), int(screen.height() * 0.9))

        self.algo = QComboBox()
        self.algo.addItems([name for name, _ in ALGORITHMS])
        self.algo.currentIndexChanged.connect(self.on_algo)

        def spin(value, lo=-1000, hi=1000):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setValue(value)
            return s

        self.x1, self.y1, self.x2, self.y2 = spin(0), spin(0), spin(8), spin(5)
        self.cx, self.cy, self.r = spin(0), spin(0), spin(8, 1, 1000)

        form = QFormLayout()
        form.addRow("Алгоритм:", self.algo)
        self.line_rows = [("Начало (x1, y1):", self.x1, self.y1), ("Конец (x2, y2):", self.x2, self.y2)]
        self.circle_rows = [("Центр (cx, cy):", self.cx, self.cy), ("Радиус R:", self.r)]
        self.row_widgets = []
        for label, *edits in self.line_rows + self.circle_rows:
            box = QWidget()
            hb = QHBoxLayout(box)
            hb.setContentsMargins(0, 0, 0, 0)
            for ed in edits:
                hb.addWidget(ed)
            lbl = QLabel(label)
            form.addRow(lbl, box)
            self.row_widgets.append((lbl, box))

        btn_draw = QPushButton("Построить")
        btn_draw.clicked.connect(self.draw)
        btn_bench = QPushButton("Сравнить время всех алгоритмов")
        btn_bench.clicked.connect(self.benchmark)

        hint = QLabel(
            "Пиксель (x, y) — клетка с центром в целой точке (x, y), линии сетки — "
            "границы пикселей (x ± 0.5). Красное — идеальная фигура, синее — пиксели.<br>"
            "ЛКМ — сдвиг, колесо — масштаб.")
        hint.setWordWrap(True)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setLineWrapMode(QTextEdit.NoWrap)

        left = QVBoxLayout()
        left.addLayout(form)
        left.addWidget(btn_draw)
        left.addWidget(btn_bench)
        left.addWidget(hint)
        left.addWidget(self.output, 1)
        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFont(QFont("Arial", 11))  # крупнее шрифт панели параметров

        self.canvas = Canvas()
        central = QWidget()
        root = QHBoxLayout(central)
        root.addWidget(left_w, 1)  # панель : график = 1 : 2
        root.addWidget(self.canvas, 2)
        self.setCentralWidget(central)
        self.on_algo()

    def on_algo(self):
        is_circle = self.algo.currentIndex() == 3
        for i, (lbl, box) in enumerate(self.row_widgets):
            visible = (i >= 2) == is_circle
            lbl.setVisible(visible)
            box.setVisible(visible)
        self.draw()

    def draw(self):
        idx = self.algo.currentIndex()
        name, func = ALGORITHMS[idx]
        if idx == 3:
            args = (self.cx.value(), self.cy.value(), self.r.value())
            shape = ("circle", *args)
            title = f"центр ({args[0]}, {args[1]}), R = {args[2]}"
        else:
            args = (self.x1.value(), self.y1.value(), self.x2.value(), self.y2.value())
            shape = ("line", *args)
            title = f"отрезок ({args[0]}, {args[1]}) — ({args[2]}, {args[3]})"

        log = []
        pixels = func(*args, log=log)       # вызов с разбором — для вывода вычислений
        t = avg_time(func, args)            # замер — без разбора
        self.canvas.set_figure(pixels, shape)

        limit = 60
        out = [f"{name}: {title}",
               f"Пикселей: {len(pixels)}",
               f"Время одного вызова: {t * 1e6:.2f} мкс (среднее)",
               "", "Вычисления:"]
        out += log[:limit]
        if len(log) > limit:
            out.append(f"... ещё {len(log) - limit} строк")
        self.output.setPlainText("\n".join(out))

    def benchmark(self):
        """Таблица времени для отчёта: отрезок (0,0)-(N, N/2) и окружность R = N."""
        sizes = (10, 100, 1000)
        out = ["Среднее время одного вызова, мкс",
               "отрезок (0,0)-(N, N/2), окружность R = N", "",
               f"{'Алгоритм':24}" + "".join(f"{'N=' + str(n):>11}" for n in sizes)]
        for name, func in ALGORITHMS:
            row = f"{name:24}"
            for n in sizes:
                args = (0, 0, n) if func is ra.bresenham_circle else (0, 0, n, n // 2)
                row += f"{avg_time(func, args) * 1e6:11.2f}"
            out.append(row)
        self.output.setPlainText("\n".join(out))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.draw()  # повторно, когда холст уже получил реальный размер
    sys.exit(app.exec_())
