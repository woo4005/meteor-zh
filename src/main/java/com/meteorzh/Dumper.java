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

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import meteordevelopment.meteorclient.settings.Setting;
import meteordevelopment.meteorclient.settings.SettingGroup;
import meteordevelopment.meteorclient.systems.modules.Module;
import meteordevelopment.meteorclient.systems.modules.Modules;
import net.fabricmc.loader.api.FabricLoader;

/**
 * {@code .zh dump} —— 把当前所有模块与设置（连同已经翻好的中文）导出成 JSON。
 *
 * <p>这个功能借鉴自 Nippaku-Zanmu/meteor-translation-addon 的 {@code JsonDump}：
 * 词典是离线从源码和 jar 常量池里扒出来的，玩家装了别的 addon 之后，
 * 那些 addon 的模块名根本不在我的源码里，只能靠词法兜底拼。让玩家自己
 * 导出一份「我这儿实际装了什么」的清单，补词条时就不用猜了。
 *
 * <p>导出的字段刻意包含 {@code name}（翻译用的 key，kebab-case 英文标识符）
 * 与 {@code translated} 标记——前者是我查表的键，后者是「有没有命中词典」。
 * 这样把文件发给我，我就能直接看出哪些标识符还缺中文。
 *
 * <p>注意：模块的 {@code title}/{@code description} 已经被 Translator 就地改写成中文了，
 * 所以这里拿到的是**译文**而不是英文原文；英文原文请看 {@code name}。
 */
public final class Dumper {
    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");
    private static final DateTimeFormatter NOW = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private Dumper() {
    }

    /** 执行导出，返回写出的文件路径（失败返回 null）。 */
    public static Path dump() {
        JsonObject root = new JsonObject();
        root.addProperty("generatedAt", LocalDateTime.now().format(NOW));
        root.addProperty("plugin", "meteor-zh " + UpdateChecker.currentVersion());
        root.addProperty("minecraft", UpdateChecker.mcVersion());
        root.addProperty("dictionary", ZhDict.summaryText());
        root.addProperty("wordTable", WordTranslator.size() + " words");
        root.addProperty("chatTemplates", ChatDict.size() + " templates");
        root.addProperty("note", "name 是查表用的英文标识符（kebab-case）；title/description 是当前显示文本（多为中文）。translated=false 表示没命中词典，建议补词条。");

        JsonArray modules = new JsonArray();
        JsonArray settings = new JsonArray();
        int untranslated = 0;

        List<Module> all = new ArrayList<>(Modules.get().getAll());
        all.sort(Comparator.comparing(m -> (m.category == null ? "" : m.category.name) + "/" + m.name));

        for (Module module : all) {
            boolean inDict = ZhDict.hasModuleTitle(module.name);
            if (!inDict) untranslated++;

            JsonObject mo = new JsonObject();
            mo.addProperty("addon", module.addon == null ? "meteor-client" : module.addon.name);
            mo.addProperty("category", module.category == null ? "" : module.category.name);
            mo.addProperty("name", module.name);
            mo.addProperty("title", safe(module.title));
            mo.addProperty("description", safe(module.description));
            mo.addProperty("translated", inDict);
            mo.addProperty("inDictionary", inDict);
            modules.add(mo);

            for (SettingGroup group : module.settings.groups) {
                for (Setting<?> setting : group) {
                    JsonObject so = new JsonObject();
                    so.addProperty("module", module.name);
                    so.addProperty("group", safe(group.name));
                    so.addProperty("name", setting.name);
                    so.addProperty("title", safe(setting.title));
                    so.addProperty("description", safe(setting.description));
                    so.addProperty("type", setting.getClass().getSimpleName());
                    so.addProperty("inDictionary", ZhDict.hasSettingTitle(setting.name));
                    settings.add(so);
                }
            }
        }

        root.addProperty("moduleCount", modules.size());
        root.addProperty("settingCount", settings.size());
        root.addProperty("untranslatedModules", untranslated);
        root.add("modules", modules);
        root.add("settings", settings);

        try {
            Path dir = FabricLoader.getInstance().getGameDir().resolve("meteor-zh");
            Files.createDirectories(dir);
            Path out = dir.resolve("dump-" + UpdateChecker.currentVersion() + "-"
                + LocalDateTime.now().format(STAMP) + ".json");
            try (Writer w = Files.newBufferedWriter(out, StandardCharsets.UTF_8)) {
                new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(root, w);
            }
            return out;
        } catch (IOException | RuntimeException e) {
            MeteorZh.LOG.error("导出词典模板失败", e);
            return null;
        }
    }

    private static String safe(String s) {
        return s == null ? "" : s;
    }
}
