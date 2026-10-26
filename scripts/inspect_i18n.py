import zipfile, json, io, os, sys

jar = r"E:\pcl\.minecraft\versions\1.21.11-Fabric 0.19.3\mods\Meteor-I18n-Support-1.21.11_to_26.1.jar"
out = r"C:\Users\wang'xiao'ya\OneDrive\Documents\deepseek-harness\default-workspace\projects\meteor-zh\i18n_ref"
os.makedirs(out, exist_ok=True)

z = zipfile.ZipFile(jar)
names = z.namelist()
print("entries:", len(names))
for n in names:
    print("  ", n, z.getinfo(n).file_size)

for f in ["assets/yalu/lang/en_us.json", "assets/yalu/lang/zh_cn.json"]:
    if f in names:
        data = z.read(f)
        d = json.loads(data.decode("utf-8-sig"))
        print(f, "->", len(d), "entries")
        pref = {}
        for k in d:
            parts = k.split(".")
            p = ".".join(parts[:2])
            pref[p] = pref.get(p, 0) + 1
        print("   prefixes:", pref)
        with io.open(os.path.join(out, os.path.basename(f)), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True))

en = json.loads(z.read("assets/yalu/lang/en_us.json").decode("utf-8-sig"))
zh = json.loads(z.read("assets/yalu/lang/zh_cn.json").decode("utf-8-sig"))
print("\n=== sample 30 keys ===")
for k in sorted(en)[:30]:
    print(" ", k, "=>", repr(en[k]), "|", repr(zh.get(k)))
print("\n=== untranslated (zh==en) count:", sum(1 for k in en if zh.get(k) == en[k]))
print("=== missing in zh:", sum(1 for k in en if k not in zh))
