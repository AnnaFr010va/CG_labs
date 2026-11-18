import math
import os
import sys

from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QPolygonF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox, QSizePolicy,
)

import algorithms as ca

NICE_STEPS = [m * 10 ** e for e in range(7) for m in (1, 2, 5)]  # 1, 2, 5, 10, 20, 50, ...

# Цвета для отрисовки.
COLOR_WINDOW = QColor(40, 140, 60)      # отсекающее окно / многоугольник — зелёный
COLOR_ORIG = QColor(180, 60, 60)        # исходные отрезки — красный
COLOR_CLIPPED = QColor(20, 60, 200)     # видимые части — синий


def rnd(v):
    """Округление координаты до целого (для подписи под курсором)."""
    return int(round(v))

class Canvas(QWidget):
    """Сетка, оси, подписи, отрезки и отсекающее окно. ЛКМ — сдвиг, колесо — масштаб."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.cell = 25.0                    # размер единицы координат на экране, px
        self.ox = self.oy = 0.0             # сдвиг начала координат от центра виджета
        self.segments = []                  # исходные отрезки
        self.clipped = []                   # видимые части
        self.window = None                  # (xmin, ymin, xmax, ymax) для прямоугольника
        self.polygon = None                 # список вершин для Кируса-Бека
        self.hover = None
        self._drag = None

    # преобразование координат
    def origin(self):
        return self.width() / 2 + self.ox, self.height() / 2 + self.oy

    def to_screen(self, x, y):
        x0, y0 = self.origin()
        return x0 + x * self.cell, y0 - y * self.cell

    def set_scene(self, segments, window=None, polygon=None, clipped=None):
        self.segments = segments or []
        self.window = window
        self.polygon = polygon
        self.clipped = clipped or []

        xs, ys = [], []
        for (p1, p2) in self.segments:
            xs += [p1[0], p2[0]]
            ys += [p1[1], p2[1]]
        if window:
            xs += [window[0], window[2]]
            ys += [window[1], window[3]]
        if polygon:
            for (px, py) in polygon:
                xs.append(px)
                ys.append(py)
        if not xs:
            xs, ys = [0, 10], [0, 10]

        bw = max(xs) - min(xs)
        bh = max(ys) - min(ys)
        bw = max(bw, 1.0)
        bh = max(bh, 1.0)
        # Подбираем cell так, чтобы сцена помещалась с отступами.
        margin = 80
        cw = (self.width() - 2 * margin) / bw if bw > 0 else 60.0
        ch = (self.height() - 2 * margin) / bh if bh > 0 else 60.0
        self.cell = max(5.0, min(80.0, cw, ch))
        # Центрируем сцену.
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        self.ox = -cx * self.cell
        self.oy = cy * self.cell
        self.update()

    # --- мышь ---
    def wheelEvent(self, e):
        new = max(2.0, min(300.0, self.cell * 1.15 ** (e.angleDelta().y() / 120)))
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
        self.hover = (rnd((e.x() - x0) / self.cell), rnd((y0 - e.y()) / self.cell))
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(Qt.ArrowCursor)

    # отрисовка
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, c = self.width(), self.height(), self.cell
        x0, y0 = self.origin()
        p.fillRect(self.rect(), Qt.white)

        # видимый диапазон координат
        xmin, xmax = math.floor(-x0 / c) - 1, math.ceil((w - x0) / c) + 1
        ymin, ymax = math.floor((y0 - h) / c) - 1, math.ceil(y0 / c) + 1

        # сетка на целых координатах
        if c >= 6:
            p.setPen(QPen(QColor(225, 225, 225), 1))
            for i in range(xmin, xmax + 1):
                sx = x0 + i * c
                p.drawLine(QLineF(sx, 0, sx, h))
            for j in range(ymin, ymax + 1):
                sy = y0 - j * c
                p.drawLine(QLineF(0, sy, w, sy))

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

        # отсекающее окно (прямоугольник или выпуклый многоугольник)
        if self.window:
            self._draw_window(p)
        if self.polygon:
            self._draw_polygon(p)

        # исходные отрезки (с номерами у начальной точки)
        p.setFont(QFont("Arial", 9))
        for i, (p1, p2) in enumerate(self.segments):
            p.setPen(QPen(COLOR_ORIG, 2))
            p.drawLine(QLineF(*self.to_screen(*p1), *self.to_screen(*p2)))
            sx, sy = self.to_screen(*p1)
            p.drawText(QPointF(sx + 4, sy - 4), str(i + 1))

        # видимые части и их концы (точки пересечения)
        if self.clipped:
            p.setPen(QPen(COLOR_CLIPPED, 4))
            p.setBrush(COLOR_CLIPPED)
            for (p1, p2) in self.clipped:
                a, b = QPointF(*self.to_screen(*p1)), QPointF(*self.to_screen(*p2))
                p.drawLine(QLineF(a, b))
                p.drawEllipse(a, 3, 3)
                p.drawEllipse(b, 3, 3)

        self._draw_labels(p, w, h, x0, y0, xmin, xmax, ymin, ymax)

        # информационная строка
        info = f"1 ед. = {c:.1f} px"
        if self.hover:
            info += f"   |   курсор: ({self.hover[0]}, {self.hover[1]})"
        p.setPen(Qt.black)
        p.fillRect(QRectF(0, h - 22, w, 22), QColor(255, 255, 255, 220))
        p.drawText(QRectF(8, h - 22, w, 22), Qt.AlignVCenter, info)

    def _draw_window(self, p):
        """Прямоугольное окно — заливка и контур."""
        xmin, ymin, xmax, ymax = self.window
        sx1, sy1 = self.to_screen(xmin, ymax)   # верхний левый
        sx2, sy2 = self.to_screen(xmax, ymin)   # нижний правый
        rect = QRectF(sx1, sy1, sx2 - sx1, sy2 - sy1)
        p.setBrush(QColor(40, 180, 70, 40))
        p.setPen(QPen(COLOR_WINDOW, 2))
        p.drawRect(rect)

    def _draw_polygon(self, p):
        """Выпуклый многоугольник — заливка и контур."""
        poly = QPolygonF([QPointF(*self.to_screen(x, y)) for (x, y) in self.polygon])
        p.setBrush(QColor(40, 180, 70, 40))
        p.setPen(QPen(COLOR_WINDOW, 2))
        p.drawPolygon(poly)
        # Подписываем вершины
        p.setPen(Qt.darkGreen)
        p.setFont(QFont("Arial", 9, QFont.Bold))
        for i, (x, y) in enumerate(self.polygon):
            sx, sy = self.to_screen(x, y)
            p.drawEllipse(QPointF(sx, sy), 3, 3)
            p.drawText(QPointF(sx + 6, sy - 6), f"V{i+1}({rnd(x)},{rnd(y)})")

    def _draw_labels(self, p, w, h, x0, y0, xmin, xmax, ymin, ymax):
        p.setFont(QFont("Arial", 9))
        fm = QFontMetrics(p.font())
        fh = fm.height()
        widest = max(fm.horizontalAdvance(str(v)) for v in (xmin, xmax, ymin, ymax))
        c = self.cell
        step_x = next(s for s in NICE_STEPS if s * c >= widest + 12)
        step_y = next(s for s in NICE_STEPS if s * c >= fh + 6)

        ly = min(max(y0 + 4, 2), h - fh - 26)
        rx = min(max(x0 - 6, widest + 4), w - 4)
        p.setPen(Qt.black)
        for i in range(math.ceil(xmin / step_x) * step_x, xmax + 1, step_x):
            sx = x0 + i * c
            half = fm.horizontalAdvance(str(i)) / 2
            if i != 0 and half <= sx <= w - half:
                p.drawLine(QLineF(sx, y0 - 3, sx, y0 + 3))
                p.drawText(QRectF(sx - 40, ly, 80, fh), Qt.AlignHCenter, str(i))
        for j in range(math.ceil(ymin / step_y) * step_y, ymax + 1, step_y):
            sy = y0 - j * c
            if j != 0 and 40 <= sy <= h - 26:
                p.drawLine(QLineF(x0 - 3, sy, x0 + 3, sy))
                p.drawText(QRectF(rx - 80, sy - fh / 2, 80, fh),
                           Qt.AlignRight | Qt.AlignVCenter, str(j))
        if 0 <= x0 <= w and 0 <= y0 <= h:
            p.drawText(QRectF(x0 - 86, y0 + 4, 80, fh), Qt.AlignRight, "0")

class MainWindow(QMainWindow):
    MODES = [
        "Алгоритм средней точки",     # часть 1: прямоугольное окно
        "Алгоритм Кируса-Бека",       # часть 2: выпуклый многоугольник
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лаб. №4. Алгоритмы отсечения отрезков (вариант 12)")
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.9), int(screen.height() * 0.9))

        self.segments, self.rect_window, self.polygon = [], None, None

        # --- левая панель ---
        self.mode = QComboBox()
        self.mode.addItems(self.MODES)
        self.mode.currentIndexChanged.connect(self.apply_clipping)

        btn_open = QPushButton("Загрузить входной файл…")
        btn_open.clicked.connect(self.on_open)

        legend = QLabel(
            "<b>Цвета:</b><br>"
            "<span style='color:#288c3c'>■</span> отсекающее окно / многоугольник<br>"
            "<span style='color:#b43c3c'>■</span> исходные отрезки<br>"
            "<span style='color:#143cc8'>■</span> видимые части отрезков")
        legend.setWordWrap(True)

        left = QVBoxLayout()
        left.addWidget(QLabel("Алгоритм отсечения:"))
        left.addWidget(self.mode)
        left.addWidget(btn_open)
        left.addWidget(legend)
        left.addStretch(1)
        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFont(QFont("Arial", 14))

        self.canvas = Canvas()
        central = QWidget()
        root = QHBoxLayout(central)
        for wdg, stretch in ((left_w, 1), (self.canvas, 3)):
            # ширина задаётся только коэффициентом растяжения, а не содержимым
            wdg.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            root.addWidget(wdg, stretch)
        self.setCentralWidget(central)

        default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input.txt")
        if os.path.exists(default):
            self.load_file(default)

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть входной файл", os.getcwd(), "Текст (*.txt);;Все файлы (*)")
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            segs, win, poly = ca.parse_input(path)
            if poly:
                poly = ca.prepare_polygon(poly)   # проверка выпуклости + обход против часовой стрелки
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать файл:\n{exc}")
            return
        self.segments, self.rect_window, self.polygon = segs, win, poly
        self.apply_clipping()

    def apply_clipping(self):
        if self.rect_window is None:
            return
        if self.mode.currentIndex() == 0:
            clipped = [ca.midpoint_clip(p1, p2, *self.rect_window) for p1, p2 in self.segments]
            self.canvas.set_scene(self.segments, window=self.rect_window,
                                  clipped=[c for c in clipped if c])
        elif self.polygon:
            clipped = [ca.cyrus_beck_clip(p1, p2, self.polygon) for p1, p2 in self.segments]
            self.canvas.set_scene(self.segments, polygon=self.polygon,
                                  clipped=[c for c in clipped if c])
        else:
            QMessageBox.warning(self, "Ошибка", "Во входном файле не задан многоугольник.")
            self.mode.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.apply_clipping()  # повторно, когда холст уже получил реальный размер
    sys.exit(app.exec_())
