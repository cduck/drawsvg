
import math
import numpy as np
import pwkit.colormaps  # pip3 install pwkit


# Most calculations from http://www.chilliant.com/rgb2hsv.html


def limit(v, low=0, high=1):
    return max(min(v, high), low)

class Srgb:
    LUMA_WEIGHTS = (0.299, 0.587, 0.114)
    def __init__(self, r, g, b):
        self.r = float(r)
        self.g = float(g)
        self.b = float(b)
    def __iter__(self):
        return iter((self.r, self.g, self.b))
    def __repr__(self):
        return 'RGB({}, {}, {})'.format(self.r, self.g, self.b)
    def __str__(self):
        return 'rgb({}%,{}%,{}%)'.format(self.r*100, self.g*100, self.b*100)
    def luma(self, wts=None):
        if wts is None: wts = self.LUMA_WEIGHTS
        rw, gw, bw = wts
        return rw*self.r + gw*self.g + bw*self.b
    def toSrgb(self):
        return self
    @staticmethod
    def fromHue(h):
        h = h % 1
        r = abs(h * 6 - 3) - 1
        g = 2 - abs(h * 6 - 2)
        b = 2 - abs(h * 6 - 4)
        return Srgb(limit(r), limit(g), limit(b))

class Hsl:
    def __init__(self, h, s, l):
        self.h = float(h) % 1
        self.s = float(s)
        self.l = float(l)
    def __iter__(self):
        return iter((self.h, self.s, self.l))
    def __repr__(self):
        return 'HSL({}, {}, {})'.format(self.h, self.s, self.l)
    def __str__(self):
        r, g, b = self.toSrgb()
        return 'rgb({}%,{}%,{}%)'.format(round(r*100), round(g*100), round(b*100))
    def toSrgb(self):
        hs = Srgb.fromHue(self.h)
        c = (1 - abs(2 * self.l - 1)) * self.s
        return Srgb(
            (hs.r - 0.5) * c + self.l,
            (hs.g - 0.5) * c + self.l,
            (hs.b - 0.5) * c + self.l
        )

class Hsv:
    def __init__(self, h, s, v):
        self.h = float(h) % 1
        self.s = float(s)
        self.v = float(v)
    def __iter__(self):
        return iter((self.h, self.s, self.v))
    def __repr__(self):
        return 'HSV({}, {}, {})'.format(self.h, self.s, self.v)
    def __str__(self):
        r, g, b = self.toSrgb()
        return 'rgb({}%,{}%,{}%)'.format(round(r*100), round(g*100), round(b*100))
    def toSrgb(self):
        hs = Srgb.fromHue(self.h)
        c = self.v * self.s
        hp = self.h * 6
        x = c * (1 - abs(hp % 2 - 1))
        if hp < 1:
            r1, g1, b1 = c, x, 0
        elif hp < 2:
            r1, g1, b1 = x, c, 0
        elif hp < 3:
            r1, g1, b1 = 0, c, x
        elif hp < 4:
            r1, g1, b1 = 0, x, c
        elif hp < 5:
            r1, g1, b1 = x, 0, c
        else:
            r1, g1, b1 = c, 0, x
        m = self.v - c
        return Srgb(r1+m, g1+m, b1+m)

class Sin:
    def __init__(self, h, s, l):
        self.h = float(h) % 1
        self.s = float(s)
        self.l = float(l)
    def __iter__(self):
        return iter((self.h, self.s, self.l))
    def __repr__(self):
        return 'Sin({}, {}, {})'.format(self.h, self.s, self.l)
    def __str__(self):
        r, g, b = self.toSrgb()
        return 'rgb({}%,{}%,{}%)'.format(round(r*100), round(g*100), round(b*100))
    def toSrgb(self):
        h = self.h
        scale = self.s / 2
        shift = self.l #* (1-2*scale)
        return Srgb(
            shift + scale * math.cos(math.pi*2 * (h - 0/6)),
            shift + scale * math.cos(math.pi*2 * (h - 2/6)),
            shift + scale * math.cos(math.pi*2 * (h - 4/6)),
        )

