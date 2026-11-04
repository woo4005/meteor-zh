/*
 * Meteor-ZH - Meteor Client 简体中文汉化
 * Copyright (C) 2026 woo4005
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

package com.meteorzh;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import meteordevelopment.meteorclient.utils.player.ChatUtils;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.toasts.SystemToast;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Util;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 更新检查器 —— 只做「发现新版本并提示」，绝不擅自替换正在运行的文件。
 *
 * <h2>行为约定</h2>
 *
 * <ol>
 *   <li><b>每次启动只检查一次</b>：{@link #checkOnStartup()} 由首次 tick 触发，内部用
 *       {@link #AUTO_TRIED} 保证同一个会话里最多访问一次 GitHub。网络失败、超时、
 *       被墙、返回 404 —— 全部安静放弃，不重试、不打扰玩家。</li>
 *   <li><b>提示位置分两种</b>：玩家已经进入世界（单人/多人）时走聊天栏；还停留在
 *       主菜单时走右下角的系统弹窗（SystemToast）。这样刚开游戏就能看到提示，
 *       而不是非得进一次世界。</li>
 *   <li><b>手动检查</b>：{@link #checkManual()} 不占用「每次启动一次」的额度，玩家点
 *       多少次都可以，且无论成功失败都会给反馈。</li>
 *   <li><b>自动下载</b>（可选，默认关闭）：只在自动检查命中新版本时触发。文件先下到
 *       {@code mods/} 下的临时文件，下载完成后注册关闭钩子，等游戏退出后由一个
 *       cmd 脚本把新 jar 换上去并删掉旧 jar。当前进程绝不会去动正在被加载的 jar。</li>
 * </ol>
 *
 * <h2>为什么下载放在「关闭游戏后」</h2>
 *
 * <p>Windows 上正在运行的 jar 是被 JVM 持有句柄的，运行期间改名/删除一定失败。
 * 所以流程是：下载 → 落盘为临时文件 → 注册 shutdown hook → 游戏正常退出后 hook
 * 里启动一个独立 cmd 进程 → cmd 循环重试 move，直到旧进程完全释放句柄 → 替换成功
 * → 删掉旧 jar 与自身脚本。玩家下次启动游戏就是新版本。
 */
public final class UpdateChecker {
    /** GitHub 仓库（不带 .git）。改这里就等于换了更新源。 */
    public static final String REPO = "woo4005/meteor-zh";
    public static final String RELEASES_PAGE = "https://github.com/" + REPO + "/releases";
    private static final String API_RELEASES = "https://api.github.com/repos/" + REPO + "/releases?per_page=30";

    private static final int CONNECT_TIMEOUT_MS = 8000;
    private static final int READ_TIMEOUT_MS = 15000;

    /** 「每次启动只自动检查一次」的闸门。手动检查不走这个。 */
    private static final AtomicBoolean AUTO_TRIED = new AtomicBoolean(false);
    /** 同一时刻只允许一个网络任务在跑。 */
    private static final AtomicBoolean BUSY = new AtomicBoolean(false);

    private static volatile String status = "尚未检查";
    private static volatile Release found;
    private static volatile boolean downloaded;
    private static volatile Path downloadedPath;
    private static volatile String downloadError;

    private UpdateChecker() {
    }

    // ------------------------------------------------------------------
    // 对外查询
    // ------------------------------------------------------------------

    /** 本插件当前版本号，如 {@code 1.4.3}。取自 fabric.mod.json，由构建脚本展开。 */
    public static String currentVersion() {
        try {
            return FabricLoader.getInstance().getModContainer(MeteorZh.MOD_ID)
                .map(c -> c.getMetadata().getVersion().getFriendlyString())
                .orElse("0.0.0");
        } catch (Throwable t) {
            return "0.0.0";
        }
    }

    /** 当前 Minecraft 版本，如 {@code 1.21.11} 或 {@code 26.1}。 */
    public static String mcVersion() {
        try {
            return FabricLoader.getInstance().getModContainer("minecraft")
                .map(c -> c.getMetadata().getVersion().getFriendlyString())
                .orElse("?");
        } catch (Throwable t) {
            return "?";
        }
    }

    /** 最近一次检查的结果说明（给「关于汉化插件」模块显示）。 */
    public static String statusText() {
        return status;
    }

    public static boolean hasUpdate() {
        return found != null;
    }

    public static boolean isDownloaded() {
        return downloaded;
    }

    public static String latestVersion() {
        return found == null ? null : found.version;
    }

