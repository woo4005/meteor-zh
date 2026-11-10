import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.meteorzh.UpdateChecker;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 更新器完整性校验的离线断言（对应桌面草稿「验收清单」前四条）。
 *
 * <p>这里只测「纯函数」部分：sha256 计算、digest 解析、下载域名白名单、资产版本匹配。
 * 真正下载与替换要联网 + 重启游戏，不可能在离线 JVM 里跑，所以那部分靠代码审阅 +
 * 真机验证；但只要这几条守住，供应链里最容易写错的环节（漏校验、白名单写成后缀匹配、
 * 版本匹配过窄）就不会再悄悄回归。
 */
public class TestUpdateIntegrity {
    private static int failed;
    private static int total;

    private static void check(String label, Object actual, Object expected) {
        total++;
        boolean ok = expected == null ? actual == null : expected.equals(actual);
        System.out.printf("  %s %-46s %s%n", ok ? "OK  " : "FAIL", label, actual);
        if (!ok) failed++;
    }

    private static void checkTrue(String label, boolean condition) {
        check(label, condition, Boolean.TRUE);
    }

    public static void main(String[] args) throws Exception {
        // ---- 1. sha256 计算结果必须与标准向量一致（"abc" 是 FIPS 180 的经典样例）----
        Path tmp = Files.createTempFile("meteor-zh-sha-", ".bin");
        try {
            Files.write(tmp, "abc".getBytes(StandardCharsets.UTF_8));
            check("sha256(\"abc\")",
                UpdateChecker.sha256Hex(tmp),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");

            Files.write(tmp, "".getBytes(StandardCharsets.UTF_8));
            check("sha256(\"\")",
                UpdateChecker.sha256Hex(tmp),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
        } finally {
            Files.deleteIfExists(tmp);
        }

        // ---- 2. digest 解析：带 sha256: 前缀、大写、缺字段 ----
        check("sha256Of(sha256:ABC123) 去前缀并转小写",
            UpdateChecker.sha256Of(asset("sha256:ABC123")), "abc123");
        check("sha256Of 缺 digest 返回 null",
            UpdateChecker.sha256Of(asset(null)), null);
        check("sha256Of 空 digest 返回 null",
            UpdateChecker.sha256Of(asset("")), null);

        // ---- 3. 下载域名白名单：必须是精确匹配或子域名，不能被后缀骗过 ----
        checkTrue("github.com 允许", UpdateChecker.isAllowedDownloadHost("github.com"));
        checkTrue("objects.githubusercontent.com 允许",
            UpdateChecker.isAllowedDownloadHost("objects.githubusercontent.com"));
        checkTrue("api.github.com 允许", UpdateChecker.isAllowedDownloadHost("api.github.com"));
        checkTrue("大小写不敏感", UpdateChecker.isAllowedDownloadHost("GitHub.COM"));
        checkTrue("evil.example.com 拒绝", !UpdateChecker.isAllowedDownloadHost("evil.example.com"));
        checkTrue("github.com.evil.example 拒绝",
            !UpdateChecker.isAllowedDownloadHost("github.com.evil.example"));
        checkTrue("notgithub.com 拒绝", !UpdateChecker.isAllowedDownloadHost("notgithub.com"));
        checkTrue("空主机拒绝", !UpdateChecker.isAllowedDownloadHost(""));
        checkTrue("null 主机拒绝", !UpdateChecker.isAllowedDownloadHost(null));

        // ---- 4. 资产版本匹配（防止再次出现「26.1.1 上永远更新不到」）----
        String jar = "meteor-zh-1.5.8-mc26.1.x.jar";
        checkTrue(".x 匹配 26.1", UpdateChecker.assetMatches(jar, "26.1"));
        checkTrue(".x 匹配 26.1.1", UpdateChecker.assetMatches(jar, "26.1.1"));
        checkTrue(".x 匹配 26.1.2", UpdateChecker.assetMatches(jar, "26.1.2"));
        checkTrue(".x 不匹配 26.2", !UpdateChecker.assetMatches(jar, "26.2"));
        checkTrue("区间覆盖低端",
            UpdateChecker.assetMatches("meteor-zh-1.5.8-mc26.1~26.1.2.jar", "26.1"));
        checkTrue("区间覆盖高端",
            UpdateChecker.assetMatches("meteor-zh-1.5.8-mc26.1~26.1.2.jar", "26.1.2"));
        checkTrue("精确版本不越界",
            !UpdateChecker.assetMatches("meteor-zh-1.4.8-mc1.21.11.jar", "1.21.10"));

        System.out.println();
        System.out.println(failed == 0
            ? "ALL OK (" + total + " checks)"
            : failed + " of " + total + " checks FAILED");
        if (failed != 0) System.exit(1);
    }

    private static JsonObject asset(String digest) {
        JsonObject json = JsonParser.parseString("{\"name\":\"x.jar\"}").getAsJsonObject();
        if (digest != null) json.addProperty("digest", digest);
        return json;
    }
}
