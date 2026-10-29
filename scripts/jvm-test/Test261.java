import com.meteorzh.FontFixer;
import com.meteorzh.Translator;
import com.meteorzh.WordTranslator;
import com.meteorzh.ZhDict;

import java.util.List;

/**
 * 26.1 离线验证：不启动游戏，只验证词典加载 + 反射字段存在 + 若干查找结果。
 * 由 scripts/verify_261.py 编译并运行（classpath 用 26.1 实例的真实库）。
 *
 * <p>每一条 check 都会累计失败数，最后非 0 退出 —— 早期的版本只 println，
 * JVM 能启动就算绿，Meteor 改个字段名也发现不了。
 */
public class Test261 {
    private static int failed;
    private static int total;

    private static void check(String label, Object actual, Object expected) {
        total++;
        boolean ok = expected == null ? actual == null : expected.equals(actual);
        System.out.printf("  %s %-44s %s%n", ok ? "OK  " : "FAIL", label, actual);
        if (!ok) failed++;
    }

    private static void checkTrue(String label, boolean condition) {
        check(label, condition, Boolean.TRUE);
    }

    /** FontFixer 在没有 GL 上下文时必须安全降级（不抛异常）。 */
    private static void fontProbe() {
        total++;
        try {
            String desc = FontFixer.describe();
            boolean vanilla = FontFixer.usingVanilla();
            System.out.println("  OK   font probe: " + desc + " (vanilla=" + vanilla + ")");
        } catch (Throwable t) {
            failed++;
            System.out.println("  FAIL font probe threw " + t);
        }
    }

    public static void main(String[] args) throws Exception {
        ZhDict.load();
        checkTrue("dictionary loaded", ZhDict.isLoaded());
        checkTrue("dictionary size > 1000", ZhDict.size() > 1000);

        // 最关键的一步：反射字段若有一个不存在，missingFields() 会列出来
        Translator.init();
        List<String> missing = Translator.missingFields();
        check("reflection fields resolvable", missing.isEmpty() ? "all" : missing, "all");

        check("module kill-aura", ZhDict.moduleTitle("kill-aura", "kill-aura"), "杀戮光环");
        check("module anti-anchor (26.1 新增)", ZhDict.moduleTitle("anti-anchor", "anti-anchor"), "防锚光环");
        check("module weather-changer (26.1 新增)", ZhDict.moduleTitle("weather-changer", "weather-changer"), "天气修改器");
        check("setting range", ZhDict.settingTitle("range", "range"), "范围");
        check("setting fluid-opacity (26.1 新增)", ZhDict.settingTitle("fluid-opacity", "fluid-opacity"), "流体不透明度");
        check("group General", ZhDict.groupTitle("General"), "通用");
        check("ui 'Bind: '", ZhDict.ui("Bind: "), "绑定: ");
        check("desc sentence", ZhDict.moduleDesc("excavator", "Excavate a selection area."), "挖掘选定的区域。");
        check("lexical chunk-render-distance", WordTranslator.translate("chunk-render-distance"), "区块渲染距离");
        check("lexical keeps chinese", WordTranslator.translate("\u81ea\u52a8\u8ddf\u968f"), null);

        System.out.println();
        fontProbe();

        System.out.println();
        System.out.println(failed == 0
            ? "ALL OK (" + total + " checks)"
            : failed + " of " + total + " checks FAILED");
        if (failed != 0) System.exit(1);
    }
}