    public static String latestUrl() {
        return found == null ? RELEASES_PAGE : found.htmlUrl;
    }

    public static String downloadErrorText() {
        return downloadError;
    }

    // ------------------------------------------------------------------
    // 触发入口
    // ------------------------------------------------------------------

    /**
     * 启动时自动检查一次。只有「关于汉化插件」里的「自动检测更新」为开时才真正访问网络；
     * 无论成败，本次会话都不会再试第二次。
     */
    public static void checkOnStartup() {
        if (!AUTO_TRIED.compareAndSet(false, true)) return;

        AboutModule module = AboutModule.get();
        if (module == null || !module.autoCheck.get()) {
            status = "已关闭自动检测";
            return;
        }

        status = "正在检查更新…";
        request(true);
    }

    /**
     * 玩家手动点「立即检查更新」。不受「每次启动一次」限制，一定会给反馈。
     */
    public static void checkManual() {
        status = "正在检查更新…";
        notifyLater("正在检查更新…", "Meteor 汉化 · 请稍候");
        request(false);
    }

    /** 打开 GitHub 的 Releases 页面。 */
    public static void openDownloadPage() {
        openUrl(found != null ? found.htmlUrl : RELEASES_PAGE);
    }

    /** 打开浏览器，失败时在聊天栏说明（不可能抛到游戏主循环）。 */
    public static void openUrl(String url) {
        try {
            Util.getPlatform().openUri(URI.create(url).toString());
            status = "已在浏览器打开下载页";
        } catch (Throwable t) {
            status = "打开浏览器失败：" + t.getClass().getSimpleName();
            notifyLater("无法自动打开浏览器，请手动访问：" + url, "Meteor 汉化");
        }
    }

    // ------------------------------------------------------------------
    // 网络任务
    // ------------------------------------------------------------------

    private static void request(boolean automatic) {
        if (!BUSY.compareAndSet(false, true)) {
            status = "正在检查中，请稍候";
            return;
        }

        Thread thread = new Thread(() -> {
            try {
                String body = httpGet(API_RELEASES);
                Release release = pickBest(body);

                if (release == null) {
                    status = "未找到适配 " + mcVersion() + " 的发布版本";
                    if (!automatic) notifyLater("没有找到适配当前游戏版本（" + mcVersion() + "）的发布", "Meteor 汉化");
                    return;
                }

                found = release;

                if (compare(release.version, currentVersion()) > 0) {
                    status = "发现新版本 " + release.version + "（当前 " + currentVersion() + "）";
                    announce(release);

                    AboutModule module = AboutModule.get();
                    if (automatic && module != null && module.autoDownload.get()) {
                        download(release);
                    }
                } else {
                    status = "已是最新版本（" + currentVersion() + "）";
                    if (!automatic) {
                        notifyLater("已是最新版本：v" + currentVersion(), "Meteor 汉化");
                    }
                }
            } catch (Throwable t) {
                // 网络不可用、超时、被墙、JSON 变了…… 一律安静收尾；手动检查才提示。
                String reason = shortReason(t);
                status = "检查失败：" + reason;
                MeteorZh.LOG.warn("Meteor-zh: update check failed: {}", reason);
                if (!automatic) {
                    notifyLater("检查更新失败：" + reason, "Meteor 汉化");
                }
            } finally {
                BUSY.set(false);
            }
        }, "meteor-zh-update-check");

        thread.setDaemon(true);
        thread.start();
    }

