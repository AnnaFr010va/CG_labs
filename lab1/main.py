import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QSlider, QDoubleSpinBox,
    QVBoxLayout, QHBoxLayout, QGroupBox, QFrame, QLineEdit
)
from PyQt5.QtCore import Qt, QPointF, QRegExp
from PyQt5.QtGui import (
    QColor, QPainter, QFont, QGuiApplication, QLinearGradient, QPen,
    QRegExpValidator
)

EPS = 1e-9

def clamp(x, l, h):
    return max(l, min(h, x))

def rgb_to_cmyk(r, g, b):
    r, g, b = r/255, g/255, b/255
    k = 1 - max(r, g, b)
    if k >= 1 - EPS:
        return 0, 0, 0, 100
    return ((1-r-k)/(1-k)*100, (1-g-k)/(1-k)*100, (1-b-k)/(1-k)*100, k*100)

def cmyk_to_rgb(c, m, y, k):
    c, m, y, k = c/100, m/100, y/100, k/100
    return (255*(1-c)*(1-k), 255*(1-m)*(1-k), 255*(1-y)*(1-k))

def rgb_to_hsv(r, g, b):
    r, g, b = r/255, g/255, b/255
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    s = 0 if mx == 0 else d/mx
    if d == 0:   h = 0
    elif mx == r: h = (60*((g-b)/d)) % 360
    elif mx == g: h = 60*((b-r)/d + 2)
    else:         h = 60*((r-g)/d + 4)
    return h, s*100, mx*100

def hsv_to_rgb(h, s, v):
    s, v = s/100, v/100
    if s == 0:
        x = v*255
        return x, x, x
    h %= 360
    i, f = int(h//60), h/60 - int(h//60)
    m, n, k = v*(1-s), v*(1-s*f), v*(1-s*(1-f))
    r, g, b = [(v,k,m),(n,v,m),(m,v,k),(m,n,v),(k,m,v),(v,m,n)][i % 6]
    return r*255, g*255, b*255

def to_qcolor(rgb):
    return QColor(*(int(round(clamp(x, 0, 255))) for x in rgb))

# Описание моделей
# (ключ, заголовок, [(имя канала, минимум, максимум)], кол-во знаков после запятой)

MODELS = [
    ("cmyk", "CMYK  (C, M, Y, K: 0..100 %)",
     [("C",0,100),("M",0,100),("Y",0,100),("K",0,100)], 0),
    ("rgb", "RGB  (R, G, B: 0..255)",
     [("R",0,255),("G",0,255),("B",0,255)], 0),
    ("hsv", "HSV  (H: 0..360°, S, V: 0..100 %)",
     [("H",0,360),("S",0,100),("V",0,100)], 0),
]

BASIC_COLORS = [
    (255,0,0), (255,255,0), (0,255,0), (0,255,255),
    (0,0,255), (255,0,255),
]


class ChannelRow(QWidget):
    def __init__(self, name, l, h, decimals, on_change):
        super().__init__()
        self.on_change = on_change
        self._lock = False
        self.scale = 10 ** decimals
        self.label = QLabel(name)
        self.label.setFixedWidth(22)
        self.label.setObjectName("chanLabel")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(l*self.scale, h*self.scale)
        self.spin = QDoubleSpinBox()
        self.spin.setRange(l, h)
        self.spin.setDecimals(decimals)
        self.spin.setFixedWidth(84)
        self.slider.valueChanged.connect(
            lambda v: self._sync(v/self.scale, self.spin.setValue))
        self.spin.valueChanged.connect(
            lambda v: self._sync(v, lambda x: self.slider.setValue(round(x*self.scale))))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(10)
        for w in (self.label, self.slider, self.spin):
            lay.addWidget(w)

    def _sync(self, v, set_other):
        if self._lock: return
        self._lock = True
        set_other(v)
        self._lock = False
        self.on_change()

    def value(self): return self.spin.value()

    def set_value(self, v):
        self._lock = True
        self.spin.setValue(v)
        self.slider.setValue(round(v*self.scale))
        self._lock = False

class SVSquare(QWidget):
    def __init__(self, on_pick):
        super().__init__()
        self.on_pick = on_pick
        self.h, self.s, self.v = 0, 100, 100
        self.setMinimumSize(200, 200)
        self.setCursor(Qt.CrossCursor)

    def set_hsv(self, h, s, v):
        self.h, self.s, self.v = h, s, v
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, to_qcolor(hsv_to_rgb(self.h, 100, 100)))
        g = QLinearGradient(0, 0, w, 0)
        g.setColorAt(0, QColor(255,255,255))
        g.setColorAt(1, QColor(255,255,255,0))
        p.fillRect(0, 0, w, h, g)
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(0,0,0,0))
        g.setColorAt(1, QColor(0,0,0))
        p.fillRect(0, 0, w, h, g)
        x, y = self.s/100*(w-1), (1 - self.v/100)*(h-1)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0,0,0), 3))
        p.drawEllipse(QPointF(x, y), 6, 6)
        p.setPen(QPen(QColor(255,255,255), 1.5))
        p.drawEllipse(QPointF(x, y), 6, 6)

    def mousePressEvent(self, e): self._pick(e.pos())
    def mouseMoveEvent(self, e):  self._pick(e.pos())

    def _pick(self, pos):
        s = clamp(pos.x()/(self.width()-1)*100, 0, 100)
        v = clamp((1 - pos.y()/(self.height()-1))*100, 0, 100)
        self.on_pick(s, v)

