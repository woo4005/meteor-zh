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

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 聊天栏消息译文。
 *
 * <p>模块名会被 {@link Translator} 反射改成中文，所以聊天里会出现
 * {@code [Meteor] [仓库寻找器] Found stash at 123, 456.} —— 前缀是中文、正文还是英文。
 *
 * <h2>为什么挂在 {@code ChatUtils.formatMsg} 上</h2>
 * 所有带文本的消息最终都会汇聚到
 * {@code ChatUtils.sendMsg(int, String, ChatFormatting, ChatFormatting, String, Object...)}，
 * 它先做 {@code String.format(模板, 参数)}，再调私有静态的
 * {@code formatMsg(String, ChatFormatting)} 处理 {@code (highlight)} 这类伪颜色标记。
 * <ul>
 *   <li>{@code info/warning/error} 只有 3 个入口不覆盖第三方 addon —— 比如 Jefff 的
 *       仓库寻找器、Meteor 的 Notifier 都是直接调 {@code sendMsg(...)}。</li>
 *   <li>{@code sendMsg} 有 7 个重载，注解里必须写描述符才能唯一定位，而描述符里
 *       含 {@code ChatFormatting}（MC 类型）—— 两条线的类名不同（1.21.11 是
 *       混淆后的 {@code class_124}、26.1 是 {@code ChatFormatting}），一份源码没法同时写。</li>
 *   <li>{@code formatMsg} 的名字在两个版本里**都是唯一**的，注解只需要写方法名，
 *       不含任何 MC 类型，{@code remap = false} 在两条线上都成立。</li>
 * </ul>
 *
 * <h2>为什么用「反查模板」而不是精确查表</h2>
 * {@code formatMsg} 拿到的是**已经填好参数**的字符串（{@code %s} 已经变成坐标、
 * 玩家名），所以不能直接拿模板当 key。这里的做法是把每条英文模板编译成正则：
 * 格式符换成捕获组，其余字符原样转义；再用对应的中文模板 + {@code $1..$n} 拼回。
 * 因为构建期已经硬校验过「中英模板的格式符个数与顺序一致」，捕获组下标天然对齐。
 *
 * <p>词典没收录的消息一律返回 {@code null}，调用方原样放行。故意不收录
 * {@code resolveArea:} / {@code GoalNear{...}} 这类调试输出：它们是诊断信息，
 * 翻译反而丢失细节。
 */
public final class ChatDict {
    /** 精确匹配表：无参数的消息（模板里没有格式符）直接命中。 */
    private static final Map<String, String> TEMPLATES = new HashMap<>();

    /** 反查表：按首字符分桶，避免每条消息都跑上百个正则。 */
    private static final Map<Character, List<Rule>> RULES = new HashMap<>();

    private static boolean loaded;

    private ChatDict() {}

    public static boolean isLoaded() {
        return loaded;
    }

    public static int size() {
        return TEMPLATES.size();
    }

    public static void load() {
        if (loaded) return;
        loadInternal();
    }

    /** 供 {@code .zh reload} 使用：清空后重新读盘。 */
    public static void reload() {
        TEMPLATES.clear();
        RULES.clear();
        loaded = false;
        loadInternal();
    }

    private static void loadInternal() {
        try (InputStream in = ChatDict.class.getResourceAsStream("/assets/meteorzh/lang/chat.json")) {
            if (in == null) {
                MeteorZh.LOG.warn("Meteor-zh: chat template file missing from jar");
                return;
            }

            JsonElement root = JsonParser.parseReader(
                new InputStreamReader(in, StandardCharsets.UTF_8));

            if (root.isJsonObject()) {
                for (Map.Entry<String, JsonElement> e : root.getAsJsonObject().entrySet()) {
                    JsonElement v = e.getValue();
                    if (v == null || !v.isJsonPrimitive()) continue;

                    String en = e.getKey();
                    String zh = v.getAsString();
                    if (en.isEmpty() || zh == null || zh.isEmpty()) continue;

                    TEMPLATES.put(en, zh);

                    Rule rule = Rule.compile(en, zh);
                    if (rule != null) {
                        RULES.computeIfAbsent(rule.key, k -> new ArrayList<>()).add(rule);
                    }
                }
            }

            // 长模板优先：越具体的模式越先尝试，避免短模板把长消息整段吃掉。
            for (List<Rule> bucket : RULES.values()) {
                bucket.sort(Comparator.comparingInt((Rule r) -> r.length).reversed());
            }

            loaded = true;
            MeteorZh.LOG.info("Meteor-zh: chat templates loaded ({} entries, {} patterns)",
                TEMPLATES.size(), countRules());
        } catch (Throwable t) {
            MeteorZh.LOG.error("Meteor-zh: failed to load chat templates", t);
        }
    }

    private static int countRules() {
        int n = 0;
        for (List<Rule> bucket : RULES.values()) n += bucket.size();
        return n;
    }

