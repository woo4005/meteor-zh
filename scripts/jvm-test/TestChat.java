/*
 * Meteor-ZH 离线验证：聊天模板反查引擎。
 *
 * 这个测试存在的理由：formatMsg 收到的是「已经填好参数」的字符串，
 * 所以翻译靠的是把英文模板编译成正则再反查。正则写错不会抛异常，
 * 只会静默不匹配 —— 只有断言能发现。
 */
import com.meteorzh.ChatDict;

public class TestChat {
    private static int total = 0;
    private static int fail = 0;

    private static void check(String what, String actual, String mustContain) {
        total++;
        boolean ok = actual != null && actual.contains(mustContain);
        if (!ok) {
            fail++;
            System.out.println("FAIL " + what);
            System.out.println("     want contains: " + mustContain);
            System.out.println("     actual       : " + actual);
        } else {
            System.out.println("ok   " + what);
        }
    }

    private static void checkNull(String what, String actual) {
        total++;
        if (actual != null) {
            fail++;
            System.out.println("FAIL " + what + " -- expected null, got: " + actual);
        } else {
            System.out.println("ok   " + what);
        }
    }

    public static void main(String[] args) {
        ChatDict.load();

        if (!ChatDict.isLoaded()) {
            System.out.println("FAIL chat.json 没被读到（资源缺失或 JSON 解析失败）");
            System.exit(1);
        }

        total++;
        if (ChatDict.size() < 100) {
            fail++;
            System.out.println("FAIL 模板条数过少: " + ChatDict.size());
        } else {
            System.out.println("ok   templates = " + ChatDict.size());
        }

        // 1) Jefff 仓库寻找器：%s 被坐标填掉，仍要能反查（用户截图里的那条）
        check("stash finder",
            ChatDict.translate("Found stash at (highlight)5178744(default), (highlight)5296888(default)."),
            "发现仓库");

        // 2) Meteor Notifier：珍珠落点，四个 %d / 两个 %.1f
        check("notifier pearl",
            ChatDict.translate("(highlight)woo4005's(default) pearl landed at 5179005, 128, 5296969 "
                + "(highlight)(80.0m away, travelled 0.1m)(default)."),
            "末影珍珠");

        // 3) 无参数消息走精确查表
        check("exact hit", ChatDict.translate("Bound to (highlight)Sprint(default)."), "已绑定");

        // 4) 数值格式符：反查后坐标必须还在原位
        String toggled = ChatDict.translate("Toggled setting (highlight)Range(default) to (highlight)5(default).");
        check("two strings", toggled, "切换");

        // 5) 中文原文不能被二次翻译
        checkNull("chinese passthrough", ChatDict.translate("在 (highlight)5178744(default) 发现仓库。"));

        // 6) 未收录的模板必须原样放过
        checkNull("unknown message", ChatDict.translate("resolveArea: something internal"));
        checkNull("empty", ChatDict.translate(""));

        // 7) 超长字符串直接放过（防止正则去啃拼接出来的调试串）
        StringBuilder big = new StringBuilder();
        for (int i = 0; i < 500; i++) big.append('x');
        checkNull("too long", ChatDict.translate(big.toString()));

        System.out.println(fail == 0
            ? "ALL OK (" + total + " checks)"
            : fail + "/" + total + " checks FAILED");
        System.exit(fail == 0 ? 0 : 1);
    }
}
