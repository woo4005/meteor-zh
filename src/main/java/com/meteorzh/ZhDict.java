package com.meteorzh;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * Loads the bundled translation dictionary and answers lookup queries.
 *
 * Dictionary layout (assets/meteorzh/lang/zh.json):
 * {
 *   "modules":      { "<module-name>":  { "title": "...", "desc": "..." } },
 *   "settings":     { "<setting-name>": { "title": "...", "desc": "..." } },
 *   "groups":       { "<english-group>": "中文" },
 *   "ui":           { "<english text>": "中文" },
 *   "descriptions": { "<english description>": "中文" }
 * }
 *
 * "descriptions" is the fallback used by third party addons whose module/setting
 * identifiers are unknown but whose description strings were harvested from the
 * addon jars.
 *
 * Every lookup falls back to the caller supplied original text so unknown entries
 * (e.g. addons that are already Chinese) are shown unchanged.
 */
public final class ZhDict {
    private static final Map<String, String> MODULE_TITLES = new HashMap<>();
    private static final Map<String, String> MODULE_DESCS = new HashMap<>();
    private static final Map<String, String> SETTING_TITLES = new HashMap<>();
    private static final Map<String, String> SETTING_DESCS = new HashMap<>();
    private static final Map<String, String> GROUPS = new HashMap<>();
    private static final Map<String, String> UI = new HashMap<>();
    private static final Map<String, String> DESCRIPTIONS = new HashMap<>();

    private static boolean loaded;

    private ZhDict() {}

    public static boolean isLoaded() {
        return loaded;
    }

    public static int size() {
        return MODULE_TITLES.size() + SETTING_TITLES.size() + GROUPS.size() + UI.size() + DESCRIPTIONS.size();
    }

    public static void load() {
        if (loaded) return;

        try (InputStream in = ZhDict.class.getResourceAsStream("/assets/meteorzh/lang/zh.json")) {
            if (in == null) {
                MeteorZh.LOG.error("Meteor-zh: language file missing from jar");
                return;
            }

            JsonObject root = JsonParser.parseReader(
                new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();

            readModuleMap(root, "modules");
            readModuleMap(root, "settings");
            readFlat(root, "groups", GROUPS);
            readFlat(root, "ui", UI);
            readFlat(root, "descriptions", DESCRIPTIONS);

            loaded = true;
            MeteorZh.LOG.info(
                "Meteor-zh: dictionary loaded ({} modules, {} settings, {} groups, {} ui, {} descriptions)",
                MODULE_TITLES.size(), SETTING_TITLES.size(), GROUPS.size(), UI.size(), DESCRIPTIONS.size());

            // Names we have no entry for are translated word-by-word at lookup time.
            WordTranslator.load();
        } catch (Throwable t) {
            MeteorZh.LOG.error("Meteor-zh: failed to load dictionary", t);
        }
    }

    private static void readModuleMap(JsonObject root, String key) {
        JsonElement el = root.get(key);
        if (el == null || !el.isJsonObject()) return;

        Map<String, String> titles = key.equals("modules") ? MODULE_TITLES : SETTING_TITLES;
        Map<String, String> descs = key.equals("modules") ? MODULE_DESCS : SETTING_DESCS;

        for (Map.Entry<String, JsonElement> e : el.getAsJsonObject().entrySet()) {
            if (!e.getValue().isJsonObject()) continue;
            JsonObject obj = e.getValue().getAsJsonObject();

            String title = optString(obj, "title");
            String desc = optString(obj, "desc");

            if (title != null && !title.isEmpty()) titles.put(e.getKey(), title);
            if (desc != null && !desc.isEmpty()) descs.put(e.getKey(), desc);
        }
    }

    private static void readFlat(JsonObject root, String key, Map<String, String> target) {
        JsonElement el = root.get(key);
        if (el == null || !el.isJsonObject()) return;

        for (Map.Entry<String, JsonElement> e : el.getAsJsonObject().entrySet()) {
            if (!e.getValue().isJsonPrimitive()) continue;
            String v = e.getValue().getAsString();
            if (v != null && !v.isEmpty()) target.put(e.getKey(), v);
        }
    }

    private static String optString(JsonObject obj, String key) {
        JsonElement el = obj.get(key);
        return el != null && el.isJsonPrimitive() ? el.getAsString() : null;
    }

    // ------------------------------------------------------------------ lookups

    /**
     * Module and setting identifiers live in separate tables for readability, but
     * in practice both are plain kebab-case names and a few addons are ambiguous
     * about which table an identifier belongs to, so each lookup cross-checks the
     * other table before falling back to the word table (unknown addons) and
     * finally to the original text.
     */
    public static String moduleTitle(String name, String fallback) {
        String v = MODULE_TITLES.get(name);
        if (v == null) v = SETTING_TITLES.get(name);
        if (v == null) v = WordTranslator.translate(name);
        return v != null ? v : fallback;
    }

    /** @param original the untranslated description, also used as a plain-text key. */
    public static String moduleDesc(String name, String original) {
        String v = MODULE_DESCS.get(name);
        if (v == null) v = SETTING_DESCS.get(name);
        if (v == null && original != null) v = DESCRIPTIONS.get(original);
        return v != null ? v : original;
    }

    public static String settingTitle(String name, String fallback) {
        String v = SETTING_TITLES.get(name);
        if (v == null) v = MODULE_TITLES.get(name);
        if (v == null) v = WordTranslator.translate(name);
        return v != null ? v : fallback;
    }

    /** @param original the untranslated description, also used as a plain-text key. */
    public static String settingDesc(String name, String original) {
        String v = SETTING_DESCS.get(name);
        if (v == null) v = MODULE_DESCS.get(name);
        if (v == null && original != null) v = DESCRIPTIONS.get(original);
        return v != null ? v : original;
    }

    /** Category / setting-group / HUD-group display name. */
    public static String groupTitle(String name) {
        if (name == null) return null;
        String v = GROUPS.get(name);
        if (v != null) return v;
        v = UI.get(name);
        return v != null ? v : name;
    }

    /** Render layer replacement for hard-coded GUI strings. Never returns null. */
    public static String ui(String text) {
        if (text == null || UI.isEmpty()) return text;
        String v = UI.get(text);
        return v != null ? v : text;
    }
}
