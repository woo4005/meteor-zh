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

import meteordevelopment.meteorclient.renderer.Fonts;
import meteordevelopment.meteorclient.renderer.text.FontFace;
import meteordevelopment.meteorclient.renderer.text.FontFamily;
import meteordevelopment.meteorclient.renderer.text.FontInfo;
import meteordevelopment.meteorclient.systems.config.Config;

/**
 * Makes sure the GUI font can actually draw Chinese.
 *
 * <p>Meteor does not use Minecraft's font. Every widget string is drawn with its
 * own renderer into a pre-baked texture atlas built from a single font file, and
 * the four bundled faces (JetBrains Mono, Comfortaa, Tw Cen MT, Pixelation) are
 * Latin-only — they contain no CJK glyphs at all. A character that is missing
 * from that atlas simply produces no quad, so translated text renders as
 * <em>nothing</em> while numbers and untranslated English keep showing up. The
 * GUI then looks like a pile of empty buttons.
 *
 * <p>Meteor itself already ships the cure: Settings → Visual → Font lets you pick
 * any font installed on the system, and almost every Windows install has a CJK
 * face (DengXian, Microsoft YaHei, SimHei...). The catch is that this is an
 * opt-in setting, so a fresh Minecraft install — a brand new 26.1 profile, for
 * example — starts on Comfortaa and Chinese silently disappears.
 *
 * <p>This class closes that gap: it measures a probe string with the active
 * renderer, and if the width comes back as zero (no glyphs) it switches Meteor
 * over to the first system font that can draw Chinese, persisting the choice to
 * {@code Config} so the next launch starts correct.
 *
 * <p>Nothing happens when the user already runs a Chinese-capable font, so the
 * 1.21.11 users who picked DengXian by hand are untouched.
 */
public final class FontFixer {
    /**
     * System families to try, best-looking first. Windows ships DengXian and
     * Microsoft YaHei; the rest cover macOS and Linux desktops.
     */
    private static final String[] PREFERRED = {
        "DengXian",
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Source Han Sans SC",
        "PingFang SC",
        "Hiragino Sans GB",
        "WenQuanYi Micro Hei",
        "Microsoft JhengHei",
    };

    /** Characters that exist in every CJK face and in none of the bundled Latin ones. */
    private static final String PROBE = "\u4e2d\u6587\u6e05\u5355";

    private static Boolean lastState;

    private FontFixer() {}

    /**
     * Checks the current renderer and, if it cannot draw Chinese, swaps in a
     * system font.
     *
     * @return {@code true} when a font switch was performed on this call.
     */
    public static boolean ensureCjkFont() {
        try {
            if (supportsChinese()) {
                lastState = Boolean.TRUE;
                return false;
            }

            FontFamily family = pickFamily();
            if (family == null) {
                if (lastState == null) {
                    lastState = Boolean.FALSE;
                    MeteorZh.LOG.warn(
                        "Meteor-zh: no CJK system font found — pick one manually in "
                            + "Settings > Visual > Font, otherwise Chinese will not render");
                }
                return false;
            }

            FontFace face = family.get(FontInfo.Type.Regular);
            if (face == null) return false;

            // Setting.set() runs the setting's own callback, which is what Meteor
            // normally uses to rebuild the renderer; Fonts.load() is idempotent and
            // only rebuilds when the face actually differs, so call it explicitly
            // too in case this Meteor build does not wire the callback.
            Config.get().font.set(face);
            Fonts.load(face);

            lastState = Boolean.TRUE;
            MeteorZh.LOG.info("Meteor-zh: switched GUI font to \"{}\" so Chinese can render", family.getName());
            return true;
        } catch (Throwable t) {
            // Never let a font problem take the game down; the translation itself is fine.
            if (lastState == null) {
                lastState = Boolean.FALSE;
                MeteorZh.LOG.warn("Meteor-zh: font check failed ({})", t.toString());
            }
            return false;
        }
    }

    /** @return whether the active GUI font can draw Chinese. */
    public static boolean supportsChinese() {
        try {
            if (Fonts.RENDERER == null) return false;
            // Missing glyphs contribute nothing to the advance width, so a face
            // without CJK measures the whole probe as 0.
            return Fonts.RENDERER.getWidth(PROBE) > 0.5;
        } catch (Throwable t) {
            return false;
        }
    }

    /** @return the family name currently in use, for diagnostics. */
    public static String currentFamily() {
        try {
            if (Fonts.RENDERER == null || Fonts.RENDERER.fontFace == null) return "?";
            return Fonts.RENDERER.fontFace.info.family();
        } catch (Throwable t) {
            return "?";
        }
    }

    private static FontFamily pickFamily() {
        // Fonts.FONT_FAMILIES only exists after Meteor's resource reload, so a very
        // early tick can legitimately see an empty list — the caller retries.
        for (String name : PREFERRED) {
            FontFamily family = Fonts.getFamily(name);
            if (family != null && family.hasType(FontInfo.Type.Regular)) return family;
        }
        return null;
    }
}
