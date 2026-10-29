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

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Type;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Lexical fallback translator.
 *
 * The bundled dictionary covers every module/setting of Meteor Client plus a few
 * addons that were harvested up front. Any addon installed later (or one that
 * ships English identifiers we never saw) still needs a readable name, so this
 * class splits the kebab-case identifier into words and translates each word with
 * the bundled word table (assets/meteorzh/lang/words.json). That covers the vast
 * majority of Meteor addon identifiers because the ecosystem reuses the same
 * vocabulary (render, color, range, delay, elytra, ...).
 *
 * Words missing from the table are left in Latin so nothing is ever mangled, and
 * a name with no recognised word at all returns null so the caller keeps the
 * original text (this is what protects addons that already ship Chinese names).
 */
public final class WordTranslator {
    private static final Map<String, String> WORDS = new HashMap<>();

    /** Function words that carry no meaning in a Chinese compound and would only make it longer. */
    private static final Set<String> SKIP = new HashSet<>(Set.of(
        "to", "in", "of", "for", "and", "or", "the", "a", "an",
        "on", "at", "by", "with", "from", "is", "are", "as"));

    private static boolean loaded;

    private WordTranslator() {}

    public static boolean isLoaded() {
        return loaded;
    }

    public static int size() {
        return WORDS.size();
    }

    /** Drops the cached table so the next {@link #load()} re-reads the jar resource. */
    public static void reset() {
        WORDS.clear();
        loaded = false;
    }

    public static void load() {
        if (loaded) return;

        try (InputStream in = WordTranslator.class.getResourceAsStream("/assets/meteorzh/lang/words.json")) {
            if (in == null) {
                MeteorZh.LOG.warn("Meteor-zh: word table missing, lexical fallback disabled");
                return;
            }

            Type type = new TypeToken<Map<String, String>>() {}.getType();
            Map<String, String> table = new Gson()
                .fromJson(new InputStreamReader(in, StandardCharsets.UTF_8), type);

            if (table != null) WORDS.putAll(table);

            loaded = !WORDS.isEmpty();
            MeteorZh.LOG.info("Meteor-zh: word table loaded ({} words)", WORDS.size());
        } catch (Throwable t) {
            MeteorZh.LOG.error("Meteor-zh: failed to load word table", t);
        }
    }

    /**
     * Best effort translation of a kebab/snake/camel case identifier.
     *
     * <p>Gives up (returns null) when the identifier is mostly made of words we do not
     * know: splicing Chinese fragments together with leftover Latin produces things
     * like「无 Such 模块 XYZ」, which is worse than leaving the original English.
     * Unknown words are allowed only up to half as many as recognised ones.
     *
     * @return Chinese text, or null when nothing (or too little) was recognised
     */
    public static String translate(String name) {
        if (name == null || name.isEmpty() || WORDS.isEmpty()) return null;

        String[] tokens = split(name);
        if (tokens.length == 0) return null;

        StringBuilder sb = new StringBuilder();
        int known = 0;
        int unknown = 0;

        for (String token : tokens) {
            if (SKIP.contains(token)) continue;

            String zh = WORDS.get(token);
            if (zh != null) {
                sb.append(zh);
                known++;
            } else if (isDigits(token)) {
                sb.append(token);
            } else {
                unknown++;
                sb.append(token.length() <= 3
                    ? token.toUpperCase(Locale.ROOT)
                    : Character.toUpperCase(token.charAt(0)) + token.substring(1));
            }
        }

        if (known == 0 || sb.length() == 0) return null;
        if (unknown > known / 2) return null;

        return joinCn(sb.toString());
    }

    private static String[] split(String name) {
        // camelCase / PascalCase -> separated, then split on the usual delimiters
        String spaced = name.replaceAll("([a-z0-9])([A-Z])", "$1-$2");
        return spaced.toLowerCase(Locale.ROOT).split("[-_\\s.]+");
    }

    private static boolean isDigits(String s) {
        for (int i = 0; i < s.length(); i++) {
            if (!Character.isDigit(s.charAt(i))) return false;
        }
        return !s.isEmpty();
    }

    /** Inserts a space between Chinese and Latin/digit runs so mixed names stay readable. */
    private static String joinCn(String s) {
        s = s.replaceAll("([\\u4e00-\\u9fff])([A-Za-z0-9])", "$1 $2");
        s = s.replaceAll("([A-Za-z0-9])([\\u4e00-\\u9fff])", "$1 $2");
        return s.trim();
    }
}
