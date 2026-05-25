#!/usr/bin/env python3
"""
Parse graphify-out/graph.json dan generate Obsidian vault markdown files.

Setiap komponen file dienerate markdown dengan:
- Nama komponen
- Deskripsi dari label/sourc_file
- Internal links [[nama-file]] ke semua dependensi (node yang satu komunitas)

FILTER RULES:
- IGNORE file .svg atau yang path-nya mengandung 'us_market/config/logos'
- Hapus relasi yang mengarah ke/dari file logo agar tidak ada orphan link
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path


def is_logo_file(source_file: str) -> bool:
    """Check jika file adalah logo SVG atau berada di folder logos."""
    # Cek ekstensi .svg
    if source_file.endswith('.svg'):
        return True
    # Cek jika path mengandung us_market/config/logos
    if 'us_market/config/logos' in source_file or '/logos/' in source_file:
        return True
    return False


def normalize_label(label: str) -> str:
    """Convert label ke filename-friendly format."""
    cleaned = re.sub(r'[^a-zA-Z0-9\s_-]', '', label)
    normalized = cleaned.strip().replace(' ', '_')
    return normalized.lower()


def extract_file_path_from_id(node_id: str) -> str | None:
    """Extract file path dari node ID."""
    mapping = {
        'us_market': 'us_market',
        'id_market': 'id_market',
        'quant_radar': 'quant_radar',
        'analysis': 'us_market/analysis',
        'engine': 'us_market/engine',
        'dashboard': 'us_market/dashboard',
        'execution': 'us_market/execution',
        'config': 'us_market/config',
        'pipeline': 'us_market/pipeline',
        'backfill': 'us_market/backfill',
        'portfolio': 'portfolio',
        'ml_data': 'ml_data',
        'scraper': 'id_market/scraper',
        'train': 'id_market/train',
        'inference': 'id_market/inference',
        'output': 'us_market/output',
    }

    for prefix, path_base in mapping.items():
        if node_id.startswith(prefix + '_'):
            rest = node_id[len(prefix) + 1:]
            for ext in ['_py', '_html', '_md', '_csv', '_json', '_js', '_css', '_svg']:
                if rest.endswith(ext):
                    rest = rest[:-len(ext)]
                    break

            parts = rest.split('_')
            if len(parts) >= 1:
                folder = path_base
                if len(parts) > 1:
                    subfolder = '/'.join(parts[:-1])
                    folder = f"{folder}/{subfolder}" if subfolder else folder
                filename = parts[-1]
                return f"{folder}/{filename}.py" if folder else f"{filename}.py"

    return None


def get_source_file_from_label(label: str, source_file: str) -> str:
    """Dapatkan nama file yang sesuai dari label atau source_file."""
    if source_file and source_file != 'N/A':
        return source_file

    if label.endswith('()'):
        label = label[:-2]

    if '/' in label or label.endswith(('.py', '.html', '.md', '.json', '.csv', '.js', '.css')):
        return label

    return label


def build_community_map(data: dict) -> dict[str, list[str]]:
    """Build mapping: node_id -> list of community_id yang dihuni node ini."""
    node_to_community = {}
    for comm_id, members in data.get('communities', {}).items():
        for member_id in members:
            if member_id not in node_to_community:
                node_to_community[member_id] = []
            node_to_community[member_id].append(int(comm_id))
    return node_to_community


def build_node_map(data: dict) -> dict[str, dict]:
    """Build mapping: node_id -> node data."""
    node_map = {}
    for node in data.get('nodes', []):
        node_id = node.get('id', '')
        if node_id:
            node_map[node_id] = node
    return node_map


def build_file_to_nodes_map(data: dict, skip_logos: bool = True) -> dict[str, list[str]]:
    """Build mapping: source_file -> list of node_ids."""
    file_map = defaultdict(list)
    for node in data.get('nodes', []):
        source_file = node.get('source_file', '')
        if source_file and source_file != 'N/A':
            if skip_logos and is_logo_file(source_file):
                continue
            file_map[source_file].append(node.get('id'))
    return dict(file_map)


def get_file_description(node_ids: list[str], node_map: dict) -> str:
    """Dapatkan deskripsi file dari node-node yang terkait."""
    descriptions = []
    for nid in node_ids:
        node = node_map.get(nid, {})
        label = node.get('label', '')
        source_loc = node.get('source_location', '')

        if label and not label.startswith(('quant_radar_', 'id_market_')):
            descriptions.append(f"{label} ({source_loc})" if source_loc else label)

    return '; '.join(descriptions[:5])


def generate_markdown_content(
    filename: str,
    node_ids: list[str],
    node_map: dict,
    node_to_community: dict,
    allowed_files: set[str],
    all_node_ids_by_file: dict[str, list[str]]
) -> str:
    """Generate markdown content untuk satu file."""
    lines = []

    # Header
    lines.append(f"# {filename}")
    lines.append("")
    lines.append(f"**Source file:** `{filename}`")
    lines.append("")

    # Deskripsi dari node nodes
    desc = get_file_description(node_ids, node_map)
    if desc:
        lines.append("## Deskripsi")
        lines.append("")
        lines.append(desc)
        lines.append("")

    # Internal links ke komponen dalam file yang sama
    lines.append("## Komponen dalam File Ini")
    lines.append("")
    for nid in node_ids:
        node = node_map.get(nid, {})
        label = node.get('label', '')
        if label and not label.startswith(('quant_radar_', 'id_market_')):
            link_name = label.replace('()', '').replace(' ', '_').replace('()', '')
            lines.append(f"- [[{link_name}]]")
    lines.append("")

    # Internal links ke file dependensi (node di community yang sama)
    lines.append("## Dependencies & Relations")
    lines.append("")

    # Dapatkan semua community yang dihuni oleh node-file ini
    all_communities = set()
    for nid in node_ids:
        all_communities.update(node_to_community.get(nid, []))

    # Kumpulkan node dari community yang sama (kecuali node kita sendiri)
    related_nodes = set()
    for comm_id in all_communities:
        for node_in_comm in node_to_community:
            if comm_id in node_to_community.get(node_in_comm, []):
                related_nodes.add(node_in_comm)

    # Filter: hanya node yang berbeda dari node kita
    related_nodes -= set(node_ids)

    # Group by file, TAPI filter hanya file yang ada di allowed_files
    file_connections = defaultdict(list)
    for rel_node_id in related_nodes:
        rel_node = node_map.get(rel_node_id, {})
        rel_file = rel_node.get('source_file', '')
        rel_label = rel_node.get('label', '')
        if rel_file and rel_file != 'N/A' and rel_file in allowed_files:
            if not rel_label.startswith(('quant_radar_', 'id_market_', 'us_market_')):
                file_connections[rel_file].append(rel_label)

    if file_connections:
        lines.append("Relasi dengan file lain:")
        lines.append("")
        for rel_file, labels in sorted(file_connections.items()):
            link_name = rel_file.replace('.py', '').replace('.html', '').replace('.md', '').replace('.json', '')
            link_name = link_name.replace('/', '_').replace('-', '_')
            lines.append(f"- [[{link_name}]] - {', '.join(set(labels[:3]))}")
    else:
        lines.append("Tidak ada relasi dengan file lain yang terdeteksi.")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by parse_graph.py*")

    return '\n'.join(lines)


def main():
    # Load graph data
    graph_path = 'graphify-out/graph.json'
    with open(graph_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded graph: {len(data.get('nodes', []))} nodes")

    # Build mappings
    node_map = build_node_map(data)
    node_to_community = build_community_map(data)

    # Build file-to-nodes map dengan filter logo
    file_to_nodes = build_file_to_nodes_map(data, skip_logos=True)

    print(f"Found {len(file_to_nodes)} unique source files (logos filtered out)")

    # Kumpulkan semua file yang diizinkan (tanpa logo)
    allowed_files = set(file_to_nodes.keys())

    # Create output directory
    output_dir = Path('obsidian-vault')
    # Hapus folder lama jika ada
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"Deleted old {output_dir}/ folder")

    output_dir.mkdir(exist_ok=True)

    # Generate markdown untuk setiap file
    processed = 0
    for source_file, node_ids in sorted(file_to_nodes.items()):
        safe_name = source_file.replace('/', '_').replace('.', '_')
        md_filename = f"{safe_name}.md"
        md_path = output_dir / md_filename

        content = generate_markdown_content(
            source_file, node_ids, node_map, node_to_community,
            allowed_files, file_to_nodes
        )

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)

        processed += 1
        if processed % 50 == 0:
            print(f"  Generated {processed} files...")

    print(f"\nTotal: {processed} markdown files generated di {output_dir}/")

    # Buat index.md untuk vault
    index_path = output_dir / 'index.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("# Quant Radar - Obsidian Vault\n\n")
        f.write("This is an Obsidian-style knowledge vault generated from the graphify analysis.\n\n")
        f.write("## File Index\n\n")
        for source_file in sorted(file_to_nodes.keys()):
            safe_name = source_file.replace('/', '_').replace('.', '_')
            f.write(f"- [[{safe_name}]] - `{source_file}`\n")

    print(f"Generated index: {index_path}")


if __name__ == '__main__':
    main()
