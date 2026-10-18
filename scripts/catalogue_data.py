"""List-page exports keep searchable statements and omit full attempt bodies."""

import json


def catalogue_attack(attack):
    # Legacy records with no usable status still derive their claim from raw text.
    omit_raw = str(attack.get('status') or '').strip().lower() in {'solved', 'partial', 'unresolved'}
    return {field: value for field, value in attack.items()
            if field != 'sections' and not (field == 'raw' and omit_raw)}


def write_catalogue_data(path, records, declaration, alias=None):
    catalogue = {
        key: {**record, 'attacks': [
            catalogue_attack(attack)
            for attack in record.get('attacks', [])
        ]}
        for key, record in records.items()
    }
    serialized = json.dumps(catalogue, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    script = f'{declaration} = {serialized};\n'
    if alias:
        script += alias + '\n'
    path.write_text(script, encoding='utf-8')
