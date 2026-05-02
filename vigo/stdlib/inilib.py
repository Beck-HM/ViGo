"""INI Configuration file parser"""
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def _parse_ini(text):
    """Parse INI Text, ReturnNested dictionary"""
    result = {}
    current_section = None
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1].strip()
            if current_section not in result:
                result[current_section] = {}
        elif '=' in line:
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            # Remove quotes
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            # Try converting numbers and booleans
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
            if current_section is None:
                if '__global__' not in result:
                    result['__global__'] = {}
                result['__global__'][key] = value
            else:
                result[current_section][key] = value
    return result


def _to_ini(data):
    """Convert nested  dictionaryConversionTo  INI Text"""
    lines = []
    for section, values in data.items():
        if section == '__global__':
            for k, v in values.items():
                lines.append(f"{k} = {v}")
        else:
            lines.append(f"[{section}]")
            for k, v in values.items():
                if isinstance(v, str):
                    lines.append(f"{k} = \"{v}\"")
                elif isinstance(v, bool):
                    lines.append(f"{k} = {'true' if v else 'false'}")
                else:
                    lines.append(f"{k} = {v}")
        lines.append('')
    return '\n'.join(lines)


def register(env):
    env.define('parse_ini', BuiltinFunction(_parse_ini, 'parse_ini'))
    env.define('to_ini',    BuiltinFunction(_to_ini, 'to_ini'))