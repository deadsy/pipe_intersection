#!/usr/bin/env python3

#------------------------------------------------------------------------------
"""

Intersect two cylinders
Create a 2D surface that can be wrapped around the cylinder to show the intersection curve.
That is: Create printable paper cutting templates for pipe intersection.

"""
#------------------------------------------------------------------------------

import math
from dxfwrite import DXFEngine as dxf

#------------------------------------------------------------------------------

# number of divisions around the cylinder circumference
_NDIVS = 32

#------------------------------------------------------------------------------

def r2d(r):
    """radians to degrees"""
    return (180.0 * r) / math.pi

#------------------------------------------------------------------------------

def dot(u, v):
    return (u[0] * v[0]) + (u[1] * v[1]) + (u[2] * v[2])

def scale(v, k):
    return (v[0] * k, v[1] * k, v[2] * k)

def normalize(v):
    l = math.sqrt(dot(v, v))
    return scale(v, 1.0/l)

def cross(u, v):
    return ((u[1] * v[2]) - (u[2] * v[1]), (u[2] * v[0]) - (u[0] * v[2]), (u[0] * v[1]) - (u[1] * v[0]))

#------------------------------------------------------------------------------

def gen_normal(v):
    """return a normal to a vector"""
    if v[0] == 0.0:
        return (1.0, 0.0, 0.0)
    if v[1] == 0.0:
        return (0.0, 1.0, 0.0)
    if v[2] == 0.0:
        return (0.0, 0.0, 1.0)
    return (0.0, v[2], -v[1])

#------------------------------------------------------------------------------

def line_x(l, t):
    """return the line position given the line and the t-parameter"""
    (u, v) = l
    return (u[0] + (v[0] * t), u[1] + (v[1] * t), u[2] + (v[2] * t))

#------------------------------------------------------------------------------

def quadratic(a, b, c):
    """return the real solutions of a quadratic"""
    a = float(a)
    b = float(b)
    c = float(c)
    if a == 0.0:
        if b == 0.0 and c == 0.0:
            return ('inf',)
        if b == 0.0 and c != 0.0:
            return ('inv',)
        if b != 0.0 and c == 0.0:
            return ('1', 0.0)
        if b != 0.0 and c != 0.0:
            return ('1', -c / b)
    # use the general form solution
    d = (b * b) - 4.0 * a * c
    if d == 0.0:
        return ('1', -b / (2.0 * a))
    if d < 0.0:
        # no real solutions
        return ('0',)
    d = math.sqrt(d)
    return ('2', (-b + d)/(2.0 * a), (-b - d)/(2.0 * a))

#------------------------------------------------------------------------------

class cylinder:
    def __init__(self, o, a, r, l, color):
        """
        o = origin coordinates
        a = axis vector
        l = length
        r = radius
        """
        self.o = o
        self.a = normalize(a)
        self.r = r
        self.l = l
        self.color = color
        # 1st normal to cylinder axis
        self.n0 = normalize(gen_normal(self.a))
        # 2nd normal to cylinder axis
        # a, n0 and n1 are orthogonal unit vectors
        self.n1 = normalize(cross(self.a, self.n0))

    def gen_lines(self):
        """
        Generate the cylinder surface lines used to intersect with
        the other cylinder.
        """
        lines = []
        # step around the parameterised base circle
        for i in range(_NDIVS):
            theta = 2.0 * math.pi * i / _NDIVS
            rc = self.r * math.cos(theta)
            rs = self.r * math.sin(theta)
            p = (self.o[0] + (rc * self.n0[0]) + (rs * self.n1[0]),
                 self.o[1] + (rc * self.n0[1]) + (rs * self.n1[1]),
                 self.o[2] + (rc * self.n0[2]) + (rs * self.n1[2]))
            # the line starts at point p and is in the direction of the cylinder axis
            lines.append((p, self.a))
        return lines

    def scad(self):
        """
        Generate OpenSCAD code for this cylinder.
        """
        s = []
        rx = r2d(math.atan2(self.a[1], self.a[2]))
        ry = r2d(math.atan2(self.a[0], self.a[2]))
        rz = r2d(math.atan2(self.a[0], self.a[1]))
        s.append('translate([%f, %f, %f])' % (self.o[0], self.o[1], self.o[2]))
        s.append('rotate([%f, %f, %f])' % (rx, ry, rz))
        s.append('color("%s")' % self.color)
        s.append('cylinder(h = %f, r = %f, $fn = 100);\n' % (self.l, self.r))
        return '\n'.join(s)

    def __str__(self):
        s = []
        s.append('o = (%f,%f,%f)' % (self.o[0], self.o[1], self.o[2]))
        s.append('a = (%f,%f,%f)' % (self.a[0], self.a[1], self.a[2]))
        s.append('r = %f' % self.r)
        s.append('l = %f' % self.l)
        return ' '.join(s)

    def intersect_line(self, l):
        """
        Intersect a line with this cylinder.
        Return the line t values for the intersection points.
        """
        (u, v) = l
        # re-express the line vector in terms of the orthogonal unit vectors
        # oriented to the cylinder axis.
        vn = (dot(v, self.n0), dot(v, self.n1), dot(v, self.a))
        # x = u + vn.t
        # d = dist to cylinder axis (ignore the component in self.a direction)
        # d^2 = (u0 + vn0 * t)^2 + (u1 + vn1 * t)^2
        # solve t for d = radius to find intersection points
        a = (vn[0] * vn[0]) + (vn[1] * vn[1])
        b = 2.0 * ((u[0] * vn[0]) + (u[1] * vn[1]))
        c = (u[0] * u[0]) + (u[1] * u[1]) - (self.r * self.r)
        return quadratic(a, b, c)

#------------------------------------------------------------------------------

def gen_scad(name, c0, c1):
    """
    Generate an OpenSCAD file to validate the cylinder positioning with a 3D model.
    """
    f = open(name, 'w')
    f.write(c0.scad())
    f.write(c1.scad())
    f.close()

#------------------------------------------------------------------------------

def gen_dxf(name, c0, c1):

    lines = c1.gen_lines()

    drawing = dxf.drawing(name)

    # base line is the circumfrence of c1
    base = 2.0 * math.pi * c1.r
    drawing.add(dxf.line((0.0, 0.0), (base, 0.0)))

    for i in range(_NDIVS):
        x = i * base / _NDIVS
        t_vals = c0.intersect_line(lines[i])
        if t_vals[0] == 'inf':
            pass
        elif t_vals[0] == '0':
            drawing.add(dxf.line((x, 0.0), (x, c1.l)))
        elif t_vals[0] == '1':
            drawing.add(dxf.line((x, 0.0), (x, c1.l)))
        elif t_vals[0] == '2':
            if t_vals[1] > t_vals[2]:
                y0 = t_vals[2]
                y1 = t_vals[1]
            else:
                y1 = t_vals[2]
                y0 = t_vals[1]
            drawing.add(dxf.line((x, 0.0), (x, y0)))
            drawing.add(dxf.line((x, y1), (x, c1.l)))

    drawing.save()

#------------------------------------------------------------------------------

def main():

    c0 = cylinder((0.0,0.0,-10.0), (0.0,0.0,1.0), 2.875/2.0, 20.0, 'red')
    c1 = cylinder((0.0,10.0,-10.0), (0.0,-1.0,1.0), 2.875/2.0, 20.0, 'blue')

    print(c0)
    print(c1)

    gen_scad('test.scad', c0, c1)
    gen_dxf('test.dxf', c0, c1)


main()

#------------------------------------------------------------------------------

