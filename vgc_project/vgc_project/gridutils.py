import numpy as np

def getFeatureXYs(trialArray, feature):
    xys = []
    height = len(trialArray)
    for _y in range(len(trialArray)):
        for x in range(len(trialArray[0])):
            if trialArray[_y][x] == feature:
                xys.append([x, height - _y - 1])
    return xys
def tonumpy(arr):
    return np.array([list(r) for r in arr])
def fromnumpy(arr):
    return [''.join(r) for r in arr]

transformations = {
    'base': lambda g: [r for r in g],
    'rot90': lambda g: fromnumpy(np.rot90(tonumpy(g), k=1)),
    'rot180': lambda g: fromnumpy(np.rot90(tonumpy(g), k=2)),
    'rot270': lambda g: fromnumpy(np.rot90(tonumpy(g), k=3)),
    'vflip': lambda g: fromnumpy(np.flipud(tonumpy(g))),
    'hflip': lambda g: fromnumpy(np.fliplr(tonumpy(g))),
    'trans': lambda g: fromnumpy(np.transpose(tonumpy(g))),
    'rtrans': lambda g: fromnumpy(np.rot90(np.transpose(tonumpy(g)), k=2)),
}

untransformations = {
    'base': transformations['base'],
    'rot90': transformations['rot270'],
    'rot180': transformations['rot180'],
    'rot270': transformations['rot90'],
    'vflip': transformations['vflip'],
    'hflip': transformations['hflip'],
    'trans': transformations['trans'],
    'rtrans': transformations['rtrans'],
}

def rotXY(deg, x, y, w, h, integer_state=True):
    rad = deg*np.pi/180
    rotMat = np.array([
        [np.cos(rad), -np.sin(rad)],
        [np.sin(rad), np.cos(rad)]
    ])
    c = np.array([w/2, h/2])
    cXY = np.array([x, y]) - c + (.5 if integer_state else 0)
    nx, ny = rotMat@cXY + c - (.5 if integer_state else 0)
    return nx, ny

def vflipXY(x, y, w, h, integer_state=True):
    return x, -(y + (.5 if integer_state else 0) - h/2) + h/2 - (.5 if integer_state else 0)

def hflipXY(x, y, w, h, integer_state=True):
    return -(x + (.5 if integer_state else 0) - w/2) + w/2 - (.5 if integer_state else 0), y

def transXY(x, y, w, h, integer_state=True):
    nx, ny = vflipXY(x, y, w, h, integer_state=integer_state)
    return rotXY(270, nx, ny, w, h, integer_state=integer_state)

def rtransXY(x, y, w, h, integer_state=True):
    nx, ny = hflipXY(x, y, w, h, integer_state=integer_state)
    return rotXY(270, nx, ny, w, h, integer_state=integer_state)

transformState = {
    'base': lambda g, s: s,
    'rot90': lambda g, s: rotXY(90, s[0], s[1], len(g[0]), len(g)),
    'rot180': lambda g, s: rotXY(180, s[0], s[1], len(g[0]), len(g)),
    'rot270': lambda g, s: rotXY(270, s[0], s[1], len(g[0]), len(g)),
    'vflip': lambda g, s: vflipXY(s[0], s[1], len(g[0]), len(g)),
    'hflip': lambda g, s: hflipXY(s[0], s[1], len(g[0]), len(g)),
    'trans': lambda g, s: transXY(s[0], s[1], len(g[0]), len(g)),
    'rtrans': lambda g, s: rtransXY(s[0], s[1], len(g[0]), len(g)),
}

untransformState = {
    'base': transformState['base'],
    'rot90': transformState['rot270'],
    'rot180': transformState['rot180'],
    'rot270': transformState['rot90'],
    'vflip': transformState['vflip'],
    'hflip': transformState['hflip'],
    'trans': transformState['trans'],
    'rtrans': transformState['rtrans'],
}

transformContinuousXY = { #used for points
    'base': lambda g, s: s,
    'rot90': lambda g, s: rotXY(90, s[0], s[1], len(g[0]), len(g), integer_state=False),
    'rot180': lambda g, s: rotXY(180, s[0], s[1], len(g[0]), len(g), integer_state=False),
    'rot270': lambda g, s: rotXY(270, s[0], s[1], len(g[0]), len(g), integer_state=False),
    'vflip': lambda g, s: vflipXY(s[0], s[1], len(g[0]), len(g), integer_state=False),
    'hflip': lambda g, s: hflipXY(s[0], s[1], len(g[0]), len(g), integer_state=False),
    'trans': lambda g, s: transXY(s[0], s[1], len(g[0]), len(g), integer_state=False),
    'rtrans': lambda g, s: rtransXY(s[0], s[1], len(g[0]), len(g), integer_state=False),
}

untransformContinuousXY = {
    'base': transformContinuousXY['base'],
    'rot90': transformContinuousXY['rot270'],
    'rot180': transformContinuousXY['rot180'],
    'rot270': transformContinuousXY['rot90'],
    'vflip': transformContinuousXY['vflip'],
    'hflip': transformContinuousXY['hflip'],
    'trans': transformContinuousXY['trans'],
    'rtrans': transformContinuousXY['rtrans'],
}

def min_dist(source, target, sourcename="s", targetname="t"):
    """Returns the minimum distance between two sets of locations"""
    mindist = float("inf")
    for si, s in enumerate(source):
        if isinstance(s, dict):
            s = (s['x'], s['y'])
        for ti, t in enumerate(target):
            if isinstance(t, dict):
                t = (t['x'], t['y'])
            dist = abs(s[0] - t[0]) + abs(s[1] - t[1])
            if dist <= mindist:
                if dist == mindist:
                    count += 1
                else:
                    count = 1
                mindist = dist
                min_sloc = s
                min_tloc = t
                min_si = si
                min_ti = ti
    return {
        "mindist": mindist,
        f"min{sourcename}loc.x": min_sloc[0],
        f"min{sourcename}loc.y": min_sloc[1],
        f"min{targetname}loc.x": min_tloc[0],
        f"min{targetname}loc.y": min_tloc[1],
        f"min{sourcename}i": min_si,
        f"min{targetname}i": min_ti,
        f"mindist.count": count
    }