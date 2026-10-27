"""Optional NDI confidence output. HDMI/RTMP and channel clocks are untouched."""
import argparse
import os
import socket
import xml.etree.ElementTree as ET
from pathlib import Path


def configure(paths, enabled):
    prepared = []
    for path in paths:
        tree = ET.parse(path)
        consumers = tree.getroot().find('channels/channel/consumers')
        if consumers is None:
            raise ValueError(f'Program consumers are missing in {path}')
        for node in list(consumers):
            if node.tag == 'ndi':
                consumers.remove(node)
        if enabled:
            ndi = ET.SubElement(consumers, 'ndi')
            for key, value in [('name', 'SkyCam Program HD'), ('allow-fields', 'false'),
                               ('width', '1280'), ('height', '720')]:
                ET.SubElement(ndi, key).text = value
        ET.indent(tree, space='  ')
        prepared.append((path, tree))
    # Validate both files before writing either one.
    for path, tree in prepared:
        temporary = path.with_suffix(path.suffix + '.ndi-tmp')
        tree.write(temporary, encoding='utf-8', xml_declaration=True)
        os.replace(temporary, path)


def apply_live(enabled):
    command = ('ADD 1-900 NDI NAME "SkyCam Program HD" WIDTH 1280 HEIGHT 720'
               if enabled else 'REMOVE 1-900')
    with socket.create_connection(('127.0.0.1', 5250), 5) as connection:
        connection.sendall((command + '\r\n').encode())
        reply = b''
        while b'\r\n' not in reply:
            part = connection.recv(4096)
            if not part:
                raise RuntimeError('CasparCG closed the connection without a result')
            reply += part
    line = reply.decode(errors='replace').splitlines()[0]
    if not line.startswith('202 ') and not (not enabled and line.startswith('404 ')):
        raise RuntimeError(line)
    return line


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['on', 'off'])
    parser.add_argument('--root', type=Path, default=Path('/srv/station'))
    args = parser.parse_args()
    enabled = args.mode == 'on'
    configure([args.root/'skycam/deploy/casparcg.config', args.root/'casparcg.config'], enabled)
    try:
        print(apply_live(enabled))
    except (OSError, RuntimeError) as exc:
        raise SystemExit(f'NDI startup setting saved as {args.mode}, but live change failed: {exc}')
    print(f'NDI is {args.mode}, including after restart. HDMI and YouTube were not changed.')


if __name__ == '__main__':
    main()