    /**
     * 把一条已渲染的聊天消息翻成中文。
     *
     * @param message {@code ChatUtils.formatMsg} 收到的文本（可能已填好参数）
     * @return 中文消息；没收录时返回 {@code null}（调用方必须原样放行）
     */
    public static String translate(String message) {
        if (message == null || message.isEmpty() || TEMPLATES.isEmpty()) return null;

        // 聊天消息都很短；超长的一定是拼接出来的调试串，别让正则去啃。
        if (message.length() > 400) return null;

        String exact = TEMPLATES.get(message);
        if (exact != null) return exact;

        List<Rule> bucket = RULES.get(message.charAt(0));
        if (bucket == null) return null;

        for (Rule rule : bucket) {
            Matcher m = rule.pattern.matcher(message);
            if (!m.matches()) continue;

            try {
                return m.replaceFirst(rule.replacement);
            } catch (Throwable ignored) {
                // 捕获组对不上（理论上不会，构建期已校验）就当没收录。
                return null;
            }
        }

        return null;
    }

    /** 一条「英文模板 → 中文模板」的正则规则。 */
    private static final class Rule {
        final char key;
        final int length;
        final Pattern pattern;
        final String replacement;

        Rule(char key, int length, Pattern pattern, String replacement) {
            this.key = key;
            this.length = length;
            this.pattern = pattern;
            this.replacement = replacement;
        }

        /**
         * 把英文模板编译成整串锚定的正则，并把中文模板里的格式符换成 {@code $n}。
         *
         * @return 没有格式符时返回 {@code null}（这类消息走精确查表就够了）
         */
        static Rule compile(String en, String zh) {
            StringBuilder re = new StringBuilder("\\A");
            int groups = 0;

            int i = 0;
            while (i < en.length()) {
                char c = en.charAt(i);
                if (c == '%' && i + 1 < en.length()) {
                    int end = specEnd(en, i);
                    if (end > i) {
                        String tail = en.substring(i, end);
                        char conv = tail.charAt(tail.length() - 1);
                        String group = groupFor(conv);
                        if (group == null) {
                            // %n / %% 之类不占参数位，直接当字面量。
                            re.append(Pattern.quote(tail));
                        } else {
                            groups++;
                            re.append(group);
                        }
                        i = end;
                        continue;
                    }
                }

                // 逐个字符转义，遇到成段的普通字符一次性 quote 会更省事，
                // 但转义后长度可控，这里直接精确控制。
                re.append(Pattern.quote(String.valueOf(c)));
                i++;
            }
            re.append("\\z");

            if (groups == 0) return null;

            return new Rule(en.charAt(0), en.length(), Pattern.compile(re.toString()), toReplacement(zh));
        }

        /** 返回 '%' 之后到转换字符（含）的结束下标，不是格式符则返回 -1。 */
        private static int specEnd(String s, int start) {
            int i = start + 1;
            // 允许 [-#+ 0,(]* 与宽度、精度
            while (i < s.length() && "-+# 0,(".indexOf(s.charAt(i)) >= 0) i++;
            while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            if (i < s.length() && s.charAt(i) == '.') {
                i++;
                while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            }
            if (i >= s.length()) return -1;

            char conv = s.charAt(i);
            if ("sdfxXeEgGcbnB%".indexOf(conv) < 0) return -1;
            return i + 1;
        }

        private static String groupFor(char conv) {
            switch (conv) {
                case 's':
                case 'S':
                    return "(.*?)";
                case 'd':
                case 'o':
                    return "(-?\\d+)";
                case 'x':
                case 'X':
                    return "([0-9a-fA-F]+)";
                case 'f':
                case 'e':
                case 'E':
                case 'g':
                case 'G':
                    return "(-?\\d+(?:\\.\\d+)?)";
                case 'b':
                case 'B':
                    return "(true|false)";
                case 'c':
                    return "(.)";
                default:
                    return null;   // %n、%% 不占参数位
            }
        }

        /** 中文模板里的第 n 个格式符替换成 {@code $n}，字面量里的 $ 和 \ 要转义。 */
        private static String toReplacement(String zh) {
            StringBuilder out = new StringBuilder();
            int group = 0;

            int i = 0;
            while (i < zh.length()) {
                char c = zh.charAt(i);
                if (c == '%' && i + 1 < zh.length()) {
                    int end = specEnd(zh, i);
                    if (end > i) {
                        String tail = zh.substring(i, end);
                        char conv = tail.charAt(tail.length() - 1);
                        if (groupFor(conv) != null) {
                            group++;
                            out.append('$').append(group);
                        } else {
                            out.append(tail);
                        }
                        i = end;
                        continue;
                    }
                }

                if (c == '$' || c == '\\') out.append('\\');
                out.append(c);
                i++;
            }

            return out.toString();
        }
    }
}
