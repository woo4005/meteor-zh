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

import meteordevelopment.meteorclient.settings.Setting;
import meteordevelopment.meteorclient.settings.SettingGroup;
import meteordevelopment.meteorclient.gui.tabs.Tab;
import meteordevelopment.meteorclient.gui.tabs.Tabs;
import meteordevelopment.meteorclient.systems.hud.Hud;
import meteordevelopment.meteorclient.systems.hud.HudElementInfo;
import meteordevelopment.meteorclient.systems.modules.Category;
import meteordevelopment.meteorclient.systems.modules.Module;
import meteordevelopment.meteorclient.systems.modules.Modules;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Rewrites the display strings of already-instantiated Meteor objects through
 * reflection.
 *
 * Only fields that do not take part in NBT serialisation are touched, so saved
 * configs stay compatible:
 *   - Module.title / Module.description   (serialised by `name`, safe)
 *   - Setting.title / Setting.description (serialised by `name`, safe)
 *   - Category.name                       (never serialised, safe)
 *   - HudElementInfo.title / description  (HUD saved by `name`, safe)
 *   - HudGroup.title                      (record component, never serialised, safe)
 *
 * SettingGroup.name is deliberately NOT modified: Settings#fromTag looks groups up
 * by name, so rewriting it would orphan every saved group. Group headings are
 * translated in the render layer instead (see GuiRendererMixin).
 */
public final class Translator {
    private static Field fModuleTitle;
    private static Field fModuleDesc;
    private static Field fSettingTitle;
    private static Field fSettingDesc;
    private static Field fCategoryName;
    private static Field fHudTitle;
    private static Field fHudDesc;

    /** Fields that rejected a reflective write; warned once each so logs stay readable. */
    private static final Set<Field> REPORTED = new HashSet<>();

    /** Fields that no longer exist in the running Meteor build. */
    private static final Set<String> MISSING = new HashSet<>();
    private static Field fTabName;

    private Translator() {}

    public static void init() {
        fModuleTitle = field(Module.class, "title");
        fModuleDesc = field(Module.class, "description");
        fSettingTitle = field(Setting.class, "title");
        fSettingDesc = field(Setting.class, "description");
        fCategoryName = field(Category.class, "name");
        fHudTitle = field(HudElementInfo.class, "title");
        fHudDesc = field(HudElementInfo.class, "description");
        fTabName = field(Tab.class, "name");
    }

    /** @return number of strings that were rewritten (for the .zh command report). */
    public static int translateAll() {
        if (!ZhDict.isLoaded()) ZhDict.load();

        int count = 0;

        Modules modules = Modules.get();
        if (modules != null) {
            count += translateModules(modules);
            count += translateCategories();
        }

        count += translateTabs();
        count += translateHud();

        MeteorZh.LOG.info("Meteor-zh: translated {} display strings", count);
        return count;
    }

    private static int translateModules(Modules modules) {
        int count = 0;

        Collection<Module> all = modules.getAll();
        if (all == null) return 0;

        List<Module> snapshot = new ArrayList<>(all);
        for (Module module : snapshot) {
            if (replace(fModuleTitle, module, ZhDict.moduleTitle(module.name, module.title))) count++;
            if (replace(fModuleDesc, module, ZhDict.moduleDesc(module.name, module.description))) count++;

            for (SettingGroup group : module.settings.groups) {
                for (Setting<?> setting : group) {
                    if (replace(fSettingTitle, setting, ZhDict.settingTitle(setting.name, setting.title))) count++;
                    if (replace(fSettingDesc, setting, ZhDict.settingDesc(setting.name, setting.description))) count++;
                }
            }
        }

        return count;
    }

    private static int translateCategories() {
        int count = 0;
        Iterable<Category> categories = Modules.loopCategories();
        if (categories == null) return 0;

        for (Category category : categories) {
            String original = category.name;
            if (original == null || original.isEmpty()) continue;

            String translated = ZhDict.groupTitle(original);
            if (translated != null && !translated.equals(original)) {
                if (replace(fCategoryName, category, translated)) count++;
            }
        }

        return count;
    }

    private static int translateTabs() {
        int count = 0;

        List<Tab> tabs = Tabs.get();
        if (tabs == null) return 0;

        for (Tab tab : new ArrayList<>(tabs)) {
            String original = tab.name;
            if (original == null || original.isEmpty()) continue;

            String translated = ZhDict.groupTitle(original);
            if (translated != null && !translated.equals(original)) {
                if (replace(fTabName, tab, translated)) count++;
            }
        }

        return count;
    }

    private static int translateHud() {
        int count = 0;

        Hud hud = Hud.get();
        if (hud == null || hud.infos == null) return 0;

        for (HudElementInfo<?> info : hud.infos.values()) {
            if (replace(fHudTitle, info, ZhDict.moduleTitle(info.name, info.title))) count++;
            if (replace(fHudDesc, info, ZhDict.moduleDesc(info.name, info.description))) count++;

            // HudGroup is a record and the JVM refuses reflective writes to record
            // components, so its title is translated at render time instead: the
            // GuiRenderer mixin routes every drawn string through ZhDict.ui(), which
            // falls back to the group table.
        }

        return count;
    }

    // ------------------------------------------------------------------ helpers

    private static Field field(Class<?> owner, String name) {
        try {
            Field f = owner.getDeclaredField(name);
            f.setAccessible(true);
            return f;
        } catch (Throwable t) {
            MISSING.add(owner.getSimpleName() + "." + name);
            MeteorZh.LOG.warn("Meteor-zh: field {}.{} unavailable ({})", owner.getSimpleName(), name, t.toString());
            return null;
        }
    }

    /**
     * @return the fields this build could not resolve, e.g.
     *         {@code ["HudElementInfo.title"]}. Empty on a healthy Meteor.
     *
     * <p>Exposed so the offline verification can actually fail when a Meteor
     * update renames something — a warning in the log is easy to miss.
     */
    public static java.util.List<String> missingFields() {
        java.util.List<String> out = new ArrayList<>(MISSING);
        out.sort(null);
        return out;
    }

    /** @return true when the value actually changed. */
    private static boolean replace(Field field, Object target, String value) {
        if (field == null || target == null || value == null) return false;

        try {
            Object current = field.get(target);
            if (value.equals(current)) return false;
            field.set(target, value);
            return true;
        } catch (Throwable t) {
            // Record components and other truly immutable slots land here. Report once
            // per field so a new Meteor version cannot silently disable a whole table.
            if (REPORTED.add(field)) {
                MeteorZh.LOG.warn(
                    "Meteor-zh: cannot rewrite {}.{} — {} (this string stays English)",
                    field.getDeclaringClass().getSimpleName(), field.getName(), t.toString());
            }
            return false;
        }
    }
}
