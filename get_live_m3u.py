import os
import sys

def parse_m3u(file_path):
    """
    Parse an M3U file into a dict of url -> full entry block string,
    and a list of (url, block) tuples for ordered processing.
    """
    entries = {}  # url -> block
    entry_list = []  # list of (url, block)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {e}")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == '#EXTM3U':
            i += 1
            continue
        if line.startswith('#EXTINF'):
            block_lines = [line]
            i += 1
            # Collect any additional lines until the URL
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('http://', 'https://')):
                block_lines.append(lines[i].strip())
                i += 1
            if i < len(lines):
                url = lines[i].strip()
                if url.startswith(('http://', 'https://')):
                    block = '\n'.join(block_lines + [url])
                    entries[url] = block
                    entry_list.append((url, block))
                i += 1
            else:
                # Malformed: #EXTINF without URL
                i += 1
        else:
            i += 1
    
    return entries, entry_list

def get_live_m3u(all, live):
    """
    Merge M3U files: for each entry in live, if URL in all, use all's full block,
    else use live's block. Output to all basename + '_live.m3u'
    """
    a_entries, _ = parse_m3u(all)
    _, b_list = parse_m3u(live)
    
    base_name = os.path.splitext(os.path.basename(all))[0]
    output_file = base_name + '_live.m3u'
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n\n')
            for url, b_block in b_list:
                if url in a_entries:
                    f.write(a_entries[url] + '\n\n')
                else:
                    f.write(b_block + '\n\n')
        print(f"Merged M3U saved to: {output_file}")
    except Exception as e:
        raise Exception(f"Error writing output file {output_file}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 get_live_m3u.py <all_channels_file> <live_channels_file>")
        sys.exit(1)
    
    all_file = sys.argv[1]
    live_file = sys.argv[2]
    get_live_m3u(all_file, live_file)