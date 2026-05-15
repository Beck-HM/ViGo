"""ViGo Standard Library: Data Format Parsing (fmtlib)
Provides YAML, TOML, XML, CSV, INI parsing/serialization.
Uses Python stdlib where possible, with optional third-party fallbacks.
"""
import os
from ..runtime.objects import BuiltinFunction


def register(env):
    """Register all fmtlib functions into the given ViGo environment."""

    # ── JSON ──

    def parse_json(text):
        import json
        return json.loads(text)

    def to_json(obj, indent=None):
        import json
        if indent is not None:
            return json.dumps(obj, ensure_ascii=False, indent=int(indent))
        return json.dumps(obj, ensure_ascii=False)

    # ── YAML ──

    def parse_yaml(text):
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            pass
        return _basic_yaml_parse(text)

    def to_yaml(obj):
        try:
            import yaml
            return yaml.dump(obj, allow_unicode=True, default_flow_style=False)
        except ImportError:
            pass
        return _basic_yaml_dump(obj)

    def parse_yaml_file(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return parse_yaml(f.read())

    def to_yaml_file(filepath, obj):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(to_yaml(obj))
        return True

    # ── TOML ──

    def parse_toml(text):
        try:
            import tomllib
            return tomllib.loads(text)
        except ImportError:
            pass
        try:
            import tomli
            return tomli.loads(text)
        except ImportError:
            pass
        try:
            import toml
            return toml.loads(text)
        except ImportError:
            pass
        raise ImportError("No TOML parser available. Install: pip install toml")

    def to_toml(obj):
        try:
            import tomli_w
            return tomli_w.dumps(obj)
        except ImportError:
            pass
        try:
            import toml
            return toml.dumps(obj)
        except ImportError:
            pass
        raise ImportError("No TOML writer available. Install: pip install tomli-w")

    def parse_toml_file(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return parse_toml(f.read())

    def to_toml_file(filepath, obj):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(to_toml(obj))
        return True

    # ── XML ──

    def parse_xml(text):
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text)
        return _xml_to_dict(root)

    def to_xml(obj, root_tag="root"):
        import xml.etree.ElementTree as ET
        root = _dict_to_xml(root_tag, obj)
        return ET.tostring(root, encoding='unicode')

    def parse_xml_file(filepath):
        import xml.etree.ElementTree as ET
        tree = ET.parse(filepath)
        return _xml_to_dict(tree.getroot())

    def to_xml_file(filepath, obj, root_tag="root"):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(to_xml(obj, root_tag))
        return True

    # ── CSV ──

    def parse_csv(text, delimiter=",", has_header=True):
        import csv
        import io
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if not rows:
            return []
        if has_header:
            headers = rows[0]
            return [dict(zip(headers, row)) for row in rows[1:]]
        return rows

    def to_csv(data, delimiter=",", headers=None):
        import csv
        import io
        output = io.StringIO()
        if not data:
            return ""
        if isinstance(data[0], dict):
            if headers is None:
                headers = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(output, delimiter=delimiter)
            if headers:
                writer.writerow(headers)
            writer.writerows(data)
        return output.getvalue()

    def parse_csv_file(filepath, delimiter=",", has_header=True):
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            return parse_csv(f.read(), delimiter, has_header)

    def to_csv_file(filepath, data, delimiter=",", headers=None):
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            f.write(to_csv(data, delimiter, headers))
        return True

    # ── INI ──

    def parse_ini(text):
        import configparser
        import io
        parser = configparser.ConfigParser()
        parser.read_string(text)
        return {s: dict(parser.items(s)) for s in parser.sections()}

    def to_ini(obj):
        import configparser
        parser = configparser.ConfigParser()
        for section, items in obj.items():
            parser[section] = {str(k): str(v) for k, v in items.items()}
        import io
        output = io.StringIO()
        parser.write(output)
        return output.getvalue()

    # ── Registration ──

    env.define("parse_json", BuiltinFunction(parse_json, "parse_json"))
    env.define("to_json", BuiltinFunction(to_json, "to_json"))
    env.define("parse_yaml", BuiltinFunction(parse_yaml, "parse_yaml"))
    env.define("to_yaml", BuiltinFunction(to_yaml, "to_yaml"))
    env.define("parse_yaml_file", BuiltinFunction(parse_yaml_file, "parse_yaml_file"))
    env.define("to_yaml_file", BuiltinFunction(to_yaml_file, "to_yaml_file"))
    env.define("parse_toml", BuiltinFunction(parse_toml, "parse_toml"))
    env.define("to_toml", BuiltinFunction(to_toml, "to_toml"))
    env.define("parse_toml_file", BuiltinFunction(parse_toml_file, "parse_toml_file"))
    env.define("to_toml_file", BuiltinFunction(to_toml_file, "to_toml_file"))
    env.define("parse_xml", BuiltinFunction(parse_xml, "parse_xml"))
    env.define("to_xml", BuiltinFunction(to_xml, "to_xml"))
    env.define("parse_xml_file", BuiltinFunction(parse_xml_file, "parse_xml_file"))
    env.define("to_xml_file", BuiltinFunction(to_xml_file, "to_xml_file"))
    env.define("parse_csv", BuiltinFunction(parse_csv, "parse_csv"))
    env.define("to_csv", BuiltinFunction(to_csv, "to_csv"))
    env.define("parse_csv_file", BuiltinFunction(parse_csv_file, "parse_csv_file"))
    env.define("to_csv_file", BuiltinFunction(to_csv_file, "to_csv_file"))
    env.define("parse_ini", BuiltinFunction(parse_ini, "parse_ini"))
    env.define("to_ini", BuiltinFunction(to_ini, "to_ini"))


# ── Internal helpers ──

def _xml_to_dict(element):
    result = {}
    if element.attrib:
        result["@attrs"] = element.attrib
    for child in element:
        child_dict = _xml_to_dict(child)
        tag = child.tag
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_dict)
        else:
            result[tag] = child_dict
    text = (element.text or "").strip()
    if text and not result:
        return text
    if text:
        result["#text"] = text
    return result


