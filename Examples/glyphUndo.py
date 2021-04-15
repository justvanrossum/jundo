from dataclasses import dataclass, field
from jundo import UndoManager


@dataclass
class Point:

    x: float
    y: float
    type: str = "line"
    smooth: bool = False


@dataclass
class Glyph:

    width: float = 0
    contours: list = field(default_factory=list)

    def drawPoints(self, pen):
        for c in self.contours:
            pen.beginPath()
            for pt in c:
                pen.addPoint((pt.x, pt.y), pt.type, pt.smooth)
            pen.endPath()


def drawGlyph(g):
    # needs DrawBot
    from drawbot_skia.drawbot import BezierPath, drawPath, translate
    # from drawBot import BezierPath, drawPath, translate
    bez = BezierPath()
    g.drawPoints(bez)
    drawPath(bez)
    translate(g.width, 0)


if __name__ == "__main__":
    modelGlyph = Glyph(width=200)
    um = UndoManager()
    proxyGlyph = um.setModel(modelGlyph)
    with um.changeSet(title="add a contour"):
        proxyGlyph.contours.append([])
        proxyGlyph.contours[-1].append(Point(100, 100))
        proxyGlyph.contours[-1].append(Point(100, 200))
        proxyGlyph.contours[-1].append(Point(200, 200))
        proxyGlyph.contours[-1].append(Point(200, 100))

    assert len(modelGlyph.contours) == 1
    assert len(modelGlyph.contours[0]) == 4

    with um.changeSet(title="add another contour"):
        proxyGlyph.contours.append([])
        proxyGlyph.contours[-1].append(Point(100, 300))
    with um.changeSet(title="add point"):
        proxyGlyph.contours[-1].append(Point(100, 400))
    with um.changeSet(title="add point"):
        proxyGlyph.contours[-1].append(Point(200, 400))
    with um.changeSet(title="add point"):
        proxyGlyph.contours[-1].append(Point(200, 300))
    assert len(modelGlyph.contours[1]) == 4

    um.undo()
    assert len(modelGlyph.contours[1]) == 3
    um.redo()
    assert len(modelGlyph.contours[1]) == 4

    with um.changeSet(title="move point"):
        proxyGlyph.contours[1][2].x += 30
        proxyGlyph.contours[1][2].y += 30
    assert modelGlyph.contours[1][2] == Point(230, 430)

    um.undo()
    assert modelGlyph.contours[1][2] == Point(200, 400)

    with um.changeSet(title="insert point"):
        proxyGlyph.contours[1].insert(2, Point(150, 430))
    assert modelGlyph.contours[1][2] == Point(150, 430)
    assert len(modelGlyph.contours[1]) == 5

    um.undo()
    assert len(modelGlyph.contours[1]) == 4
