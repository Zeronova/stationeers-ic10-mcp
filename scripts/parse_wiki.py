"""Parse Stationeers wiki HTML files and extract device data network properties."""

import json
import os
import re
import glob
from html.parser import HTMLParser


class WikiTableParser(HTMLParser):
    """Parse WikiTables to find Data Network Properties tables."""
    
    def __init__(self):
        super().__init__()
        self.in_wikitable = False
        self.in_tr = False
        self.in_th = False
        self.in_td = False
        self.current_cell = ""
        self.current_row = []
        self.tables = []
        self.table_class = ""
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'table':
            cls = attrs_dict.get('class', '')
            self.table_class = cls
            self.in_wikitable = 'wikitable' in cls
            if self.in_wikitable:
                self.current_table_rows = []
            return
        
        if not self.in_wikitable:
            return
        
        if tag == 'tr':
            self.current_row = []
        elif tag == 'th':
            self.in_th = True
            self.current_cell = ""
        elif tag == 'td':
            self.in_td = True
            self.current_cell = ""
        elif tag == 'br':
            if self.in_td or self.in_th:
                self.current_cell += '\n'
        elif tag in ('a', 'span', 'small', 'sup', 'sub', 'b', 'i', 'em', 'strong'):
            pass  # skip inline tags
    
    def handle_endtag(self, tag):
        if tag == 'table':
            if self.in_wikitable and self.current_table_rows:
                self.tables.append({
                    'class': self.table_class,
                    'rows': self.current_table_rows
                })
            self.in_wikitable = False
            return
        
        if not self.in_wikitable:
            return
        
        if tag == 'th':
            self.in_th = False
            self.current_row.append(self.current_cell.strip())
        elif tag == 'td':
            self.in_td = False
            self.current_row.append(self.current_cell.strip())
        elif tag == 'tr':
            if self.current_row:
                self.current_table_rows.append(self.current_row)
    
    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data
        elif self.in_th:
            self.current_cell += data


def extract_device_name(content, filename):
    """Extract the page title."""
    match = re.search(r'<title>(.*?)(?: - Stationeers.*?)?</title>', content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r'<[^>]+>', '', match.group(1)).strip()
    return os.path.splitext(os.path.basename(filename))[0].replace('_', ' ')


def detect_section(headers):
    """Detect if table is about Data Parameters (write) or Output (read) or something else."""
    all_text = ' '.join(h.lower() for h in headers)
    if 'parameter' in all_text or 'setting' in all_text:
        return 'parameters'
    if 'output' in all_text:
        return 'outputs'
    return 'unknown'


def parse_properties_table(rows):
    """Parse a property table into structured data."""
    if not rows:
        return []
    
    # First row might be header
    first_row = rows[0]
    
    # Detect columns
    col_count = len(first_row)
    
    # Determine if first row is header
    is_header = False
    header_map = {}
    if col_count >= 2:
        col_lower = [c.lower().strip() for c in first_row]
        
        # Check for known header patterns
        if any(kw in col_lower[0] for kw in ['parameter name', 'output name', 'property', 'setting']):
            is_header = True
            header_map = {}
            for i, h in enumerate(col_lower):
                if 'name' in h or 'parameter' in h or 'output' in h or 'property' in h or 'setting' in h:
                    header_map[i] = 'property'
                elif 'type' in h or 'data type' in h:
                    header_map[i] = 'type'
                elif 'desc' in h or 'note' in h:
                    header_map[i] = 'description'
                elif 'read' in h:
                    header_map[i] = 'read'
                elif 'write' in h:
                    header_map[i] = 'write'
                elif 'range' in h:
                    header_map[i] = 'range'
                elif 'default' in h:
                    header_map[i] = 'default'
                else:
                    header_map[i] = h  # keep original
    
    # If it's known properties-like, check surrounding heading for context
    section_type = 'unknown'
    if is_header:
        # Try to find the h3 heading before this table
        section_type = detect_section(first_row)
    
    properties = []
    data_rows = rows[1:] if is_header else rows
    
    for row in data_rows:
        if not row or all(c == '' for c in row):
            continue
        
        if len(row) >= 3 and is_header:
            # Structured table: property, type, description
            entry = {}
            for i, val in enumerate(row):
                col_role = header_map.get(i, f'col{i}')
                if col_role == 'property':
                    entry['property'] = val
                elif col_role == 'type':
                    entry['type'] = val
                elif col_role == 'description':
                    entry['description'] = val
                elif col_role == 'read':
                    entry['read'] = val
                elif col_role == 'write':
                    entry['write'] = val
                else:
                    entry[col_role] = val
            
            if 'property' in entry:
                # Clean up property name - remove newlines
                entry['property'] = entry['property'].replace('\n', ' ').strip()
                entry['_section'] = section_type
                properties.append(entry)
        else:
            # Two-column: property + description
            entry = {
                'property': row[0].replace('\n', ' ').strip(),
                'description': row[-1].replace('\n', ' ').strip() if len(row) > 1 else '',
            }
            if len(row) >= 2:
                entry['_raw_type'] = row[1] if len(row) > 1 else ''
            entry['_section'] = section_type
            properties.append(entry)
    
    return properties