def _dict_to_xml(tag, obj):
    import xml.etree.ElementTree as ET
    if isinstance(obj, str):
        elem = ET.Element(tag)
        elem.text = obj
        return elem
    elem = ET.Element(tag)
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "@attrs" and isinstance(value, dict):
                for ak, av in value.items():
                    elem.set(ak, str(av))
            elif key == "#text":
                elem.text = str(value)
            elif isinstance(value, list):
                for item in value:
                    elem.append(_dict_to_xml(key, item))
            else:
                elem.append(_dict_to_xml(key, value))
    return elem


def _basic_yaml_parse(text):
    result = {}
    lines = text.split("\n")
    stack = [(result, -1)]
    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip().strip("'\"")
            value = value.strip().strip("'\"")
            while stack and indent <= stack[-1][1]:
                stack.pop()
            current, _ = stack[-1]
            if value:
                if value.lower() == "true":
                    current[key] = True
                elif value.lower() == "false":
                    current[key] = False
                elif value.lower() in ("null", "none", "~"):
                    current[key] = None
                else:
                    try:
                        if "." in value:
                            current[key] = float(value)
                        else:
                            current[key] = int(value)
                    except ValueError:
                        current[key] = value
            else:
                current[key] = {}
                stack.append((current[key], indent))
    return result


def _basic_yaml_dump(obj, indent=0):
    lines = []
    prefix = "  " * indent
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(_basic_yaml_dump(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {_yaml_value(item)}")
            else:
                lines.append(f"{prefix}{key}: {_yaml_value(value)}")
    elif isinstance(obj, list):
        for item in obj:
            lines.append(f"{prefix}- {_yaml_value(item)}")
    return "\n".join(lines)


def _yaml_value(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)