// Meteor-ZH 词典加载的 JVM 侧验证（不启动 Minecraft）。
//
// 由 scripts/verify_dict.py 编译并运行：加载 jar 内 assets/meteorzh/lang/zh.json，
// 打印若干真实查找结果，用来确认「资源在 jar 里」「Gson 能解析」「回落顺序符合设计」。
public class TestZh {
    public static void main(String[] args) throws Exception {
        com.meteorzh.ZhDict.load();
        System.out.println("loaded   = " + com.meteorzh.ZhDict.isLoaded());
        System.out.println("size     = " + com.meteorzh.ZhDict.size());
        System.out.println("module   anti-afk          -> " + com.meteorzh.ZhDict.moduleTitle("anti-afk", "<miss>"));
        System.out.println("module   kill-aura         -> " + com.meteorzh.ZhDict.moduleTitle("kill-aura", "<miss>"));
        System.out.println("module   elytra-finder     -> " + com.meteorzh.ZhDict.moduleTitle("elytra-finder", "<miss>"));
        System.out.println("setting  range             -> " + com.meteorzh.ZhDict.settingTitle("range", "<miss>"));
        System.out.println("group    General           -> " + com.meteorzh.ZhDict.groupTitle("General"));
        System.out.println("group    Render            -> " + com.meteorzh.ZhDict.groupTitle("Render"));
        System.out.println("ui       Bind              -> " + com.meteorzh.ZhDict.ui("Bind"));
        System.out.println("ui       Bind: (trailing)  -> " + com.meteorzh.ZhDict.ui("Bind: "));
        System.out.println("ui       None              -> " + com.meteorzh.ZhDict.ui("None"));
        System.out.println("ui       Left Shift        -> " + com.meteorzh.ZhDict.ui("Left Shift"));
        System.out.println("ui       unmodified str    -> " + com.meteorzh.ZhDict.ui("Superflat World"));
        System.out.println("desc     via text          -> " + com.meteorzh.ZhDict.moduleDesc("no-such-module",
                "Fly an Archimedean spiral."));
    }
}