class Hcy:
    HCY_WEIGHTS = Srgb.LUMA_WEIGHTS
    def __init__(self, h, c, y):
        self.h = float(h) % 1
        self.c = float(c)
        self.y = float(y)
    def __iter__(self):
        return iter((self.h, self.c, self.y))
    def __repr__(self):
        return 'HCY({}, {}, {})'.format(self.h, self.c, self.y)
    def __str__(self):
        r, g, b = self.toSrgb()
        return 'rgb({}%,{}%,{}%)'.format(r*100, g*100, b*100)
    def toSrgb(self):
        hs = Srgb.fromHue(self.h)
        y = hs.luma(wts=self.HCY_WEIGHTS)
        c = self.c
        if self.y < y:
            c *= self.y / y
        elif y < 1:
            c *= (1 - self.y) / (1 - y)
        return Srgb(
            (hs.r - y) * c + self.y,
            (hs.g - y) * c + self.y,
            (hs.b - y) * c + self.y,
        )
    @staticmethod
    def _rgbToHcv(srgb):
        if srgb.g < srgb.b:
            p = (srgb.b, srgb.g, -1., 2./3.)
        else:
            p = (srgb.g, srgb.b, 0., -1./3.)
        if srgb.r < p[0]:
            q = (p[0], p[1], p[3], srgb.r)
        else:
            q = (srgb.r, p[1], p[2], p[0])
        c = q[0] - min(q[3], q[1])
        h = abs((q[3] - q[1]) / (6*c + 1e-10) + q[2])
        return (h, c, q[0])
    @classmethod
    def fromSrgb(cls, srgb):
        hcv = list(cls._rgbToHcv(srgb))
        rw, gw, bw = cls.HCY_WEIGHTS
        y = rw*srgb.r + gw*srgb.g + bw*srgb.b
        hs = Srgb.fromHue(hcv[0])
        z = rw*hs.r + gw*hs.g + bw*hs.b
        if y < z:
            hcv[1] *= z / (y + 1e-10)
        else:
            hcv[1] *= (1 - z) / (1 - y + 1e-10)
        return Hcy(hcv[0], hcv[1], y)

class Cielab:
    REF_WHITE = (0.95047, 1., 1.08883)
    def __init__(self, l, a, b):
        self.l = float(l)
        self.a = float(a)
        self.b = float(b)
    def __iter__(self):
        return iter((self.l, self.a, self.b))
    def __repr__(self):
        return 'CIELAB({}, {}, {})'.format(self.l, self.a, self.b)
    def __str__(self):
        r, g, b = self.toSrgb()
        return 'rgb({}%,{}%,{}%)'.format(round(r*100), round(g*100), round(b*100))
    def toSrgb(self):
        inArr = np.array((*self.l,), dtype=float)
        xyz = pwkit.colormaps.cielab_to_xyz(inArr, self.REF_WHITE)
        linSrgb = pwkit.colormaps.xyz_to_linsrgb(xyz)
        r, g, b = pwkit.colormaps.linsrgb_to_srgb(linSrgb)
        return Srgb(r, g, b)
    @classmethod
    def fromSrgb(cls, srgb, refWhite=None):
        if refWhite is None: refWhite = cls.REF_WHITE
        inArr = np.array((*srgb,), dtype=float)
        linSrgb = pwkit.colormaps.srgb_to_linsrgb(inArr)
        xyz = pwkit.colormaps.linsrgb_to_xyz(linSrgb)
        l, a, b = pwkit.colormaps.xyz_to_cielab(xyz, refWhite)
        return Cielab(l, a, b)
    def toSrgb(self):
        inArr = np.array((self.l, self.a, self.b))
        xyz = pwkit.colormaps.cielab_to_xyz(inArr, self.REF_WHITE)
        linSrgb = pwkit.colormaps.xyz_to_linsrgb(xyz)
        r, g, b = pwkit.colormaps.linsrgb_to_srgb(linSrgb)
        return Srgb(r, g, b)