def parse_all_pages(wiki_dir):
    """Parse all HTML files in the wiki directory."""
    all_devices = {}
    
    html_files = sorted(glob.glob(os.path.join(wiki_dir, '*.html')))
    skip_patterns = ['Data_Network_Colors', 'ItemHash']
    
    for filepath in html_files:
        basename = os.path.basename(filepath)
        
        if any(p in basename for p in skip_patterns):
            continue
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        device_name = extract_device_name(content, filepath)
        
        parser = WikiTableParser()
        parser.feed(content)
        
        all_props = []
        for table in parser.tables:
            rows = table.get('rows', [])
            props = parse_properties_table(rows)
            all_props.extend(props)
        
        if all_props:
            # Deduplicate by property name
            seen = set()
            unique_props = []
            for p in all_props:
                prop_name = p.get('property', '')
                if prop_name and prop_name not in seen:
                    seen.add(prop_name)
                    unique_props.append(p)
            
            device_key = os.path.splitext(basename)[0]
            all_devices[device_key] = {
                'name': device_name,
                'properties': unique_props
            }
            print(f"  {device_name}: {len(unique_props)} properties")
    
    return all_devices


def main():
    wiki_dir = '/root/.nanobot/workspace/stationeers-wiki'
    output_dir = '/root/.nanobot/workspace/stationeers-ic10-mcp/stationeers_ic10_mcp/data'
    
    print("Parsing wiki files...")
    devices = parse_all_pages(wiki_dir)
    
    print(f"\nFound {len(devices)} devices with data network properties.\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Combine all properties into a single reference
    all_properties = set()
    device_index = {}
    
    for device_key, device_data in sorted(devices.items()):
        props = device_data['properties']
        
        # Create individual device file
        safe_key = re.sub(r'[^a-zA-Z0-9_]', '_', device_key)
        filepath = os.path.join(output_dir, f"device_{safe_key}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(device_data, f, indent=2, ensure_ascii=False)
        
        # Build search index
        prop_list = [p['property'] for p in props if 'property' in p]
        all_properties.update(prop_list)
        
        device_index[safe_key] = {
            'name': device_data['name'],
            'properties': prop_list,
            'count': len(props)
        }
        
        print(f"  {device_data['name']}: {len(props)} properties")
    
    # Write device index
    with open(os.path.join(output_dir, 'device_index.json'), 'w', encoding='utf-8') as f:
        json.dump(device_index, f, indent=2, ensure_ascii=False)
    
    print(f"\nTotal: {len(devices)} devices, {len(all_properties)} unique properties")
    print(f"Index saved to {output_dir}/device_index.json")


if __name__ == '__main__':
    main()
