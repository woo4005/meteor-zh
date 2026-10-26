import os, re, json, io, collections

SRC = r"C:\Users\wang'xiao'ya\OneDrive\Documents\deepseek-harness\default-workspace\projects\_refs\meteor-client-1.21.11\src\main\java"
OUT = r"C:\Users\wang'xiao'ya\OneDrive\Documents\deepseek-harness\default-workspace\projects\meteor-zh\dict"
os.makedirs(OUT, exist_ok=True)

files = []
for root, dirs, fs in os.walk(SRC):
    for f in fs:
        if f.endswith(".java"):
            files.append(os.path.join(root, f))
print("java files:", len(files))

groups = collections.Counter()
labels = collections.Counter()
sections = collections.Counter()
buttons = collections.Counter()
tooltips = collections.Counter()
titles = collections.Counter()

re_group = re.compile(r'createGroup\(\s*"([^"]+)"')
re_label = re.compile(r'theme\.label\(\s*"([^"]+)"')
re_section = re.compile(r'theme\.section\(\s*"([^"]+)"')
re_button = re.compile(r'theme\.button\(\s*"([^"]+)"')
re_tooltip = re.compile(r'\.tooltip\s*=\s*"([^"]+)"')
re_title = re.compile(r'\.title\(\s*"([^"]+)"')

for p in files:
    try:
        s = io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    for m in re_group.finditer(s):
        groups[m.group(1)] += 1
    for m in re_label.finditer(s):
        labels[m.group(1)] += 1
    for m in re_section.finditer(s):
        sections[m.group(1)] += 1
    for m in re_button.finditer(s):
        buttons[m.group(1)] += 1
    for m in re_tooltip.finditer(s):
        tooltips[m.group(1)] += 1
    for m in re_title.finditer(s):
        titles[m.group(1)] += 1

def dump(name, c):
    print(f"\n=== {name}: {len(c)} unique ===")
    for k, v in sorted(c.items()):
        print(f"  {v:3d}  {k}")

dump("GROUPS (createGroup)", groups)
dump("LABELS (theme.label)", labels)
dump("SECTIONS (theme.section)", sections)
dump("BUTTONS (theme.button)", buttons)
dump("TOOLTIPS", tooltips)
dump("TITLES", titles)

payload = {
    "groups": sorted(groups),
    "labels": sorted(labels),
    "sections": sorted(sections),
    "buttons": sorted(buttons),
    "tooltips": sorted(tooltips),
    "titles": sorted(titles),
}
io.open(os.path.join(OUT, "raw_ui.json"), "w", encoding="utf-8").write(
    json.dumps(payload, ensure_ascii=False, indent=1))
print("\nwrote raw_ui.json")
