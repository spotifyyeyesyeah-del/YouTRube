from flask import Flask, request, Response, jsonify
import yt_dlp
import requests

app = Flask(__name__)

YDL_OPTS_BASE = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['web'],
        }
    },
}

@app.route('/')
def index():
    html = open('index.html', encoding='utf-8').read()
    return Response(html, mimetype='text/html')

@app.route('/api/info')
def video_info():
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        with yt_dlp.YoutubeDL(YDL_OPTS_BASE) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen = set()
            for f in info.get('formats', []):
                label = f.get('format_note') or f.get('height')
                if label and f.get('ext') == 'mp4' and label not in seen:
                    formats.append({
                        'format_id': f['format_id'],
                        'label': str(label),
                        'filesize': f.get('filesize')
                    })
                    seen.add(label)

            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'formats': formats[-6:],
                'video_id': info.get('id')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No query'}), 400

    try:
        opts = {**YDL_OPTS_BASE, 'extract_flat': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            results = ydl.extract_info(f"ytsearch8:{query}", download=False)
            videos = []
            for entry in results.get('entries', []):
                videos.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'thumbnail': f"https://i.ytimg.com/vi/{entry.get('id')}/mqdefault.jpg",
                    'duration': entry.get('duration'),
                    'uploader': entry.get('uploader') or entry.get('channel'),
                })
            return jsonify(videos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stream')
def stream():
    url = request.args.get('url', '')
    fmt = request.args.get('format', 'best[ext=mp4]/best')

    try:
        opts = {**YDL_OPTS_BASE, 'format': fmt}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']

        headers = {k: v for k, v in request.headers if k != 'Host'}
        r = requests.get(stream_url, headers=headers, stream=True, timeout=30)

        def generate():
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        response_headers = {
            'Content-Type': r.headers.get('Content-Type', 'video/mp4'),
            'Accept-Ranges': 'bytes',
        }
        if 'Content-Length' in r.headers:
            response_headers['Content-Length'] = r.headers['Content-Length']

        return Response(generate(), headers=response_headers, status=r.status_code)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    url = request.args.get('url', '')
    fmt = request.args.get('format', 'best[ext=mp4]/best')

    try:
        opts = {**YDL_OPTS_BASE, 'format': fmt}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info.get('title', 'video')

        r = requests.get(stream_url, stream=True, timeout=30)

        def generate():
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk

        return Response(generate(),
            headers={
                'Content-Type': 'video/mp4',
                'Content-Disposition': f'attachment; filename="{title}.mp4"'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
