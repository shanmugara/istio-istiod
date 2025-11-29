#!/usr/bin/env python3
# update_images.py
# Safely update image repository references and global.hub in YAML files using ruamel.yaml

from ruamel.yaml import YAML
import os
import sys
from pathlib import Path
import re

yaml = YAML()
yaml.preserve_quotes = True

LOCAL_REPO = os.environ.get('LOCAL_REPO', 'myrepo.local')
DRY_RUN = '--dry-run' in sys.argv

IMAGE_STR_RE = re.compile(r"^(?P<prefix>[^\S\r\n]*image:\s*)(?P<registry>[^/\s]+)(?P<rest>/.*)$")

def update_node(node):
    # If mapping
    if isinstance(node, dict):
        # Update global.hub if present
        if 'global' in node and isinstance(node['global'], dict) and 'hub' in node['global']:
            node['global']['hub'] = LOCAL_REPO
        # Update image key
        if 'image' in node:
            im = node['image']
            # image: <string>
            if isinstance(im, str):
                if '/' in im:
                    rest = im.split('/', 1)[1]
                    node['image'] = f"{LOCAL_REPO}/{rest}"
            # image: { repository: ... }
            elif isinstance(im, dict) and 'repository' in im:
                im['repository'] = LOCAL_REPO
        # Recurse
        for k, v in list(node.items()):
            update_node(v)
    elif isinstance(node, list):
        for item in node:
            update_node(item)


def process_file(path: Path):
    try:
        text = path.read_text()
    except Exception as e:
        print(f"SKIP unable to read {path}: {e}")
        return False

    # Quick check: if neither 'image' nor 'hub' nor typical registry patterns exist, skip
    if 'image' not in text and 'hub' not in text and 'registry' not in text:
        # still may contain image refs like quay.io, docker.io etc; we'll scan for known registries
        if not re.search(r"[\w.-]+\/(?:[\w.-]+\/)*[\w.-]+(:[0-9]+)?(:[\w.-]+)?", text):
            return False

    # First, try structured edit with ruamel
    try:
        data = yaml.load(text)
    except Exception as e:
        # Not a YAML doc we can parse, fall back to regex edits
        data = None

    if data is not None:
        try:
            update_node(data)
            if DRY_RUN:
                print(f"DRY-RUN would update (structured): {path}")
                return True
            yaml.indent(mapping=2, sequence=4, offset=2)
            path.write_text(yaml.dump(data))
            print(f"UPDATED (structured): {path}")
            return True
        except Exception as e:
            print(f"WARNING structured update failed for {path}: {e}")
            # fall through to regex replacement

    # Fallback: simple regex replacement for lines like 'image: registry/name:tag' or 'hub: registry'
    try:
        new_text = []
        changed = False
        for line in text.splitlines(keepends=True):
            m = IMAGE_STR_RE.match(line)
            if m:
                new_line = f"{m.group('prefix')}{LOCAL_REPO}{m.group('rest')}\n"
                new_text.append(new_line)
                changed = True
                continue
            # Replace lines like 'hub: something'
            if re.match(r"^\s*hub:\s*.+", line):
                prefix = re.match(r"^(\s*hub:\s*)", line).group(1)
                new_text.append(prefix + LOCAL_REPO + "\n")
                changed = True
                continue
            # Replace values like 'global:
            #   hub: xyz'
            new_text.append(line)
        if changed:
            if DRY_RUN:
                print(f"DRY-RUN would update (regex): {path}")
                return True
            backup = path.with_suffix(path.suffix + '.bak')
            backup.write_text(text)
            path.write_text(''.join(new_text))
            print(f"UPDATED (regex): {path}")
            return True
        return False
    except Exception as e:
        print(f"ERROR processing {path}: {e}")
        return False


def main():
    root = Path('.')
    changed_any = False
    for p in root.rglob('*'):
        if p.is_file() and p.suffix in ('.yaml', '.yml'):
            if process_file(p):
                changed_any = True
    if changed_any:
        print('Files were modified')
        sys.exit(0)
    else:
        print('No files modified')
        sys.exit(0)

if __name__ == '__main__':
    main()

