"""Demo 8 (motion.html / motion-m.html): demo 4's clouds on a Theatre.js timeline.

01.10, «давай пограємось в мовшн дизайн»: built from demo 4's pages as they stand, so the
clouds are the approved ones; adds the Theatre.js bundle (studio + core, vendored in js/),
the starting choreography (motion-state.js, gen_motion_state.py) and motion.js. With the
studio open the demo panels are hidden: the studio has its own panels in the same corners.

    python gen_motion_state.py && python build_motion.py
"""
import pathlib

DST = pathlib.Path(__file__).parent
V = '20261001b'


def build(src, out, partner, src_partner):
    html = (DST / src).read_text()
    html = html.replace(f"location.replace('{src_partner}?", f"location.replace('{partner}?")
    html = html.replace('Sky demo 4: cloud field', 'Sky demo 8: motion')
    html = html.replace('</head>', '<style>html.xx-studio .xx-proto, html.xx-studio .xx-tune, html.xx-play .xx-proto, html.xx-play .xx-tune { display: none !important; }</style>\n</head>', 1)
    a = html.index('<script src="field.js')
    b = html.index('</script>', a) + len('</script>')
    html = (html[:b] + f'\n<script src="motion-state.js?v={V}"></script>\n'
            # the studio checks for updates through Node's `process`; the page has no network
            # access (connect-src 'none') and no `process`, so give it an empty one
            '<script>window.process = window.process || { env: { NODE_ENV: "production" } };</script>\n'
            f'<script src="js/theatre-core-and-studio.js?v={V}"></script>\n'
            f'<script src="motion.js?v={V}"></script>' + html[b:])
    assert 'motion.js' in html and 'field.js' in html
    (DST / out).write_text(html)
    print(out, len(html) // 1024, 'KB')


if __name__ == '__main__':
    build('field.html', 'motion.html', 'motion-m.html', 'field-m.html')
    build('field-m.html', 'motion-m.html', 'motion.html', 'field.html')
