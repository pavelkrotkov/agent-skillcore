#!/usr/bin/env python3
"""Fit/check a floor-plane homography from JSON; Python standard library only."""
import json
import math
import sys


def pair(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float))
                   or not math.isfinite(v) for v in value)):
        raise ValueError('coordinates must be two finite numbers')
    return tuple(float(v) for v in value)


def solve(a, b):
    rows = [list(row) + [rhs] for row, rhs in zip(a, b)]
    n = len(b)
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(rows[i][col]))
        if abs(rows[pivot][col]) < 1e-10:
            raise ValueError('singular/ill-conditioned calibration; use better landmarks')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [v / scale for v in rows[col]]
        for i in range(n):
            if i != col:
                scale = rows[i][col]
                rows[i] = [u - scale*v for u, v in zip(rows[i], rows[col])]
    return [row[-1] for row in rows]


def normalize(points):
    center = tuple(sum(p[i] for p in points)/len(points) for i in (0, 1))
    spread = math.sqrt(sum((p[0]-center[0])**2 + (p[1]-center[1])**2
                           for p in points)/len(points))
    if spread < 1e-12:
        raise ValueError('degenerate landmarks')
    return center, spread


def fit(controls):
    if not isinstance(controls, list) or len(controls) < 4:
        raise ValueError('at least four controls are required')
    pixels = [pair(p['image']) for p in controls]
    court = [pair(p['court']) for p in controls]
    pc, ps = normalize(pixels)
    wc, ws = normalize(court)
    rows, rhs = [], []
    for (px, py), (cx, cy) in zip(pixels, court):
        x, y = (px-pc[0])/ps, (py-pc[1])/ps
        u, v = (cx-wc[0])/ws, (cy-wc[1])/ws
        rows.extend([[x, y, 1, 0, 0, 0, -u*x, -u*y],
                     [0, 0, 0, x, y, 1, -v*x, -v*y]])
        rhs.extend([u, v])
    normal = [[sum(row[i]*row[j] for row in rows) for j in range(8)]
              for i in range(8)]
    target = [sum(row[i]*v for row, v in zip(rows, rhs)) for i in range(8)]
    h = solve(normal, target)
    if not all(math.isfinite(v) for v in h):
        raise ValueError('non-finite calibration')
    return {'coefficients': h, 'image_center': pc, 'image_scale': ps,
            'court_center': wc, 'court_scale': ws}


def project(model, pixel):
    px, py = pair(pixel)
    pc, ps = model['image_center'], model['image_scale']
    wc, ws = model['court_center'], model['court_scale']
    x, y = (px-pc[0])/ps, (py-pc[1])/ps
    a, b, c, d, e, f, g, h = model['coefficients']
    divisor = g*x + h*y + 1
    if abs(divisor) < 1e-10:
        raise ValueError('point projects near infinity')
    result = [(a*x+b*y+c)/divisor*ws+wc[0],
              (d*x+e*y+f)/divisor*ws+wc[1]]
    if not all(math.isfinite(v) for v in result):
        raise ValueError('non-finite projection')
    return result


def reconstruct(data):
    controls, holdouts = data['controls'], data['holdouts']
    if not isinstance(holdouts, list) or not holdouts:
        raise ValueError('at least one independent holdout is required')
    model = fit(controls)
    control_pixels = {pair(p['image']) for p in controls}
    checks = []
    for item in holdouts:
        if pair(item['image']) in control_pixels:
            raise ValueError('holdout duplicates a fitted control')
        expected = pair(item['court'])
        projected = project(model, item['image'])
        checks.append({'image': item['image'], 'expected_court': expected,
                       'projected_court': projected,
                       'error_m': math.dist(expected, projected)})
    points, ids = [], set()
    for item in data.get('points', []):
        if item.get('kind') != 'floor':
            raise ValueError('only explicitly grounded floor points can be projected')
        if not isinstance(item.get('id'), str) or not item['id'] or item['id'] in ids:
            raise ValueError('point IDs must be unique nonempty strings')
        ids.add(item['id'])
        points.append({'id': item['id'], 'kind': 'floor', 'image': item['image'],
                       'court': project(model, item['image'])})
    return {'model': model, 'holdouts': checks,
            'holdout_rms_m': math.sqrt(sum(p['error_m']**2 for p in checks)/len(checks)),
            'holdout_max_m': max(p['error_m'] for p in checks), 'points': points,
            'warning': 'Floor estimates only. Inspect holdouts, camera geometry and uncertainty.'}


def main():
    if len(sys.argv) != 2:
        print('usage: floor_map.py calibration.json', file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding='utf-8') as handle:
            result = reconstruct(json.load(handle))
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        print(f'calibration error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
