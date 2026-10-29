// Meteor-ZH 词法兜底引擎的 JVM 侧验证（不启动 Minecraft）。
//
// 由 scripts/verify_lexical.py 编译并运行：喂一批「词典里没有的」标识符，看
// WordTranslator 能否逐词合成出可读中文；再喂已是中文的名字，确认返回 null
// （这是兜底引擎不破坏 Miku/Lotus 中文模块名的关键设计）。
//
// 断言的写法刻意保持宽松但有效：只要求「必须合成出中文」「必须包含某个关键
// 词根」「中文输入必须返回 null」，不去比对完整句子 —— 词表会继续扩充，
// 逐字比对会让每次补词都得改测试。
public class TestLex {
    private static int fail;
    private static int total;

    private static void expectChinese(String name, String mustContain) {
        total++;
        String zh = com.meteorzh.WordTranslator.translate(name);
        boolean ok = zh != null && zh.matches(".*[\\u4e00-\\u9fff].*");
        if (ok && mustContain != null) ok = zh.contains(mustContain);
        if (ok) {
            System.out.println("  OK   " + name + " -> " + zh);
        } else {
            fail++;
            System.out.println("  FAIL " + name + " -> " + zh
                + (mustContain == null ? "" : " (must contain " + mustContain + ")"));
        }
    }

    private static void expectNull(String name) {
        total++;
        String zh = com.meteorzh.WordTranslator.translate(name);
        if (zh == null) {
            System.out.println("  OK   " + name + " -> (null)");
        } else {
            fail++;
            System.out.println("  FAIL " + name + " -> " + zh + " (should be null)");
        }
    }

    public static void main(String[] a) {
        com.meteorzh.WordTranslator.load();

        total++;
        int words = com.meteorzh.WordTranslator.size();
        if (words < 900) {
            fail++;
            System.out.println("  FAIL word table only " + words + " words (expected >= 900)");
        } else {
            System.out.println("  OK   word table -> " + words + " words");
        }

        // 词典里没有的假想 addon 标识符：必须能合成出可读中文
        expectChinese("chunk-render-distance", "区块");
        expectChinese("auto-totem-refill", "图腾");
        expectChinese("potion-refill-threshold", "阈值");
        expectChinese("beam-width-limit", null);
        expectChinese("inventory-manager", null);
        expectChinese("smart-crystal-placement", null);

        // 已经是中文的名字：必须返回 null，绝不能把中文再「翻译」一遍
        expectNull("\u81ea\u52a8\u8ddf\u968f");
        expectNull("miku-\u6295\u5f71\u6253\u5370\u673a");

        System.out.println();
        System.out.println(fail == 0
            ? "ALL OK (" + total + " checks)"
            : fail + " of " + total + " checks FAILED");
        System.exit(fail == 0 ? 0 : 1);
    }
}
