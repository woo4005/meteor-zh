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

import meteordevelopment.meteorclient.renderer.text.VanillaTextRenderer;
import meteordevelopment.meteorclient.systems.config.Config;

/**
 * Switches Meteor's GUI over to Minecraft's own font so Chinese can actually be drawn.
 *
 * <h2>Why this is necessary</h2>
 *
 * <p>Meteor does not draw widget text with Minecraft's font. It bakes the active
 * font file into its own texture atlas once and then draws quads from that atlas.
 * The bakery only packs six Unicode blocks, hard-coded in
 * {@code meteordevelopment.meteorclient.renderer.text.Font}:
 *
 * <pre>
 *   Basic Latin      32 - 126
 *   Latin-1         160 - 255
 *   Latin Ext-A     256 - 383
 *   Greek           880 - 1023
 *   Cyrillic       1024 - 1279
 *   Infinity          8734
 * </pre>
 *
 * <p>There is no CJK block at all, so no matter which font file is installed or
 * selected in {@code Settings > Visual > Font}, the atlas never contains a single
 * Chinese glyph. Worse, {@code Font#getWidth} substitutes {@code charMap.get(32)}
 * (a space) for every missing glyph and {@code Font#render} skips the quad
 * entirely — which is exactly the failure mode users hit: the layout keeps the
 * space for each character but every Chinese character draws as nothing, so
 * buttons look blank while numbers and untranslated English still show.
 *
 * <h2>The fix</h2>
 *
 * <p>Meteor ships two text renderers and switches between them with a single
 * config flag:
 *
 * <pre>
 *   TextRenderer.get() = Config.get().customFont.get()
 *       ? Fonts.RENDERER             // the baked atlas, Latin only
 *       : VanillaTextRenderer.INSTANCE;  // Minecraft's font, full CJK support
 * </pre>
 *
 * <p>So turning {@code customFont} off is the supported, upstream way to get
 * Chinese on screen — the same thing a user would do by hand in the settings
 * menu. Doing it programmatically means a fresh profile is translated correctly
 * on the very first launch instead of showing a wall of empty buttons.
 *
 * <p>{@code scaleIndividually} is forced on as well: the vanilla renderer then
 * advances every code point by its own scaled width, which is what Meteor's
 * widget code assumes when it measures a label. Without it, double-width CJK
 * characters overrun their slot and neighbouring widgets overlap.
 *
 * <p>The setting is persisted by Meteor, so on later launches the flag is
 * already off and this class is a no-op.
 */
public final class FontFixer {
    /** Bumped only once so a normal session logs the switch a single time. */
    private static Boolean logged;

    private FontFixer() {}

    /**
     * Turns Meteor's custom font renderer off and returns whether this call
     * changed anything.
     *
     * <p>Never throws: a font problem must not take the game down, and the
     * translation itself keeps working either way.
     */
    public static boolean ensureVanillaRenderer() {
        try {
            Config cfg = Config.get();
            if (cfg == null || cfg.customFont == null) return false;

            boolean wasCustom = cfg.customFont.get();
            if (wasCustom) cfg.customFont.set(false);

            // Public field on the singleton; Meteor's own layout code expects it on
            // whenever the vanilla renderer is in use.
            VanillaTextRenderer.INSTANCE.scaleIndividually = true;

            if (wasCustom || logged == null) {
                logged = Boolean.TRUE;
                if (wasCustom) {
                    MeteorZh.LOG.info(
                        "Meteor-zh: turned Meteor's custom font off and switched the GUI to "
                            + "Minecraft's font — the baked atlas only packs Latin/Greek/Cyrillic, "
                            + "so Chinese cannot render with it");
                } else {
                    MeteorZh.LOG.info(
                        "Meteor-zh: GUI already uses Minecraft's font (custom font off)");
                }
            }
            return wasCustom;
        } catch (Throwable t) {
            if (logged == null) {
                logged = Boolean.FALSE;
                MeteorZh.LOG.warn(
                    "Meteor-zh: could not switch to the vanilla font renderer ({}); "
                        + "Chinese may render as blank — turn off Settings > Visual > Custom Font manually",
                    t.toString());
            }
            return false;
        }
    }

    /** @return whether the GUI currently draws through Minecraft's font. */
    public static boolean usingVanilla() {
        try {
            Config cfg = Config.get();
            return cfg != null && cfg.customFont != null && !cfg.customFont.get();
        } catch (Throwable t) {
            return false;
        }
    }

    /** @return a short label for logs and the {@code .zh info} command. */
    public static String describe() {
        return usingVanilla() ? "vanilla (Minecraft font, CJK capable)" : "custom (atlas, Latin only)";
    }
}
