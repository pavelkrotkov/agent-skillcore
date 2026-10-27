#!/usr/bin/env python3
"""Local media sampling, conservative review candidates and verified publication."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def probe(video):
    data = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(video)]))
    stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    rotation = stream.get('tags', {}).get('rotate', '0')
    rotations = [entry.get('rotation', 0) for entry in stream.get('side_data_list', [])]
    if float(rotation) % 360 or any(float(value) % 360 for value in rotations):
        raise ValueError('Rotated video requires an explicitly oriented working copy and crop coordinates')
    duration = float(stream.get('duration', data['format']['duration']))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Video duration must be positive and finite')
    return dict(width=stream['width'], height=stream['height'], duration=duration)


def rectangle(value):
    try:
        box = tuple(int(p) for p in value.split(','))
    except ValueError as error:
        raise argparse.ArgumentTypeError('Expected x,y,width,height integers') from error
    if len(box) != 4 or min(box[:2]) < 0 or min(box[2:]) <= 0:
        raise argparse.ArgumentTypeError('Expected nonnegative x,y and positive width,height')
    return box


def check_box(box, width, height):
    x, y, w, h = box
    if x + w > width or y + h > height:
        raise ValueError('Crop exceeds source dimensions')


def sample(args):
    from PIL import Image  # dependency check before allocating work
    video = args.video.resolve(strict=True)
    info = probe(video)
    if not math.isfinite(args.interval) or args.interval <= 0 or args.width < 1:
        raise ValueError('Interval and thumbnail width must be positive')
    args.output.mkdir(parents=True, exist_ok=False)
    before = digest(video)
    subprocess.run([
        'ffmpeg', '-v', 'error', '-threads', '2', '-filter_threads', '1', '-n',
        '-i', str(video), '-map', '0:v:0', '-an', '-vf',
        f"setpts=PTS-STARTPTS,select='gte(t,selected_n*{args.interval})',scale={args.width}:-1",
        '-fps_mode', 'vfr', '-q:v', '3', str(args.output / '%06d.jpg')], check=True)
    frames = sorted(args.output.glob('*.jpg'))
    expected = math.ceil(info['duration'] / args.interval)
    if len(frames) != expected or digest(video) != before:
        raise ValueError('Incomplete sampling or source changed; retain source and use a new work directory')
    with Image.open(frames[0]) as image:
        size = image.size
    write_json(args.output / 'sample.json', dict(
        source=str(video), source_sha256=before, **info, interval_seconds=args.interval,
        sample_dimensions=size, method='first decoded frame at/after each target; no keyframe restriction',
        samples=[dict(file=f.name, target_seconds=i * args.interval) for i, f in enumerate(frames)]))
    print(json.dumps(dict(samples=len(frames), manifest=str(args.output / 'sample.json'))))


def contact_sheets(items, samples, output):
    from PIL import Image, ImageDraw
    output.mkdir()
    for start in range(0, len(items), 30):
        subset = items[start:start+30]
        sheet = Image.new('RGB', (1600, 200 * math.ceil(len(subset)/5)), 'white')
        draw = ImageDraw.Draw(sheet)
        for j, item in enumerate(subset):
            x, y = j % 5 * 320, j // 5 * 200
            with Image.open(samples / item['file']) as image:
                sheet.paste(image.resize((320, 180)), (x, y))
            draw.text((x+3, y+182), f"{start+j}: {item['target_seconds']:g}s", fill='black')
        sheet.save(output / f'contact-{start//30:03}.jpg')


def dedupe(args):
    from PIL import Image, ImageChops, ImageStat
    if not math.isfinite(args.threshold) or args.threshold < 0:
        raise ValueError('Threshold must be nonnegative and finite')
    data = json.loads((args.samples / 'sample.json').read_text())
    if args.region:
        check_box(args.region, data['width'], data['height'])
    report = args.report or args.samples / 'review'
    report.mkdir(parents=True, exist_ok=False)
    representatives, mapping = [], []
    for item in data['samples']:
        path = args.samples / item['file']
        with Image.open(path) as image:
            im = image.convert('L')
        if args.region:
            x, y, w, h = args.region
            sx, sy = im.width / data['width'], im.height / data['height']
            im = im.crop((round(x*sx), round(y*sy), round((x+w)*sx), round((y+h)*sy)))
        im = im.resize((320, 180))
        diffs = [ImageStat.Stat(ImageChops.difference(im, old)).mean[0] for _, old in representatives]
        best = min(diffs) if diffs else None
        if best is None or best > args.threshold:
            representatives.append((item, im))
            index = len(representatives) - 1
        else:
            index = diffs.index(best)
        mapping.append(dict(**item, candidate=index, mean_difference=best))
    contact_sheets([item for item, _ in representatives], args.samples, report / 'candidates')
    contact_sheets(data['samples'], args.samples, report / 'all-samples')
    write_json(report / 'candidates.json', dict(
        source_sha256=data['source_sha256'], threshold=args.threshold,
        region_original_coordinates=args.region, samples=mapping,
        candidates=[item for item, _ in representatives],
        warning='Review all-samples as well: candidate filtering can suppress small numeric changes. This is not a count of substantive screenshares.'))
    print(json.dumps(dict(samples=len(mapping), candidates=len(representatives), report=str(report))))


def extract(args):
    video = args.video.resolve(strict=True)
    info = probe(video)
    if not math.isfinite(args.seconds) or not 0 <= args.seconds < info['duration']:
        raise ValueError('Extraction timestamp is outside video')
    check_box(args.crop, info['width'], info['height'])
    if args.output.suffix.lower() != '.png':
        raise ValueError('Evidence output must be a PNG')
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    x, y, w, h = args.crop
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-ss', str(args.seconds), '-i', str(video),
                    '-map', '0:v:0', '-frames:v', '1', '-vf', f'crop={w}:{h}:{x}:{y}:exact=1',
                    str(args.output)], check=True)
    if not args.output.is_file() or args.output.stat().st_size == 0:
        raise ValueError('No evidence frame was extracted')
    print(json.dumps(dict(source=str(video), seconds=args.seconds, crop=args.crop,
                          output=str(args.output), sha256=digest(args.output))))


def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlinked archive content refused: {path}')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f'Nonregular archive content refused: {path}')
        result[str(path.relative_to(root))] = dict(size=path.stat().st_size, sha256=digest(path))
    return result


def publish(args):
    source = args.stage.resolve(strict=True)
    destination = args.destination.absolute()
    if not source.is_dir():
        raise ValueError('Staging source must be a directory')
    if not destination.parent.is_dir():
        raise ValueError('Destination parent must already exist; check the share/mount')
    if any(p.is_symlink() for p in [destination, *destination.parents]):
        raise ValueError('Symlinked destination ancestors refused')
    destination = destination.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('Source and destination cannot overlap')
    lock = destination.parent / f'.{destination.name}.publish-lock'
    lock.mkdir()
    try:
        if destination.exists():
            raise FileExistsError(f'Publication target already exists: {destination}')
        expected = inventory(source)
        if not expected or 'publication.json' in expected:
            raise ValueError('Stage must be nonempty and must not contain a publication.json receipt')
        # Exclusive mkdir closes the check/rename race, even for non-cooperating writers.
        # Normal mkdir/open permissions and inherited ACLs follow the destination policy.
        destination.mkdir()
        for relative in expected:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with (source / relative).open('rb') as incoming, target.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        if inventory(destination) != expected or inventory(source) != expected:
            raise ValueError('Publication/source verification failed')
        receipt = dict(verified_at=datetime.now(timezone.utc).isoformat(), files=expected,
                       destination=str(destination), source_preserved=True)
        with (destination / 'publication.json').open('x') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
        print(json.dumps(dict(published=str(destination), files=len(expected), verified=True)))
    finally:
        # Failed uploads stay visibly incomplete for inspection; never delete evidence
        # or a concurrent writer's additions. Only a valid final receipt marks completion.
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('sample')
    p.add_argument('video', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--interval', type=float, default=5); p.add_argument('--width', type=int, default=960)
    p.set_defaults(func=sample)
    p = commands.add_parser('dedupe')
    p.add_argument('samples', type=Path); p.add_argument('--region', type=rectangle)
    p.add_argument('--threshold', type=float, default=0.6); p.add_argument('--report', type=Path)
    p.set_defaults(func=dedupe)
    p = commands.add_parser('extract')
    p.add_argument('video', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--seconds', type=float, required=True); p.add_argument('--crop', type=rectangle, required=True)
    p.set_defaults(func=extract)
    p = commands.add_parser('publish')
    p.add_argument('stage', type=Path); p.add_argument('destination', type=Path)
    p.set_defaults(func=publish)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
