// Meteor-ZH 词典加载的 JVM 侧验证（不启动 Minecraft）。
//
// 由 scripts/verify_dict.py 编译并运行：加载 jar 内 assets/meteorzh/lang/zh.json，
// 断言若干真实查找结果。**任何一条断言失败都会以退出码 1 结束**，这样
// verify_dict.py / CI 才会真的变红 —— 早期版本只有 println，JVM 能启动就算通过，
// 词典坏了也照样绿。
public class TestZh {
    private static int fail;
    private static int total;

    private static void check(String what, Object expected, Object actual) {
        total++;
        boolean ok = expected == null ? actual == null : expected.equals(actual);
        if (ok) {
            System.out.println("  OK   " + what + " -> " + actual);
        } else {
            fail++;
            System.out.println("  FAIL " + what + " -> got " + actual + ", want " + expected);
        }
    }

    public static void main(String[] args) {
        com.meteorzh.ZhDict.load();

        check("isLoaded", Boolean.TRUE, com.meteorzh.ZhDict.isLoaded());

        // 词典条目数：allow a wide band — size() sums all seven lookup tables, so the
        // number moves whenever a translation is added. Only the order of magnitude matters.
        int size = com.meteorzh.ZhDict.size();
        total++;
        if (size < 4000 || size > 6000) {
            fail++;
            System.out.println("  FAIL size = " + size + " (expected 4000..6000)");
        } else {
            System.out.println("  OK   size -> " + size);
        }

        // 模块名：既有 I18n 语料也有 addon 补译
        check("module anti-afk", "防AFK", com.meteorzh.ZhDict.moduleTitle("anti-afk", "<miss>"));
        check("module kill-aura", "杀戮光环", com.meteorzh.ZhDict.moduleTitle("kill-aura", "<miss>"));
        check("module elytra-finder", "鞘翅搜寻器", com.meteorzh.ZhDict.moduleTitle("elytra-finder", "<miss>"));

        // 设置项
        check("setting range", "范围", com.meteorzh.ZhDict.settingTitle("range", "<miss>"));

        // 分组 / 分类
        check("group General", "通用", com.meteorzh.ZhDict.groupTitle("General"));
        check("group Render", "渲染", com.meteorzh.ZhDict.groupTitle("Render"));

        // 渲染层固定短语（注意尾部空格的键）
        check("ui Bind", "绑定", com.meteorzh.ZhDict.ui("Bind"));
        check("ui \"Bind: \"", "绑定: ", com.meteorzh.ZhDict.ui("Bind: "));
        check("ui None", "无", com.meteorzh.ZhDict.ui("None"));
        check("ui Left Shift", "左Shift", com.meteorzh.ZhDict.ui("Left Shift"));

        // 未收录的串必须原样返回，绝不能变成 null 或空
        check("ui unknown", "Superflat World", com.meteorzh.ZhDict.ui("Superflat World"));
        check("module unknown keeps fallback", "<miss>",
            com.meteorzh.ZhDict.moduleTitle("no-such-module-xyz", "<miss>"));

        // 英文描述句按原句查表
        check("desc via sentence", "沿阿基米德螺旋飞行。",
            com.meteorzh.ZhDict.moduleDesc("no-such-module-xyz", "Fly an Archimedean spiral."));

        System.out.println();
        System.out.println(fail == 0
            ? "ALL OK (" + total + " checks)"
            : fail + " of " + total + " checks FAILED");
        System.exit(fail == 0 ? 0 : 1);
    }
}
