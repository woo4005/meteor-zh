// Meteor-ZH 词法兜底引擎的 JVM 侧验证（不启动 Minecraft）。
//
// 由 scripts/verify_lexical.py 编译并运行：喂一批「词典里没有的」标识符，看
// WordTranslator 能否逐词合成出可读中文；再喂已是中文的名字，确认返回 null
// （这是兜底引擎不破坏 Miku/Lotus 中文模块名的关键设计）。
public class TestLex {
    public static void main(String[] a) {
        com.meteorzh.WordTranslator.load();
        System.out.println("words=" + com.meteorzh.WordTranslator.size());

        String[] names = {
            // 词典里没有的假想 addon 标识符
            "nether-crystal-aura", "beam-width-limit", "auto-totem-refill",
            "sprint-reset-delay", "elytra-speed-boost", "chunk-render-distance",
            "chest-stealer-percent", "potion-refill-threshold", "inventory-manager",
            "anti-knockback", "no-fall-damage", "smart-crystal-placement",
            // 词典里已有的（用于对比词法结果与人工译名的差距）
            "world-origin", "min-height-log", "elytra-finder", "spiral-flight",
            "auto-firework", "render-chunks", "trail-color", "pull-up-angle",
            "search-window-rad", "item-frame-search", "waypoint-reader",
            // 已经是中文的名字：必须返回 null，交给调用方原样显示
            "自动跟随", "miku-投影打印机",
        };
        for (String n : names) {
            String zh = com.meteorzh.WordTranslator.translate(n);
            System.out.println(String.format("%-26s -> %s", n, zh == null ? "(null)" : zh));
        }
    }
}
