# -*- coding: utf-8 -*-
"""Assemble the runtime dictionary consumed by the Meteor-zh addon.

Sources
  i18n_ref/en_us.json, i18n_ref/zh_cn.json  -> Meteor Client core (CC0, extracted
                                               from the Meteor-I18n-Support jar)
  dict/zh_ui.json                           -> GUI hard-coded phrases translated by
                                               the dict-ui teammate
  dict/zh_addons.json  (optional)           -> third party addons (Baritone, AutoElytra, ...)

Output
  src/main/resources/assets/meteorzh/lang/zh.json
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "i18n_ref")
DICT = os.path.join(ROOT, "dict")
OUT = os.path.join(ROOT, "src", "main", "resources", "assets", "meteorzh", "lang", "zh.json")


def load_json(path):
    if not os.path.exists(path):
        return {}
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_ascii(s):
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def convert_core():
    en = load_json(os.path.join(REF, "en_us.json"))
    zh = load_json(os.path.join(REF, "zh_cn.json"))

    modules = {}
    settings = {}

    for key, en_val in en.items():
        if not key.startswith("Module.Meteor.") and not key.startswith("Setting.Meteor."):
            continue

        target_name = None
        is_module = key.startswith("Module.Meteor.")
        rest = key[len("Module.Meteor."):] if is_module else key[len("Setting.Meteor."):]

        if rest.endswith(".Description"):
            continue  # handled together with the title below

        target_name = rest
        desc_key = key + ".Description"

        zh_title = zh.get(key)
        zh_desc = zh.get(desc_key)

        # If the Chinese value is identical to the English one it was never translated.
        title = zh_title if zh_title and zh_title != en_val else None
        desc = zh_desc if zh_desc and zh_desc != en.get(desc_key) else None

        # Core module/setting names are already the English identifier; prefer the
        # Chinese title, otherwise fall back to the readable English value.
        if title is None and not is_ascii(en_val):
            title = en_val

        bucket = modules if is_module else settings
        entry = {}
        if title:
            entry["title"] = title
        if desc:
            entry["desc"] = desc
        if entry:
            bucket[target_name] = entry

    return modules, settings


def convert_ui():
    ui_src = load_json(os.path.join(DICT, "zh_ui.json"))

    groups = {}
    ui = {}

    for name, value in (ui_src.get("groups") or {}).items():
        if value and value != name:
            groups[name] = value
            ui[name] = value

    for bucket in ("labels", "sections", "buttons", "tooltips", "titles"):
        for name, value in (ui_src.get(bucket) or {}).items():
            if value and value != name:
                ui[name] = value

    # key / mouse button labels rendered next to "Bind: "
    for name, value in (load_json(os.path.join(DICT, "zh_keynames.json")) or {}).items():
        if value:
            ui[name] = value

    # GUI tab titles (Modules / Config / GUI / ...); they are also rewritten through
    # reflection, the ui entry keeps the render layer consistent
    for name, value in (load_json(os.path.join(DICT, "zh_tabs.json")) or {}).items():
        if value:
            groups[name] = value
            ui[name] = value

    return groups, ui


def convert_addons(modules, settings):
    """Merge third party addon entries.

    Two shapes are accepted:
      {"names": {"<kebab>": "中文"}, "descs": {"<english sentence>": "中文"}}
      {"modules": {...}, "settings": {...}, "groups": {...}, "ui": {...}}

    Plain identifiers are stored in the settings bucket; ZhDict cross-checks the
    module table as well, so one bucket is enough for identifiers whose real
    owner (module vs setting) we cannot tell apart from the jar alone.
    """
    addons = load_json(os.path.join(DICT, "zh_addons.json"))
    if not addons:
        return {}

    groups = {}
    ui = {}
    descriptions = {}

    for name, value in (addons.get("names") or {}).items():
        if not value:
            continue
        settings.setdefault(name, {}).setdefault("title", value)
        modules.setdefault(name, {}).setdefault("title", value)

    for text, value in (addons.get("descs") or {}).items():
        if value and value != text:
            descriptions[text] = value

    for key, target in (("modules", modules), ("settings", settings), ("groups", groups), ("ui", ui)):
        src = addons.get(key)
        if not src:
            continue
        for k, v in src.items():
            if key in ("modules", "settings"):
                target.setdefault(k, {}).update(v)
            else:
                target.setdefault(k, v)

    return {"groups": groups, "ui": ui, "descriptions": descriptions}


def main():
    modules, settings = convert_core()
    groups, ui = convert_ui()
    extra = convert_addons(modules, settings)
    groups.update(extra.get("groups") or {})
    ui.update(extra.get("ui") or {})
    descriptions = extra.get("descriptions") or {}

    result = {
        "modules": dict(sorted(modules.items())),
        "settings": dict(sorted(settings.items())),
        "groups": dict(sorted(groups.items())),
        "ui": dict(sorted(ui.items())),
    }
    if descriptions:
        result["descriptions"] = dict(sorted(descriptions.items()))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")

    size = os.path.getsize(OUT)
    print("modules  : %d (with desc: %d)" % (
        len(result["modules"]), sum(1 for v in result["modules"].values() if "desc" in v)))
    print("settings : %d (with desc: %d)" % (
        len(result["settings"]), sum(1 for v in result["settings"].values() if "desc" in v)))
    print("groups   : %d" % len(result["groups"]))
    print("ui       : %d" % len(result["ui"]))
    print("descs    : %d" % len(result.get("descriptions") or {}))
    print("written  : %s (%d bytes)" % (OUT, size))


if __name__ == "__main__":
    main()