class HueStrip(QWidget):
    def __init__(self, on_pick):
        super().__init__()
        self.on_pick = on_pick
        self.h = 0
        self.setFixedWidth(26)
        self.setMinimumHeight(200)
        self.setCursor(Qt.PointingHandCursor)

    def set_hue(self, h):
        self.h = h
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, h)
        for i in range(7):
            g.setColorAt(i/6, to_qcolor(hsv_to_rgb(i*60, 100, 100)))
        p.fillRect(0, 0, w, h, g)
        y = round(self.h/360*(h-1))
        p.setPen(QPen(QColor(0,0,0), 3))
        p.drawLine(0, y, w, y)
        p.setPen(QPen(QColor(255,255,255), 1))
        p.drawLine(0, y, w, y)

    def mousePressEvent(self, e): self._pick(e.pos())
    def mouseMoveEvent(self, e):  self._pick(e.pos())

    def _pick(self, pos):
        self.on_pick(clamp(pos.y()/(self.height()-1)*360, 0, 360))

class Swatch(QFrame):
    def __init__(self, rgb, on_click):
        super().__init__()
        self.rgb, self.on_click = rgb, on_click
        self.setFixedSize(30, 30)
        self.setToolTip(to_qcolor(rgb).name().upper())
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(255,255,255,60))
        p.setBrush(to_qcolor(self.rgb))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.on_click(self.rgb)

class ColorPreview(QFrame):
    def __init__(self):
        super().__init__()
        self._color = QColor(255, 0, 0)
        self.setMinimumSize(120, 120)

    def set_color(self, c):
        self._color = c
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        side = min(self.width(), self.height()) - 4
        x, y = (self.width()-side)//2, (self.height()-side)//2
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0,0,0,80))
        p.drawRoundedRect(x+4, y+4, side, side, 10, 10)
        p.setBrush(self._color)
        p.drawRoundedRect(x, y, side, side, 10, 10)
        p.setBrush(Qt.NoBrush)
        p.setPen(QColor(255,255,255,60))
        p.drawRoundedRect(x, y, side, side, 10, 10)


class ColorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Цветовые модели: CMYK - RGB - HSV")
        self.rgb  = (0, 0, 0)
        self.cmyk = (0, 0, 0, 0)
        self.hsv  = (0, 0, 0)
        self.groups = {}

        left = QVBoxLayout()
        left.setSpacing(14)
        for key, title, chans, decimals in MODELS:
            box = QGroupBox(title)
            lay = QVBoxLayout(box)
            lay.setContentsMargins(12, 18, 12, 12)
            lay.setSpacing(8)
            rows = []
            for n, lo, hi in chans:
                row = ChannelRow(n, lo, hi, decimals,
                                 lambda k=key: self.on_model_changed(k))
                lay.addWidget(row)
                rows.append(row)
            self.groups[key] = rows
            left.addWidget(box)
        left.addStretch(1)

        basic_box = QGroupBox("Базовые цвета")
        basic = QHBoxLayout(basic_box)
        basic.setContentsMargins(12, 18, 12, 12)
        basic.setSpacing(8)
        for rgb in BASIC_COLORS:
            basic.addWidget(Swatch(rgb, self.on_swatch_click))
        basic.addStretch(1)
        left.addWidget(basic_box)

        self.sv  = SVSquare(self.on_sv_pick)
        self.hue = HueStrip(self.on_hue_pick)
        pal_box = QGroupBox("Палитра")
        pal = QHBoxLayout(pal_box)
        pal.setContentsMargins(12, 18, 12, 12)
        pal.setSpacing(10)
        pal.addWidget(self.sv, 1)
        pal.addWidget(self.hue)

        self.preview = ColorPreview()

        self.hex_edit = QLineEdit()
        self.hex_edit.setValidator(QRegExpValidator(QRegExp("#?[0-9A-Fa-f]{0,6}")))
        self.hex_edit.editingFinished.connect(self.on_hex_entered)
        hex_row = QHBoxLayout()
        hex_row.addWidget(QLabel("HEX"))
        hex_row.addWidget(self.hex_edit, 1)

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(pal_box, 3)
        right.addWidget(self.preview, 2)
        right.addLayout(hex_row)

        root = QHBoxLayout(self)
        root.setContentsMargins(18,18,18,18)
        root.setSpacing(18)
        root.addLayout(left, 3)
        root.addLayout(right, 2)

        self.set_color((255, 0, 0), source=None)

    def on_model_changed(self, key):
        values = tuple(row.value() for row in self.groups[key])
        if key == "rgb":
            self.set_color(values, source="rgb")
        elif key == "cmyk":
            self.set_color(cmyk_to_rgb(*values), source="cmyk", cmyk=values)
        else:
            self.set_color(hsv_to_rgb(*values), source="hsv", hsv=values)

    def on_sv_pick(self, s, v):
        hsv = (self.hsv[0], s, v)
        self.set_color(hsv_to_rgb(*hsv), source="palette", hsv=hsv)

    def on_hue_pick(self, h):
        hsv = (h, self.hsv[1], self.hsv[2])
        self.set_color(hsv_to_rgb(*hsv), source="palette", hsv=hsv)

    def on_hex_entered(self):
        text = self.hex_edit.text().lstrip("#")
        if len(text) != 6:
            self.refresh_ui(source=None)
            return
        rgb = tuple(int(text[i:i+2], 16) for i in (0, 2, 4))
        self.set_color(rgb, source="hex")

    def on_swatch_click(self, rgb):
        self.set_color(rgb, source="swatch")

    def set_color(self, rgb, source, cmyk=None, hsv=None):
        self.rgb  = tuple(rgb)
        self.cmyk = cmyk if cmyk is not None else self._cmyk_from_rgb()
        self.hsv  = hsv  if hsv  is not None else self._hsv_from_rgb()
        self.refresh_ui(source)

    def _cmyk_from_rgb(self):
        c, m, y, k = rgb_to_cmyk(*self.rgb)
        if k >= 100 - EPS:
            c, m, y = self.cmyk[:3]
        return c, m, y, k

    def _hsv_from_rgb(self):
        h, s, v = rgb_to_hsv(*self.rgb)
        old_h, old_s, _ = self.hsv
        if v <= EPS:
            h, s = old_h, old_s
        elif s <= EPS:
            h = old_h
        return h, s, v

    def refresh_ui(self, source):
        for key, rows in self.groups.items():
            if key == source: continue
            for row, v in zip(rows, getattr(self, key)):
                row.set_value(v)
        self.sv.set_hsv(*self.hsv)
        self.hue.set_hue(self.hsv[0])
        color = to_qcolor(self.rgb)
        self.preview.set_color(color)
        if source != "hex":
            self.hex_edit.setText(color.name().upper())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("""
        QWidget { background:#1e1f22; color:#e6e6e6; font-size:10pt; }
        QGroupBox { border:1px solid #35373b; border-radius:10px; margin-top:14px; padding:10px; }
        QGroupBox::title { subcontrol-origin:margin; left:12px; color:#9aa4b2; font-weight:600; }
        QLabel#chanLabel { color:#9aa4b2; font-weight:600; }
        QSlider::groove:horizontal { height:6px; background:#2c2f33; border-radius:3px; }
        QSlider::sub-page:horizontal { background:#4a90d9; border-radius:3px; }
        QSlider::handle:horizontal { background:#e6e6e6; width:14px; margin:-5px 0; border-radius:7px; }
        QDoubleSpinBox, QLineEdit { background:#2a2c30; border:1px solid #3a3d42; border-radius:6px; padding:3px 6px; }
        QDoubleSpinBox:focus, QLineEdit:focus { border:1px solid #4a90d9; }
    """)

    s = QGuiApplication.primaryScreen().availableGeometry()
    w, h = int(s.width()*0.6), int(s.height()*0.75)
    win = ColorApp()
    win.resize(w, h)
    win.move(s.center().x() - w//2, s.center().y() - h//2)
    win.show()
    sys.exit(app.exec_())