    private static String httpGet(String url) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) URI.create(url).toURL().openConnection();
        try {
            connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
            connection.setReadTimeout(READ_TIMEOUT_MS);
            connection.setRequestMethod("GET");
            connection.setRequestProperty("Accept", "application/vnd.github+json");
            connection.setRequestProperty("User-Agent", "meteor-zh/" + currentVersion());
            connection.setInstanceFollowRedirects(true);

            int code = connection.getResponseCode();
            if (code == 404) {
                throw new IOException("仓库或发布页不存在（404）");
            }
            if (code != 200) {
                throw new IOException("HTTP " + code);
            }

            try (InputStream in = connection.getInputStream()) {
                return readAll(in);
            }
        } finally {
            connection.disconnect();
        }
    }

    private static String readAll(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream(16 * 1024);
        byte[] buffer = new byte[8192];
        int read;
        while ((read = in.read(buffer)) > 0) {
            out.write(buffer, 0, read);
        }
        return out.toString(StandardCharsets.UTF_8);
    }

    /**
     * 从 releases 列表里挑出「当前游戏版本 + 当前版本线」的最新一条。
     *
     * <p>光看 tag 不够：仓库里同时存在 {@code v1.4.x}（1.21.11 线）与 {@code v1.5.x}（26.1 线），
     * 而玩家装的是其中一个。所以真正的判据是「这个 release 有没有挂着以
     * {@code -mc<当前 MC 版本>.jar} 结尾的产物」—— 有才说明它是给我这个游戏版本用的。
     */
    private static Release pickBest(String jsonBody) {
        JsonArray array;
        try {
            JsonElement parsed = JsonParser.parseString(jsonBody);
            if (!parsed.isJsonArray()) return null;
            array = parsed.getAsJsonArray();
        } catch (Throwable t) {
            return null;
        }

        String mc = mcVersion();
        String targetSuffix = "-mc" + mc + ".jar";
        List<Release> candidates = new ArrayList<>();

        for (JsonElement element : array) {
            if (!element.isJsonObject()) continue;
            JsonObject release = element.getAsJsonObject();

            if (bool(release, "draft") || bool(release, "prerelease")) continue;

            String tag = str(release, "tag_name");
            if (tag == null || tag.isEmpty()) continue;
            String version = normaliseTag(tag);

            JsonArray assets = release.has("assets") && release.get("assets").isJsonArray()
                ? release.getAsJsonArray("assets") : new JsonArray();

            String assetName = null;
            String assetUrl = null;
            long assetSize = 0;

            for (JsonElement assetElement : assets) {
                if (!assetElement.isJsonObject()) continue;
                JsonObject asset = assetElement.getAsJsonObject();
                String name = str(asset, "name");
                if (name == null || !name.endsWith(".jar")) continue;
                if (!name.endsWith(targetSuffix)) continue;
                assetName = name;
                assetUrl = str(asset, "browser_download_url");
                assetSize = number(asset, "size");
                break;
            }

            if (assetUrl == null || assetUrl.isEmpty()) continue;

            String htmlUrl = str(release, "html_url");
            candidates.add(new Release(version, htmlUrl == null ? RELEASES_PAGE : htmlUrl, assetName, assetUrl, assetSize));
        }

        candidates.sort((a, b) -> compare(b.version, a.version));
        return candidates.isEmpty() ? null : candidates.get(0);
    }

    private static String normaliseTag(String tag) {
        String value = tag.trim();
        if (value.startsWith("v") || value.startsWith("V")) value = value.substring(1);
        return value;
    }

    // ------------------------------------------------------------------
    // 下载 + 退出后替换
    // ------------------------------------------------------------------

    private static void download(Release release) {
        try {
            Path mods = modsDirectory();
            if (mods == null) {
                downloadError = "找不到 mods 目录";
                status = "发现 " + release.version + "，但定位 mods 目录失败";
                return;
            }

            Path target = mods.resolve(release.assetName);
            Path temp = mods.resolve(release.assetName + ".download");
            Files.deleteIfExists(temp);

            status = "发现 " + release.version + "，正在后台下载…";
            MeteorZh.LOG.info("Meteor-zh: downloading {}", release.assetUrl);

            HttpURLConnection connection = (HttpURLConnection) URI.create(release.assetUrl).toURL().openConnection();
            try {
                connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
                connection.setReadTimeout(60000);
                connection.setRequestProperty("Accept", "application/octet-stream");
                connection.setRequestProperty("User-Agent", "meteor-zh/" + currentVersion());
                connection.setInstanceFollowRedirects(true);

                int code = connection.getResponseCode();
                if (code != 200) throw new IOException("下载失败 HTTP " + code);

                try (InputStream in = connection.getInputStream();
                     OutputStream out = Files.newOutputStream(temp)) {
                    byte[] buffer = new byte[16 * 1024];
                    int read;
                    while ((read = in.read(buffer)) > 0) {
                        out.write(buffer, 0, read);
                    }
                }
            } finally {
                connection.disconnect();
            }

            if (Files.size(temp) < 1024) {
                Files.deleteIfExists(temp);
                throw new IOException("下载内容过小，可能是错误页");
            }

            downloaded = true;
            downloadedPath = temp;
            downloadError = null;

            // 老的 jar（正在被 JVM 使用的那一个），退出后要删掉，否则两个同 id 的模组会打架。
            Path oldJar = currentJar();
            registerInstaller(temp, target, oldJar);

            String message = "更新已下载完成（v" + release.version + "），关闭游戏后会自动替换并生效";
            status = message;
            notifyLater(message, "Meteor 汉化 · 更新就绪");
        } catch (Throwable t) {
            downloaded = false;
            downloadError = shortReason(t);
            status = "发现 " + release.version + "，但自动下载失败：" + downloadError;
            MeteorZh.LOG.warn("Meteor-zh: auto download failed", t);
            notifyLater("自动下载失败：" + downloadError + "，可手动前往下载页", "Meteor 汉化");
        }
    }

    /**
     * 注册退出钩子：游戏正常关闭后，由一个独立 cmd 进程完成「替换 + 删旧 + 自删」。
     *
     * <p>用脚本而不是 Java 直接操作，是因为正在运行的 jar 在 Windows 上被 JVM 独占，
     * 只有主进程彻底退出、句柄释放后才能动。脚本会循环重试到成功为止。
     */
    private static void registerInstaller(Path temp, Path target, Path oldJar) {
        try {
            Path script = Files.createTempFile("meteor-zh-update-", ".bat");

            StringBuilder sb = new StringBuilder();
            sb.append("@echo off\r\n");
            sb.append("chcp 65001 >nul\r\n");
            sb.append("setlocal\r\n");
            sb.append(":retry\r\n");
            sb.append("move /y \"").append(temp).append("\" \"").append(target).append("\" >nul 2>&1\r\n");
            sb.append("if errorlevel 1 (\r\n");
            sb.append("  ping -n 2 127.0.0.1 >nul\r\n");
            sb.append("  goto retry\r\n");
            sb.append(")\r\n");
            if (oldJar != null && !oldJar.equals(target)) {
                sb.append("del /q \"").append(oldJar).append("\" >nul 2>&1\r\n");
            }
            sb.append("(goto) 2>nul & del \"%~f0\"\r\n");

            Files.write(script, sb.toString().getBytes(StandardCharsets.UTF_8));

            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                try {
                    // start /min 让脚本脱离本进程的生命周期
                    new ProcessBuilder("cmd", "/c", "start", "/min", script.toString())
                        .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                        .redirectError(ProcessBuilder.Redirect.DISCARD)
                        .start();
                } catch (Throwable t) {
                    MeteorZh.LOG.warn("Meteor-zh: failed to spawn update installer", t);
                }
            }, "meteor-zh-update-installer"));

            MeteorZh.LOG.info("Meteor-zh: installer registered ({} -> {})", temp.getFileName(), target.getFileName());
        } catch (Throwable t) {
            downloadError = "写入更新脚本失败：" + shortReason(t);
            MeteorZh.LOG.warn("Meteor-zh: failed to register installer", t);
        }
    }

    /** 当前运行的 jar 路径（mods 目录里名字最匹配的那个），找不到就返回 null。 */
    private static Path currentJar() {
        try {
            Path mods = modsDirectory();
            if (mods == null) return null;
            Path best = null;
            List<Path> entries;
            try (var stream = Files.list(mods)) {
                entries = stream.toList();
            }
            for (Path path : entries) {
                String name = path.getFileName().toString();
                if (!name.startsWith("meteor-zh-") || !name.endsWith(".jar")) continue;
                if (!name.contains(currentVersion())) continue;
                if (best == null || name.length() > best.getFileName().toString().length()) {
                    best = path;
                }
            }
            return best;
        } catch (Throwable t) {
            return null;
        }
    }

    private static Path modsDirectory() {
        try {
            Path gameDir = FabricLoader.getInstance().getGameDir();
            Path mods = gameDir.resolve("mods");
            if (Files.isDirectory(mods)) return mods;
            // 少数整合包把 mods 放在版本隔离目录里，游戏目录本身就是那一层，所以这里再直接试一次。
            return Files.isDirectory(gameDir) ? mods : null;
        } catch (Throwable t) {
            return null;
        }
    }

    // ------------------------------------------------------------------
    // 提示（聊天栏 / 右下角弹窗）
    // ------------------------------------------------------------------

    /**
     * 发现新版本时的提示。玩家在世界里 → 聊天栏；在主菜单 → 右下角弹窗。
     */
    private static void announce(Release release) {
        String title = "Meteor 汉化 有新版本";
        String detail = "v" + release.version + "（当前 v" + currentVersion() + "）";
        String url = release.htmlUrl;

        if (inWorld()) {
            ChatUtils.info(title + "：" + detail);
            ChatUtils.info("下载地址：" + url);
            ChatUtils.info("也可以在「关于汉化插件」里点「立即检查更新」或「打开下载页面」");
        } else {
            toast(title, detail + " · " + url);
        }
    }

    /** 通用提示：在世界里发聊天栏，否则弹窗。 */
    static void notifyLater(String message, String title) {
        try {
            if (inWorld()) {
                ChatUtils.info(message);
            } else {
                toast(title, message);
            }
        } catch (Throwable t) {
            MeteorZh.LOG.info("Meteor-zh: {}", message);
        }
    }

    private static void toast(String title, String subtitle) {
        try {
            Minecraft mc = Minecraft.getInstance();
            if (mc == null) return;
            SystemToast.add(mc.getToastManager(), TOAST_ID,
                Component.literal(title), Component.literal(subtitle));
        } catch (Throwable t) {
            MeteorZh.LOG.warn("Meteor-zh: failed to show toast", t);
        }
    }

    private static final SystemToast.SystemToastId TOAST_ID = new SystemToast.SystemToastId(6000L);

    private static boolean inWorld() {
        Minecraft mc = Minecraft.getInstance();
        return mc != null && mc.level != null && mc.player != null;
    }

    // ------------------------------------------------------------------
    // 小工具
    // ------------------------------------------------------------------

    /** 版本比较：{@code compare("1.4.3", "1.4.2") > 0}。非数字段按 0 处理。 */
    public static int compare(String a, String b) {
        int[] left = segments(a);
        int[] right = segments(b);
        int length = Math.max(left.length, right.length);
        for (int i = 0; i < length; i++) {
            int x = i < left.length ? left[i] : 0;
            int y = i < right.length ? right[i] : 0;
            if (x != y) return Integer.compare(x, y);
        }
        return 0;
    }

    private static int[] segments(String version) {
        if (version == null) return new int[0];
        String[] parts = version.trim().split("[.+\\-]");
        List<Integer> numbers = new ArrayList<>();
        for (String part : parts) {
            StringBuilder digits = new StringBuilder();
            for (int i = 0; i < part.length(); i++) {
                char c = part.charAt(i);
                if (c >= '0' && c <= '9') digits.append(c);
                else break;
            }
            if (digits.length() == 0) continue;
            try {
                numbers.add(Integer.parseInt(digits.toString()));
            } catch (NumberFormatException ignored) {
                // 超长数字段直接跳过
            }
        }
        int[] result = new int[numbers.size()];
        for (int i = 0; i < result.length; i++) result[i] = numbers.get(i);
        return result;
    }

    private static String shortReason(Throwable t) {
        String message = t.getMessage();
        if (message == null || message.isBlank()) message = t.getClass().getSimpleName();
        if (message.length() > 80) message = message.substring(0, 80) + "…";
        return message;
    }

    private static String str(JsonObject object, String key) {
        try {
            return object.has(key) && !object.get(key).isJsonNull() ? object.get(key).getAsString() : null;
        } catch (Throwable t) {
            return null;
        }
    }

    private static boolean bool(JsonObject object, String key) {
        try {
            return object.has(key) && !object.get(key).isJsonNull() && object.get(key).getAsBoolean();
        } catch (Throwable t) {
            return false;
        }
    }

    private static long number(JsonObject object, String key) {
        try {
            return object.has(key) && !object.get(key).isJsonNull() ? object.get(key).getAsLong() : 0L;
        } catch (Throwable t) {
            return 0L;
        }
    }

    /** 一个 GitHub release 里我们需要的字段。 */
    private static final class Release {
        final String version;
        final String htmlUrl;
        final String assetName;
        final String assetUrl;
        @SuppressWarnings("unused")
        final long assetSize;

        Release(String version, String htmlUrl, String assetName, String assetUrl, long assetSize) {
            this.version = version;
            this.htmlUrl = htmlUrl;
            this.assetName = assetName;
            this.assetUrl = assetUrl;
            this.assetSize = assetSize;
        }
    }

    /** 给「关于汉化插件」显示的一行摘要。 */
    public static String summaryLine() {
        StringBuilder sb = new StringBuilder();
        sb.append("当前版本 v").append(currentVersion());
        sb.append("（Minecraft ").append(mcVersion()).append("）");
        if (found != null && compare(found.version, currentVersion()) > 0) {
            sb.append(" · 可更新到 v").append(found.version);
        }
        if (downloaded) {
            sb.append(" · 已下载，重启后生效");
        }
        return sb.toString();
    }

    /** 未使用的提示：确保 static 初始化不会因为 Optional 缺失而崩。 */
    static Optional<String> emptyOptional() {
        return Optional.empty();
    }
}
