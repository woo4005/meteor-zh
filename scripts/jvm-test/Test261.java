import com.meteorzh.Translator;
import com.meteorzh.WordTranslator;
import com.meteorzh.ZhDict;

/**
 * 26.1 离线验证：不启动游戏，只验证词典加载 + 反射字段存在 + 若干查找结果。
 * 由 scripts/verify_261.py 编译并运行（classpath 用 26.1 实例的真实库）。
 */
public class Test261 {
    private static int failed = 0;

    private static void check(String label, Object actual, Object expected) {
        boolean ok = expected == null ? actual == null : expected.equals(actual);
        System.out.printf("%-46s %s  %s%n", label, ok ? "OK  " : "FAIL", actual);
        if (!ok) failed++;
    }

        /** FontFixer must load and fail soft outside a GL context. */
    private static void fontProbe() {
        try {
            boolean cn = com.meteorzh.FontFixer.supportsChinese();
            String fam = com.meteorzh.FontFixer.currentFamily();
            System.out.println("font probe: supportsChinese=" + cn + " family=" + fam);
        } catch (Throwable t) {
            System.out.println("font probe: THREW " + t);
            throw t;
        }
    }

public static void main(String[] args) throws Exception {
        ZhDict.load();
        check("dictionary size > 0", ZhDict.size() > 0, true);

        // 最关键的一步：9 个反射字段若有一个不存在，这里会抛 NoSuchFieldException
        Translator.init();
        System.out.println("Translator.init()                 OK   (9 个反射字段全部存在)");

        check("module kill-aura", ZhDict.moduleTitle("kill-aura", "kill-aura"), "杀戮光环");
        check("module anti-anchor (26.1 新增)", ZhDict.moduleTitle("anti-anchor", "anti-anchor"), "防锚光环");
        check("module weather-changer (26.1 新增)", ZhDict.moduleTitle("weather-changer", "weather-changer"), "天气修改器");
        check("setting range", ZhDict.settingTitle("range", "range"), "范围");
        check("setting fluid-opacity (26.1 新增)", ZhDict.settingTitle("fluid-opacity", "fluid-opacity"), "流体不透明度");
        check("group General", ZhDict.groupTitle("General"), "通用");
        check("ui 'Bind: '", ZhDict.ui("Bind: "), "绑定: ");
        check("desc sentence", ZhDict.moduleDesc("excavator", "Excavate a selection area."), "挖掘选定的区域。");
        check("lexical chunk-render-distance",
              WordTranslator.translate("chunk-render-distance"), "区块渲染距离");
        check("lexical keeps chinese", WordTranslator.translate("自动跟随"), null);

        System.out.println();
        fontProbe();
        System.out.println(failed == 0 ? "ALL OK" : (failed + " FAILED"));
        if (failed != 0) System.exit(1);
    }
}
