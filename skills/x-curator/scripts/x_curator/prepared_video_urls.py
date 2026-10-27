"""Bind selected media variants, attachment capacity and observed audio intervals."""
import json
from .source_evidence import branch
from .x_quote_views import typed_post


def urls(entry):
    result = entry['content']['itemContent']['tweet_results']['result']
    tweet = result.get('tweet', result)
    quote = typed_post(branch(tweet, 'quoted_status_result', 'result'))
    matched = quote if quote and branch(tweet, 'legacy').get('quoted_status_id_str') == quote['rest_id'] else {}
    return variants(tweet) | variants(matched)


def variants(post):
    return {v['url'] for m in branch(post, 'legacy', 'extended_entities').get('media', []) if m['type'] in ('video', 'animated_gif')
            for v in m.get('video_info', {}).get('variants', []) if v['content_type'] == 'video/mp4'}

def capacity(db, job, current, payload):
    rows = db.execute('SELECT payload FROM prepared_videos WHERE account=? AND source=? AND revision=?',
                      (job['account'], job['id'], current))
    images = set(payload['images'])
    for row in rows:
        images.update(json.loads(row[0])['images'])
    if len(images) > 24:
        raise ValueError('prepared post exceeds its aggregate frame budget')

def coverage(manifest):
    full, observed = manifest['audio_duration'], manifest['transcribed_duration']
    if not (0 < full <= manifest['duration']+.05 and 0 < observed <= full+.05):
        raise ValueError('prepared audio interval is outside its video')
    return observed


def limitations(manifest):
    if 'audio_duration' not in manifest:
        return []
    return [f"Audio duration: {manifest['audio_duration']:.3f}s; transcribed input: {manifest['transcribed_duration']:.3f}s. Only the retained timestamped portions were reviewed."]
